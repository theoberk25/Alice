"""Small, offline score mapping; no training, model loading, or authorization."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from itertools import islice
import math
from typing import Iterable


MIN_CALIBRATION_SAMPLES = 1_000
MAX_CALIBRATION_SAMPLES = 100_000


def finite_number(value: object, name: str) -> float:
    """Accept JSON numbers, excluding booleans and overflow/non-finite values."""
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def validate_thresholds(elevated_min: float, high_min: float) -> None:
    elevated_min = finite_number(elevated_min, "elevated_min")
    high_min = finite_number(high_min, "high_min")
    if not 0 <= elevated_min < high_min <= 1:
        raise ValueError("thresholds must satisfy 0 <= elevated_min < high_min <= 1")


def severity_band(score: float, elevated_min: float, high_min: float) -> str:
    """Assign a band before display rounding, including exact boundary values."""
    score = finite_number(score, "score")
    validate_thresholds(elevated_min, high_min)
    if not 0 <= score <= 1:
        raise ValueError("score must be in [0, 1]")
    if score < elevated_min:
        return "LOW"
    return "ELEVATED" if score < high_min else "HIGH"


@dataclass(frozen=True, slots=True)
class ScoredSample:
    raw_score: float
    score: float
    result: str


@dataclass(frozen=True, slots=True, init=False)
class CalibrationReference:
    """Frozen normal-score reference, loaded once and searched in O(log N).

    This mapper does not authenticate a reference or establish model quality.
    The future package loader must verify and bind its provenance separately.
    """

    samples: tuple[float, ...]
    elevated_min: float
    high_min: float

    def __init__(
        self,
        samples: Iterable[float],
        *,
        elevated_min: float = 0.95,
        high_min: float = 0.99,
    ) -> None:
        validate_thresholds(elevated_min, high_min)
        # Read at most the limit plus one even if passed an unbounded generator.
        values = tuple(
            finite_number(value, "calibration sample")
            for value in islice(samples, MAX_CALIBRATION_SAMPLES + 1)
        )
        if not MIN_CALIBRATION_SAMPLES <= len(values) <= MAX_CALIBRATION_SAMPLES:
            raise ValueError(
                f"reference needs {MIN_CALIBRATION_SAMPLES}.."
                f"{MAX_CALIBRATION_SAMPLES} samples"
            )
        ordered = tuple(sorted(values))
        if ordered[0] == ordered[-1]:
            raise ValueError("calibration reference must contain distinct scores")
        object.__setattr__(self, "samples", ordered)
        object.__setattr__(self, "elevated_min", float(elevated_min))
        object.__setattr__(self, "high_min", float(high_min))

    def score(self, raw_score: float) -> ScoredSample:
        raw = finite_number(raw_score, "raw_score")
        left = bisect_left(self.samples, raw)
        right = bisect_right(self.samples, raw)
        count = len(self.samples)
        rank = ((count - right) + 0.5 * (right - left)) / count
        return ScoredSample(
            raw, rank, severity_band(rank, self.elevated_min, self.high_min)
        )
