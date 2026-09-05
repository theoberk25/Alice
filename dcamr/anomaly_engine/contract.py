"""Strict anomaly-result parsing and dispatch binding. Never grants permission."""

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .scoring import finite_number, severity_band, validate_thresholds


MAX_RESULT_BYTES = 16 * 1024
MAX_JSON_DEPTH = 16
SCHEMA_PATH = files("common.schemas").joinpath("anomaly_result.json")
CORRELATION_FIELDS = (
    "evaluation_id", "previous_evaluation_id", "request_id", "request_sha256",
    "input_snapshot",
)
ARTIFACT_FIELDS = ("baseline", "model", "calibration")
SUCCESS_REASONS = {
    "WITHIN_BASELINE", "AGENT_UNSEEN", "TARGET_UNSEEN", "DESTINATION_UNSEEN",
    "SEQUENCE_UNUSUAL", "REQUEST_RATE_UNUSUAL", "OUTSIDE_OPERATING_WINDOW",
    "HIGH_MODEL_ANOMALY", "ELEVATED_MODEL_ANOMALY",
}
FAILURE_REASONS = {
    "UNAVAILABLE": {
        "BASELINE_MISSING", "BASELINE_EXPIRED", "BASELINE_UNTRUSTED", "MODEL_MISSING",
        "MODEL_BASELINE_MISMATCH", "CALIBRATION_INVALID", "FEATURE_SCHEMA_MISMATCH",
        "REQUIRED_INPUT_MISSING", "INPUT_STALE", "INPUT_UNSUPPORTED", "CLOCK_UNTRUSTED",
        "HISTORY_INCOMPLETE", "HISTORY_CAPACITY_EXCEEDED", "CAPACITY_EXCEEDED",
    },
    "INVALID_INPUT": {"INPUT_NONFINITE", "INPUT_UNSUPPORTED", "INPUT_LIMIT_EXCEEDED"},
    "TIMEOUT": {"INFERENCE_TIMEOUT"},
    "ERROR": {"INFERENCE_ERROR"},
    "SKIPPED": {"POLICY_DENY_SHORT_CIRCUIT"},
}


class ContractError(ValueError):
    """A bounded diagnostic without echoing the untrusted payload."""


def _reject_constant(_: str) -> None:
    raise ContractError("JSON numbers must be finite")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON object key")
        result[key] = value
    return result


