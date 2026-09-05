"""Strict local audit records, independent of anomaly/request wire contracts.

These checks establish bounded structure and correspondence, never source trust,
execution permission, evidence availability, or the physical truth of a reading.
"""

from copy import deepcopy
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


MAX_EVENT_BYTES = 16 * 1024
MAX_JSON_DEPTH = 16
GENESIS_HASH = "0" * 64
SCHEMA_VERSION = "alice-audit-event-v1"
CANONICALIZATION_VERSION = "alice-json-v1"
INPUT_FIELDS = ("event_id", "event_type", "correlation", "attribution", "authority", "provenance", "detail")
EVENT_TYPES = ("REQUEST", "REJECTION", "ASSESSMENT", "DECISION", "CONTEXT_CHALLENGE", "CONTEXT_RESPONSE",
               "TECHNICIAN_ACTION", "EXECUTION_ATTEMPT", "CONTROLLER_RECEIPT", "EXECUTION_RESULT",
               "OBSERVED_STATE", "AUTHORITY_TRANSITION", "CACHE_ACTIVATION", "RECONCILIATION_FINDING", "RECORDER_FAILURE")
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "common" / "schemas" / "audit_event.json"
HASH_DOMAIN = b"alice-audit-event-v1\x00"


class LedgerInputError(ValueError):
    """Bounded diagnostics that never echo caller content."""


def _check_tree(value, depth=0, *, allow_floats=False, _budget=None):
    # A Python caller can supply a tiny shared object graph whose expanded JSON
    # is enormous. Count a lower bound on encoded bytes during traversal, before
    # serialization or schema iteration; per-container limits alone do not bound
    # the whole graph. The final encoder still enforces the exact byte ceiling.
    if _budget is None:
        _budget = [MAX_EVENT_BYTES]
    _budget[0] -= 1
    if _budget[0] < 0:
        raise LedgerInputError("JSON aggregate traversal exceeds limit")
    if depth > MAX_JSON_DEPTH:
        raise LedgerInputError("JSON nesting exceeds limit")
    if type(value) is dict:
        if len(value) > 64:
            raise LedgerInputError("JSON object exceeds field limit")
        for key, item in value.items():
            if type(key) is not str or not key.isascii() or not 1 <= len(key) <= 128:
                raise LedgerInputError("JSON keys must be bounded ASCII strings")
            _budget[0] -= len(key) + 3
            _check_tree(item, depth + 1, allow_floats=allow_floats, _budget=_budget)
    elif type(value) is list:
        if len(value) > 64:
            raise LedgerInputError("JSON array exceeds item limit")
        for item in value:
            _check_tree(item, depth + 1, allow_floats=allow_floats, _budget=_budget)
    elif type(value) is str:
        if len(value) > 4096:
            raise LedgerInputError("JSON string exceeds limit")
        try:
            _budget[0] -= len(value.encode("utf-8"))
            if _budget[0] < 0:
                raise LedgerInputError("JSON aggregate traversal exceeds limit")
        except UnicodeError:
            raise LedgerInputError("invalid Unicode string") from None
    elif type(value) is int:
        if not -(2**63) <= value < 2**63:
            raise LedgerInputError("JSON integer exceeds signed 64-bit range")
    elif type(value) is float and allow_floats and math.isfinite(value):
        pass
    elif value is not None and type(value) is not bool:
        raise LedgerInputError("unsupported JSON value type")


def canonical_bytes(value) -> bytes:
    """UTF-8, sorted ASCII keys, exact Unicode values and integer-only numbers."""
    _check_tree(value)
    try:
        result = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError):
        raise LedgerInputError("invalid bounded JSON") from None
    if len(result) > MAX_EVENT_BYTES:
        raise LedgerInputError("JSON exceeds 16 KiB")
    return result


def _reject_number(_):
    raise LedgerInputError("only JSON integers are supported")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LedgerInputError("duplicate JSON object key")
        result[key] = value
    return result


def parse_json(payload: bytes):
    """Parse bounded JSON, refusing duplicates, floats and malformed Unicode."""
    if type(payload) is not bytes or len(payload) > MAX_EVENT_BYTES:
        raise LedgerInputError("payload must be at most 16 KiB of UTF-8 bytes")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_float=_reject_number, parse_constant=_reject_number)
    except LedgerInputError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise LedgerInputError("invalid UTF-8 JSON") from None
    canonical_bytes(value)
    return value


