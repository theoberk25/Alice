"""Routing, support, lineage isolation and bounded failure for the lab comparison."""

from dataclasses import replace
from contextlib import redirect_stderr
from hashlib import sha256
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.features import build_features
from dcamr.anomaly_engine.scoring import CalibrationReference
from lab.anomaly_training import PreparedExample, json_bytes
from lab.compare_anomaly_calibration import (
    COHORTS, LineageGuard, collect_reference_sources, compare_scores, main, route_batch,
)
from lab.synthetic_anomaly_data import generate_examples


ROOT = Path(__file__).resolve().parents[1]


class CalibrationComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = (ROOT / "tests/fixtures/features/baseline.json").read_bytes()
        cls.baseline = load_baseline(data, expected_sha256=sha256(data).hexdigest())
        cls.examples = tuple(generate_examples(baseline=cls.baseline, normal_sessions=5,
                                              requests_per_session=2, challenge_sessions_per_scenario=1))
        cls.rows = tuple(PreparedExample(row.group_id, row.scenario, row.label,
                         build_features(row.input_bytes, cls.baseline,
                                        expected_sha256=row.input_sha256)) for row in cls.examples)

    def reference(self, values=None, **kwargs):
        return CalibrationReference(values if values is not None else [-0.7] * 20 + [-0.5] * 980,
                                    **kwargs)

    def test_route_uses_fixed_profile_and_applicability_not_score_or_novelty(self):
        diagnostic = next(row.batch for row in self.rows if row.batch.values[4] == 0)
        change = next(row.batch for row in self.rows if row.batch.values[4] == 1)
        self.assertEqual(route_batch(diagnostic), "diagnostic")
        self.assertEqual(route_batch(change), "state_change")
        self.assertEqual(route_batch(replace(change, novelty_flags=("DESTINATION_UNSEEN",))), "state_change")
        for invalid in (0.5, float("nan"), True):
            values = list(change.values)
            values[4] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                route_batch(replace(change, values=tuple(values)))
        with self.assertRaisesRegex(ValueError, "profile"):
            route_batch(replace(change, feature_schema_version="motor-v1"))
        with self.assertRaisesRegex(ValueError, "profile"):
            route_batch(replace(change, names=tuple(reversed(change.names))))

    def test_each_reference_requires_real_minimum_and_nondegenerate_raw_scores(self):
        for samples in ([-0.7] * 499 + [-0.5] * 500, [-0.5] * 1000):
            with self.subTest(count=len(samples)), self.assertRaises(ValueError):
                self.reference(samples)

    def test_missing_family_or_changed_threshold_never_falls_back(self):
        reference = self.reference()
        rows = self.rows[:1]
        for mapping in ({}, {"diagnostic": reference}, {"diagnostic": reference, "other": reference}):
            with self.subTest(keys=list(mapping)), self.assertRaisesRegex(ValueError, "no global fallback"):
                compare_scores(rows, [-0.6], reference, mapping)
        with self.assertRaisesRegex(ValueError, "thresholds"):
            compare_scores(rows, [-0.6], reference,
                           {"diagnostic": reference, "state_change": self.reference(elevated_min=0.9)})
        with self.assertRaisesRegex(ValueError, "fixed"):
            compare_scores(rows, [-0.6], self.reference(elevated_min=0.9),
                           {cohort: reference for cohort in COHORTS})

    def test_one_raw_score_and_novelty_flags_are_preserved_in_both_mappings(self):
        global_reference = self.reference()
        conditional = self.reference([-0.8] * 500 + [-0.4] * 500)
        rows = tuple(row for row in self.rows if row.label == "CHALLENGE")
        raw = [-0.6] * len(rows)
        measured = compare_scores(rows, raw, global_reference,
                                  {cohort: conditional for cohort in COHORTS})
        for source, output in zip(rows, measured):
            self.assertEqual(output["raw_score"], -0.6)
            self.assertEqual(output["novelty_flags"], list(source.batch.novelty_flags))
            self.assertEqual(output["global"]["score"], global_reference.score(-0.6).score)
            self.assertEqual(output["conditional"]["score"], conditional.score(-0.6).score)
            self.assertNotEqual(output["global"]["score"], output["conditional"]["score"])
        with self.assertRaisesRegex(ValueError, "counts"):
            compare_scores(rows, [], global_reference, {cohort: conditional for cohort in COHORTS})

    def test_correlated_session_sources_cannot_cross_comparison_pools(self):
        first, later = self.examples[:2]
        guard = LineageGuard()
        guard.observe(first, "fit")
        with self.assertRaisesRegex(ValueError, "overlaps"):
            guard.observe(later, "conditional")

    def test_same_partition_history_reuse_is_valid_but_current_retry_is_not(self):
        guard = LineageGuard()
        guard.observe(self.examples[0], "conditional")
        guard.observe(self.examples[1], "conditional")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            guard.observe(self.examples[1], "conditional")

    def test_changed_bytes_and_copied_history_are_detected(self):
        example = self.examples[0]
        with self.assertRaisesRegex(ValueError, "digest"):
            LineageGuard().observe(replace(example, input_bytes=example.input_bytes + b" "), "fit")
        import json
        guard = LineageGuard()
        guard.observe(example, "fit")
        other = self.examples[2]
        payload = json.loads(other.input_bytes)
        copied = json.loads(self.examples[1].input_bytes)["snapshot"]["history"]
        payload["snapshot"]["history"] = copied
        data = json_bytes(payload)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            guard.observe(replace(other, input_bytes=data, input_sha256=sha256(data).hexdigest()), "evaluation")

    def test_fresh_seed_lineage_is_deterministic_and_disjoint(self):
        kwargs = dict(baseline=self.baseline, seed=1730, normal_sessions=5,
                      requests_per_session=2, challenge_sessions_per_scenario=0)
        fresh = tuple(generate_examples(**kwargs))
        repeated = tuple(generate_examples(**kwargs))
        self.assertEqual([row.input_sha256 for row in fresh], [row.input_sha256 for row in repeated])
        guard = LineageGuard()
        for row in self.examples:
            guard.observe(row, "original")
        for row in fresh:
            guard.observe(row, "conditional")
        evaluation = tuple(generate_examples(**{**kwargs, "seed": 1829}))
        for row in evaluation:
            guard.observe(row, "fresh_evaluation")
        groups = [{row.group_id for row in pool} for pool in (self.examples, fresh, evaluation)]
        self.assertFalse(groups[0] & groups[2])
        self.assertFalse(groups[1] & groups[2])

    def test_collector_reports_insufficient_support_without_padding(self):
        normal = self.examples[:2]
        calls = []
        def few(**kwargs):
            calls.append(kwargs)
            return iter(normal)
        with self.assertRaisesRegex(ValueError, "insufficient conditional"):
            collect_reference_sources(self.baseline, seed=1729, guard=LineageGuard(),
                                      max_batches=1, generator=few)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["seed"], 1730)
        self.assertEqual(calls[0]["challenge_sessions_per_scenario"], 0)

    def test_collector_never_admits_challenges_baseline_mismatch_or_retries(self):
        challenge = next(row for row in self.examples if row.label == "CHALLENGE")
        wrong_baseline = replace(self.examples[0], baseline_sha256="0" * 64)
        for row in (challenge, wrong_baseline):
            with self.subTest(label=row.label), self.assertRaisesRegex(ValueError, "normal sources"):
                collect_reference_sources(self.baseline, seed=1729, guard=LineageGuard(),
                                          max_batches=1, generator=lambda **_: iter([row]))
        import json
        row = self.examples[0]
        payload = json.loads(row.input_bytes)
        payload["snapshot"]["context_attempt"] = 1
        data = json_bytes(payload)
        retry = replace(row, input_bytes=data, input_sha256=sha256(data).hexdigest())
        with self.assertRaisesRegex(ValueError, "context retries"):
            collect_reference_sources(self.baseline, seed=1729, guard=LineageGuard(),
                                      max_batches=1, generator=lambda **_: iter([retry]))

    def test_collector_budget_and_seed_validation_are_bounded(self):
        for bad in (0, 9, True):
            with self.subTest(batches=bad), self.assertRaisesRegex(ValueError, "batches"):
                collect_reference_sources(self.baseline, seed=1729, guard=LineageGuard(), max_batches=bad)
        for bad in (-1, True, 2**32 - 1):
            with self.subTest(seed=bad), self.assertRaisesRegex(ValueError, "seed"):
                collect_reference_sources(self.baseline, seed=bad, guard=LineageGuard())
        with patch("lab.compare_anomaly_calibration.ROWS_PER_BATCH", 1), self.assertRaisesRegex(ValueError, "budget"):
            collect_reference_sources(self.baseline, seed=1729, guard=LineageGuard(), max_batches=1,
                                      generator=lambda **_: iter(self.examples[:2]))
        with patch("lab.compare_anomaly_calibration.MAX_DATASET_BYTES", 1), self.assertRaisesRegex(ValueError, "budget"):
            collect_reference_sources(self.baseline, seed=1729, guard=LineageGuard(), max_batches=1,
                                      generator=lambda **_: iter(self.examples[:1]))

    def test_existing_output_is_preserved_before_any_training(self):
        with tempfile.TemporaryDirectory() as existing, patch("lab.compare_anomaly_calibration.run_comparison") as run, patch("sys.stderr"):
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as raised:
                main(["--output", existing])
            self.assertEqual(raised.exception.code, 2)
            run.assert_not_called()

    def test_import_does_not_load_training_runtime(self):
        code = ("import sys; import lab.compare_anomaly_calibration; "
                "assert not {'numpy','sklearn','scipy'} & sys.modules.keys()")
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
