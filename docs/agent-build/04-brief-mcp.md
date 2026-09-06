# Build 04 — Decision-Brief MCP Server (BUILD THIS FIRST for the brief agent)

> Build order: **this file first**, then `05-brief-harness.md` (the Goose "brief"
> agent). The agent is just a client of this server. This is a **second, parallel
> agent build** that reuses the exact strategy of the Light-Control stack
> (`03-light-mcp.md` + `02-local-harness.md`) — Goose harness → local Ollama →
> Streamable-HTTP MCP — for a different job: the **technician review dashboard**.

## Session orientation (read first)
Working inside the **Alice** repo (`/Users/theo/Desktop/DNHacks/Alice`). Per
`CLAUDE.md`, read `AGENTS.md` and `current.md` first. Conventions that matter here:
- Python runs in the repo `.venv`; config via `.env` (see `.env.example`).
- Existing services live in `services/*`; deploy units in `services/systemd/`.
  This server follows the same pattern as [`services/light_mcp/`](../../services/light_mcp/).
- Alice emits **decision records** (`dcamr/decision_model.py`, the `alice.decision`
  event in [technician-console.md](../integration/technician-console.md)) with
  outcomes `ALLOW` / `REQUEST_CONTEXT` / `HOLD` / `DENY`. A **HOLD** is an action
  the Pi held pending a **human technician**.
- The dashboard scaffolding (`apps/dashboard/` — `DecisionView`, `ProvenanceTable`,
  `RawDecisionViewer`, `TechnicianControls`) is where a technician reviews a hold
  and, after biometric verification, decides it.

## Goal
A standalone MCP server that lets a local agent turn ALICE's **held decisions**
into plain-language, provenance-first **briefs** rendered in the review dashboard,
so a technician can decide the HOLD faster and better-informed. The model does the
*formatting/explaining*; the *decision* stays with the human.