@lru_cache(maxsize=2)
def _validator(caller_input=False):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if caller_input:
        schema["properties"] = {name: schema["properties"][name] for name in INPUT_FIELDS}
        schema["required"] = list(INPUT_FIELDS)
    checker = FormatChecker()

    @checker.checks("date-time", raises=(ValueError, TypeError))
    def utc(value):
        if not isinstance(value, str):
            return True
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value and value.endswith("Z") and parsed.utcoffset().total_seconds() == 0

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=checker)


@lru_cache(maxsize=4)
def _definition_validator(name):
    validator = _validator()
    return validator.evolve(schema={"$defs": validator.schema["$defs"], "$ref": "#/$defs/" + name})


def _validate_definition(name, value):
    canonical_bytes(value)
    if next(_definition_validator(name).iter_errors(value), None) is not None:
        raise LedgerInputError("audit component schema violation")


def _clock_semantics(value, time_field):
    absent = value[time_field] is None
    if (value["confidence"] == "UNAVAILABLE") != absent:
        raise LedgerInputError("clock availability and timestamp disagree")


def validate_time(value) -> None:
    """Use the identical bounded local-clock contract for events and seals."""
    _validate_definition("time", value)
    _clock_semantics(value, "recorded_at")


def _assessment_semantics(detail, correlation, evidence):
    status, result, kind = detail["status"], detail["result"], detail["kind"]
    if (status != "OK" and result != "UNKNOWN") or (status == "OK" and result == "UNKNOWN"):
        raise LedgerInputError("assessment status and result disagree")
    if status == "OK" and result not in (("PASS", "FAIL") if kind == "POLICY" else ("LOW", "ELEVATED", "HIGH")):
        raise LedgerInputError("assessment result does not match assessment kind")
    compact = detail["contextual"]
    if (kind == "CONTEXTUAL_ML") != (compact is not None):
        raise LedgerInputError("contextual assessment requires its compact projection only")
    if compact is None:
        return
    if status not in ("OK", "UNAVAILABLE", "INVALID_INPUT", "ERROR"):
        raise LedgerInputError("unsupported contextual assessment status")
    dispatch, parsed = compact["dispatch"], compact["parsed"]
    for key in ("assessment_id", "request_id", "request_sha256", "execution_id"):
        if correlation[key] != dispatch[key]:
            raise LedgerInputError("contextual assessment and event dispatch disagree")
    for key in ("request_id", "input_sha256", "execution_id"):
        if parsed[key] is not None and parsed[key] != dispatch[key]:
            raise LedgerInputError("parsed contextual identity disagrees with dispatch")
    if compact["profile_sha256"] != dispatch["profile_sha256"] or compact["phase"] != dispatch["phase"]:
        raise LedgerInputError("contextual profile or phase disagrees with dispatch")
    if (dispatch["phase"] == "PRE_ACTION") != (dispatch["execution_id"] is None):
        raise LedgerInputError("contextual phase and dispatched execution disagree")
    parsed_identity = [parsed[key] for key in ("observation_id", "request_id", "input_sha256")]
    request_at, cutoff_at, execution_at = (compact[key] for key in ("request_at_ms", "cutoff_at_ms", "execution_at_ms"))
    if any(item is not None for item in parsed_identity):
        if (any(item is None for item in parsed_identity) or request_at is None or cutoff_at is None
                or not compact["context"] or not compact["source_ids"]):
            raise LedgerInputError("parsed contextual observation requires complete retained metadata")
        if compact["phase"] == "PRE_ACTION":
            if cutoff_at != request_at or parsed["execution_id"] is not None or execution_at is not None:
                raise LedgerInputError("pre-action contextual timing disagrees with request")
        elif parsed["execution_id"] is None or execution_at is None or not request_at <= execution_at <= cutoff_at:
            raise LedgerInputError("post-action contextual timing requires ordered execution binding")
    elif (status in ("OK", "ERROR") or parsed["execution_id"] is not None
          or any(item is not None for item in (request_at, cutoff_at, execution_at, compact["calibration_sha256"]))
          or compact["context"] or compact["source_ids"]):
        raise LedgerInputError("unparsed contextual observation must have absent retained metadata")
    if status == "OK" and any(compact[key] is None for key in ("model_id", "model_fingerprint", "calibration_sha256")):
        raise LedgerInputError("scored contextual assessment requires model and calibration identity")
    if (compact["model_id"] is None) != (compact["model_fingerprint"] is None):
        raise LedgerInputError("contextual model identity and fingerprint must be paired")
    keys = [item["key"] for item in compact["context"]]
    if keys != sorted(set(keys)):
        raise LedgerInputError("context keys must be sorted and unique")
    binding = compact["assessment_evidence"]
    if evidence.get(binding["ref"]) != binding["sha256"]:
        raise LedgerInputError("contextual original assessment evidence is unbound")


