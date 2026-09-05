"""Strict audit boundary tests; no external source authentication implied."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
import subprocess
import sys
import unittest

from tests.audit_fixtures import DIGEST, clock, event, evidence


FAMILIES = ("REQUEST", "REJECTION", "ASSESSMENT", "DECISION", "CONTEXT_CHALLENGE", "CONTEXT_RESPONSE",
            "TECHNICIAN_ACTION", "EXECUTION_ATTEMPT", "CONTROLLER_RECEIPT", "EXECUTION_RESULT",
            "OBSERVED_STATE", "AUTHORITY_TRANSITION", "CACHE_ACTIVATION", "RECONCILIATION_FINDING", "RECORDER_FAILURE")


class ContractTests(unittest.TestCase):
    def setUp(self):
        try:
            self.contract = importlib.import_module("dcamr.audit.event_contract")
        except ModuleNotFoundError:
            self.fail("audit event contract must be implemented")

    def invalid(self, value):
        with self.assertRaises(self.contract.LedgerInputError):
            self.contract.validate_input(value)

    def complete(self):
        result = event()
        result.update(schema_version="alice-audit-event-v1", canonicalization_version="alice-json-v1",
                      ledger_id="ledger-1", node_id="node-1", sequence=1, time=clock(), previous_hash="0" * 64,
                      outbox_id="event-1", initial_state="LOCAL")
        result["event_hash"] = self.contract.event_hash(result)
        return result

    def test_canonical_utf8_sorted_keys_and_no_normalization(self):
        self.assertEqual(self.contract.canonical_bytes({"b": 2, "a": "é"}), b'{"a":"\xc3\xa9","b":2}')
        self.assertNotEqual(self.contract.canonical_bytes("é"), self.contract.canonical_bytes("e\u0301"))
        self.assertEqual(self.contract.canonical_bytes([2, 1]), b"[2,1]")

    def test_rejects_non_json_float_large_integer_and_non_ascii_key(self):
        for value in ({"score": 0.1}, {"a": float("nan")}, 2**63, -(2**63)-1,
                      {"é": 1}, {1: "x"}, (1, 2), b"data", "\ud800"):
            with self.subTest(value=type(value)), self.assertRaises(self.contract.LedgerInputError):
                self.contract.canonical_bytes(value)

    def test_bounds_depth_strings_arrays_and_total_bytes(self):
        deep = None
        for _ in range(18):
            deep = [deep]
        for value in (deep, [0] * 65, "a" * 4097, {str(i): "a" * 4000 for i in range(5)}):
            with self.assertRaises(self.contract.LedgerInputError):
                self.contract.canonical_bytes(value)

    def test_expanded_shared_tree_is_rejected_without_unbounded_traversal(self):
        script = """
from dcamr.audit.event_contract import canonical_bytes, LedgerInputError
value = 0
for _ in range(6):
    value = [value] * 64
try:
    canonical_bytes(value)
except LedgerInputError:
    print('REJECTED')
