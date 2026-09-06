"""Decision-Brief MCP server (FastMCP, Streamable HTTP).

Serves four stable tools — ``list_holds``, ``get_decision``, ``publish_brief``,
``get_brief`` — over Streamable HTTP at ``http://<host>:<port>/mcp`` so a local
Goose agent (and, later, a cloud agent) can share one tool layer for turning
ALICE's held decisions into technician-facing briefs on the review dashboard.

Run from the repo root with the ``.venv`` active:

    python -m services.brief_mcp.server

Config: held decisions come from ``holds.yaml`` (mock) or ALICE (later); the
source is chosen by ``BRIEF_SOURCE`` (mock | alice). See
docs/agent-build/04-brief-mcp.md.

Governance boundary: this server is a presentation/explanation layer. It reads
the authoritative decision and publishes a *brief*; it never recomputes the
decision and offers NO tool to decide a HOLD. Choosing
``APPROVE_ONCE``/``HOLD``/``RESEARCH``/``REJECT`` is a human technician action
taken after biometric verification, outside this service.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .sources import DecisionSource, load_holds, make_source

logging.basicConfig(
    level=os.environ.get("BRIEF_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("brief_mcp.server")

# --- Config (env-overridable) -------------------------------------------------
HOST = os.environ.get("BRIEF_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("BRIEF_MCP_PORT", "8793"))
SOURCE_KIND = os.environ.get("BRIEF_SOURCE", "mock")
CONFIG_PATH = os.environ.get(
    "BRIEF_HOLDS_CONFIG", str(Path(__file__).with_name("holds.yaml"))
)

# The mock source reads fixtures from disk; the alice source ignores them.
_holds = load_holds(CONFIG_PATH) if SOURCE_KIND.lower() == "mock" else {}

# The source is the single source of truth for held decisions and their briefs.
# Tools call it; the server never keeps a second copy.
source: DecisionSource = make_source(SOURCE_KIND, _holds)

mcp = FastMCP("decision-brief", host=HOST, port=PORT)


@mcp.tool()
def list_holds(status: str | None = None) -> dict:
    """List held ALICE decisions awaiting a technician (the review queue).

    Omit ``status`` for all *open* holds (HELD / AWAITING_AGENT_RESPONSE /
    REASSESSMENT_PENDING), or pass an exact status to filter. Each row is a
    summary — ``request_id``, agent, action, target, outcome, reason_code,
    status, whether biometric verification is required, and ``brief_status``
    (``published`` | ``none``). Use ``get_decision`` for the full record.
    """
    try:
        return {"holds": source.list_holds(status)}
    except Exception as exc:
        return {"holds": [], "error": str(exc)}


@mcp.tool()
def get_decision(request_id: str) -> dict:
    """Get one hold's full authoritative decision record.

    Returns the immutable decision as ALICE emitted it: permission finding,
    anomaly assessment (band + score in [0,1]), evidence and its freshness,
    context-challenge state and biometric requirement. This is the raw material
    the agent formats into a brief — do not treat any field as re-derivable here.
    ``ok: false`` with an error (no crash) if the hold is unknown.
    """
    try:
        record = source.get_decision(request_id)
    except Exception as exc:
        return {"request_id": request_id, "ok": False, "error": str(exc)}
    if record is None:
        return {"request_id": request_id, "ok": False, "error": f"unknown request_id {request_id!r}"}
    return {"ok": True, "decision": record}


@mcp.tool()
def publish_brief(
    request_id: str,
    summary: str,
    factors: list[dict] | None = None,
    watch_items: list[str] | None = None,
) -> dict:
    """Publish a technician-facing brief for a held decision to the dashboard.

    This is how the agent "formats ALICE output into the dashboard": a plain,
    neutral explanation the technician reads before deciding the HOLD.

    * ``summary`` — one short paragraph in plain language: what the agent asked
      for, and why it is held.
    * ``factors`` — the decision factors as rows, provenance-first. Each item:
      ``{"label", "value", "source", "freshness"}`` (e.g. permission rule,
      anomaly band/score, evidence + how old it is). Mirror what ``get_decision``
      returned; do not invent factors.
    * ``watch_items`` — optional short strings the technician should check.

    The brief is decision-SUPPORT, not a decision: it must NOT recommend or
    assert ``APPROVE_ONCE``/``HOLD``/``RESEARCH``/``REJECT`` — that human choice
    happens in the dashboard's technician controls after biometric verification.
    Returns ``ok: false`` on unknown hold or malformed input (no crash).
    """
    if not isinstance(summary, str) or not summary.strip():
        return {"request_id": request_id, "ok": False, "error": "summary must be a non-empty string"}
    rows: list[dict] = []
    for f in factors or []:
        if not isinstance(f, dict):
            return {"request_id": request_id, "ok": False, "error": "each factor must be an object"}
        rows.append({
            "label": str(f.get("label", "")),
            "value": str(f.get("value", "")),
            "source": str(f.get("source", "")),
            "freshness": str(f.get("freshness", "")),
        })
    brief = {
        "summary": summary.strip(),
        "factors": rows,
        "watch_items": [str(w) for w in (watch_items or [])],
        # Echo the human's options so the dashboard can render controls, but the
        # brief itself takes no position on which to pick.
        "disposition_options": ["APPROVE_ONCE", "HOLD", "RESEARCH", "REJECT"],
    }
    try:
        source.publish_brief(request_id, brief)
    except KeyError:
        return {"request_id": request_id, "ok": False, "error": f"unknown request_id {request_id!r}"}
    except Exception as exc:
        return {"request_id": request_id, "ok": False, "error": str(exc)}
    return {"request_id": request_id, "ok": True}


@mcp.tool()
def get_brief(request_id: str) -> dict:
    """Return the brief currently published for ``request_id`` (or ``None``).

    Lets the dashboard — or the agent, to check its own work — read back what was
    formatted for a hold.
    """
    try:
        brief = source.get_brief(request_id)
    except Exception as exc:
        return {"request_id": request_id, "ok": False, "error": str(exc)}
    return {"request_id": request_id, "ok": True, "brief": brief}


def main() -> None:
    path = getattr(mcp.settings, "streamable_http_path", "/mcp")
    log.info(
        "decision-brief MCP starting: source=%s host=%s port=%s path=%s config=%s",
        SOURCE_KIND, HOST, PORT, path, CONFIG_PATH,
    )
    log.info("open holds: %s", [h["request_id"] for h in source.list_holds()])
    log.info("serving streamable-http at http://%s:%s%s", HOST, PORT, path)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
