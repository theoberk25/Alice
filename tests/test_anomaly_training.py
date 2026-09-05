"""Session isolation and real-estimator checks for the Mac-only lab pipeline."""

from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.feature_types import FEATURE_NAMES, FeatureError
from lab.anomaly_training import (
    ESTIMATORS, TREE_SAMPLES, TrainingExample, json_bytes, prepare_dataset,
    train_and_evaluate, training_readiness,
)
from lab.synthetic_anomaly_data import generate_examples


ROOT = Path(__file__).resolve().parents[1]


def baseline():
    data = (ROOT / "tests/fixtures/features/baseline.json").read_bytes()
    return load_baseline(data, expected_sha256=sha256(data).hexdigest())


def edited(example, change):
    payload = json.loads(example.input_bytes)
    change(payload)
    data = json_bytes(payload)
    return replace(example, input_bytes=data, input_sha256=sha256(data).hexdigest())


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = baseline()
        cls.examples = tuple(generate_examples(normal_sessions=10, requests_per_session=3,
                                               challenge_sessions_per_scenario=1))

    def prepare(self, rows=None, **kwargs):
        return prepare_dataset(self.examples if rows is None else rows, self.baseline, **kwargs)

    def test_whole_sessions_split_and_challenges_only_evaluated(self):
        result = self.prepare()
        groups = [{r.group_id for r in getattr(result, part)}
                  for part in ("train", "calibration", "evaluation")]
        for i in range(3):
            for j in range(i):
                self.assertFalse(groups[i] & groups[j])
        self.assertEqual([len(result.train), len(result.calibration), len(result.evaluation)], [18, 6, 11])
        self.assertTrue(all(r.label == "NORMAL" for r in (*result.train, *result.calibration)))
        self.assertEqual(sum(r.label == "CHALLENGE" for r in result.evaluation), 5)
        self.assertTrue(all(r.batch.names == FEATURE_NAMES for r in result.train))

    def test_membership_reproducible_independent_of_input_order(self):
        self.assertEqual(self.prepare().manifest(), self.prepare(reversed(self.examples)).manifest())
        self.assertNotEqual(self.prepare().manifest()["splits"], self.prepare(seed=9).manifest()["splits"])

    def test_digest_mismatch_is_not_dropped(self):
        changed = replace(self.examples[0], input_bytes=self.examples[0].input_bytes + b" ")
        with self.assertRaises(FeatureError):
            self.prepare([changed, *self.examples[1:]])

    def test_examples_cannot_be_relabelled_under_a_different_baseline(self):
        changed = replace(self.examples[0], baseline_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "baseline binding"):
            self.prepare([changed, *self.examples[1:]])

    def test_duplicate_current_request_and_context_retries_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.prepare([*self.examples, self.examples[0]])
        retried = edited(self.examples[0], lambda p: p["snapshot"].update(context_attempt=1))
        with self.assertRaisesRegex(ValueError, "context retries"):
            self.prepare([retried, *self.examples[1:]])

    def test_renamed_group_cannot_split_original_session(self):
        changed = replace(self.examples[1], group_id="another-group")
        with self.assertRaisesRegex(ValueError, "lineage"):
            self.prepare([self.examples[0], changed, *self.examples[2:]])

    def test_copied_history_cannot_cross_group_with_a_new_current_identity(self):
        original = json.loads(self.examples[1].input_bytes)
        def copy_history(payload):
            payload["snapshot"]["observed_at"] = original["snapshot"]["observed_at"]
            payload["snapshot"]["history"] = original["snapshot"]["history"]
        changed = edited(self.examples[3], copy_history)
        with self.assertRaisesRegex(ValueError, "lineage"):
            self.prepare([*self.examples[:3], changed, *self.examples[4:]])

    def test_one_group_cannot_mix_normal_and_challenge_classification(self):
        changed = replace(self.examples[1], label="CHALLENGE")
        with self.assertRaisesRegex(ValueError, "one classification"):
            self.prepare([self.examples[0], changed, *self.examples[2:]])

    def test_input_limits_stop_unbounded_iterator(self):
        with patch("lab.anomaly_training.MAX_EXAMPLES", 2), self.assertRaisesRegex(ValueError, "example limit"):
            self.prepare(iter(self.examples))
        with patch("lab.anomaly_training.MAX_DATASET_BYTES", 1), self.assertRaisesRegex(ValueError, "byte limit"):
            self.prepare()

    def test_insufficient_data_cannot_fit(self):
        result = self.prepare()
        self.assertEqual(len(training_readiness(result)), 2)
        with self.assertRaisesRegex(ValueError, "1000"):
            train_and_evaluate(self.examples, self.baseline)

    def test_no_numeric_vector_bypass_and_invalid_metadata(self):
        with self.assertRaisesRegex(ValueError, "not numeric vectors"):
            self.prepare([[0.0] * len(FEATURE_NAMES)])
        for override in ({"label": []}, {"group_id": ""}, {"scenario": "has spaces"}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.prepare([replace(self.examples[0], **override)])
        for seed in (True, -1, 2**32):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                self.prepare(seed=seed)

    def test_preparation_does_not_import_numerical_training_runtime(self):
        code = "import sys; import lab.anomaly_training; assert not {'sklearn', 'numpy', 'scipy'} & sys.modules.keys()"
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True)


