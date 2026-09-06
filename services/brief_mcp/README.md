# Decision-Brief MCP server

Standalone [MCP](https://modelcontextprotocol.io) server that turns ALICE's
**held decisions** into plain-language, technician-facing **briefs** rendered in
the review dashboard (`apps/dashboard/` — `DecisionView`, `ProvenanceTable`,
`RawDecisionViewer`, `TechnicianControls`). It exposes one shared tool layer over
**Streamable HTTP** so the local Goose "brief" agent
([05](../../docs/agent-build/05-brief-harness.md)) — and, later, a cloud agent —
connect to the same server.

Spec: [`docs/agent-build/04-brief-mcp.md`](../../docs/agent-build/04-brief-mcp.md).
This mirrors the [Light-Control MCP](../light_mcp/) strategy (Goose harness →
local Ollama → Streamable-HTTP MCP); only the tool layer differs.

## Governance boundary (keep it)
This server is a **presentation/explanation layer**. It **reads** the
authoritative, immutable `alice.decision` for a hold and **publishes a brief**;
it never recomputes permissions or model scores (the technician console doesn't
either — see [technician-console.md](../../docs/integration/technician-console.md)),
and it exposes **no tool to decide a HOLD**. Choosing
`APPROVE_ONCE` / `HOLD` / `RESEARCH` / `REJECT` is a human technician action taken
after biometric verification, in the dashboard's technician controls — outside
this service. Briefs are decision-support, not decisions.

## Design seams
- **Transport = Streamable HTTP** (not stdio): one long-running HTTP service is
  reachable by a local *and* a remote/cloud agent.
- **Source swap seam**: ALICE + the dashboard sit behind
  [`DecisionSource`](sources.py). `MockSource` ships now (fixture holds from
  [`holds.yaml`](holds.yaml) + an in-memory brief store); `AliceSource` drops in
  later — reading authoritative held decisions from the Pi runtime / audit ledger
  and publishing briefs to the dashboard — with **zero change** to the server or
  the agent. Select with `BRIEF_SOURCE`.
- **Holds are config-driven** in [`holds.yaml`](holds.yaml): illustrative but
  faithful to the real contracts (`set_light_state` action, `LOW`/`ELEVATED`/`HIGH`
  anomaly bands, categorical permission outcomes). Remap without touching code.

## Tools (stable contract — the agent depends on these)
| Tool | Signature | Returns |
|---|---|---|
| `list_holds` | `(status: str \| None = None)` | `{"holds": [{request_id, agent_id, action, target, outcome, reason_code, status, biometric_required, brief_status}]}` — open holds if `status` omitted |
| `get_decision` | `(request_id: str)` | `{"ok", "decision": {...}}` — the full authoritative record (permission, anomaly, evidence+freshness, bindings); `ok:false` if unknown |
| `publish_brief` | `(request_id, summary, factors=[], watch_items=[])` | `{"request_id","ok"}` — pushes a technician-facing brief to the dashboard; explanation-only |
| `get_brief` | `(request_id: str)` | `{"request_id","ok","brief"}` — the published brief, or `brief:null` |

`factors` rows are provenance-first: `{"label","value","source","freshness"}`.

## Run (repo root, `.venv` active)
```bash
pip install -r services/brief_mcp/requirements.txt   # first time
python -m services.brief_mcp.server
```
Serves at **`http://127.0.0.1:8793/mcp`**. Host/port/source are env-overridable
(see below and `.env.example`).

## Verify with the MCP Inspector
```bash
npx @modelcontextprotocol/inspector
```
Connect to `http://127.0.0.1:8793/mcp` (Streamable HTTP) and confirm the four
tools are listed. Then:
- `list_holds()` → three open holds (`req-2026-0906-0001..0003`).
- `get_decision("req-2026-0906-0002")` → PERMITTED permission, `HIGH` anomaly.
- `publish_brief("req-2026-0906-0002", "…", [{label,value,source,freshness}])` →
  `ok:true`; `get_brief(...)` returns it and `list_holds()` now shows
  `brief_status: published`.
- `get_decision("nope")` → clean `ok:false`, not a crash.

## Environment
| Var | Default | Meaning |
|---|---|---|
| `BRIEF_MCP_HOST` | `127.0.0.1` | bind host |
| `BRIEF_MCP_PORT` | `8793` | bind port (avoids backend/adk/biometrics/feed/light) |
| `BRIEF_SOURCE` | `mock` | `mock` \| `alice` |
| `BRIEF_HOLDS_CONFIG` | `services/brief_mcp/holds.yaml` | fixture holds (mock) |
| `BRIEF_DASHBOARD_URL` | *(empty)* | where `alice` source publishes briefs (later) |
| `ALICE_RUNTIME_URL` | `http://127.0.0.1:18080` | Pi runtime the `alice` source reads (shared with Light MCP) |

## Deploy (optional)
[`services/systemd/brief-mcp.service`](../systemd/brief-mcp.service) mirrors the
existing units; adjust `WorkingDirectory`/`User` for the target host.
