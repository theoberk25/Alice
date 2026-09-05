"""Bounded parsing for local feature inputs and baseline payloads."""

from datetime import datetime
from functools import lru_cache
from hashlib import sha256
import hmac
import ipaddress
import json
import math
from importlib.resources import files
import re
from types import MappingProxyType

from jsonschema import Draft202012Validator, FormatChecker

from .feature_types import FeatureError


MAX_BASELINE_BYTES = 8 * 1024 * 1024
MAX_FEATURE_INPUT_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 16 * 1024
SCHEMA_DIR = files("common.schemas")


def normalize_host(value: str, field: str) -> str:
    """Compare IP literals or DNS names without DNS/network lookups."""
    try:
        return ipaddress.ip_address(value).compressed
    except ValueError:
        pass
    host = value.removesuffix(".").lower()
    labels = host.split(".")
    if (len(host) > 253 or not host or all(label.isdigit() for label in labels)
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                   for label in labels)):
        raise FeatureError("INPUT_UNSUPPORTED", field, status="INVALID_INPUT")
    return host


def timestamp(value: str | None, field: str) -> datetime:
    if value is None:
        raise FeatureError("CLOCK_UNTRUSTED", field)
    try:
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value
        ):
            raise ValueError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset().total_seconds() != 0:
            raise ValueError
        return parsed
    except (ValueError, AttributeError):
        raise FeatureError("INPUT_UNSUPPORTED", field, status="INVALID_INPUT") from None


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise FeatureError("INPUT_UNSUPPORTED", "duplicate_key", status="INVALID_INPUT")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise FeatureError("INPUT_NONFINITE", "json", status="INVALID_INPUT")


def _walk(value, depth: int = 0) -> None:
    # Prevent schema traversal of deep/cyclic inputs; bytes bound parsing cost.
    if depth > 16:
        raise FeatureError("INPUT_LIMIT_EXCEEDED", "json.depth", status="INVALID_INPUT")
    if isinstance(value, dict):
        for item in value.values():
            _walk(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _walk(item, depth + 1)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise FeatureError("INPUT_NONFINITE", "json.number", status="INVALID_INPUT")
        # These contracts have integer counts and strings, no floating-point input.
        raise FeatureError("INPUT_UNSUPPORTED", "json.number", status="INVALID_INPUT")
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise FeatureError("INPUT_UNSUPPORTED", "json.unicode", status="INVALID_INPUT") from None


@lru_cache(maxsize=2)
def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()

    @checker.checks("date-time", raises=FeatureError)
    def check_time(value):
        if not isinstance(value, str):
            return True
        timestamp(value, "timestamp")
        return True

    return Draft202012Validator(schema, format_checker=checker)


def parse_bound_json(data: bytes, *, expected_sha256: str, schema_name: str,
                     max_bytes: int) -> tuple[dict, str]:
    """Verify exact payload bytes against a digest captured by the trusted caller.

    This is integrity/correlation only. It is not package-signature verification
    or the canonical hashing algorithm for the outer request/decision protocol.
    """
    if type(data) is not bytes:
        raise FeatureError("INPUT_UNSUPPORTED", "payload", status="INVALID_INPUT")
    if len(data) > max_bytes:
        raise FeatureError("INPUT_LIMIT_EXCEEDED", "payload", status="INVALID_INPUT")
    if not isinstance(expected_sha256, str) or not re.fullmatch("[a-f0-9]{64}", expected_sha256):
        raise FeatureError("INPUT_UNSUPPORTED", "expected_sha256", status="INVALID_INPUT")
    actual = sha256(data).hexdigest()
    if not hmac.compare_digest(actual, expected_sha256):
        raise FeatureError("INPUT_UNSUPPORTED", "payload.sha256", status="INVALID_INPUT")
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=_constant)
        _walk(result)
    except FeatureError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise FeatureError("INPUT_UNSUPPORTED", "json", status="INVALID_INPUT") from None
    error = next(_validator(schema_name).iter_errors(result), None)
    if error:
        path = ".".join(map(str, error.absolute_path)) or "payload"
        if path == "feature_schema_version":
            raise FeatureError("FEATURE_SCHEMA_MISMATCH", path)
        code = "INPUT_LIMIT_EXCEEDED" if error.validator in ("maxItems", "maxProperties", "maxLength") else "INPUT_UNSUPPORTED"
        raise FeatureError(code, path[:256], status="INVALID_INPUT")
    return result, actual


def freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    return value