HAS_TRAINING_DEPS = all(importlib.util.find_spec(name) is not None
                        for name in ("numpy", "sklearn", "threadpoolctl"))


@unittest.skipUnless(HAS_TRAINING_DEPS, "install requirements-anomaly-training.txt for real-estimator lab tests")
class ForestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training_run = train_and_evaluate(generate_examples(), baseline())

    def test_real_fit_uses_bounded_single_worker_settings(self):
        model = self.training_run.model
        self.assertEqual(len(model.estimators_), ESTIMATORS)
        self.assertEqual(model.max_samples_, TREE_SAMPLES)
        self.assertEqual(model.n_features_in_, len(FEATURE_NAMES))
        self.assertEqual(model.n_jobs, 1)
        self.assertFalse(model.warm_start)

    def test_calibration_and_report_reuse_finite_tail_rank(self):
        reference, report = self.training_run.calibration, self.training_run.report
        self.assertEqual(len(reference.samples), 1200)
        self.assertGreater(len(set(reference.samples)), 1)
        payload = report["calibration"]["reference"]
        self.assertEqual(sha256(json_bytes(payload)).hexdigest(), report["calibration"]["sha256"])
        for row in report["evaluation_samples"]:
            mapped = reference.score(row["raw_score"])
            self.assertEqual((row["score"], row["band"]), (mapped.score, mapped.result))
        self.assertFalse(report["model_persisted"])
        self.assertIsNone(report["model_sha256"])
        self.assertFalse(report["deployment_ready"])
        json_bytes(report)  # Complete report can be strict JSON without NaN/Infinity.

    def test_forest_does_not_erase_or_manufacture_novelty(self):
        report = self.training_run.report
        self.assertIn("agent_known", report["constant_training_features"])
        cases = [row for row in report["evaluation_samples"] if row["scenario"] == "new_agent"]
        self.assertEqual(len(cases), 20)
        self.assertTrue(all("AGENT_UNSEEN" in row["novelty_flags"] for row in cases))
        # Intentionally no assertion that a new agent must have a high ML band.

    def test_metrics_partition_held_out_normals_and_legitimate_changes(self):
        report = self.training_run.report
        self.assertEqual(report["normal_evaluation"]["sample_count"], 1200)
        self.assertEqual(report["normal_diagnostics"]["sample_count"] +
                         report["normal_changes"]["sample_count"], 1200)
        self.assertGreater(report["normal_changes"]["sample_count"], 0)
        self.assertEqual(len(report["evaluation_samples"]), 1300)
        self.assertEqual(sum(report["normal_evaluation"]["bands"].values()), 1200)


if __name__ == "__main__":
    unittest.main()
