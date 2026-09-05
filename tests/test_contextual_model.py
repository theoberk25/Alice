"""Context-aware scoring with test-only signals, not ESP operating baselines.

The two artificial action contexts have deliberately different numeric ranges.
These inputs exercise conditioning, provenance and failure handling; they make
no claim about normal voltage, lamp behavior or production anomaly detection.
"""

from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from dcamr.anomaly_engine.context_profile import load_context_profile
from dcamr.anomaly_engine.contextual_model import ContextualModel
from lab.contextual_training import NormalExample, fit_contextual_model


ROOT = Path(__file__).resolve().parents[1]
HAS_TRAINING_DEPS = all(importlib.util.find_spec(name) is not None
                        for name in ("numpy", "sklearn", "threadpoolctl"))


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def profile(phase="PRE_ACTION"):
    encoded = json_bytes({
        "schema_version": "context-behavior-profile-v1",
        "profile_id": "test-context-signals",
        "version": "1.0.0",
        "phase": phase,
        "features": [
            {"name": "signal", "unit": "unitless", "max_age_ms": 5_000,
             "timing": "AT_OR_AFTER_EXECUTION" if phase == "POST_ACTION"
             else "AT_OR_BEFORE_REQUEST"},
            {"name": "constant", "unit": "unitless", "max_age_ms": 5_000,
             "timing": "AT_OR_BEFORE_REQUEST"},
        ],
        "context_keys": ["action"],
    })
    digest = sha256(encoded).hexdigest()
    return load_context_profile(encoded, expected_sha256=digest), digest


def observation(profile_digest, *, phase="PRE_ACTION", split="evaluation",
                action="off", index=0, signal=0.5, constant=5.0):
    """Every measurement has its own evidence ID; sessions stay within splits."""
    identity = f"{split}-{action}-{index}"
    request_at = 1_700_000_000_000 + index * 10_000
    execution_at = request_at + 1_000 if phase == "POST_ACTION" else None
    cutoff = execution_at + 1_000 if execution_at is not None else request_at
    return {
        "schema_version": "context-behavior-observation-v1",
        "profile_sha256": profile_digest,
        "observation_id": f"observation-{identity}",
        "request_id": f"request-{identity}",
        "session_id": f"session-{split}-{action}-{index // 16}",
        "phase": phase,
        "request_at_ms": request_at,
        "cutoff_at_ms": cutoff,
        "execution_id": f"execution-{identity}" if execution_at is not None else None,
        "execution_at_ms": execution_at,
        "context": {"action": action},
        "measurements": {
            "signal": {"value": signal, "unit": "unitless", "observed_at_ms": cutoff,
                       "source_id": f"source-signal-{identity}"},
            "constant": {"value": constant, "unit": "unitless", "observed_at_ms": request_at,
                         "source_id": f"source-constant-{identity}"},
        },
    }


def example(payload, *, label="NORMAL"):
    encoded = json_bytes(payload)
    return NormalExample(input_bytes=encoded, input_sha256=sha256(encoded).hexdigest(),
                         label=label)


def edit(source, change):
    payload = json.loads(source.input_bytes)
    change(payload)
    return example(payload, label=source.label)


def normal_examples(profile_digest, *, phase="PRE_ACTION", actions=("off", "on")):
    """Explicit disjoint splits; all values and NORMAL labels are test-only."""
    rows = {}
    for split, count, multiplier, denominator in (
            ("training", 256, 37, 257), ("calibration", 1_000, 53, 1_009)):
        rows[split] = tuple(
            example(observation(profile_digest, phase=phase, split=split, action=action,
                                index=i, signal=(0.0 if action == "off" else 10.0) +
                                ((i * multiplier) % denominator) / denominator))
            for action in actions for i in range(count)
        )
    return rows["training"], rows["calibration"]


def assess(model, payload):
    encoded = json_bytes(payload)
    return model.assess(encoded, expected_sha256=sha256(encoded).hexdigest())


