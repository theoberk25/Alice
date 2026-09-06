"""Producer tests for the technician "request more context" ledger records.

Record 1 (CONTEXT_CHALLENGE) and Record 2 (CONTEXT_RESPONSE) must be
schema-valid bounded audit events that seal into an intact hash chain. See
docs/plans/2026-09-06-request-more-context-pipeline.md.
"""

from copy import deepcopy

import pytest

from dcamr.audit.event_contract import (GENESIS_HASH, LedgerInputError, event_hash,
                                        validate_event, validate_input)
from dcamr.challenge.challenge import (ContextChallengeProducer, TECHNICIAN_REQUESTED_CONTEXT,
                                       agent_response_projection, context_challenge,
                                       context_response)
from tests.audit_fixtures import clock


NEUTRAL_AUTHORITY = {"product_mode": "UNRECEIVED", "connectivity": "UNKNOWN",
                     "execution_owner": "UNKNOWN", "authority_interval_ref": None,
                     "confirmation": "UNKNOWN"}
NEUTRAL_PROVENANCE = {name: {"id": None, "sha256": None, "missing_reason": "NOT_APPLICABLE"}
                      for name in ("policy", "baseline", "model", "calibration", "snapshot")}
NEUTRAL_PROVENANCE["evidence"] = []

BLURB = {
    "mission_justification": "Isolating the host on scope MISSION-291 is required to stop the "
                             "suspected command-and-control traffic. The elevated outbound signal "
                             "reflects that objective, not a new intent.",
    "expected_effect": "Prevents further outbound communication within the requested scope.",
    "evidence_references": ["PROC-8821", "EDR-9921"],
    "alternatives_considered": ["Hold the action for technician review before proceeding."],
}


def _assemble(fields):
    return {**deepcopy(fields), "authority": deepcopy(NEUTRAL_AUTHORITY),
            "provenance": deepcopy(NEUTRAL_PROVENANCE)}


def _seal(fields, *, sequence, previous_hash):
    value = _assemble(fields)
    value.update(schema_version="alice-audit-event-v1", canonicalization_version="alice-json-v1",
                 ledger_id="ledger-1", node_id="node-1", sequence=sequence, time=clock(),
                 previous_hash=previous_hash, outbox_id=value["event_id"], initial_state="LOCAL")
    value["event_hash"] = event_hash(value)
    return value


def test_context_challenge_is_schema_valid_and_attributed_to_technician():
    fields = context_challenge(request_id="REQ-88291", request_sha256="a" * 64,
                               challenge_id="CTX-441", technician_id="TECH-DEMO")
    validate_input(_assemble(fields))  # caller-owned fields pass before the recorder seals.
    sealed = _seal(fields, sequence=1, previous_hash=GENESIS_HASH)
    validate_event(sealed)  # full event, including hash, validates against the v1 schema.
    assert fields["event_type"] == "CONTEXT_CHALLENGE"
    assert fields["attribution"]["actor_kind"] == "TECHNICIAN"
    assert fields["attribution"]["technician_id"] == "TECH-DEMO"
    assert fields["correlation"]["request_id"] == "REQ-88291"
    assert fields["detail"] == {"challenge_id": "CTX-441", "outcome": "ISSUED",
                                "reason_codes": [TECHNICIAN_REQUESTED_CONTEXT]}


def test_context_response_is_a_bounded_record_attributed_to_the_agent():
    fields = context_response(request_id="REQ-88291", request_sha256="a" * 64,
                              challenge_id="CTX-441", agent_id="diagnostic-agent-04")
    validate_event(_seal(fields, sequence=1, previous_hash=GENESIS_HASH))
    assert fields["event_type"] == "CONTEXT_RESPONSE"
    assert fields["attribution"]["actor_kind"] == "AGENT"
    assert fields["attribution"]["agent_id"] == "diagnostic-agent-04"
    # The bounded audit detail records only the structural fact; no free text.
    assert fields["detail"] == {"challenge_id": "CTX-441", "outcome": "RECEIVED", "reason_codes": []}


def test_agent_response_projection_carries_the_blurb_for_the_console():
    projection = agent_response_projection(
        decision_id="DEC-20260905-000184", request_id="REQ-88291",
        agent_id="diagnostic-agent-04", challenge_id="CTX-441", response=BLURB,
        timestamp="2026-09-05T15:44:04Z")
    # Mirrors packages/contracts/src/alice/events.ts AgentResponseSchema so the
    # existing dashboard renders it with no UI change.
    assert projection["event_type"] == "alice.agent_response"
    assert projection["challenge_id"] == "CTX-441"
    assert projection["response"]["mission_justification"] == BLURB["mission_justification"]
    assert projection["response"]["evidence_references"] == ["PROC-8821", "EDR-9921"]


def test_records_seal_into_an_intact_hash_chain():
    challenge = context_challenge(request_id="REQ-88291", request_sha256="a" * 64,
                                  challenge_id="CTX-441", technician_id="TECH-DEMO")
    first = _seal(challenge, sequence=1, previous_hash=GENESIS_HASH)
    response = context_response(request_id="REQ-88291", request_sha256="a" * 64,
                                challenge_id="CTX-441", agent_id="diagnostic-agent-04",
                                parent_event_id=first["event_id"])
    second = _seal(response, sequence=2, previous_hash=first["event_hash"])
    validate_event(first)
    validate_event(second)
    assert second["previous_hash"] == first["event_hash"]
    assert second["correlation"]["parent_event_id"] == first["event_id"]


def test_producer_emits_both_records_through_the_bound_append():
    captured = []

    def append(**fields):
        captured.append(fields)
        return fields

    producer = ContextChallengeProducer(append)
    producer.issue(request_id="REQ-88291", request_sha256="a" * 64,
                   challenge_id="CTX-441", technician_id="TECH-DEMO")
    producer.respond(request_id="REQ-88291", request_sha256="a" * 64,
                     challenge_id="CTX-441", agent_id="diagnostic-agent-04")
    assert [f["event_type"] for f in captured] == ["CONTEXT_CHALLENGE", "CONTEXT_RESPONSE"]
    # Every emitted record still validates against the schema once sealed.
    for sequence, fields in enumerate(captured, start=1):
        validate_event(_seal(fields, sequence=sequence,
                             previous_hash=GENESIS_HASH if sequence == 1 else "b" * 64))


def test_missing_request_binding_is_refused():
    with pytest.raises(LedgerInputError):
        context_challenge(request_id="REQ-88291", request_sha256="",
                          challenge_id="CTX-441", technician_id="TECH-DEMO")


def test_projection_requires_the_exact_console_fields():
    incomplete = {k: v for k, v in BLURB.items() if k != "expected_effect"}
    with pytest.raises(LedgerInputError):
        agent_response_projection(decision_id="DEC-1", request_id="REQ-88291",
                                  agent_id="diagnostic-agent-04", challenge_id="CTX-441",
                                  response=incomplete, timestamp="2026-09-05T15:44:04Z")
