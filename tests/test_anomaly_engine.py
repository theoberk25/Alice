"""Score-mapping tests; these do not assert Isolation Forest detection quality."""

from dataclasses import FrozenInstanceError
from itertools import repeat
import math
import unittest

from dcamr.anomaly_engine.scoring import CalibrationReference, severity_band


class ScoreMappingTests(unittest.TestCase):
    def setUp(self):
        self.samples = [-.7] * 10 + [-.6] * 40 + [-.5] * 950
        self.reference = CalibrationReference(self.samples)

    def test_reference_cases_ties_and_endpoints(self):
        for raw, score, band in ((-.5, .475, "LOW"), (-.6, .97, "ELEVATED"),
                                 (-.7, .995, "HIGH"), (-.55, .95, "ELEVATED"),
                                 (-.65, .99, "HIGH"), (-.4, 0, "LOW"), (-.8, 1, "HIGH")):
            with self.subTest(raw=raw):
                actual = self.reference.score(raw)
                self.assertEqual((actual.score, actual.result), (score, band))

    def test_more_abnormal_raw_scores_cannot_lower_rank(self):
        ranks = [self.reference.score(-i / 1000).score for i in range(1000)]
        self.assertEqual(ranks, sorted(ranks))

    def test_boundary_neighbors_do_not_get_rounded_across_thresholds(self):
        for edge, below, at in ((.95, "LOW", "ELEVATED"), (.99, "ELEVATED", "HIGH")):
            self.assertEqual(severity_band(math.nextafter(edge, 0), .95, .99), below)
            self.assertEqual(severity_band(edge, .95, .99), at)

    def test_reference_is_frozen_and_independent_of_input_mutation(self):
        before = self.reference.score(-.6)
        self.samples[:] = [0.0] * 1000
        self.assertEqual(self.reference.score(-.6), before)
        with self.assertRaises(FrozenInstanceError):
            self.reference.high_min = .5

    def test_invalid_reference_rejected_instead_of_zero_score(self):
        for samples in ([], [-.5] * 999, [-.5] * 1000,
                        [-.5] * 999 + [float("nan")],
                        [-.5] * 999 + [True], repeat(-.5)):
            with self.subTest(kind=type(samples)), self.assertRaises(ValueError):
                CalibrationReference(samples)

    def test_invalid_raw_score_and_thresholds_rejected(self):
        for raw in (True, None, "-.5", float("nan"), float("inf")):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.reference.score(raw)
        for elevated, high in ((.99, .95), (.95, .95), (-1, .99), (.95, 2), (True, 1)):
            with self.subTest(elevated=elevated, high=high), self.assertRaises(ValueError):
                CalibrationReference(self.samples, elevated_min=elevated, high_min=high)


if __name__ == "__main__":
    unittest.main()
