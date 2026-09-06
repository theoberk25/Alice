> **Current integrated behavior:** [machine-metrics integration](../../docs/guides/machine-metrics-integration.md). `MACHINE_BACKEND=thermal` is the default: it reads the authoritative plant and routes fan changes through ALICE. The file-backed behavior below is retained only for explicit `MACHINE_BACKEND=file` standalone tests, and does not control the demo.

# Machine-metrics MCP server

> Repurposed from light control (dir/package name kept as `light_mcp` to preserve
> the import path, URL and deploy wiring). Spec background:
> [`docs/agent-build/03-light-mcp.md`](../../docs/agent-build/03-light-mcp.md).

Standalone [MCP](https://modelcontextprotocol.io) server over **Streamable HTTP**
that reads a JSON **state file on the Raspberry Pi** holding three numbers:

```json
{"fan_speed": 50, "server_temperature": 45, "power_consumption": 300}
```

The agent may **read all three** and may request changes only to `fan_speed`.
Each physical agent deployment runs its own loopback instance at
**`http://127.0.0.1:8795/mcp`**, configured with that agent's private signing key.
Do not expose an `agent_id` tool argument or share one signing process across
different agent identities.

## Tools (stable contract)
| Tool | Signature | Returns |
|---|---|---|
| `get_metrics` | `()` | `{"fan_speed", "server_temperature", "power_consumption"}` — read from the file |
| `set_fan_speed` | `(value: int)` | Signed ALICE request result: ALLOW, HOLD (`CHALLENGE`), or DENY. A HOLD does not change the state until a technician approves it. |

`server_temperature` and `power_consumption` are treated as externally owned
(e.g. a sensor/simulator loop on the Pi). Reads always hit disk; `set_fan_speed`
submits through ALICE and never writes the file directly. The ALICE runtime owns
the protected fan-state write after an automatic ALLOW or technician approval.

## Files
- [`server.py`](server.py) — FastMCP server + the two tools.
- [`state.py`](state.py) — `MachineState`: atomic, locked JSON store; seeds the
  file if missing. The file path (`MACHINE_STATE_FILE`) is the dev→Pi seam.
- [`poller.py`](poller.py) — **per-agent** 0.1s poller (see below).
- `drivers.py` / `machines.yaml` — legacy light-control backend, retained but
  **no longer used** by `server.py`.

## Run (repo root, `.venv` active)
```bash
pip install -r services/light_mcp/requirements.txt   # mcp<2 (v1 FastMCP), pyyaml
python -m services.light_mcp.server
```
Serves at **`http://127.0.0.1:8795/mcp`**. Env-overridable: `LIGHT_MCP_HOST`,
`LIGHT_MCP_PORT`, `MACHINE_STATE_FILE`, `FAN_SPEED_MIN`/`MAX`, `SEED_*` (see
`.env.example`). On the Pi, point `MACHINE_STATE_FILE` at the real path.

## Verify (MCP Inspector or programmatic client)
```bash
npx @modelcontextprotocol/inspector    # connect to http://127.0.0.1:8795/mcp (Streamable HTTP)
```
Confirm two tools listed, then: `get_metrics()` → three numbers;
`set_fan_speed(72)` → `ok:true` and `get_metrics().fan_speed == 72`;
`set_fan_speed(150)` → `ok:false` (out of range), server keeps serving.

## Per-agent metrics poller (the "0.1s cron")
Each agent runs **one** poller. Real cron can't do sub-second, so this is a
long-running 10 Hz loop (deployed as systemd — the sub-second analog of cron):
it opens one MCP session, calls `get_metrics` every `--interval` seconds (default
0.1), logs a ~1/sec heartbeat, and writes the latest sample to a per-agent
snapshot file the agent can read without its own round-trip.

```bash
python -m services.light_mcp.poller --agent cloud     # cloud ADK agent
python -m services.light_mcp.poller --agent local     # local Goose agent
python -m services.light_mcp.poller --agent cloud --once   # single poll (tests)
```
Snapshot default: `poller_<agent>_latest.json` beside this module (gitignored).

## Deploy (optional, systemd)
- [`services/systemd/light-mcp.service`](../systemd/light-mcp.service) — the server.
- [`light-metrics-poller-cloud.service`](../systemd/light-metrics-poller-cloud.service)
  and [`light-metrics-poller-local.service`](../systemd/light-metrics-poller-local.service)
  — the two per-agent pollers (each `Requires=`/`After=` the server).
Adjust `WorkingDirectory`/`User`/`MACHINE_STATE_FILE` for the target host.