## Two hard design decisions (already made — keep them)
1. **Transport = Streamable HTTP**, not stdio. One long-running HTTP service serves
   the local harness now and a possibly-remote/cloud agent later. (A stdio
   subprocess can't be reached by a cloud agent.)
2. **The agent formats; it never decides.** This server is a presentation layer:
   it **reads** the authoritative, immutable decision and **publishes a brief**. It
   **does not** recompute permissions or model scores (the technician console
   doesn't either), and it exposes **no tool to approve/reject/hold**. The
   authorization outcome (`APPROVE_ONCE` / `HOLD` / `RESEARCH` / `REJECT`) is a
   human action taken in the dashboard after biometric verification — never a tool
   call here. This keeps the governance story intact: "never manufacture model
   results or overwrite the authoritative decision."

## Source swap seam (mirrors the Light MCP driver seam)
ALICE and the dashboard sit behind a `DecisionSource` interface:
- `MockSource` now: fixture holds from `holds.yaml` + an in-memory brief store.
  Fully demoable with no Pi, no ledger, no dashboard backend.
- `AliceSource` later: reads authoritative held decisions from the Pi runtime /
  audit ledger and publishes briefs to the dashboard — dropped in with **zero
  change** to the server or the agent. Selection via `BRIEF_SOURCE=mock|alice`.

## Holds are config-driven
The held decisions in `holds.yaml` are **illustrative but faithful** to the repo's
real contracts (`set_light_state` per `common/schemas/action_request.json`;
`LOW`/`ELEVATED`/`HIGH` anomaly bands per `dcamr/anomaly_engine/scoring.py`;
categorical permission outcomes per `dcamr/decision_model.py`). They are **not**
live model output. Rename/remap without touching code.

## Location
```
Alice/services/brief_mcp/
├── __init__.py
├── server.py        # FastMCP server + the four tools (contract below)
├── sources.py       # DecisionSource (ABC) + MockSource (now) + AliceSource (stub, later)
├── holds.yaml       # config-driven fixture held decisions
├── requirements.txt
└── README.md
```

## The tool contract (STABLE — the agent depends on these names/shapes)
| Tool | Signature | Returns |
|---|---|---|
| `list_holds` | `(status: str \| None = None)` | `{"holds": [{request_id, agent_id, action, target, outcome, reason_code, status, biometric_required, brief_status}]}` — open holds if `status` omitted; else exact-match |
| `get_decision` | `(request_id: str)` | `{"ok": bool, "decision": {...}}` — full authoritative record (permission, anomaly band+score, evidence+freshness, context_challenge, biometric_required); `ok:false` if unknown |
| `publish_brief` | `(request_id, summary, factors=[], watch_items=[])` | `{"request_id","ok": bool}` — pushes a technician-facing brief to the dashboard; explanation-only |
| `get_brief` | `(request_id: str)` | `{"request_id","ok","brief"}` — the published brief, or `brief:null` |

- `factors` rows are provenance-first: `{"label","value","source","freshness"}` —
  mirror what `get_decision` returned; do not invent factors.
- `publish_brief` must **not** carry an authorization verdict; the brief schema
  has no field for one. `disposition_options` is echoed (`APPROVE_ONCE`/`HOLD`/
  `RESEARCH`/`REJECT`) only so the dashboard can render controls.
- Unknown holds and malformed input return `ok:false` (a clean result the agent
  can report), never a crash.

## Implementation notes
- Official **MCP Python SDK** (`pip install "mcp<2"`) with `FastMCP`:
  ```python
  from mcp.server.fastmcp import FastMCP
  mcp = FastMCP("decision-brief", host="127.0.0.1", port=8793)

  @mcp.tool()
  def publish_brief(request_id: str, summary: str, factors: list[dict] | None = None,
                    watch_items: list[str] | None = None) -> dict: ...

  if __name__ == "__main__":
      mcp.run(transport="streamable-http")   # serves at http://127.0.0.1:8793/mcp
  ```
  > Same SDK gotcha as the Light MCP: pin `mcp<2` (2.x renames `FastMCP`). The
  > canonical URL the agent expects is **`http://127.0.0.1:8793/mcp`**.
- Port **8793** avoids clashes (backend, `adk web`→8000, biometrics→8765,
  feed→8787, esp-op→8789, light MCP→8795). Make host/port/source env-overridable.
- `sources.py`:
  ```python
  class DecisionSource(ABC):
      def list_holds(self, status: str | None = None) -> list[dict]: ...
      def get_decision(self, request_id: str) -> dict | None: ...
      def publish_brief(self, request_id: str, brief: dict) -> None: ...
      def get_brief(self, request_id: str) -> dict | None: ...

  class MockSource(DecisionSource):   # holds.yaml fixtures + in-memory brief store
  class AliceSource(DecisionSource):  # STUB: Pi runtime/ledger read + dashboard publish
  ```
  `AliceSource` methods may `raise NotImplementedError` with the documented seams
  (read authoritative `alice.decision`; publish to `dcamr/api/dashboard_api.py` or
  an `alice.*` display event). **Agree the console wire schema (their Zod / JSON
  schemas + fixtures) before coding it** — do not invent omitted payload fields.
- `server.py` loads `holds.yaml`, instantiates the source from `BRIEF_SOURCE`, and
  keeps the source as the single source of truth (tools call it; no second copy).

## Env (append to `.env.example`)
```
BRIEF_MCP_HOST=127.0.0.1
BRIEF_MCP_PORT=8793
BRIEF_SOURCE=mock            # mock | alice
BRIEF_HOLDS_CONFIG=services/brief_mcp/holds.yaml
BRIEF_DASHBOARD_URL=         # alice source only; where briefs are published
# alice source also reads ALICE_RUNTIME_URL (shared with the Light MCP block).
```

## Acceptance / verification (must pass before building the agent)
1. Server starts: `python -m services.brief_mcp.server` (repo root, `.venv`) and
   logs `serving streamable-http at http://127.0.0.1:8793/mcp` with three open holds.
2. Inspect with the MCP Inspector: `npx @modelcontextprotocol/inspector` → connect
   to `http://127.0.0.1:8793/mcp` (Streamable HTTP). Confirm the four tools.
3. `list_holds()` → `req-2026-0906-0001..0003`. `get_decision("req-2026-0906-0002")`
   → PERMITTED permission + `HIGH` anomaly. `publish_brief(...)` → `ok:true`;
   `get_brief(...)` returns it; `list_holds()` now shows `brief_status: published`.
4. `get_decision("nope")` and `publish_brief("nope", "x")` → clean `ok:false`.
5. Optional: add `services/systemd/brief-mcp.service` mirroring existing units.

## Handoff to the agent file
The brief agent connects to **`http://127.0.0.1:8793/mcp`** (Streamable HTTP) and
uses the four tool names above. Nothing about the agent depends on `MockSource`
vs `AliceSource`.
