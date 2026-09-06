"""Decision-source seam for the Decision-Brief MCP server.

The server never talks to ALICE (the Pi runtime / audit ledger) or the
dashboard directly; it talks to a ``DecisionSource``. Ship ``MockSource`` now
(fixture holds from ``holds.yaml`` + an in-memory brief store); drop in
``AliceSource`` later with zero change to the server or the agent. Selection is
via ``BRIEF_SOURCE``.

The source is the single source of truth for held decisions and their published
briefs — the server keeps no second copy.

Governance boundary (keep it): a ``DecisionSource`` READS authoritative decisions
and STORES/forwards a technician-facing *brief*. It never produces an
authorization outcome (`APPROVE_ONCE` / `HOLD` / `RESEARCH` / `REJECT`) — that
remains a human technician choice made after biometric verification, outside this
service. Briefs are decision-support, not decisions.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

import yaml

log = logging.getLogger("brief_mcp.source")

# Held decisions still awaiting a technician are "open". Mirrors the reported
# reassessment sequence in docs/integration/technician-console.md
# (HOLD_RECEIVED -> AUTO_CONTEXT_REQUEST -> AWAITING_AGENT_RESPONSE ->
# AGENT_RESPONSE_RECEIVED -> REASSESSMENT_PENDING). SUPERSEDED/RESOLVED are closed.
OPEN_STATUSES = (
    "HELD",
    "AWAITING_AGENT_RESPONSE",
    "REASSESSMENT_PENDING",
)


def _now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class DecisionSource(ABC):
    """Abstract read/publish surface between ALICE's held decisions and the dashboard."""

    @abstractmethod
    def list_holds(self, status: str | None = None) -> list[dict]:
        """Return the review-queue rows (open holds if ``status`` is omitted)."""

    @abstractmethod
    def get_decision(self, request_id: str) -> dict | None:
        """Return one hold's full authoritative decision record, or ``None`` if unknown."""

    @abstractmethod
    def publish_brief(self, request_id: str, brief: dict) -> None:
        """Store/forward a technician-facing brief for ``request_id``."""

    @abstractmethod
    def get_brief(self, request_id: str) -> dict | None:
        """Return the currently-published brief for ``request_id``, or ``None``."""


class MockSource(DecisionSource):
    """In-memory source. Fixture holds from ``holds.yaml`` + a brief store.

    Fully demoable today with no Pi, no ledger and no dashboard backend — swapping
    to ``AliceSource`` later is invisible to the MCP server and the agent.
    """

    def __init__(self, holds: dict[str, dict]) -> None:
        # request_id -> full decision record (authoritative, read-only here)
        self._holds: dict[str, dict] = dict(holds)
        # request_id -> published brief (the only thing this source mutates)
        self._briefs: dict[str, dict] = {}
        log.info("MockSource init: %d held decision(s) %s",
                 len(self._holds), list(self._holds))

    def list_holds(self, status: str | None = None) -> list[dict]:
        rows: list[dict] = []
        for request_id, rec in self._holds.items():
            rec_status = str(rec.get("status", "HELD"))
            if status is None:
                if rec_status not in OPEN_STATUSES:
                    continue
            elif rec_status != status:
                continue
            rows.append({
                "request_id": request_id,
                "agent_id": rec.get("agent_id"),
                "action": rec.get("action"),
                "target": rec.get("target"),
                "outcome": rec.get("outcome"),
                "reason_code": rec.get("reason_code"),
                "status": rec_status,
                "created_at": rec.get("created_at"),
                "biometric_required": bool(rec.get("biometric_required", True)),
                "brief_status": "published" if request_id in self._briefs else "none",
            })
        return rows

    def get_decision(self, request_id: str) -> dict | None:
        rec = self._holds.get(request_id)
        if rec is None:
            return None
        # Return a copy so tool callers can't mutate the authoritative record.
        out = dict(rec)
        out["request_id"] = request_id
        return out

    def publish_brief(self, request_id: str, brief: dict) -> None:
        if request_id not in self._holds:
            raise KeyError(f"unknown request_id {request_id!r}")
        stored = dict(brief)
        stored["request_id"] = request_id
        stored["published_at"] = _now_z()
        self._briefs[request_id] = stored
        log.info("MockSource.publish_brief %s (%d factor(s))",
                 request_id, len(stored.get("factors", [])))

    def get_brief(self, request_id: str) -> dict | None:
        return self._briefs.get(request_id)