class UntrainedContextTests(unittest.TestCase):
    def test_untrained_model_never_fabricates_a_normal_score(self):
        selected, digest = profile()
        model = ContextualModel.untrained(selected)
        result = assess(model, observation(digest))
        self.assertEqual((result.status, result.result), ("UNAVAILABLE", "UNKNOWN"))
        self.assertIsNone(result.raw_score)
        self.assertIsNone(result.score)
        self.assertIn("MODEL_UNAVAILABLE", result.reason_codes)
        self.assertEqual(result.profile_sha256, digest)
        self.assertIsNone(result.model_id)
        self.assertIsNone(result.model_fingerprint)
        self.assertIsNone(result.calibration_sha256)

    def test_imports_and_untrained_assessment_do_not_load_numerical_runtime(self):
        code = """
import sys
from tests.test_contextual_model import profile, observation, assess
from dcamr.anomaly_engine.contextual_model import ContextualModel
p, digest = profile()
assert assess(ContextualModel.untrained(p), observation(digest)).result == 'UNKNOWN'
assert not {'sklearn', 'numpy', 'scipy'} & sys.modules.keys()
"""
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True,
                       capture_output=True, timeout=30)


@unittest.skipUnless(HAS_TRAINING_DEPS, "install requirements-anomaly-training.txt for forest tests")
class ContextualTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sklearn.ensemble import IsolationForest
        from threadpoolctl import threadpool_info

        cls.profile, cls.profile_digest = profile()
        cls.training, cls.calibration = normal_examples(cls.profile_digest)
        cls.estimators, cls.thread_settings = [], []

        def capture_estimator(**parameters):
            estimator = IsolationForest(**parameters)
            cls.estimators.append(estimator)
            cls.thread_settings.extend(threadpool_info())
            return estimator

        with patch("sklearn.ensemble.IsolationForest", side_effect=capture_estimator):
            cls.model = fit_contextual_model(cls.profile, cls.training, cls.calibration,
                                            model_id="test-context-forest")

    def fit(self, training=None, calibration=None, **kwargs):
        return fit_contextual_model(self.profile,
                                    self.training if training is None else training,
                                    self.calibration if calibration is None else calibration,
                                    model_id="test-validation-forest", **kwargs)

    def test_bounded_single_worker_forest_and_phase_metadata(self):
        metadata = self.model.metadata
        self.assertEqual(metadata["algorithm"], "IsolationForest")
        self.assertEqual(metadata["parameters"]["n_estimators"], 64)
        self.assertEqual(metadata["parameters"]["max_samples"], 256)
        self.assertEqual(metadata["parameters"]["n_jobs"], 1)
        self.assertEqual(metadata["profile_sha256"], self.profile_digest)
        self.assertEqual(metadata["phase"], "PRE_ACTION")
        self.assertEqual(metadata["context_count"], 2)
        self.assertFalse(metadata["model_persisted"])
        self.assertFalse(metadata["deployment_ready"])
        self.assertEqual(len(self.estimators), 2)
        for estimator in self.estimators:
            self.assertEqual(len(estimator.estimators_), 64)
            self.assertEqual(estimator.max_samples_, 256)
            self.assertEqual(estimator.n_features_in_, 2)
            self.assertEqual(estimator.n_jobs, 1)
            self.assertFalse(estimator.warm_start)
        self.assertTrue(all(pool["num_threads"] == 1 for pool in self.thread_settings))
        for context in metadata["contexts"]:
            self.assertEqual(context["training_count"], 256)
            self.assertEqual(context["calibration_count"], 1_000)
            self.assertIn("constant", context["constant_features"])
        json_bytes(metadata)

    def test_identical_measurement_is_scored_against_its_action_context(self):
        off = assess(self.model, observation(self.profile_digest, action="off", signal=0.5))
        on = assess(self.model, observation(self.profile_digest, action="on", signal=0.5))
        self.assertEqual((off.status, on.status), ("OK", "OK"))
        self.assertEqual(off.result, "LOW")
        self.assertGreater(on.score, off.score)
        self.assertLess(on.raw_score, off.raw_score)
        self.assertNotEqual(off.calibration_sha256, on.calibration_sha256)
        self.assertIn("OUTSIDE_TRAINING_RANGE", on.reason_codes)
        self.assertIn("WITHIN_TRAINING_RANGES", off.reason_codes)

    def test_unseen_context_is_unknown_without_a_global_fallback(self):
        result = assess(self.model, observation(self.profile_digest, action="never-observed"))
        self.assertEqual((result.status, result.result), ("UNAVAILABLE", "UNKNOWN"))
        self.assertIsNone(result.score)
        self.assertIsNone(result.raw_score)
        self.assertIsNone(result.calibration_sha256)
        self.assertIn("CONTEXT_UNSEEN", result.reason_codes)

    def test_estimator_failure_is_unknown_and_does_not_echo_exception_details(self):
        with patch.object(self.estimators[0], "score_samples",
                          side_effect=RuntimeError("private service details")):
            result = assess(self.model, observation(self.profile_digest, action="off"))
        self.assertEqual((result.status, result.result), ("ERROR", "UNKNOWN"))
        self.assertIsNone(result.score)
        self.assertIsNone(result.raw_score)
        self.assertIn("MODEL_ERROR", result.reason_codes)
        self.assertNotIn("private service details", json_bytes(result.to_dict()).decode())

    def test_changed_constant_feature_keeps_independent_range_evidence(self):
        normal = assess(self.model, observation(self.profile_digest, constant=5.0))
        changed = assess(self.model, observation(self.profile_digest, constant=99.0))
        # An Isolation Forest cannot split on a feature that never varied at fit.
        # Its low score must not conceal the separately reported observed change.
        self.assertEqual(changed.result, "LOW")
        self.assertEqual(changed.raw_score, normal.raw_score)
        self.assertEqual(changed.score, normal.score)
        factor = next(item for item in changed.factors if item.name == "constant")
        self.assertEqual((factor.unit, factor.observed), ("unitless", 99.0))
        self.assertEqual((factor.training_min, factor.training_max), (5.0, 5.0))
        self.assertTrue(factor.outside_training_range)
        self.assertIn("OUTSIDE_TRAINING_RANGE", changed.reason_codes)

    def test_assessment_and_metadata_are_repeatable_independent_copies(self):
        source = observation(self.profile_digest)
        initial_metadata = self.model.metadata
        first = assess(self.model, source)
        second = assess(self.model, source)
        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(self.model.metadata, initial_metadata)
        copied = self.model.metadata
        copied["parameters"]["n_jobs"] = 99
        copied["contexts"].clear()
        self.assertEqual(self.model.metadata, initial_metadata)
        payload = first.to_dict()
        self.assertEqual(payload["schema_version"], "context-behavior-assessment-v1")
        self.assertEqual(payload["phase"], "PRE_ACTION")
        self.assertEqual(payload["observation_id"], source["observation_id"])
        self.assertEqual(payload["request_id"], source["request_id"])
        self.assertEqual(payload["model_id"], "test-context-forest")
        self.assertRegex(payload["model_fingerprint"], r"^[a-f0-9]{64}$")
        self.assertRegex(payload["calibration_sha256"], r"^[a-f0-9]{64}$")
        json_bytes(payload)
        payload["factors"].clear()
        self.assertTrue(first.factors)

    def test_missing_stale_or_untrusted_inputs_never_produce_numeric_scores(self):
        mutations = {
            "missing": lambda value: value["measurements"].pop("signal"),
            "stale": lambda value: value["measurements"]["signal"].update(
                observed_at_ms=value["cutoff_at_ms"] - 5_001),
            "future": lambda value: value["measurements"]["signal"].update(
                observed_at_ms=value["cutoff_at_ms"] + 1),
            "wrong_unit": lambda value: value["measurements"]["signal"].update(unit="volts"),
            "wrong_profile": lambda value: value.update(profile_sha256="0" * 64),
        }
        for name, mutation in mutations.items():
            with self.subTest(case=name):
                value = observation(self.profile_digest)
                mutation(value)
                result = assess(self.model, value)
                self.assertNotEqual(result.status, "OK")
                self.assertEqual(result.result, "UNKNOWN")
                self.assertIsNone(result.raw_score)
                self.assertIsNone(result.score)
                self.assertTrue(result.reason_codes)
        value = json_bytes(observation(self.profile_digest))
        result = self.model.assess(value, expected_sha256="0" * 64)
        self.assertEqual(result.result, "UNKNOWN")
        self.assertIsNone(result.score)

    def test_request_or_source_lineage_cannot_leak_across_splits(self):
        original = json.loads(self.training[0].input_bytes)
        for key in ("observation_id", "request_id", "session_id"):
            with self.subTest(identity=key):
                altered = edit(self.calibration[0], lambda row: row.update({key: original[key]}))
                with self.assertRaises(ValueError):
                    self.fit(calibration=(altered, *self.calibration[1:]))
        altered = edit(self.calibration[0], lambda row: row["measurements"]["signal"].update(
            source_id=original["measurements"]["signal"]["source_id"]))
        with self.assertRaises(ValueError):
            self.fit(calibration=(altered, *self.calibration[1:]))

    def test_duplicate_observations_and_requests_within_a_split_are_rejected(self):
        with self.assertRaises(ValueError):
            self.fit(training=(*self.training, self.training[0]))
        first = json.loads(self.calibration[0].input_bytes)
        for key in ("observation_id", "request_id"):
            with self.subTest(identity=key):
                duplicate = edit(self.calibration[1], lambda row: row.update({key: first[key]}))
                with self.assertRaises(ValueError):
                    self.fit(calibration=(self.calibration[0], duplicate, *self.calibration[2:]))

    def test_reused_measurement_cannot_be_moved_to_another_training_session(self):
        source = json.loads(self.training[0].input_bytes)["measurements"]["signal"]["source_id"]
        moved = edit(self.training[16], lambda row: row["measurements"]["signal"].update(
            source_id=source))
        with self.assertRaisesRegex(ValueError, "lineage"):
            self.fit(training=(*self.training[:16], moved, *self.training[17:]))

    def shared_sensor_rows(self):
        """Two requests in one session consume the same still-fresh sensor event."""
        first = json.loads(self.training[0].input_bytes)
        # One sensor event can legitimately carry two differently named values.
        first["measurements"]["constant"]["source_id"] = first["measurements"]["signal"]["source_id"]
        second = json.loads(self.training[1].input_bytes)
        second["request_at_ms"] = first["request_at_ms"] + 1_000
        second["cutoff_at_ms"] = second["request_at_ms"]
        second["measurements"] = first["measurements"]
        return example(first), example(second)

    def test_reused_source_feature_cannot_change_value_or_timestamp_within_session(self):
        first, repeated = self.shared_sensor_rows()
        for field in ("value", "observed_at_ms"):
            with self.subTest(field=field):
                def change(row):
                    row["measurements"]["signal"][field] -= 1
                altered = edit(repeated, change)
                with self.assertRaisesRegex(ValueError, "source feature changed"):
                    self.fit(training=(first, altered, *self.training[2:]))

    def test_identical_sensor_event_can_be_reused_by_requests_in_the_same_session(self):
        first, repeated = self.shared_sensor_rows()
        model = self.fit(training=(first, repeated, *self.training[2:]))
        self.assertEqual(model.metadata["context_count"], 2)
        self.assertEqual(model.metadata["contexts"][0]["training_count"], 256)
        self.assertEqual(assess(model, observation(self.profile_digest)).status, "OK")

    def test_every_context_needs_sufficient_fit_and_calibration_examples(self):
        with self.assertRaises(ValueError):
            self.fit(training=self.training[1:])
        with self.assertRaises(ValueError):
            self.fit(calibration=self.calibration[1:])
        with self.assertRaises(ValueError):
            self.fit(training=self.training[:256])

    def test_only_normal_examples_can_define_fit_or_reference(self):
        for label in ("CHALLENGE", "ANOMALOUS", "", None, []):
            with self.subTest(label=label), self.assertRaises(ValueError):
                changed = replace(self.training[0], label=label)
                self.fit(training=(changed, *self.training[1:]))
        with self.assertRaises(ValueError):
            changed = replace(self.calibration[0], label="CHALLENGE")
            self.fit(calibration=(changed, *self.calibration[1:]))

    def test_bad_source_digest_and_seed_are_not_silently_repaired(self):
        with self.assertRaises(ValueError):
            bad = replace(self.training[0], input_sha256="0" * 64)
            self.fit(training=(bad, *self.training[1:]))
        for seed in (True, -1, 2**32):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                self.fit(seed=seed)

    def test_dataset_limits_bound_iterators_and_retained_source_bytes(self):
        with patch("lab.contextual_training.MAX_EXAMPLES", 2):
            with self.assertRaisesRegex(ValueError, "example limit"):
                self.fit(training=iter(self.training))
        with patch("lab.contextual_training.MAX_DATASET_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "byte limit"):
                self.fit()
        with patch("lab.contextual_training.MAX_CONTEXTS", 1):
            with self.assertRaisesRegex(ValueError, "context limit"):
                self.fit()

    def test_degenerate_calibration_does_not_become_a_valid_model(self):
        one_context_training = self.training[:256]
        constant_calibration = tuple(
            edit(row, lambda value: value["measurements"]["signal"].update(value=0.5))
            for row in self.calibration[:1_000]
        )
        with self.assertRaises(ValueError):
            self.fit(training=one_context_training, calibration=constant_calibration)

    def test_all_constant_training_data_cannot_create_a_ready_forest(self):
        constant_training = tuple(
            edit(row, lambda value: value["measurements"]["signal"].update(value=0.5))
            for row in self.training[:256]
        )
        with self.assertRaisesRegex(ValueError, "constant"):
            self.fit(training=constant_training, calibration=self.calibration[:1_000])


@unittest.skipUnless(HAS_TRAINING_DEPS, "install requirements-anomaly-training.txt for forest tests")
class PostActionContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile, cls.profile_digest = profile("POST_ACTION")
        cls.training, cls.calibration = normal_examples(cls.profile_digest, phase="POST_ACTION",
                                                       actions=("off",))
        cls.model = fit_contextual_model(cls.profile, cls.training, cls.calibration,
                                        model_id="test-post-action-forest")

    def test_post_action_assessment_is_bound_to_its_own_phase(self):
        row = observation(self.profile_digest, phase="POST_ACTION")
        result = assess(self.model, row)
        self.assertEqual((result.status, result.phase), ("OK", "POST_ACTION"))
        self.assertEqual(self.model.metadata["phase"], "POST_ACTION")
        wrong_phase = observation(self.profile_digest, phase="PRE_ACTION")
        result = assess(self.model, wrong_phase)
        self.assertNotEqual(result.status, "OK")
        self.assertEqual(result.result, "UNKNOWN")
        self.assertIsNone(result.score)

    def test_post_action_cannot_use_readings_after_the_captured_cutoff(self):
        row = observation(self.profile_digest, phase="POST_ACTION")
        row["measurements"]["signal"]["observed_at_ms"] = row["cutoff_at_ms"] + 1
        result = assess(self.model, row)
        self.assertNotEqual(result.status, "OK")
        self.assertEqual(result.result, "UNKNOWN")
        self.assertIsNone(result.score)

    def test_post_action_outcome_reading_must_be_after_execution(self):
        row = observation(self.profile_digest, phase="POST_ACTION")
        row["measurements"]["signal"]["observed_at_ms"] = row["execution_at_ms"] - 1
        result = assess(self.model, row)
        self.assertEqual((result.status, result.result), ("UNAVAILABLE", "UNKNOWN"))
        self.assertIsNone(result.score)
        self.assertIn("TEMPORAL_FEATURE_MISMATCH", result.reason_codes)

    def test_post_action_pre_request_context_cannot_be_replaced_with_later_values(self):
        row = observation(self.profile_digest, phase="POST_ACTION")
        row["measurements"]["constant"]["observed_at_ms"] = row["execution_at_ms"]
        result = assess(self.model, row)
        self.assertEqual((result.status, result.result), ("UNAVAILABLE", "UNKNOWN"))
        self.assertIsNone(result.score)
        self.assertIn("TEMPORAL_FEATURE_MISMATCH", result.reason_codes)

    def test_post_action_execution_lineage_cannot_cross_training_and_calibration(self):
        first = json.loads(self.training[0].input_bytes)
        altered = edit(self.calibration[0], lambda row: row.update(execution_id=first["execution_id"]))
        with self.assertRaises(ValueError):
            fit_contextual_model(self.profile, self.training,
                                 (altered, *self.calibration[1:]), model_id="test-overlap")

    def test_execution_cannot_be_counted_twice_within_one_training_session(self):
        first = json.loads(self.training[0].input_bytes)
        altered = edit(self.training[1], lambda row: row.update(execution_id=first["execution_id"]))
        with self.assertRaisesRegex(ValueError, "duplicate execution"):
            fit_contextual_model(self.profile, (self.training[0], altered, *self.training[2:]),
                                 self.calibration, model_id="test-duplicate-execution")


if __name__ == "__main__":
    unittest.main()
