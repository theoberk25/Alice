"""General profile boundaries; values and units here are inert contract fixtures."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest

from dcamr.anomaly_engine.context_profile import (
    ContextError, FLOAT32_MAX, MAX_OBSERVATION_BYTES, MAX_PROFILE_BYTES,
    MAX_TIMESTAMP_MS, json_bytes, load_context_profile, parse_context_observation,
)


ROOT = Path(__file__).resolve().parents[1]


def profile_payload(phase="PRE_ACTION"):
    return {
        "schema_version": "context-behavior-profile-v1",
        "profile_id": "contract-fixture", "version": "1.0.0", "phase": phase,
        "features": [
            {"name": "request_value", "unit": "fixture_unit", "max_age_ms": 1000,
             "timing": "AT_OR_BEFORE_REQUEST"},
            {"name": "observed_value", "unit": "fixture_unit", "max_age_ms": 2000,
             "timing": "AT_OR_AFTER_EXECUTION" if phase == "POST_ACTION" else "AT_OR_BEFORE_REQUEST"},
        ],
        "context_keys": ["action_family", "operating_context"],
    }


def load(payload=None):
    data = json_bytes(profile_payload() if payload is None else payload)
    return load_context_profile(data, expected_sha256=sha256(data).hexdigest())


def observation_payload(profile):
    post = profile.phase == "POST_ACTION"
    return {
        "schema_version": "context-behavior-observation-v1",
        "profile_sha256": profile.sha256,
        "observation_id": "observation-1", "request_id": "request-1", "session_id": "session-1",
        "phase": profile.phase, "request_at_ms": 10000, "cutoff_at_ms": 11000 if post else 10000,
        "execution_id": "execution-1" if post else None,
        "execution_at_ms": 10500 if post else None,
        "context": {"action_family": "fixture-change", "operating_context": "fixture-mode"},
        "measurements": {
            "request_value": {"value": 0.25, "unit": "fixture_unit", "observed_at_ms": 10000,
                              "source_id": "request-sample-1"},
            "observed_value": {"value": -2.5, "unit": "fixture_unit",
                               "observed_at_ms": 10900 if post else 9900, "source_id": "sensor-sample-1"},
        },
    }


def parse(payload, profile):
    # Standard JSON serialization can produce deliberately malformed NaN/Infinity
    # fixtures; the production json_bytes helper correctly rejects them earlier.
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return parse_context_observation(data, profile, expected_sha256=sha256(data).hexdigest())


class ContextAssertions(unittest.TestCase):
    def assert_failure(self, callback, code="INPUT_INVALID", status="INVALID_INPUT"):
        with self.assertRaises(ContextError) as caught:
            callback()
        self.assertEqual((caught.exception.code, caught.exception.status), (code, status))


class ContextProfileTests(ContextAssertions):
    def test_profile_is_frozen_with_explicit_order_and_source_digest(self):
        payload = profile_payload()
        original = json_bytes(payload)
        profile = load(payload)
        payload["features"][0]["unit"] = "changed"
        self.assertEqual(profile.sha256, sha256(original).hexdigest())
        self.assertEqual(tuple(feature.name for feature in profile.features), ("request_value", "observed_value"))
        self.assertEqual(profile.features[0].unit, "fixture_unit")
        self.assertEqual(profile.context_keys, ("action_family", "operating_context"))
        with self.assertRaises(FrozenInstanceError):
            profile.phase = "POST_ACTION"
        with self.assertRaises(FrozenInstanceError):
            profile.features[0].unit = "changed"

    def test_profile_rejects_unknown_fields_duplicate_names_and_invalid_dimensions(self):
        cases = []
        payload = profile_payload()
        payload["normal_maximum"] = 20
        cases.append(payload)
        for value in ([], [profile_payload()["features"][0]] * 33,
                      [profile_payload()["features"][0]] * 2, {}, None):
            payload = profile_payload()
            payload["features"] = value
            cases.append(payload)
        for value in ([], ["a"] * 2, ["a", "b", "c", "d", "e"], [None], ["has spaces"]):
            payload = profile_payload()
            payload["context_keys"] = value
            cases.append(payload)
        payload = profile_payload()
        payload["features"][0]["allowed_max"] = 2
        cases.append(payload)
        for payload in cases:
            with self.subTest(payload=payload):
                self.assert_failure(lambda: load(payload))

    def test_profile_age_units_schema_and_phase_are_explicit(self):
        for value in (-1, 86400001, True, 1.0, None):
            payload = profile_payload()
            payload["features"][0]["max_age_ms"] = value
            self.assert_failure(lambda: load(payload))
        for value in ("", " ", "a\n", "a" * 65, 3, None):
            payload = profile_payload()
            payload["features"][0]["unit"] = value
            self.assert_failure(lambda: load(payload))
        for key, value in (("schema_version", "future-version"), ("phase", "PRE"),
                           ("version", []), ("profile_id", "a" * 129)):
            payload = profile_payload()
            payload[key] = value
            self.assert_failure(lambda: load(payload))

    def test_feature_timing_is_required_and_consistent_with_profile_phase(self):
        for value in (None, "BEFORE", [], True):
            payload = profile_payload()
            payload["features"][0]["timing"] = value
            self.assert_failure(lambda: load(payload))
        payload = profile_payload()
        del payload["features"][0]["timing"]
        self.assert_failure(lambda: load(payload))
        payload = profile_payload()
        payload["features"][1]["timing"] = "AT_OR_AFTER_EXECUTION"
        self.assert_failure(lambda: load(payload))
        payload = profile_payload("POST_ACTION")
        payload["features"][1]["timing"] = "AT_OR_BEFORE_REQUEST"
        self.assert_failure(lambda: load(payload))
        self.assertEqual(load(profile_payload("POST_ACTION")).features[1].timing, "AT_OR_AFTER_EXECUTION")

    def test_json_boundary_rejects_duplicate_keys_bad_unicode_depth_and_non_objects(self):
        cases = [b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b"\xff",
                 b'{"a":"\\ud800"}', b'{"a":NaN}', b'{"a":1e999}', b"[]", b"null", b"true"]
        for data in cases:
            with self.subTest(data=data):
                self.assert_failure(lambda: load_context_profile(data, expected_sha256=sha256(data).hexdigest()))
        data = b'{"a":' * 14 + b"0" + b"}" * 14
        self.assert_failure(lambda: load_context_profile(data, expected_sha256=sha256(data).hexdigest()),
                            "INPUT_LIMIT_EXCEEDED")

    def test_byte_limits_and_digest_precede_parsing(self):
        data = b" " * (MAX_PROFILE_BYTES + 1)
        self.assert_failure(lambda: load_context_profile(data, expected_sha256=sha256(data).hexdigest()),
                            "INPUT_LIMIT_EXCEEDED")
        data = json_bytes(profile_payload())
        self.assert_failure(lambda: load_context_profile(data + b" ", expected_sha256=sha256(data).hexdigest()),
                            "DIGEST_MISMATCH")
        for digest in (None, "", "A" * 64, "0" * 63):
            self.assert_failure(lambda: load_context_profile(data, expected_sha256=digest))
        def endless():
            self.fail("a non-bytes input must be rejected without iteration")
            yield b"a"
        self.assert_failure(lambda: load_context_profile(endless(), expected_sha256="0" * 64))

    def test_helpers_and_imports_require_only_standard_library(self):
        self.assertEqual(json_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')
        for value in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                json_bytes({"value": value})
        code = ("import sys; import dcamr.anomaly_engine.context_profile; "
                "assert not {'numpy', 'sklearn', 'scipy', 'jsonschema'} & sys.modules.keys()")
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True)


class ContextObservationTests(ContextAssertions):
    def setUp(self):
        self.profile = load()
        self.payload = observation_payload(self.profile)

    def test_context_measurements_provenance_follow_profile_order_and_are_immutable(self):
        payload = deepcopy(self.payload)
        payload["context"] = dict(reversed(list(payload["context"].items())))
        payload["measurements"] = dict(reversed(list(payload["measurements"].items())))
        observation = parse(payload, self.profile)
        self.assertEqual(observation.values, (0.25, -2.5))
        self.assertEqual(observation.context, (("action_family", "fixture-change"),
                                               ("operating_context", "fixture-mode")))
        self.assertEqual(observation.source_ids, ("request-sample-1", "sensor-sample-1"))
        self.assertEqual(observation.observed_at_ms, (10000, 9900))
        payload["measurements"]["request_value"]["value"] = 999
        self.assertEqual(observation.values[0], 0.25)
        with self.assertRaises(FrozenInstanceError):
            observation.request_id = "different"
        changed = deepcopy(self.payload)
        changed["context"]["operating_context"] = "different-mode"
        other = parse(changed, self.profile)
        self.assertEqual(other.values, observation.values)
        self.assertNotEqual(other.context, observation.context)

    def test_measurements_can_share_one_actual_source_without_dropping_positions(self):
        self.payload["measurements"]["observed_value"]["source_id"] = "request-sample-1"
        self.assertEqual(parse(self.payload, self.profile).source_ids, ("request-sample-1", "request-sample-1"))

    def test_profile_phase_and_units_cannot_be_substituted(self):
        for change, code in (({"profile_sha256": "0" * 64}, "PROFILE_MISMATCH"),
                             ({"phase": "POST_ACTION"}, "PHASE_MISMATCH")):
            payload = dict(self.payload, **change)
            self.assert_failure(lambda: parse(payload, self.profile), code)
        self.payload["measurements"]["observed_value"]["unit"] = "other_unit"
        self.assert_failure(lambda: parse(self.payload, self.profile), "UNIT_MISMATCH")

    def test_exact_field_sets_prevent_silently_ignored_context_and_features(self):
        changes = [lambda p: p.update(approval=True),
                   lambda p: p.pop("execution_id"),
                   lambda p: p["context"].update(extra="value"),
                   lambda p: p["context"].pop("action_family"),
                   lambda p: p["measurements"].update(extra=p["measurements"]["request_value"]),
                   lambda p: p["measurements"].pop("request_value"),
                   lambda p: p["measurements"]["request_value"].update(extra=2)]
        for change in changes:
            payload = deepcopy(self.payload)
            change(payload)
            self.assert_failure(lambda: parse(payload, self.profile))

    def test_null_required_readings_are_unavailable_not_zero(self):
        for key in ("value", "observed_at_ms", "source_id"):
            payload = deepcopy(self.payload)
            payload["measurements"]["request_value"][key] = None
            self.assert_failure(lambda: parse(payload, self.profile), "TELEMETRY_MISSING", "UNAVAILABLE")
        self.payload["measurements"]["request_value"]["value"] = None
        self.payload["measurements"]["request_value"]["observed_at_ms"] = True
        self.assert_failure(lambda: parse(self.payload, self.profile))

    def test_future_and_stale_readings_fail_with_exact_freshness_boundaries(self):
        reading = self.payload["measurements"]["observed_value"]
        reading["observed_at_ms"] = 8000
        self.assertEqual(parse(self.payload, self.profile).observed_at_ms[1], 8000)
        reading["observed_at_ms"] = 7999
        self.assert_failure(lambda: parse(self.payload, self.profile), "STALE_OBSERVATION", "UNAVAILABLE")
        reading["observed_at_ms"] = 10001
        self.assert_failure(lambda: parse(self.payload, self.profile), "TEMPORAL_FEATURE_MISMATCH", "UNAVAILABLE")

    def test_pre_action_cannot_move_cutoff_or_embed_execution(self):
        for change in ({"cutoff_at_ms": 10001}, {"cutoff_at_ms": 9999},
                       {"execution_id": "executed"}, {"execution_at_ms": 10000}):
            payload = dict(self.payload, **change)
            self.assert_failure(lambda: parse(payload, self.profile), "TEMPORAL_BINDING_INVALID")

    def test_post_action_accepts_bound_result_and_context_but_not_future_information(self):
        profile = load(profile_payload("POST_ACTION"))
        payload = observation_payload(profile)
        observation = parse(payload, profile)
        self.assertEqual((observation.execution_id, observation.execution_at_ms), ("execution-1", 10500))
        self.assertEqual(observation.observed_at_ms, (10000, 10900))
        for change in ({"execution_at_ms": 9999}, {"execution_at_ms": 11001}, {"cutoff_at_ms": 10499}):
            changed = dict(payload, **change)
            self.assert_failure(lambda: parse(changed, profile), "TEMPORAL_BINDING_INVALID")
        for key in ("execution_id", "execution_at_ms"):
            changed = dict(payload, **{key: None})
            self.assert_failure(lambda: parse(changed, profile))
        payload["measurements"]["observed_value"]["observed_at_ms"] = 11001
        self.assert_failure(lambda: parse(payload, profile), "FUTURE_OBSERVATION", "UNAVAILABLE")

    def test_post_action_cannot_treat_old_sensor_data_as_outcome_or_replace_request_context(self):
        profile = load(profile_payload("POST_ACTION"))
        payload = observation_payload(profile)
        payload["measurements"]["observed_value"]["observed_at_ms"] = 10499
        self.assert_failure(lambda: parse(payload, profile), "TEMPORAL_FEATURE_MISMATCH", "UNAVAILABLE")
        # An observation exactly at execution is admissible; timestamp binding
        # alone still does not prove that a physical effect was measured.
        payload["measurements"]["observed_value"]["observed_at_ms"] = 10500
        self.assertEqual(parse(payload, profile).observed_at_ms, (10000, 10500))
        payload["measurements"]["request_value"]["observed_at_ms"] = 10001
        self.assert_failure(lambda: parse(payload, profile), "TEMPORAL_FEATURE_MISMATCH", "UNAVAILABLE")

    def test_numeric_inputs_reject_bools_nonfinite_and_float32_overflow(self):
        for value in (True, "0.2", [], {}, float("nan"), float("inf"), -float("inf"), 1e100, -1e100):
            payload = deepcopy(self.payload)
            payload["measurements"]["request_value"]["value"] = value
            self.assert_failure(lambda: parse(payload, self.profile))
        for value in (0, -5, FLOAT32_MAX, -FLOAT32_MAX, 1e-40):
            payload = deepcopy(self.payload)
            payload["measurements"]["request_value"]["value"] = value
            self.assertEqual(parse(payload, self.profile).values[0], float(value))

    def test_timestamps_and_provenance_identifiers_are_strict(self):
        for value in (True, 10000.0, -1, MAX_TIMESTAMP_MS + 1, "10000"):
            for key in ("request_at_ms", "cutoff_at_ms"):
                payload = dict(self.payload, **{key: value})
                self.assert_failure(lambda: parse(payload, self.profile))
            payload = deepcopy(self.payload)
            payload["measurements"]["request_value"]["observed_at_ms"] = value
            self.assert_failure(lambda: parse(payload, self.profile))
        for value in ("", True, "https://source.invalid/sample", "x" * 129):
            payload = deepcopy(self.payload)
            payload["measurements"]["request_value"]["source_id"] = value
            self.assert_failure(lambda: parse(payload, self.profile))
        self.payload["context"]["action_family"] = {"agent_claim": "not-a-trusted-context"}
        self.assert_failure(lambda: parse(self.payload, self.profile))

    def test_observation_digest_and_size_are_bound(self):
        data = json_bytes(self.payload)
        digest = sha256(data).hexdigest()
        self.assertEqual(parse_context_observation(data, self.profile, expected_sha256=digest).input_sha256, digest)
        self.assert_failure(lambda: parse_context_observation(data + b" ", self.profile, expected_sha256=digest),
                            "DIGEST_MISMATCH")
        huge = b" " * (MAX_OBSERVATION_BYTES + 1)
        self.assert_failure(lambda: parse_context_observation(huge, self.profile,
                            expected_sha256=sha256(huge).hexdigest()), "INPUT_LIMIT_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
