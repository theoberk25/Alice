"""Bounded, domain-neutral observations for contextual anomaly experiments.

These contracts preserve supplied measurements and their provenance; they do not
extract sensor features, establish identity, define safe operating ranges, or
authorize actions. The trusted caller authenticates sources before binding exact
bytes. Their SHA-256 digests provide correlation, not signature verification.
"""

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import math
import re


PROFILE_SCHEMA_VERSION = "context-behavior-profile-v1"
OBSERVATION_SCHEMA_VERSION = "context-behavior-observation-v1"
MAX_PROFILE_BYTES = 16 * 1024
MAX_OBSERVATION_BYTES = 32 * 1024
MAX_FEATURES = 32
MAX_CONTEXT_KEYS = 4
MAX_AGE_MS = 86_400_000
MAX_TIMESTAMP_MS = 2**53 - 1
FLOAT32_MAX = 3.4028234663852886e38
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_PHASES = {"PRE_ACTION", "POST_ACTION"}
_FEATURE_TIMINGS = {"AT_OR_BEFORE_REQUEST", "AT_OR_AFTER_EXECUTION"}


class ContextError(ValueError):
    """Typed failure without echoing untrusted measurements or identifiers."""

    def __init__(self, code: str, field: str = "payload", *, status: str = "INVALID_INPUT") -> None:
        self.code = code
        self.field = field
        self.status = status
        super().__init__(f"{code}: {field}")