class AliceSource(DecisionSource):
    """STUB — real path: read held ``alice.decision`` records and post briefs.

    Drops in later with zero change to the server or the agent. Two seams:

    * **Read** held decisions from the ALICE side. The authoritative, immutable
      ``alice.decision`` events (decision / request / policy / anomaly / evidence /
      packages / biometric requirement — see docs/integration/technician-console.md)
      are the truth. Candidate wiring: query the Pi runtime for open holds, or
      project them from the audit ledger / USB SQL slice
      (docs/integration/live-dashboard.md). This source READS ONLY — it never
      recomputes permissions or model scores (the console does not either).

    * **Publish** the technician-facing brief to the dashboard review queue,
      e.g. ``POST`` to ``dcamr/api/dashboard_api.py`` (or emit an
      ``alice.*`` display event the technician Mac renders). The brief is
      decision-support attached to the hold; it is NOT an ``alice.technician_action``
      and carries no authorization outcome.

    Deliberately unimplemented so the wire contract is agreed with the console team
    (their Zod/JSON schemas + fixtures) before coding, per AGENTS.md — do not invent
    omitted payload fields from prose.
    """

    def __init__(self, runtime_url: str, dashboard_url: str | None = None,
                 *, timeout: float = 10.0) -> None:
        self._runtime_url = runtime_url.rstrip("/")
        self._dashboard_url = (dashboard_url or "").rstrip("/") or None
        self._timeout = timeout
        log.info("AliceSource -> runtime=%s dashboard=%s (stub)",
                 self._runtime_url, self._dashboard_url)

    def list_holds(self, status: str | None = None) -> list[dict]:
        raise NotImplementedError(
            "wire ALICE held-decision read here (Pi runtime / audit ledger projection)"
        )

    def get_decision(self, request_id: str) -> dict | None:
        raise NotImplementedError(
            "wire authoritative alice.decision fetch here (read-only, no recompute)"
        )

    def publish_brief(self, request_id: str, brief: dict) -> None:
        raise NotImplementedError(
            "wire brief publish to the dashboard here (POST dashboard_api / alice.* display event)"
        )

    def get_brief(self, request_id: str) -> dict | None:
        raise NotImplementedError("wire published-brief read-back here")


# --- Fixture loading ----------------------------------------------------------

def load_holds(path: str) -> dict[str, dict]:
    """Load fixture held-decision records from ``holds.yaml`` keyed by ``request_id``.

    Fixtures are illustrative but faithful to the repo's real contracts (the
    ``set_light_state`` action_request enums, the ``LOW``/``ELEVATED``/``HIGH``
    anomaly bands, the categorical permission outcomes). They are not live model
    output — the ``AliceSource`` path replaces them with authoritative records.
    """
    data = yaml.safe_load(Path(path).read_text()) or {}
    holds: dict[str, dict] = {}
    for entry in data.get("holds", []):
        request_id = str(entry["request_id"])
        holds[request_id] = dict(entry)
    return holds


def make_source(kind: str, holds: dict[str, dict]) -> DecisionSource:
    """Instantiate a source from ``BRIEF_SOURCE``:

    * ``mock`` — fixture holds + in-memory brief store (default); no ALICE, no
      dashboard backend.
    * ``alice``/``pi`` — STUB: read authoritative held decisions from the Pi
      runtime / ledger and publish briefs to the dashboard. Needs env
      ``ALICE_RUNTIME_URL`` (shared with the Light MCP) and, to publish,
      ``BRIEF_DASHBOARD_URL``.
    """
    kind = (kind or "mock").lower()
    if kind == "mock":
        return MockSource(holds)
    if kind in ("alice", "pi", "governed"):
        runtime_url = os.environ.get("ALICE_RUNTIME_URL", "http://127.0.0.1:18080")
        dashboard_url = os.environ.get("BRIEF_DASHBOARD_URL") or None
        return AliceSource(runtime_url, dashboard_url)
    raise ValueError(f"unknown BRIEF_SOURCE={kind!r} (expected 'mock' or 'alice'/'pi')")