def contextual_projection(assessment_bytes: bytes, *, dispatch: dict, evidence_ref: str) -> dict:
    """Project original contextual bytes without copying scores or numeric factors.

    dispatch is captured by the trusted caller before inference. Parsing failure
    may leave result IDs null; it cannot erase the independently captured IDs.
    The caller must retain these exact original bytes under the returned digest.
    This validates correspondence, not the model's computation or source trust.
    """
    _validate_definition("contextual_dispatch", dispatch)
    if type(assessment_bytes) is not bytes or len(assessment_bytes) > MAX_EVENT_BYTES:
        raise LedgerInputError("contextual assessment exceeds bounded bytes contract")
    try:
        original = json.loads(assessment_bytes.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_reject_number)
        _check_tree(original, allow_floats=True)
    except LedgerInputError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise LedgerInputError("invalid contextual assessment JSON") from None
    expected = {"schema_version", "status", "result", "raw_score", "score", "reason_codes", "phase",
                "observation_id", "request_id", "input_sha256", "profile_sha256", "model_id",
                "model_fingerprint", "calibration_sha256", "context", "request_at_ms", "cutoff_at_ms",
                "execution_id", "execution_at_ms", "source_ids", "factors"}
    if type(original) is not dict or set(original) != expected or type(original["context"]) is not dict:
        raise LedgerInputError("unsupported contextual assessment shape")
    for key in ("raw_score", "score"):
        number = original[key]
        if number is not None and type(number) not in (int, float):
            raise LedgerInputError("invalid original contextual score")
        if (original["status"] == "OK") != (number is not None):
            raise LedgerInputError("original contextual scores disagree with status")
    if original["score"] is not None and not 0 <= original["score"] <= 1:
        raise LedgerInputError("original contextual score is out of range")
    if type(original["factors"]) is not list or len(original["factors"]) > 32:
        raise LedgerInputError("original contextual factors exceed limit")
    compact = {
        "schema_version": "alice-contextual-projection-v1", "assessment_schema_version": original["schema_version"],
        "dispatch": deepcopy(dispatch),
        "parsed": {key: original[key] for key in ("observation_id", "request_id", "input_sha256", "execution_id")},
        **{key: deepcopy(original[key]) for key in ("phase", "profile_sha256", "model_id", "model_fingerprint",
          "calibration_sha256", "request_at_ms", "cutoff_at_ms", "execution_at_ms", "source_ids")},
        "context": [{"key": key, "value": item} for key, item in sorted(original["context"].items())],
        "assessment_evidence": {"ref": evidence_ref, "sha256": sha256(assessment_bytes).hexdigest()},
    }
    detail = {"kind": "CONTEXTUAL_ML", "status": original["status"], "result": original["result"],
              "reason_codes": deepcopy(original["reason_codes"]), "contextual": compact}
    _validate_definition("assessment", detail)
    if detail["reason_codes"] != sorted(set(detail["reason_codes"])):
        raise LedgerInputError("reason codes must be sorted and unique")
    _assessment_semantics(detail, dispatch, {evidence_ref: compact["assessment_evidence"]["sha256"]})
    return detail