"""
        try:
            result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            self.fail("oversized shared trees must be rejected before traversing their expanded payload")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "REJECTED")

    def test_parse_rejects_duplicate_nested_keys_unicode_numbers_and_size(self):
        for value in (b'{"a":{"b":1,"b":2}}', b'"\xff"', b'"\\ud800"', b"0.1", b"NaN",
                      b"1e0", b" " * 16385, b'{"a":1} trailing'):
            with self.assertRaises(self.contract.LedgerInputError):
                self.contract.parse_json(value)
        self.assertEqual(self.contract.parse_json(b'{"b":2,"a":1}'), {"a": 1, "b": 2})

    def test_all_event_families_have_valid_strict_inputs(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                value = event(event_type=family)
                self.contract.validate_input(value)
                value["detail"]["payload"] = "raw-prompt"
                self.invalid(value)

    def test_unknown_fields_and_type_are_rejected(self):
        for group in (None, "attribution", "authority", "provenance", "correlation"):
            value = event()
            (value if group is None else value[group])["secret"] = "password"
            self.invalid(value)
        value = event()
        value["event_type"] = "OTHER"
        self.invalid(value)

    def test_identifiers_and_digests_cannot_hide_trailing_newlines(self):
        for group, key in ((None, "event_id"), ("correlation", "request_sha256")):
            value = event()
            target = value if group is None else value[group]
            target[key] += "\n"
            self.invalid(value)

    def test_scoped_and_actor_identifiers_allow_slash_and_at_sign(self):
        value = event("site-a/event@recorder")
        value["attribution"]["actor_id"] = "service/recorder@site-a"
        self.contract.validate_input(value)

    def test_resolved_attribution_requires_known_actor_kind_and_identity(self):
        for change in ({"actor_kind": "UNKNOWN"}, {"actor_id": None}):
            value = event()
            value["attribution"].update(resolution="RESOLVED", **change)
            self.invalid(value)
        value = event()
        value["attribution"]["resolution"] = "RESOLVED"
        self.contract.validate_input(value)

    def test_request_binding_required_but_pre_admission_rejection_allowed(self):
        for family in FAMILIES[:1] + FAMILIES[2:10]:
            value = event(event_type=family)
            value["correlation"]["request_sha256"] = None
            self.invalid(value)
        self.contract.validate_input(event(event_type="REJECTION"))

    def test_assessment_and_execution_ids_are_required(self):
        for family, field in (("ASSESSMENT", "assessment_id"), ("DECISION", "assessment_id"),
                              ("EXECUTION_ATTEMPT", "action_id"), ("EXECUTION_RESULT", "execution_id")):
            value = event(event_type=family)
            value["correlation"][field] = None
            self.invalid(value)

    def test_missing_provenance_is_explicit_and_evidence_bounded(self):
        value = event()
        value["provenance"]["model"]["missing_reason"] = None
        self.invalid(value)
        value["provenance"]["model"] = {"id": "model-1", "sha256": DIGEST, "missing_reason": None}
        self.contract.validate_input(value)
        value["provenance"]["evidence"] = [evidence(str(i)) for i in range(17)]
        self.invalid(value)

    def test_reason_codes_sorted_unique_and_bounded(self):
        for reasons in (["Z", "A"], ["A", "A"], ["free form text"]):
            value = event()
            value["detail"]["reason_codes"] = reasons
            self.invalid(value)

    def test_authority_claim_combinations_do_not_infer_disconnected_authority(self):
        value = event()
        value["authority"]["connectivity"] = "DISCONNECTED"
        self.contract.validate_input(value)
        self.assertEqual(value["authority"]["execution_owner"], "UNKNOWN")
        value["authority"]["execution_owner"] = "ALICE"
        self.invalid(value)
        value = event(event_type="EXECUTION_ATTEMPT")
        value["authority"]["authority_interval_ref"] = None
        self.invalid(value)

    def test_observation_requires_evidence_source_quality_and_explicit_uncorrelated_reason(self):
        for field in ("source", "quality", "correlation_absence_reason", "evidence_ref"):
            value = event(event_type="OBSERVED_STATE")
            del value["detail"][field]
            self.invalid(value)
        value = event(event_type="OBSERVED_STATE")
        value["provenance"]["evidence"] = []
        self.invalid(value)

    def test_physical_measurement_is_decimal_string_with_unit_and_no_false_success(self):
        for measurement in (0.25, "NaN", "1e3", "01.2"):
            value = event(event_type="OBSERVED_STATE")
            value["detail"]["value"] = measurement
            self.invalid(value)
        value = event(event_type="OBSERVED_STATE")
        value["detail"]["value"] = None
        self.invalid(value)
        value["detail"]["quality"] = "UNAVAILABLE"
        value["detail"]["source"]["availability"] = "UNAVAILABLE"
        self.contract.validate_input(value)

    def test_correlated_observation_requires_both_action_and_execution(self):
        value = event(event_type="OBSERVED_STATE")
        value["correlation"]["action_id"] = "action-1"
        self.invalid(value)
        value["correlation"]["execution_id"] = "execution-1"
        value["detail"]["correlation_absence_reason"] = None
        self.contract.validate_input(value)

    def test_finding_parent_binding_cannot_disagree(self):
        value = event(event_type="RECONCILIATION_FINDING")
        value["correlation"]["parent_event_id"] = "other"
        self.invalid(value)

    def test_event_hash_domain_and_binding_are_checked(self):
        value = self.complete()
        encoded = json.dumps({k: v for k, v in value.items() if k != "event_hash"},
                             ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(value["event_hash"], sha256(b"alice-audit-event-v1\x00" + encoded).hexdigest())
        self.contract.validate_event(value)
        value["node_id"] = "another-node"
        with self.assertRaises(self.contract.LedgerInputError):
            self.contract.validate_event(value)

    def test_delivery_sequence_and_genesis_bindings_are_checked(self):
        for key, replacement in (("outbox_id", "other"), ("initial_state", "QUEUED"),
                                 ("sequence", 0), ("sequence", True), ("previous_hash", DIGEST)):
            value = self.complete()
            value[key] = replacement
            value["event_hash"] = self.contract.event_hash(value)
            with self.assertRaises(self.contract.LedgerInputError):
                self.contract.validate_event(value)

    def test_clock_confidence_and_utc_are_consistent(self):
        for change in ({"recorded_at": None}, {"recorded_at": "2026-09-05T20:00:00+01:00"},
                       {"monotonic_ns": -1}, {"confidence": "UNAVAILABLE"}):
            value = self.complete()
            value["time"].update(change)
            value["event_hash"] = self.contract.event_hash(value)
            with self.assertRaises(self.contract.LedgerInputError):
                self.contract.validate_event(value)
        value = self.complete()
        value["time"].update(recorded_at=None, confidence="UNAVAILABLE")
        value["event_hash"] = self.contract.event_hash(value)
        self.contract.validate_event(value)

    def test_clock_contract_can_validate_checkpoint_time_independently(self):
        self.assertTrue(hasattr(self.contract, "validate_time"), "standalone clock validator must exist")
        self.contract.validate_time(clock())
        invalid = clock()
        invalid["recorded_at"] = None
        with self.assertRaises(self.contract.LedgerInputError):
            self.contract.validate_time(invalid)

    def assessment(self, status="OK"):
        parsed = status != "INVALID_INPUT"
        return {
            "schema_version": "context-behavior-assessment-v1", "status": status,
            "result": "LOW" if status == "OK" else "UNKNOWN", "raw_score": -0.125 if status == "OK" else None,
            "score": 0.25 if status == "OK" else None, "reason_codes": ["WITHIN_TRAINING_RANGES"] if status == "OK" else ["INPUT_INVALID"],
            "phase": "PRE_ACTION", "observation_id": "observation-1" if parsed else None,
            "request_id": "request-1" if parsed else None, "input_sha256": DIGEST if parsed else None,
            "profile_sha256": DIGEST, "model_id": "model-1", "model_fingerprint": DIGEST, "calibration_sha256": DIGEST if status == "OK" else None,
            "context": {"action": "off"} if parsed else {}, "request_at_ms": 100 if parsed else None,
            "cutoff_at_ms": 100 if parsed else None, "execution_id": None, "execution_at_ms": None,
            "source_ids": ["sensor-1"] if parsed else [],
            "factors": [{"name": "signal", "unit": "unitless", "observed": 0.25, "training_min": 0.0,
                         "training_max": 1.0, "outside_training_range": False, "timing": "AT_OR_BEFORE_REQUEST",
                         "source_id": "sensor-1", "observed_at_ms": 100}] if status == "OK" else [],
        }

    def dispatch(self):
        return {"assessment_id": "assessment-1", "request_id": "request-1", "request_sha256": DIGEST,
                "input_sha256": DIGEST, "execution_id": None, "profile_sha256": DIGEST, "phase": "PRE_ACTION"}

    def projected(self, raw=None, *, dispatch=None):
        raw = self.assessment() if raw is None else raw
        dispatch = self.dispatch() if dispatch is None else dispatch
        encoded = json.dumps(raw, separators=(",", ":")).encode()
        self.assertTrue(hasattr(self.contract, "contextual_projection"), "compact contextual projection must exist")
        detail = self.contract.contextual_projection(encoded, dispatch=dispatch, evidence_ref="assessment-evidence")
        value = event(event_type="ASSESSMENT")
        value["correlation"].update({key: dispatch[key] for key in ("assessment_id", "request_id", "request_sha256", "execution_id")})
        value["detail"] = detail
        value["provenance"]["evidence"] = [evidence("assessment-evidence", sha256(encoded).hexdigest())]
        return value, encoded

    def test_contextual_projection_preserves_binding_and_original_bytes_digest_without_scores(self):
        value, encoded = self.projected()
        self.contract.validate_input(value)
        compact = value["detail"]["contextual"]
        self.assertEqual(compact["dispatch"], self.dispatch())
        self.assertEqual(compact["assessment_evidence"], {"ref": "assessment-evidence", "sha256": sha256(encoded).hexdigest()})
        self.assertEqual(compact["parsed"]["observation_id"], "observation-1")
        text = self.contract.canonical_bytes(value)
        for forbidden in (b'"score"', b'"raw_score"', b'"factors"', b'"observed"', b'"training_min"'):
            self.assertNotIn(forbidden, text)

    def test_invalid_contextual_input_retains_trusted_dispatch_when_parse_ids_absent(self):
        value, _ = self.projected(self.assessment("INVALID_INPUT"))
        self.contract.validate_input(value)
        compact = value["detail"]["contextual"]
        self.assertIsNone(compact["parsed"]["request_id"])
        self.assertEqual(compact["dispatch"]["request_id"], "request-1")
        self.assertEqual(compact["dispatch"]["input_sha256"], DIGEST)

    def test_contextual_projection_rejects_dispatch_mismatch_and_unbounded_original(self):
        self.assertTrue(hasattr(self.contract, "contextual_projection"), "compact contextual projection must exist")
        for key, replacement in (("request_id", "other"), ("profile_sha256", "b" * 64), ("input_sha256", "c" * 64),
                                 ("execution_id", "other"), ("phase", "POST_ACTION"), ("raw_score", float("nan"))):
            raw = self.assessment()
            raw[key] = replacement
            with self.assertRaises(self.contract.LedgerInputError):
                self.contract.contextual_projection(json.dumps(raw).encode(), dispatch=self.dispatch(), evidence_ref="evidence-1")
        for raw in (b" " * 16385, b'{"status":"OK","status":"ERROR"}', b'{}'):
            with self.assertRaises(self.contract.LedgerInputError):
                self.contract.contextual_projection(raw, dispatch=self.dispatch(), evidence_ref="evidence-1")

    def test_contextual_projection_must_bind_event_and_retained_evidence(self):
        value, _ = self.projected()
        value["correlation"]["assessment_id"] = "different"
        self.invalid(value)
        value, _ = self.projected()
        value["provenance"]["evidence"][0]["sha256"] = DIGEST
        self.invalid(value)

    def test_contextual_status_result_and_detail_kinds_cannot_conflict(self):
        value = event(event_type="ASSESSMENT")
        value["detail"].update(status="ERROR", result="PASS")
        self.invalid(value)
        value = event(event_type="ASSESSMENT")
        value["detail"]["kind"] = "CONTEXTUAL_ML"
        self.invalid(value)

    def test_contextual_projection_supports_existing_32_feature_contract(self):
        original = self.assessment()
        original["factors"] *= 32
        original["source_ids"] = ["sensor-" + str(index) for index in range(32)]
        value, _ = self.projected(original)
        self.contract.validate_input(value)
        self.assertEqual(len(value["detail"]["contextual"]["source_ids"]), 32)

    def test_contextual_projection_rejects_status_outside_existing_model_contract(self):
        with self.assertRaises(self.contract.LedgerInputError):
            self.projected(self.assessment("SKIPPED"))

    def test_existing_untrained_contextual_assessment_can_be_projected(self):
        from dcamr.anomaly_engine.contextual_model import ContextualModel
        from tests.test_contextual_model import profile, observation

        context_profile, digest = profile()
        raw_input = json.dumps(observation(digest)).encode()
        assessment = ContextualModel.untrained(context_profile).assess(raw_input, expected_sha256=sha256(raw_input).hexdigest())
        dispatch = self.dispatch()
        dispatch.update(request_id=assessment.request_id, input_sha256=assessment.input_sha256, profile_sha256=digest)
        original = json.dumps(assessment.to_dict()).encode()
        compact = self.contract.contextual_projection(original, dispatch=dispatch, evidence_ref="retained-assessment")
        self.assertEqual(compact["status"], "UNAVAILABLE")
        self.assertEqual(compact["reason_codes"], ["MODEL_UNAVAILABLE"])

    def test_parsed_contextual_metadata_cannot_be_partial_for_any_model_status(self):
        for status in ("OK", "UNAVAILABLE", "ERROR"):
            for key, replacement in (("request_at_ms", None), ("cutoff_at_ms", None), ("observation_id", None),
                                     ("request_id", None), ("input_sha256", None), ("context", {}), ("source_ids", [])):
                with self.subTest(status=status, field=key):
                    original = self.assessment(status)
                    original[key] = replacement
                    with self.assertRaises(self.contract.LedgerInputError):
                        self.projected(original)

    def test_pre_action_contextual_cutoff_must_equal_request_time(self):
        for cutoff in (99, 101):
            original = self.assessment()
            original["cutoff_at_ms"] = cutoff
            with self.assertRaises(self.contract.LedgerInputError):
                self.projected(original)

    def test_post_action_contextual_requires_execution_and_ordered_times(self):
        dispatch = dict(self.dispatch(), phase="POST_ACTION", execution_id="execution-1")
        original = dict(self.assessment(), phase="POST_ACTION", execution_id="execution-1",
                        execution_at_ms=150, cutoff_at_ms=200)
        valid, _ = self.projected(original, dispatch=dispatch)
        self.contract.validate_input(valid)
        for key, replacement in (("execution_id", None), ("execution_at_ms", None),
                                 ("execution_at_ms", 99), ("execution_at_ms", 201), ("cutoff_at_ms", 99)):
            with self.subTest(field=key, replacement=replacement), self.assertRaises(self.contract.LedgerInputError):
                self.projected(dict(original, **{key: replacement}), dispatch=dispatch)

    def test_contextual_parse_failure_requires_empty_parsed_metadata_and_keeps_dispatch(self):
        for key, replacement in (("observation_id", "observation-1"), ("request_at_ms", 100),
                                 ("cutoff_at_ms", 100), ("context", {"action": "off"}), ("source_ids", ["sensor-1"]),
                                 ("calibration_sha256", DIGEST)):
            with self.subTest(field=key), self.assertRaises(self.contract.LedgerInputError):
                self.projected(dict(self.assessment("INVALID_INPUT"), **{key: replacement}))
        dispatch = dict(self.dispatch(), phase="POST_ACTION", execution_id="execution-1")
        original = dict(self.assessment("INVALID_INPUT"), phase="POST_ACTION", status="UNAVAILABLE")
        value, _ = self.projected(original, dispatch=dispatch)
        self.contract.validate_input(value)
        self.assertEqual(value["detail"]["contextual"]["dispatch"]["execution_id"], "execution-1")
        self.assertIsNone(value["detail"]["contextual"]["parsed"]["execution_id"])

    def test_retained_contextual_metadata_is_checked_on_direct_event_validation(self):
        value, _ = self.projected()
        value["detail"]["contextual"]["request_at_ms"] = None
        self.invalid(value)


if __name__ == "__main__":
    unittest.main()
