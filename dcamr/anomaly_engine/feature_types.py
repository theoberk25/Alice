"""Immutable feature artifacts and typed failures; no anomaly scores or decisions."""

from dataclasses import asdict, dataclass


FEATURE_NAMES = (
    "agent_known", "action_seen_for_profile", "target_known", "profile_target_seen",
    "destination_applicable", "destination_seen", "action_frequency",
    "recent_request_count_5m", "recent_executed_state_changes_5m",
    "sequence_has_previous", "sequence_transition_probability",
)
FEATURE_SCHEMA_VERSION = "cyber-behavior-v1"


class FeatureError(ValueError):
    """Future evaluator maps this to a non-OK result with a null score.

    No input values or arbitrary exception text are echoed into diagnostics.
    """

    def __init__(self, code: str, field: str, *, status: str = "UNAVAILABLE") -> None:
        self.code = code
        self.field = field
        self.status = status
        super().__init__(f"{code}: {field}")


@dataclass(frozen=True, slots=True)
class BaselineIdentity:
    package_id: str
    version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class Factor:
    id: str
    state: str
    observed: bool | float | None
    expected: bool | float | None
    unit: str
    baseline_ref: str | None
    observation_ref: str | None


@dataclass(frozen=True, slots=True)
class FeatureSource:
    feature: str
    baseline_ref: str | None
    observation_ref: str


@dataclass(frozen=True, slots=True)
class FeatureBatch:
    """Numeric model input with independently bound provenance, not AnomalyResult."""

    feature_schema_version: str
    input_sha256: str
    baseline: BaselineIdentity
    request_id: str
    request_sha256: str
    snapshot_id: str
    snapshot_sha256: str
    context_attempt: int
    selected_profile_id: str
    profile_source: str
    names: tuple[str, ...]
    values: tuple[float, ...]
    sources: tuple[FeatureSource, ...]
    factors: tuple[Factor, ...]
    novelty_flags: tuple[str, ...]

    def to_dict(self) -> dict:
        """Return an independent display/transport copy of the immutable batch."""
        result = asdict(self)
        for field in ("names", "values", "sources", "factors", "novelty_flags"):
            result[field] = list(result[field])
        return result
