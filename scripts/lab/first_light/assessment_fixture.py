"""Explicitly-labelled fixture assessment for the first-light test.

Produces a normal/OK contextual assessment whose bytes carry
context.fixture_mode = "true" (contextual_projection's strict key set forbids a
top-level marker, so the marker lives in the retained context map, following
the tests/fixtures/anomaly mock-marking pattern). This proves ledger wiring,
not detection: no model runs. Scope per AGENTS.md working agreements.
"""

from hashlib import sha256
import json

FIXTURE_PROFILE_SHA256 = sha256(b"first-light-fixture-profile").hexdigest()
FIXTURE_CALIBRATION_SHA256 = sha256(b"first-light-fixture-calibration").hexdigest()


def build_assessment(*, request_id: str, input_sha256: str, request_at_ms: int) -> bytes:
    """Return the exact assessment bytes the runtime retains as evidence."""
    assessment = {
        "schema_version": "context-behavior-assessment-v1",
        "status": "OK",
        "result": "LOW",
        "raw_score": 0.0,
        "score": 0.05,
        "reason_codes": [],
        "phase": "PRE_ACTION",
        "observation_id": f"{request_id}.obs",
        "request_id": request_id,
        "input_sha256": input_sha256,
        "profile_sha256": FIXTURE_PROFILE_SHA256,
        "model_id": "first-light-fixture-model",
        "model_fingerprint": sha256(b"first-light-fixture-model").hexdigest(),
        "calibration_sha256": FIXTURE_CALIBRATION_SHA256,
        "context": {
            "action": "set_light_state",
            "fixture_mode": "true",
            "target": "ESP-LIGHT-01",
        },
        "request_at_ms": request_at_ms,
        "cutoff_at_ms": request_at_ms,
        "execution_id": None,
        "execution_at_ms": None,
        "source_ids": ["first-light-fixture"],
        "factors": [],
    }
    return json.dumps(assessment, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