def _check_tree(value: Any, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ContractError("JSON nesting exceeds limit")
    if type(value) is dict:
        if len(value) > 64:
            raise ContractError("JSON object exceeds field limit")
        for key, item in value.items():
            if type(key) is not str:
                raise ContractError("JSON object keys must be strings")
            _check_tree(item, depth + 1)
    elif type(value) is list:
        if len(value) > 16:
            raise ContractError("JSON array exceeds item limit")
        for item in value:
            _check_tree(item, depth + 1)
    elif type(value) in (int, float):
        try:
            finite_number(value, "JSON value")
        except ValueError as exc:
            raise ContractError(str(exc)) from exc
    elif value is not None and type(value) not in (str, bool):
        raise ContractError("unsupported JSON value type")


def _encode(value: Any) -> str:
    _check_tree(value)
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False,
                             sort_keys=True, separators=(",", ":"))
        size = len(encoded.encode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("value is not valid UTF-8 JSON") from exc
    if size > MAX_RESULT_BYTES:
        raise ContractError("result exceeds 16 KiB")
    return encoded


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()

    @checker.checks("date-time", raises=(ValueError, TypeError))
    def utc_datetime(value: Any) -> bool:
        if not isinstance(value, str):
            return True  # Type constraints handle non-strings.
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0

    return Draft202012Validator(schema, format_checker=checker)


def validate_result(result: Any) -> None:
    """Validate structure and semantics, including fields JSON Schema cannot relate."""
    _encode(result)
    error = next(_validator().iter_errors(result), None)
    if error is not None:
        # Schema validation messages can embed entire values; expose only a path.
        path = "/".join(map(str, error.absolute_path)) or "$"
        raise ContractError(f"schema violation at {path[:256]} ({error.validator})")
    reasons = set(result["reason_codes"])
    if result["status"] == "OK":
        if not reasons <= SUCCESS_REASONS:
            raise ContractError("OK status cannot contain failure reasons")
        band_reason = {"ELEVATED": "ELEVATED_MODEL_ANOMALY", "HIGH": "HIGH_MODEL_ANOMALY"}
        for band, code in band_reason.items():
            if (result["result"] == band) != (code in reasons):
                raise ContractError("behavioral band and model reason must agree")
        if "WITHIN_BASELINE" in reasons:
            if result["result"] != "LOW" or reasons != {"WITHIN_BASELINE"}:
                raise ContractError("WITHIN_BASELINE cannot accompany anomaly reasons")
            if any(f["state"] in ("UNUSUAL", "UNKNOWN") for f in result["factors"]):
                raise ContractError("WITHIN_BASELINE conflicts with factor observations")
    else:
        required_reasons = FAILURE_REASONS[result["status"]]
        observations = SUCCESS_REASONS - {
            "WITHIN_BASELINE", "HIGH_MODEL_ANOMALY", "ELEVATED_MODEL_ANOMALY"
        }
        allowed = required_reasons | observations | {"CLOCK_UNTRUSTED"}
        if not reasons & required_reasons or not reasons <= allowed:
            raise ContractError("failure status requires compatible reasons only")
    for name, values in [("reason_codes", result["reason_codes"]),
                         *result["quality"].items()]:
        if values != sorted(set(values)):
            raise ContractError(f"{name} must be sorted and unique")
    ids = [factor["id"] for factor in result["factors"]]
    if ids != sorted(set(ids)):
        raise ContractError("factor IDs must be sorted and unique")
    for factor in result["factors"]:
        if factor["state"] == "UNKNOWN":
            paths = [path for values in result["quality"].values() for path in values]
            if not any(factor["id"] == path.split(".")[-1] for path in paths):
                raise ContractError("UNKNOWN factor needs a matching quality field path")
            if not reasons & (FAILURE_REASONS["UNAVAILABLE"] | FAILURE_REASONS["INVALID_INPUT"]):
                raise ContractError("UNKNOWN factor needs an input/availability reason")
    calibration = result["calibration"]
    if calibration is not None:
        try:
            validate_thresholds(calibration["elevated_min"], calibration["high_min"])
        except ValueError as exc:
            raise ContractError(str(exc)) from exc
    if result["status"] == "OK":
        if any(result["quality"].values()):
            raise ContractError("OK result cannot have missing, stale or unsupported inputs")
        expected = severity_band(result["score"], calibration["elevated_min"],
                                 calibration["high_min"])
        if result["result"] != expected:
            raise ContractError("result band does not match score and thresholds")
        if calibration["sample_count"] < 1000:
            raise ContractError("OK result requires at least 1000 calibration samples")
    if result["baseline"] is not None:
        baseline = result["baseline"]
        expected_source = f"OPS_BASELINE:{baseline['package_id']}/{baseline['version']}"
        if result["source"] != expected_source:
            raise ContractError("source must identify the accepted baseline")
    elif result["source"] is not None:
        raise ContractError("source must be null without an accepted baseline")


def parse_result(payload: str | bytes) -> dict[str, Any]:
    """Parse a bounded UTF-8 envelope; reject duplicate keys and non-finite values."""
    try:
        raw = payload.encode("utf-8") if isinstance(payload, str) else payload
        if not isinstance(raw, bytes):
            raise ContractError("payload must be UTF-8 str or bytes")
        if len(raw) > MAX_RESULT_BYTES:
            raise ContractError("result exceeds 16 KiB")
        decoded = raw.decode("utf-8")
        result = json.loads(decoded, parse_constant=_reject_constant,
                            object_pairs_hook=_unique_object)
    except ContractError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError("invalid UTF-8 JSON result") from exc
    validate_result(result)
    return result


def serialize_result(result: dict[str, Any]) -> str:
    """Emit deterministic JSON; this is not the shared request-hashing protocol."""
    validate_result(result)
    return _encode(result)


def _select(context: dict[str, Any], fields: tuple[str, ...]) -> str:
    try:
        return _encode({key: context[key] for key in fields})
    except KeyError as exc:
        raise ContractError("trusted dispatch context is incomplete") from exc


@dataclass(frozen=True, slots=True)
class EvaluationBinding:
    """Immutable copies of trusted dispatch metadata, not supplied by the agent.

    Construct before dispatch from DCAMR's normalized request, snapshot and
    accepted artifacts. Do not construct this from an arriving model result.
    Full request canonicalization, signature verification and expiry are owned
    by their respective DCAMR components, not by this comparison helper.
    """

    correlation_json: str
    artifacts_json: str

    @classmethod
    def capture(cls, trusted_context: dict[str, Any]) -> "EvaluationBinding":
        return cls(_select(trusted_context, CORRELATION_FIELDS),
                   _select(trusted_context, ARTIFACT_FIELDS))

    def check(
        self,
        result: dict[str, Any],
        *,
        active_artifacts: dict[str, Any],
        allow_fixtures: bool = False,
    ) -> None:
        """Check correspondence only; even a matching OK result is not permission."""
        validate_result(result)
        if result["runtime"]["execution_mode"] == "FIXTURE" and not allow_fixtures:
            raise ContractError("FIXTURE result is forbidden on the live path")
        if _select(result, CORRELATION_FIELDS) != self.correlation_json:
            raise ContractError("ANOMALY_RESULT_MISMATCH: dispatch correlation")
        if _select(result, ARTIFACT_FIELDS) != self.artifacts_json:
            raise ContractError("ANOMALY_RESULT_MISMATCH: dispatched artifacts")
        if result["status"] == "OK":
            if _select(active_artifacts, ARTIFACT_FIELDS) != self.artifacts_json:
                raise ContractError("ANOMALY_RESULT_MISMATCH: active artifacts changed")
