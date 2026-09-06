# Light-Control MCP server

Standalone [MCP](https://modelcontextprotocol.io) server that controls simulated
"machine" indicator lights (imagine machines at a base / power plant). It exposes
one shared tool layer over **Streamable HTTP** so both agents in
[`docs/agent-build/`](../../docs/agent-build/) — the local Goose harness
([02](../../docs/agent-build/02-local-harness.md)) and the cloud ADK agent
([01](../../docs/agent-build/01-cloud-agent.md)) — connect to the same server.

Spec: [`docs/agent-build/03-light-mcp.md`](../../docs/agent-build/03-light-mcp.md).

## Design seams
- **Transport = Streamable HTTP** (not stdio): one long-running HTTP service is
  reachable over the network by a local *and* a remote/cloud agent.
- **Driver swap seam**: hardware sits behind [`LightDriver`](drivers.py).
  `MockDriver` ships now (in-memory + logs); `SerialDriver` drops in later with
  **zero change** to the server or either agent. Select with `LIGHT_DRIVER`.
- **Machines are config-driven** in [`machines.yaml`](machines.yaml) — rename /
  remap later without touching code.

## Tools (stable contract — both agents depend on these)
| Tool | Signature | Returns |
|---|---|---|
| `list_machines` | `()` | `{"machines": [{"id","state","allowed_states"}]}` |
| `get_status` | `(machine_id: str \| None = None)` | one machine's state, or all if omitted |
| `set_machine` | `(machine_id, state)` | `{"machine_id","state","ok"}` — error if state not allowed |
| `blink` | `(machine_id, count=3, interval_ms=300)` | `{"machine_id","ok"}` — transient, returns to prior state |

## Run (repo root, `.venv` active)
```bash
pip install -r services/light_mcp/requirements.txt   # first time
python -m services.light_mcp.server
```
Serves at **`http://127.0.0.1:8790/mcp`**. Host/port/driver are env-overridable
(see below and `.env.example`).

## Verify with the MCP Inspector
```bash
npx @modelcontextprotocol/inspector
```
Connect to `http://127.0.0.1:8790/mcp` (Streamable HTTP) and confirm the four
tools are listed. Then:
- `set_machine("machine-01","on")` → `ok:true`; `get_status()` shows `machine-01: on`.
- `blink("machine-01")` → returns, leaves state `on`.
- `set_machine("machine-01","banana")` → clean error (`ok:false`), not a crash.

## Environment
| Var | Default | Meaning |
|---|---|---|
| `LIGHT_MCP_HOST` | `127.0.0.1` | bind host |
| `LIGHT_MCP_PORT` | `8790` | bind port (avoids backend/adk/biometrics/feed) |
| `LIGHT_DRIVER` | `mock` | `mock` \| `serial` |
| `LIGHT_SERIAL_PORT` | *(empty)* | e.g. `/dev/tty.usbmodem*` (later) |
| `LIGHT_SERIAL_BAUD` | `115200` | serial baud (later) |
| `LIGHT_MACHINES_CONFIG` | `services/light_mcp/machines.yaml` | machine list |

## Deploy (optional)
[`services/systemd/light-mcp.service`](../systemd/light-mcp.service) mirrors the
existing units; adjust `WorkingDirectory`/`User` for the target host.
