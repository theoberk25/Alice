"""Bounded, explicitly simulated caller records for audit component tests."""

from copy import deepcopy


DIGEST = "a" * 64


def clock():
    return {"recorded_at": "2026-09-05T20:00:00Z", "clock_source": "test-clock",
            "confidence": "TRUSTED", "boot_id": "boot-1", "monotonic_ns": 1}


def source():
    return {"source_id": "source-1", "source_event_id": "source-event-1",
            "observed_at": "2026-09-05T20:00:00Z", "confidence": "TRUSTED",
            "verification": "UNVERIFIED", "freshness": "UNKNOWN", "availability": "AVAILABLE"}


def evidence(ref="evidence-1", sha256=DIGEST):
    return {"ref": ref, "sha256": sha256, "source": source()}


def event(event_id="event-1", event_type="REQUEST"):
    correlation = dict.fromkeys(("correlation_id", "request_id", "request_sha256",
                                "assessment_id", "action_id", "execution_id", "parent_event_id"))
    request_types = {"REQUEST", "ASSESSMENT", "DECISION", "CONTEXT_CHALLENGE", "CONTEXT_RESPONSE",
                     "TECHNICIAN_ACTION", "EXECUTION_ATTEMPT", "CONTROLLER_RECEIPT", "EXECUTION_RESULT"}
    if event_type in request_types:
        correlation.update(correlation_id="correlation-1", request_id="request-1", request_sha256=DIGEST)
    if event_type in {"ASSESSMENT", "DECISION"}:
        correlation["assessment_id"] = "assessment-1"
    if event_type in {"EXECUTION_ATTEMPT", "CONTROLLER_RECEIPT", "EXECUTION_RESULT"}:
        correlation.update(action_id="action-1", execution_id="execution-1")
    details = {
        "REQUEST": {"outcome": "RECEIVED", "reason_codes": []},
        "REJECTION": {"outcome": "REJECTED", "reason_codes": ["MALFORMED_REQUEST"]},
        "ASSESSMENT": {"kind": "POLICY", "status": "OK", "result": "PASS", "reason_codes": [], "contextual": None},
        "DECISION": {"outcome": "DENY", "reason_codes": ["POLICY_DENY"]},
        "CONTEXT_CHALLENGE": {"challenge_id": "challenge-1", "outcome": "ISSUED", "reason_codes": []},
        "CONTEXT_RESPONSE": {"challenge_id": "challenge-1", "outcome": "RECEIVED", "reason_codes": []},
        "TECHNICIAN_ACTION": {"intent": "REQUEST_STOP", "reason_codes": []},
        "EXECUTION_ATTEMPT": {"command_ref": "command-1", "command_sha256": DIGEST, "outcome": "ATTEMPTED", "reason_codes": []},
        "CONTROLLER_RECEIPT": {"outcome": "ACCEPTED", "source": source(), "reason_codes": []},
        "EXECUTION_RESULT": {"outcome": "UNKNOWN", "source": source(), "reason_codes": ["NO_FEEDBACK"]},
        "OBSERVED_STATE": {"asset_id": "asset-1", "sensor_id": "sensor-1", "origin": "SIMULATED",
                           "property": "position", "value": "0.25", "unit": "m", "quality": "GOOD",
                           "correlation_absence_reason": "UNSOLICITED", "source": source(), "evidence_ref": "evidence-1"},
        "AUTHORITY_TRANSITION": {"previous_owner": "UNKNOWN", "new_owner": "ENTERPRISE", "interval_ref": None,
                                 "outcome": "OBSERVED", "source": source(), "reason_codes": []},
        "CACHE_ACTIVATION": {"cache_id": "cache-1", "cache_sha256": DIGEST, "outcome": "ACTIVATED", "reason_codes": []},
        "RECONCILIATION_FINDING": {"original_event_id": "original-1", "original_event_hash": DIGEST,
                                   "finding": "CONSISTENT", "reason_codes": [], "source": source()},
        "RECORDER_FAILURE": {"operation": "APPEND", "error_code": "STORAGE_UNAVAILABLE", "reason_codes": []},
    }
    if event_type == "RECONCILIATION_FINDING":
        correlation["parent_event_id"] = "original-1"
    result = {
        "event_id": event_id, "event_type": event_type, "correlation": correlation,
        "attribution": {"actor_kind": "SYSTEM", "actor_id": "actor-1", "authenticated_requester_id": None,
                        "agent_id": None, "responsible_user_id": None, "delegator_id": None,
                        "technician_id": "technician-1" if event_type == "TECHNICIAN_ACTION" else None,
                        "assignment_source_id": None, "resolution": "UNRESOLVED"},
        "authority": {"product_mode": "UNRECEIVED", "connectivity": "UNKNOWN", "execution_owner": "UNKNOWN",
                      "authority_interval_ref": None, "confirmation": "UNKNOWN"},
        "provenance": {name: {"id": None, "sha256": None, "missing_reason": "NOT_APPLICABLE"}
                       for name in ("policy", "baseline", "model", "calibration", "snapshot")},
        "detail": details[event_type],
    }
    result["provenance"]["evidence"] = [evidence()] if event_type == "OBSERVED_STATE" else []
    if event_type == "EXECUTION_ATTEMPT":
        result["authority"].update(product_mode="OFFLINE", execution_owner="ALICE",
                                   authority_interval_ref="interval-1", confirmation="CONFIRMED")
    return deepcopy(result)
