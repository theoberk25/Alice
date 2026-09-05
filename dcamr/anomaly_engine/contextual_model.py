"""Context-routed behavioral scoring; no permission, execution or training API.

Heavy numerical dependencies are imported only for a fitted model's score call.
This in-memory interface is not a model loader, signing protocol or supervised
Pi worker. Its result is separate from the existing cyber AnomalyResult schema.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
import math
from types import MappingProxyType

from .context_profile import ContextError, ContextProfile, parse_context_observation
from .scoring import CalibrationReference


ASSESSMENT_SCHEMA_VERSION = "context-behavior-assessment-v1"


@dataclass(frozen=True, slots=True)
class NumericComparison:
    name: str
    unit: str
    observed: float
    training_min: float
    training_max: float
    outside_training_range: bool
    timing: str
    source_id: str
    observed_at_ms: int


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    schema_version: str
    status: str
    result: str
    raw_score: float | None
    score: float | None
    reason_codes: tuple[str, ...]
    phase: str
    observation_id: str | None
    request_id: str | None
    input_sha256: str | None
    profile_sha256: str
    model_id: str | None
    model_fingerprint: str | None
    calibration_sha256: str | None
    context: tuple[tuple[str, str], ...]
    request_at_ms: int | None
    cutoff_at_ms: int | None
    execution_id: str | None
    execution_at_ms: int | None
    source_ids: tuple[str, ...]
    factors: tuple[NumericComparison, ...]

    def to_dict(self) -> dict:
        """Independent JSON-compatible copy; this is not an execution token."""
        result = asdict(self)
        result["context"] = dict(self.context)
        result["reason_codes"] = list(self.reason_codes)
        result["source_ids"] = list(self.source_ids)
        result["factors"] = list(result["factors"])
        return result


@dataclass(frozen=True, slots=True)
class _ContextState:
    """Private fitted state, constructed only by the Mac training function."""

    estimator: object
    reference: CalibrationReference
    calibration_sha256: str
    minima: tuple[float, ...]
    maxima: tuple[float, ...]


class ContextualModel:
    """Read-only scoring facade over bounded, explicitly supported contexts.

    Each exact context has its own forest and normal calibration reference. A
    new context never falls back to a different operating mode/action. Python
    access to private fields is not a security sandbox; trusted code owns this
    object. The API does not fit or adapt to arriving observations.
    """

    __slots__ = ("_profile", "_model_id", "_fingerprint", "_contexts", "_metadata")

    def __init__(self, profile: ContextProfile, *, model_id: str | None = None,
                 model_fingerprint: str | None = None, contexts=None,
                 metadata: dict | None = None) -> None:
        self._profile = profile
        self._model_id = model_id
        self._fingerprint = model_fingerprint
        self._contexts = MappingProxyType(dict(contexts or {}))
        self._metadata = deepcopy(metadata or {
            "algorithm": "IsolationForest", "profile_sha256": profile.sha256,
            "phase": profile.phase, "context_count": 0, "contexts": [],
            "model_persisted": False, "deployment_ready": False,
        })

    @classmethod
    def untrained(cls, profile: ContextProfile) -> "ContextualModel":
        return cls(profile)

    @property
    def profile(self) -> ContextProfile:
        return self._profile

    @property
    def metadata(self) -> dict:
        return deepcopy(self._metadata)

    def assess(self, input_bytes: bytes, *, expected_sha256: str) -> ContextAssessment:
        """Validate, select an exact context, then score one captured observation.

        Required missing/stale telemetry, unknown context and unavailable models
        produce UNKNOWN with null scores. Invalid input is never silently repaired.
        No network, data retention, model fitting or protected action occurs here.
        A caller must still authenticate input and supervise deadlines/capacity.
        """
        observation = None

        def result(status, band="UNKNOWN", *, raw=None, score=None, reasons=(),
                   calibration_sha256=None, factors=()):
            return ContextAssessment(
                schema_version=ASSESSMENT_SCHEMA_VERSION, status=status,
                result=band, raw_score=raw, score=score, reason_codes=tuple(reasons),
                phase=self._profile.phase,
                observation_id=observation.observation_id if observation else None,
                request_id=observation.request_id if observation else None,
                input_sha256=observation.input_sha256 if observation else None,
                profile_sha256=self._profile.sha256, model_id=self._model_id,
                model_fingerprint=self._fingerprint,
                calibration_sha256=calibration_sha256,
                context=observation.context if observation else (),
                request_at_ms=observation.request_at_ms if observation else None,
                cutoff_at_ms=observation.cutoff_at_ms if observation else None,
                execution_id=observation.execution_id if observation else None,
                execution_at_ms=observation.execution_at_ms if observation else None,
                source_ids=observation.source_ids if observation else (),
                factors=tuple(factors),
            )

        try:
            observation = parse_context_observation(
                input_bytes, self._profile, expected_sha256=expected_sha256)
        except ContextError as exc:
            return result(exc.status, reasons=(exc.code,))
        if not self._contexts:
            return result("UNAVAILABLE", reasons=("MODEL_UNAVAILABLE",))
        state = self._contexts.get(observation.context)
        if state is None:
            return result("UNAVAILABLE", reasons=("CONTEXT_UNSEEN",))
        factors = tuple(
            NumericComparison(feature.name, feature.unit, value, low, high,
                              value < low or value > high, feature.timing, source_id,
                              observed_at)
            for feature, value, low, high, source_id, observed_at in zip(
                self._profile.features, observation.values, state.minima, state.maxima,
                observation.source_ids, observation.observed_at_ms)
        )
        reasons = ("OUTSIDE_TRAINING_RANGE",) if any(
            factor.outside_training_range for factor in factors
        ) else ("WITHIN_TRAINING_RANGES",)
        try:
            import numpy as np
            from threadpoolctl import threadpool_limits
            vector = np.asarray([observation.values], dtype=np.float32)
            if not np.isfinite(vector).all():
                return result("INVALID_INPUT", reasons=("NUMERIC_RANGE_INVALID",))
            # n_jobs on the estimator is fixed to 1 by the trainer. This class
            # scores one observation at a time, with no per-request thread pool.
            with threadpool_limits(limits=1):
                raw_scores = state.estimator.score_samples(vector)
            if len(raw_scores) != 1 or not math.isfinite(float(raw_scores[0])):
                raise ValueError("invalid scorer output")
            scored = state.reference.score(float(raw_scores[0]))
        except Exception:
            # Do not echo estimator/service exception contents into a decision.
            # Resource deadlines/process termination remain a supervisor concern.
            return result("ERROR", reasons=("MODEL_ERROR",),
                          calibration_sha256=state.calibration_sha256, factors=factors)
        return result("OK", scored.result, raw=scored.raw_score, score=scored.score,
                      reasons=reasons, calibration_sha256=state.calibration_sha256,
                      factors=factors)
