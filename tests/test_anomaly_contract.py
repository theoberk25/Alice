"""Behavioral checks for the anomaly boundary, including invalid/stale results."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from dcamr.anomaly_engine.contract import (
    ARTIFACT_FIELDS, ContractError, EvaluationBinding, MAX_RESULT_BYTES,
    parse_result, serialize_result, validate_result,
)
from lab.replay_anomaly_fixtures import replay


FIXTURES = Path(__file__).parent / "fixtures/anomaly"


def load(name: str = "scored-elevated.json") -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.result = load()

    def test_all_committed_fixtures_replay(self):
        self.assertEqual(len(replay()), 8)

    def test_round_trip_preserves_exact_fields_and_nulls(self):
        for name in ("scored-elevated.json", "unavailable.json", "clock-untrusted.json"):
            with self.subTest(name=name):
                result = load(name)
                self.assertEqual(parse_result(serialize_result(result)), result)

    def test_duplicate_key_is_rejected_at_any_depth(self):
        for payload in ('{"score": 0, "score": 1}', '{"nested":{"id":1,"id":2}}'):
            with self.subTest(payload=payload), self.assertRaisesRegex(ContractError, "duplicate"):
                parse_result(payload)

    def test_nonfinite_overflow_and_booleans_cannot_be_scores(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, 10**1000):
            with self.subTest(value=type(value)):
                result = deepcopy(self.result)
                result["score"] = value
                with self.assertRaises(ContractError):
                    validate_result(result)
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(token=token), self.assertRaises(ContractError):
                parse_result('{"score":' + token + '}')

    def test_invalid_encoding_size_and_depth_rejected(self):
        for payload in (b"\xff", b" " * (MAX_RESULT_BYTES + 1), "[" * 1000 + "]" * 1000):
            with self.subTest(payload_type=type(payload)), self.assertRaises(ContractError):
                parse_result(payload)

    def test_nested_unknown_fields_and_future_schema_are_rejected(self):
        for mutate in (
            lambda r: r.update(schema_version="2.0"),
            lambda r: r.update(decision="ALLOW"),
            lambda r: r["model"].update(approved=True),
            lambda r: r["factors"][0].update(contribution=0.99),
        ):
            result = deepcopy(self.result)
            mutate(result)
            with self.assertRaises(ContractError):
                validate_result(result)

    def test_failure_must_not_look_like_zero_risk(self):
        for status in ("UNAVAILABLE", "INVALID_INPUT", "TIMEOUT", "ERROR", "SKIPPED"):
            with self.subTest(status=status):
                result = deepcopy(self.result)
                result.update(status=status, score=0, result="LOW")
                with self.assertRaises(ContractError):
                    validate_result(result)

    def test_ok_requires_complete_artifacts_and_input_quality(self):
        for key in ("baseline", "model", "calibration", "raw_score", "evaluated_at"):
            result = deepcopy(self.result)
            result[key] = None
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_result(result)
        self.result["quality"]["missing_fields"] = ["destination_seen"]
        with self.assertRaises(ContractError):
            validate_result(self.result)

    def test_dates_are_actually_parsed_without_optional_format_dependency(self):
        for timestamp in ("2026-02-30T00:00:00Z", "2026-09-05T25:00:00Z",
                          "2026-09-05T00:00:00", "2026-09-05T00:00:00-04:00"):
            self.result["evaluated_at"] = timestamp
            with self.subTest(timestamp=timestamp), self.assertRaises(ContractError):
                validate_result(self.result)

    def test_clock_unknown_needs_explicit_reason_and_quality_paths(self):
        for field in ("reason", "quality"):
            result = load("clock-untrusted.json")
            if field == "reason":
                result["reason_codes"] = ["MODEL_MISSING"]
            else:
                result["quality"]["missing_fields"] = []
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_result(result)

    def test_skipped_denial_can_be_recorded_without_trusted_clock(self):
        result = load("skipped-policy-deny.json")
        result["evaluated_at"] = None
        result["input_snapshot"]["observed_at"] = None
        result["reason_codes"] = ["CLOCK_UNTRUSTED", "POLICY_DENY_SHORT_CIRCUIT"]
        result["quality"]["missing_fields"] = ["evaluated_at", "input_snapshot.observed_at"]
        validate_result(result)

    def test_thresholds_and_band_must_agree(self):
        for elevated, high in ((.99, .95), (.95, .95), (-.1, .9), (.9, 1.1)):
            result = deepcopy(self.result)
            result["calibration"].update(elevated_min=elevated, high_min=high)
            with self.subTest(elevated=elevated, high=high), self.assertRaises(ContractError):
                validate_result(result)
        self.result["result"] = "LOW"
        with self.assertRaisesRegex(ContractError, "band"):
            validate_result(self.result)

    def test_exact_threshold_uses_unrounded_score(self):
        for score, band in ((.949999, "LOW"), (.95, "ELEVATED"), (.99, "HIGH")):
            result = deepcopy(self.result)
            result.update(score=score, result=band)
            result["reason_codes"] = ["DESTINATION_UNSEEN"]
            if band != "LOW":
                result["reason_codes"].append(f"{band}_MODEL_ANOMALY")
            validate_result(result)

    def test_status_reasons_cannot_claim_success_during_failure(self):
        for filename, reasons in (
            ("scored-low.json", ["INFERENCE_ERROR"]),
            ("scored-high.json", ["ELEVATED_MODEL_ANOMALY"]),
            ("unavailable.json", ["WITHIN_BASELINE"]),
            ("timeout.json", ["MODEL_MISSING"]),
            ("timeout.json", ["HIGH_MODEL_ANOMALY", "INFERENCE_TIMEOUT"]),
            ("unavailable.json", ["BASELINE_MISSING", "POLICY_DENY_SHORT_CIRCUIT"]),
            ("unavailable.json", ["BASELINE_MISSING", "INFERENCE_TIMEOUT"]),
        ):
            result = load(filename)
            result["reason_codes"] = reasons
            with self.subTest(filename=filename), self.assertRaises(ContractError):
                validate_result(result)

    def test_low_score_with_new_agent_remains_visible(self):
        result = load("new-agent-low.json")
        validate_result(result)
        self.assertEqual(result["result"], "LOW")
        self.assertIn("AGENT_UNSEEN", result["reason_codes"])
        result["reason_codes"] = ["WITHIN_BASELINE"]
        with self.assertRaises(ContractError):
            validate_result(result)

    def test_baseline_label_cannot_misrepresent_identity(self):
        self.result["baseline"]["version"] = "43"
        with self.assertRaisesRegex(ContractError, "source"):
            validate_result(self.result)

    def test_reason_quality_and_factor_ordering_is_stable(self):
        for mutate in (
            lambda r: r["reason_codes"].reverse(),
            lambda r: r["reason_codes"].append(r["reason_codes"][0]),
            lambda r: r["factors"].append(deepcopy(r["factors"][0])),
        ):
            result = deepcopy(self.result)
            mutate(result)
            with self.assertRaises(ContractError):
                validate_result(result)

    def test_unknown_factor_is_not_an_unexplained_normal_value(self):
        result = load("unavailable.json")
        result["factors"] = deepcopy(self.result["factors"])
        factor = result["factors"][0]
        factor.update(state="UNKNOWN", observed=None)
        with self.assertRaises(ContractError):
            validate_result(result)
        result["quality"]["missing_fields"].append("destination_seen")
        result["quality"]["missing_fields"].sort()
        validate_result(result)

    def test_payload_diagnostics_do_not_echo_values(self):
        self.result["score"] = "private-agent-prose"
        with self.assertRaises(ContractError) as caught:
            validate_result(self.result)
        self.assertNotIn("private-agent-prose", str(caught.exception))


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.result = load()
        self.result["runtime"]["execution_mode"] = "LIVE"
        self.context = deepcopy(self.result)  # Represents the separately trusted dispatch metadata.
        self.binding = EvaluationBinding.capture(self.context)
        self.active = {key: deepcopy(self.context[key]) for key in ARTIFACT_FIELDS}

    def test_matching_result_is_accepted_without_granting_a_decision(self):
        self.assertIsNone(self.binding.check(self.result, active_artifacts=self.active))
        self.assertNotIn("decision", self.result)

    def test_fixture_mode_is_rejected_by_default(self):
        self.result["runtime"]["execution_mode"] = "FIXTURE"
        with self.assertRaisesRegex(ContractError, "FIXTURE"):
            self.binding.check(self.result, active_artifacts=self.active)
        self.binding.check(self.result, active_artifacts=self.active, allow_fixtures=True)

    def test_changed_action_snapshot_evaluation_or_attempt_rejected(self):
        for mutate in (
            lambda r: r.update(request_sha256="f" * 64),
            lambda r: r.update(evaluation_id="eval-stale"),
            lambda r: r.update(previous_evaluation_id="eval-unrelated"),
            lambda r: r["input_snapshot"].update(sha256="f" * 64),
            lambda r: r["input_snapshot"].update(context_attempt=1),
        ):
            result = deepcopy(self.result)
            mutate(result)
            with self.assertRaisesRegex(ContractError, "dispatch correlation"):
                self.binding.check(result, active_artifacts=self.active)

    def test_model_or_threshold_substitution_rejected(self):
        for mutate in (
            lambda r: r["model"].update(sha256="f" * 64),
            lambda r: r["calibration"].update(elevated_min=.9),
        ):
            result = deepcopy(self.result)
            mutate(result)
            with self.assertRaisesRegex(ContractError, "dispatched artifacts"):
                self.binding.check(result, active_artifacts=self.active)

    def test_active_swap_invalidates_old_scored_result(self):
        self.active["model"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ContractError, "active artifacts changed"):
            self.binding.check(self.result, active_artifacts=self.active)

    def test_dispatch_binding_does_not_mutate_with_caller_dictionary(self):
        self.context["model"]["sha256"] = "f" * 64
        self.context["input_snapshot"]["context_attempt"] = 10
        self.binding.check(self.result, active_artifacts=self.active)


if __name__ == "__main__":
    unittest.main()
