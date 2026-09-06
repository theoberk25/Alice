# Local agent harness — summary + setup runbook

Companion to [02-local-harness.md](02-local-harness.md) (the spec) and
[03-light-mcp.md](03-light-mcp.md) (the tool server). Per [AGENTS.md](../../AGENTS.md).

## What we built

A fully local, air-gapped agent that controls the machine lights by calling the
Light-Control MCP over Streamable HTTP. Three moving parts, all on loopback:

```
Goose CLI  ──HTTP──▶ Ollama  (local LLM, tool calls)      127.0.0.1:11434
   │
   └────────HTTP───▶ Light MCP (light_control tools)      127.0.0.1:8790/mcp
                        └─ MockDriver (in-memory; esp/alice drivers = real path)
```

- **Harness = Goose** (Block, Apache-2.0), driven by Alice's existing **Ollama** —
  no second model server. Verified: Goose loads all four tools
  (`light_control__{list_machines,get_status,set_machine,blink}`), queries status,
  turns a machine on, and blinks one. Egress is loopback-only.

## Where it lives

| Piece | Location | In git? |
|---|---|---|
| Tool server (MCP) | [`services/light_mcp/`](../../services/light_mcp/) | yes |
| Build spec | [`docs/agent-build/02-local-harness.md`](02-local-harness.md) | yes |
| Env vars | [`.env.example`](../../.env.example) (`LIGHT_*`) | yes |
| Deploy unit | [`services/systemd/light-mcp.service`](../../services/systemd/light-mcp.service) | yes |
| **Goose config** | `~/.config/goose/config.yaml` | **no** (host-specific, per doc 02) |
| **Local model** | Ollama (`qwen2.5-tools`) | **no** (pulled per host) |

The harness (Goose binary + its config + the model) is intentionally host-local, not
committed. Only the MCP tool server and docs live in the repo.

## Setup runbook (for a fresh machine)

Assumes the Light MCP is running in mock mode
(`python -m services.light_mcp.server` → serves `http://127.0.0.1:8790/mcp`).

```bash
# 1. Install Goose + Ollama
brew install block-goose-cli ollama

# 2. Start Ollama and pull a TOOL-CAPABLE model
ollama serve &                      # 127.0.0.1:11434
ollama pull qwen2.5                  # strong tool-calling; ~4.7 GB

# 3. Give the model a real context window (agent loops need >>4096; default is 4096)
printf 'FROM qwen2.5:latest\nPARAMETER num_ctx 32768\n' | ollama create qwen2.5-tools -f -
ollama show qwen2.5-tools | grep -iE 'tools|context'   # expect: tools, 32768
```

Write `~/.config/goose/config.yaml`:

```yaml
GOOSE_PROVIDER: ollama
GOOSE_MODEL: qwen2.5-tools
OLLAMA_HOST: http://127.0.0.1:11434
extensions:
  light_control:
    enabled: true
    type: streamable_http          # Goose 1.49 key/type; verify with `goose configure`
    name: light_control
    uri: http://127.0.0.1:8790/mcp  # fixed by file 03
    timeout: 300
```

Verify (headless):

```bash
goose run --no-session --max-turns 8 \
  --system "You are the local machine-operations agent. Use the light_control tools." \
  -t "Which machines are off? Turn machine-02 on and confirm."
# Expect get_status -> set_machine(machine-02,on); MCP log shows MockDriver.set.
```

## Notes / gotchas

- **MCP SDK pin:** `pip install mcp` now resolves to 2.x (FastMCP → MCPServer);
  server.py uses v1 FastMCP, so `requirements.txt` pins `mcp<2` (verified 1.29.1).
- **Model, not harness, is the constraint.** Prefer a ≥7B tool-caller with ≥32K
  context; tiny models call tools poorly and the loop truncates.
- **Local 7B narration can drift** — trust the MCP server log (the driver is the
  source of truth), not the model's prose summary.
- Config/model are per-host; keep `~/.config/goose/` out of git.
