# Decision-Brief agent harness — summary + setup runbook

Companion to [05-brief-harness.md](05-brief-harness.md) (the spec) and
[04-brief-mcp.md](04-brief-mcp.md) (the tool server). Per [AGENTS.md](../../AGENTS.md).
Reuses the shared Goose + Ollama setup from
[local-harness-setup.md](local-harness-setup.md) — only the tool server and role differ.

## What we built

A fully local, air-gapped agent that turns ALICE's **held decisions** into
technician-facing **briefs** on the review dashboard, by calling the Decision-Brief
MCP over Streamable HTTP. Three moving parts, all on loopback:

```
Goose CLI  ──HTTP──▶ Ollama  (local LLM, tool calls)         127.0.0.1:11434
   │
   └────────HTTP───▶ Decision-Brief MCP (decision_brief tools) 127.0.0.1:8793/mcp
                        └─ MockSource (fixture holds; AliceSource = real Pi/dashboard path)
```

- **Harness = Goose** driven by Alice's existing **Ollama** and the same
  `qwen2.5-tools` model as the Light harness — no second model server. The agent
  calls `list_holds` → `get_decision` → `publish_brief`; egress is loopback-only.
- **The agent formats; it never decides.** There is deliberately no
  approve/reject/hold tool — the technician decides the HOLD in the dashboard after
  biometric verification.

## Where it lives

| Piece | Location | In git? |
|---|---|---|
| Tool server (MCP) | [`services/brief_mcp/`](../../services/brief_mcp/) | yes |
| Build specs | [`04-brief-mcp.md`](04-brief-mcp.md), [`05-brief-harness.md`](05-brief-harness.md) | yes |
| Env vars | [`.env.example`](../../.env.example) (`BRIEF_*`) | yes |
| Deploy unit | [`services/systemd/brief-mcp.service`](../../services/systemd/brief-mcp.service) | yes |
| **Goose config** | `~/.config/goose/config.yaml` | **no** (host-specific) |
| **Local model** | Ollama (`qwen2.5-tools`) | **no** (shared with the Light harness) |

The harness (Goose binary + config + model) is host-local, not committed. Only the
MCP tool server and docs live in the repo.

## Setup runbook (for a fresh machine)

Goose + Ollama + the `qwen2.5-tools` model are the **same install** as the Light
harness — do steps 1–3 of [local-harness-setup.md](local-harness-setup.md) once and
reuse them. Then start the Decision-Brief MCP and point Goose at it.

```bash
# Decision-Brief MCP in mock mode (repo root, .venv active) -> http://127.0.0.1:8793/mcp
pip install -r services/brief_mcp/requirements.txt   # first time
python -m services.brief_mcp.server
```

Add the extension to `~/.config/goose/config.yaml` (keep any `light_control`
extension too, or use a separate Goose profile for this agent):

```yaml
GOOSE_PROVIDER: ollama
GOOSE_MODEL: qwen2.5-tools
OLLAMA_HOST: http://127.0.0.1:11434
extensions:
  decision_brief:
    enabled: true
    type: streamable_http           # Goose 1.49 key/type; verify with `goose configure`
    name: decision_brief
    uri: http://127.0.0.1:8793/mcp   # fixed by file 04
    timeout: 300
```

Verify (headless):

```bash
goose run --no-session --max-turns 10 \
  --system "You prepare held ALICE decisions for a human technician. Call get_decision, then publish_brief a neutral summary + provenance-first factors. Never state a verdict; the technician decides." \
  -t "Brief the oldest open hold for the technician."
# Expect list_holds -> get_decision(req-2026-0906-0001) -> publish_brief; MCP log shows publish_brief.
```

## Notes / gotchas

- **MCP SDK pin:** `pip install mcp` resolves to 2.x (FastMCP → MCPServer);
  `requirements.txt` pins `mcp<2`, same as the Light MCP.
- **Model, not harness, is the constraint.** Prefer a ≥7B tool-caller with ≥32K
  context; tiny models call tools poorly and the loop truncates.
- **No verdict from the model.** The brief is decision-support; there is no tool to
  decide a HOLD, and the role prompt forbids recommending one. If the model narrates
  a decision, it is prose only — trust the MCP log, and the human's action in the
  dashboard, as the source of truth.
- Config/model are per-host; keep `~/.config/goose/` out of git.