def _semantics(value):
    correlation, kind, detail = value["correlation"], value["event_type"], value["detail"]
    attribution = value["attribution"]
    if attribution["resolution"] == "RESOLVED" and (attribution["actor_kind"] == "UNKNOWN" or attribution["actor_id"] is None):
        raise LedgerInputError("resolved attribution requires known actor kind and identity")
    if (correlation["request_id"] is None) != (correlation["request_sha256"] is None):
        raise LedgerInputError("request identity and exact digest must be paired")
    if kind in EVENT_TYPES[:1] + EVENT_TYPES[2:10]:
        if correlation["request_id"] is None:
            raise LedgerInputError("event requires exact request binding")
    if kind in ("ASSESSMENT", "DECISION") and correlation["assessment_id"] is None:
        raise LedgerInputError("event requires assessment binding")
    if kind in ("EXECUTION_ATTEMPT", "CONTROLLER_RECEIPT", "EXECUTION_RESULT"):
        if correlation["action_id"] is None or correlation["execution_id"] is None:
            raise LedgerInputError("execution requires action and execution identity")
    if kind == "TECHNICIAN_ACTION" and value["attribution"]["technician_id"] is None:
        raise LedgerInputError("technician action requires technician identity")
    authority = value["authority"]
    if authority["execution_owner"] == "ALICE":
        if (authority["product_mode"] != "OFFLINE" or authority["confirmation"] != "CONFIRMED"
                or authority["authority_interval_ref"] is None):
            raise LedgerInputError("ALICE ownership requires confirmed offline authority interval")
    if kind == "EXECUTION_ATTEMPT" and authority["authority_interval_ref"] is None:
        raise LedgerInputError("execution attempt requires authority interval")
    for name in ("policy", "baseline", "model", "calibration", "snapshot"):
        artifact = value["provenance"][name]
        if artifact["id"] is None:
            if artifact["sha256"] is not None or artifact["missing_reason"] is None:
                raise LedgerInputError("missing provenance requires explicit reason")
        elif artifact["sha256"] is None or artifact["missing_reason"] is not None:
            raise LedgerInputError("present provenance requires digest and no missing reason")
    evidence = value["provenance"]["evidence"]
    refs = [item["ref"] for item in evidence]
    if len(refs) != len(set(refs)):
        raise LedgerInputError("evidence references must be unique")
    for source in [item["source"] for item in evidence] + ([detail["source"]] if "source" in detail else []):
        _clock_semantics(source, "observed_at")
        if source["availability"] == "AVAILABLE" and (source["source_id"] is None or source["source_event_id"] is None):
            raise LedgerInputError("available source requires stable source identities")
    if "reason_codes" in detail and detail["reason_codes"] != sorted(set(detail["reason_codes"])):
        raise LedgerInputError("reason codes must be sorted and unique")
    if kind == "ASSESSMENT":
        _assessment_semantics(detail, correlation, {item["ref"]: item["sha256"] for item in evidence})
    if kind == "OBSERVED_STATE":
        action, execution = correlation["action_id"], correlation["execution_id"]
        if (action is None) != (execution is None):
            raise LedgerInputError("observation action and execution must be paired")
        if (action is None) != (detail["correlation_absence_reason"] is not None):
            raise LedgerInputError("uncorrelated observation needs explicit absence reason")
        if detail["evidence_ref"] not in refs:
            raise LedgerInputError("observation evidence reference is unbound")
        if detail["value"] is None and detail["quality"] not in ("UNAVAILABLE", "UNKNOWN", "INVALID"):
            raise LedgerInputError("absent measurement cannot have good quality")
        if detail["value"] is not None and (detail["quality"] == "UNAVAILABLE" or detail["source"]["availability"] != "AVAILABLE"):
            raise LedgerInputError("measurement requires available source")
    if kind == "RECONCILIATION_FINDING" and correlation["parent_event_id"] != detail["original_event_id"]:
        raise LedgerInputError("finding original event and parent binding disagree")
    if kind == "AUTHORITY_TRANSITION" and detail["outcome"] == "CONFIRMED":
        if detail["new_owner"] != authority["execution_owner"] or detail["interval_ref"] != authority["authority_interval_ref"]:
            raise LedgerInputError("confirmed transition and authority snapshot disagree")


def _validate(value, caller_input):
    canonical_bytes(value)
    error = next(_validator(caller_input).iter_errors(value), None)
    if error is not None:
        raise LedgerInputError("audit event schema violation")
    _semantics(value)


def validate_input(value: dict) -> None:
    """Validate caller-owned fields before the recorder assigns local identity."""
    _validate(value, True)


def event_hash(value: dict) -> str:
    """Hash all event fields except event_hash under the versioned domain."""
    if type(value) is not dict:
        raise LedgerInputError("event must be an object")
    return sha256(HASH_DOMAIN + canonical_bytes({key: item for key, item in value.items() if key != "event_hash"})).hexdigest()


def validate_event(value: dict) -> None:
    """Validate one full event; store validation additionally checks history."""
    _validate(value, False)
    _clock_semantics(value["time"], "recorded_at")
    if value["outbox_id"] != value["event_id"]:
        raise LedgerInputError("outbox identity must equal event identity")
    if (value["sequence"] == 1) != (value["previous_hash"] == GENESIS_HASH):
        raise LedgerInputError("genesis predecessor binding disagrees")
    if value["event_hash"] != event_hash(value):
        raise LedgerInputError("event hash mismatch")