def json_bytes(value: object) -> bytes:
    """Stable local serialization; not the shared package-signing protocol."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ContextError("INPUT_INVALID", field)
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise ContextError("INPUT_INVALID", field)
    return value


def _integer(value: object, field: str, maximum: int = MAX_TIMESTAMP_MS) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ContextError("INPUT_INVALID", field)
    return value


def _unit(value: object, field: str) -> str:
    if (type(value) is not str or not 1 <= len(value) <= 64
            or not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ContextError("INPUT_INVALID", field)
    try:
        if len(value.encode("utf-8")) > 128:
            raise ContextError("INPUT_INVALID", field)
    except UnicodeError:
        raise ContextError("INPUT_INVALID", field) from None
    return value


def _phase(value: object) -> str:
    if type(value) is not str or value not in _PHASES:
        raise ContextError("INPUT_INVALID", "phase")
    return value


def _fields(value: object, expected: set[str], field: str) -> dict:
    if type(value) is not dict or set(value) != expected:
        raise ContextError("INPUT_INVALID", field)
    return value


def _number(value: object, field: str) -> float:
    if type(value) not in (int, float):
        raise ContextError("INPUT_INVALID", field)
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        raise ContextError("INPUT_INVALID", field) from None
    if not math.isfinite(converted) or abs(converted) > FLOAT32_MAX:
        raise ContextError("INPUT_INVALID", field)
    return converted


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContextError("INPUT_INVALID", "json.duplicate_key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise ContextError("INPUT_INVALID", "json.number")


def _walk(value: object, depth: int = 0) -> None:
    if depth > 12:
        raise ContextError("INPUT_LIMIT_EXCEEDED", "json.depth")
    if type(value) is dict:
        if len(value) > 128:
            raise ContextError("INPUT_LIMIT_EXCEEDED", "json.object")
        for key, item in value.items():
            _walk(key, depth + 1)
            _walk(item, depth + 1)
    elif type(value) is list:
        if len(value) > 128:
            raise ContextError("INPUT_LIMIT_EXCEEDED", "json.array")
        for item in value:
            _walk(item, depth + 1)
    elif type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise ContextError("INPUT_INVALID", "json.unicode") from None
    elif type(value) is float and not math.isfinite(value):
        raise ContextError("INPUT_INVALID", "json.number")


def _parse(data: bytes, expected_sha256: str, max_bytes: int) -> tuple[dict, str]:
    if type(data) is not bytes:
        raise ContextError("INPUT_INVALID", "payload")
    if len(data) > max_bytes:
        raise ContextError("INPUT_LIMIT_EXCEEDED", "payload")
    _digest(expected_sha256, "expected_sha256")
    digest = sha256(data).hexdigest()
    if not hmac.compare_digest(digest, expected_sha256):
        raise ContextError("DIGEST_MISMATCH", "payload.sha256")
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=_constant)
        _walk(result)
    except ContextError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ContextError("INPUT_INVALID", "json") from None
    if type(result) is not dict:
        raise ContextError("INPUT_INVALID", "payload")
    return result, digest


@dataclass(frozen=True, slots=True)
class NumericFeature:
    name: str
    unit: str
    max_age_ms: int
    timing: str

    def __post_init__(self) -> None:
        _identifier(self.name, "feature.name")
        _unit(self.unit, "feature.unit")
        _integer(self.max_age_ms, "feature.max_age_ms", MAX_AGE_MS)
        if type(self.timing) is not str or self.timing not in _FEATURE_TIMINGS:
            raise ContextError("INPUT_INVALID", "feature.timing")


@dataclass(frozen=True, slots=True)
class ContextProfile:
    sha256: str
    profile_id: str
    version: str
    phase: str
    features: tuple[NumericFeature, ...]
    context_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _digest(self.sha256, "profile.sha256")
        _identifier(self.profile_id, "profile_id")
        _identifier(self.version, "version")
        _phase(self.phase)
        if (type(self.features) is not tuple or not 1 <= len(self.features) <= MAX_FEATURES
                or any(type(feature) is not NumericFeature for feature in self.features)
                or len({feature.name for feature in self.features}) != len(self.features)):
            raise ContextError("INPUT_INVALID", "features")
        has_outcome = any(feature.timing == "AT_OR_AFTER_EXECUTION" for feature in self.features)
        if (self.phase == "PRE_ACTION" and has_outcome) or (self.phase == "POST_ACTION" and not has_outcome):
            raise ContextError("INPUT_INVALID", "features.timing")
        if type(self.context_keys) is not tuple or not 1 <= len(self.context_keys) <= MAX_CONTEXT_KEYS:
            raise ContextError("INPUT_INVALID", "context_keys")
        for key in self.context_keys:
            _identifier(key, "context_keys")
        if len(set(self.context_keys)) != len(self.context_keys):
            raise ContextError("INPUT_INVALID", "context_keys")


@dataclass(frozen=True, slots=True)
class ContextObservation:
    observation_id: str
    request_id: str
    session_id: str
    phase: str
    request_at_ms: int
    cutoff_at_ms: int
    execution_id: str | None
    execution_at_ms: int | None
    profile_sha256: str
    input_sha256: str
    context: tuple[tuple[str, str], ...]
    values: tuple[float, ...]
    source_ids: tuple[str, ...]
    observed_at_ms: tuple[int, ...]


def load_context_profile(data: bytes, *, expected_sha256: str) -> ContextProfile:
    payload, digest = _parse(data, expected_sha256, MAX_PROFILE_BYTES)
    _fields(payload, {"schema_version", "profile_id", "version", "phase", "features", "context_keys"},
            "profile")
    if payload["schema_version"] != PROFILE_SCHEMA_VERSION:
        raise ContextError("INPUT_INVALID", "schema_version")
    features, keys = payload["features"], payload["context_keys"]
    if type(features) is not list or not 1 <= len(features) <= MAX_FEATURES:
        raise ContextError("INPUT_INVALID", "features")
    if type(keys) is not list or not 1 <= len(keys) <= MAX_CONTEXT_KEYS:
        raise ContextError("INPUT_INVALID", "context_keys")
    frozen_features = []
    for value in features:
        feature = _fields(value, {"name", "unit", "max_age_ms", "timing"}, "features.item")
        frozen_features.append(NumericFeature(feature["name"], feature["unit"], feature["max_age_ms"],
                                              feature["timing"]))
    return ContextProfile(digest, payload["profile_id"], payload["version"], payload["phase"],
                          tuple(frozen_features), tuple(keys))


def parse_context_observation(data: bytes, profile: ContextProfile, *,
                              expected_sha256: str) -> ContextObservation:
    """Freeze supplied features in profile order, rejecting unavailable telemetry.

    PRE_ACTION has an exact request-time cutoff and no execution metadata.
    POST_ACTION has a separately bound execution and cutoff, with at least one
    feature observed at or after execution. A profile can preserve request-time
    context alongside those outcome features. Both phases use only observations
    at or before the cutoff. These comparisons rely on trusted timestamps; they
    do not establish sensor causality or prove the requested physical effect.
    """
    if type(profile) is not ContextProfile:
        raise ContextError("INPUT_INVALID", "profile")
    payload, digest = _parse(data, expected_sha256, MAX_OBSERVATION_BYTES)
    _fields(payload, {"schema_version", "profile_sha256", "observation_id", "request_id", "session_id",
                      "phase", "request_at_ms", "cutoff_at_ms", "execution_id", "execution_at_ms",
                      "context", "measurements"}, "observation")
    if payload["schema_version"] != OBSERVATION_SCHEMA_VERSION:
        raise ContextError("INPUT_INVALID", "schema_version")
    supplied_profile = _digest(payload["profile_sha256"], "profile_sha256")
    if not hmac.compare_digest(supplied_profile, profile.sha256):
        raise ContextError("PROFILE_MISMATCH", "profile_sha256")
    phase = _phase(payload["phase"])
    if phase != profile.phase:
        raise ContextError("PHASE_MISMATCH", "phase")
    identities = tuple(_identifier(payload[key], key)
                       for key in ("observation_id", "request_id", "session_id"))
    request_at = _integer(payload["request_at_ms"], "request_at_ms")
    cutoff_at = _integer(payload["cutoff_at_ms"], "cutoff_at_ms")
    execution_id, execution_at = payload["execution_id"], payload["execution_at_ms"]
    if phase == "PRE_ACTION":
        if cutoff_at != request_at or execution_id is not None or execution_at is not None:
            raise ContextError("TEMPORAL_BINDING_INVALID", "execution")
    else:
        _identifier(execution_id, "execution_id")
        _integer(execution_at, "execution_at_ms")
        if not request_at <= execution_at <= cutoff_at:
            raise ContextError("TEMPORAL_BINDING_INVALID", "execution")
    context = _fields(payload["context"], set(profile.context_keys), "context")
    selected_context = tuple((key, _identifier(context[key], "context.value"))
                             for key in profile.context_keys)
    measurements = _fields(payload["measurements"], {feature.name for feature in profile.features},
                           "measurements")
    values, sources, times = [], [], []
    for feature in profile.features:
        reading = _fields(measurements[feature.name], {"value", "unit", "observed_at_ms", "source_id"},
                          "measurements.item")
        if _unit(reading["unit"], "measurement.unit") != feature.unit:
            raise ContextError("UNIT_MISMATCH", "measurement.unit")
        # Validate every present field before reporting a null as unavailable.
        # A malformed field must not hide behind another field's missing value.
        value = None if reading["value"] is None else _number(reading["value"], "measurement.value")
        observed_at = (None if reading["observed_at_ms"] is None
                       else _integer(reading["observed_at_ms"], "measurement.observed_at_ms"))
        source = (None if reading["source_id"] is None
                  else _identifier(reading["source_id"], "measurement.source_id"))
        if value is None or observed_at is None or source is None:
            raise ContextError("TELEMETRY_MISSING", "measurement", status="UNAVAILABLE")
        if ((feature.timing == "AT_OR_BEFORE_REQUEST" and observed_at > request_at)
                or (feature.timing == "AT_OR_AFTER_EXECUTION" and observed_at < execution_at)):
            raise ContextError("TEMPORAL_FEATURE_MISMATCH", "measurement.observed_at_ms", status="UNAVAILABLE")
        if observed_at > cutoff_at:
            raise ContextError("FUTURE_OBSERVATION", "measurement.observed_at_ms", status="UNAVAILABLE")
        if cutoff_at - observed_at > feature.max_age_ms:
            raise ContextError("STALE_OBSERVATION", "measurement.observed_at_ms", status="UNAVAILABLE")
        values.append(value)
        sources.append(source)
        times.append(observed_at)
    return ContextObservation(*identities, phase, request_at, cutoff_at, execution_id, execution_at,
                              profile.sha256, digest, selected_context, tuple(values), tuple(sources),
                              tuple(times))
