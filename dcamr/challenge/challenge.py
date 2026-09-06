"""Producers for the technician "request more context" ledger records.

When a technician chooses *Request more context* on a HOLD, two facts become
part of the audit record of record:

* **Record 1 — CONTEXT_CHALLENGE** — the audited fact that the technician asked
  the agent for more context, attributed to the technician.
* **Record 2 — CONTEXT_RESPONSE** — the agent's returned claim (a 1-2 sentence
  blurb) answering that challenge, attributed to the agent.

Both are modeled as first-class bounded audit events; the schema enum already
lists ``CONTEXT_CHALLENGE`` and ``CONTEXT_RESPONSE`` and the detail shapes match
``tests/audit_fixtures.py``. These builders emit only the caller-owned fields
(``event_id``/``event_type``/``correlation``/``attribution``/``detail``); the
recorder assigns ledger identity, sequence, local time and the hash chain.

Nothing here asserts source trust, execution permission, or that the agent's
returned claim is true. A returned response is a *claim*, not a re-decision: it
does not change a HOLD. See
``docs/plans/2026-09-06-request-more-context-pipeline.md`` and
``docs/architecture/hold-workflow.md``.
"""

from __future__ import annotations

from dcamr.audit.event_contract import LedgerInputError


#: Reason code recorded on a technician-initiated context challenge.
TECHNICIAN_REQUESTED_CONTEXT = "TECHNICIAN_REQUESTED_CONTEXT"

#: The exact response fields the console renders (mirrors ``alice.agent_response``
#: so the runtime feed can project Record 2 with no dashboard change).
RESPONSE_FIELDS = ("mission_justification", "expected_effect",
                   "evidence_references", "alternatives_considered")


def _reason_codes(reason_codes) -> list:
    codes = list(reason_codes)
    for code in codes:
        if not isinstance(code, str) or not 1 <= len(code) <= 128:
            raise LedgerInputError("reason code must be a bounded string")
    # The audit contract requires detail reason codes to be sorted and unique.
    return sorted(set(codes))


def _identity(value, label):
    if not isinstance(value, str) or not value:
        raise LedgerInputError(f"{label} must be a non-empty string")
    return value


def _correlation(request_id, request_sha256, *, parent_event_id=None) -> dict:
    # CONTEXT_CHALLENGE/CONTEXT_RESPONSE both require an exact request binding;
    # request_id and request_sha256 must be present and paired.
    return {"correlation_id": _identity(request_id, "request_id"),
            "request_id": request_id,
            "request_sha256": _identity(request_sha256, "request_sha256"),
            "assessment_id": None, "action_id": None, "execution_id": None,
            "parent_event_id": parent_event_id}


def _base_attribution() -> dict:
    return dict.fromkeys(("actor_id", "authenticated_requester_id", "agent_id",
                          "responsible_user_id", "delegator_id", "technician_id",
                          "assignment_source_id"))


def _technician_attribution(technician_id) -> dict:
    technician_id = _identity(technician_id, "technician_id")
    base = _base_attribution()
    base.update(actor_kind="TECHNICIAN", actor_id=technician_id,
                authenticated_requester_id=technician_id, technician_id=technician_id,
                resolution="RESOLVED")
    return base


def _agent_attribution(agent_id) -> dict:
    agent_id = _identity(agent_id, "agent_id")
    base = _base_attribution()
    base.update(actor_kind="AGENT", actor_id=agent_id, authenticated_requester_id=agent_id,
                agent_id=agent_id, resolution="RESOLVED")
    return base


def challenge_detail(challenge_id, *, outcome="ISSUED",
                     reason_codes=(TECHNICIAN_REQUESTED_CONTEXT,)) -> dict:
    """Record 1 detail: the technician's issued context challenge.

    The bounded audit detail records only the structural fact — which challenge
    was issued and why — not any free text.
    """
    return {"challenge_id": _identity(challenge_id, "challenge_id"),
            "outcome": outcome, "reason_codes": _reason_codes(reason_codes)}


def response_detail(challenge_id, *, outcome="RECEIVED", reason_codes=()) -> dict:
    """Record 2 detail: the agent returned context for the challenge.

    Like every bounded audit detail this carries only the structural fact
    (``additionalProperties: false`` in the schema); the free-text blurb never
    enters the ledger. It rides the separate console projection built by
    :func:`agent_response_projection`.
    """
    return {"challenge_id": _identity(challenge_id, "challenge_id"),
            "outcome": outcome, "reason_codes": _reason_codes(reason_codes)}


def clean_response(response) -> dict:
    """Validate and normalise the agent's console-facing response payload."""
    if not isinstance(response, dict) or set(response) != set(RESPONSE_FIELDS):
        raise LedgerInputError("context response must supply exactly the console fields")
    justification = response["mission_justification"]
    effect = response["expected_effect"]
    for text, label in ((justification, "mission_justification"), (effect, "expected_effect")):
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise LedgerInputError(f"{label} must be a bounded non-empty string")
    references = list(response["evidence_references"])
    alternatives = list(response["alternatives_considered"])
    for item in references + alternatives:
        if not isinstance(item, str) or not 1 <= len(item) <= 4096:
            raise LedgerInputError("response list entries must be bounded strings")
    return {"mission_justification": justification, "expected_effect": effect,
            "evidence_references": references, "alternatives_considered": alternatives}


def context_challenge(*, request_id, request_sha256, challenge_id, technician_id,
                      reason_codes=(TECHNICIAN_REQUESTED_CONTEXT,), event_id=None) -> dict:
    """Caller-owned fields for a CONTEXT_CHALLENGE, ready for ``_append(**fields)``."""
    return {"event_id": event_id or f"{request_id}.context_challenge",
            "event_type": "CONTEXT_CHALLENGE",
            "correlation": _correlation(request_id, request_sha256),
            "attribution": _technician_attribution(technician_id),
            "detail": challenge_detail(challenge_id, reason_codes=reason_codes)}


def context_response(*, request_id, request_sha256, challenge_id, agent_id,
                     reason_codes=(), event_id=None, parent_event_id=None) -> dict:
    """Caller-owned fields for a CONTEXT_RESPONSE, ready for ``_append(**fields)``."""
    return {"event_id": event_id or f"{request_id}.context_response",
            "event_type": "CONTEXT_RESPONSE",
            "correlation": _correlation(request_id, request_sha256,
                                        parent_event_id=parent_event_id),
            "attribution": _agent_attribution(agent_id),
            "detail": response_detail(challenge_id, reason_codes=reason_codes)}


def agent_response_projection(*, decision_id, request_id, agent_id, challenge_id, response,
                              timestamp) -> dict:
    """Build the console ``alice.agent_response`` projection carrying the blurb.

    This is the separate display channel referenced by the CONTEXT_RESPONSE
    record: the runtime feed maps the ledger event to this shape so the existing
    dashboard renders the blurb with no UI change. It mirrors
    ``packages/contracts/src/alice/events.ts`` ``AgentResponseSchema``. The blurb
    text is ``response["mission_justification"]``.
    """
    return {"schema_version": "1.0", "event_type": "alice.agent_response",
            "timestamp": timestamp, "decision_id": _identity(decision_id, "decision_id"),
            "request_id": _identity(request_id, "request_id"),
            "challenge_id": _identity(challenge_id, "challenge_id"),
            "agent_id": _identity(agent_id, "agent_id"),
            "response": clean_response(response)}


class ContextChallengeProducer:
    """Emit the two context records through a bound runtime append.

    ``append`` is the recorder entry point that seals the caller-owned fields
    into the ledger (the Pi runtime's ``FirstLightRuntime._append``); it is
    injected so the producer is testable in isolation and wireable into the
    runtime without importing it. The producer never touches ledger internals.
    """

    def __init__(self, append):
        self._append = append

    def issue(self, *, request_id, request_sha256, challenge_id, technician_id,
              reason_codes=(TECHNICIAN_REQUESTED_CONTEXT,), event_id=None):
        """Emit Record 1 — the technician's context challenge."""
        return self._append(**context_challenge(
            request_id=request_id, request_sha256=request_sha256, challenge_id=challenge_id,
            technician_id=technician_id, reason_codes=reason_codes, event_id=event_id))

    def respond(self, *, request_id, request_sha256, challenge_id, agent_id,
                reason_codes=(), event_id=None, parent_event_id=None):
        """Emit Record 2 — the structural fact that the agent returned context.

        The free-text blurb never enters the ledger; deliver it to the console
        separately with :func:`agent_response_projection`.
        """
        return self._append(**context_response(
            request_id=request_id, request_sha256=request_sha256, challenge_id=challenge_id,
            agent_id=agent_id, reason_codes=reason_codes,
            event_id=event_id, parent_event_id=parent_event_id))
