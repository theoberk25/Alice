# Build 03 — Light-Control MCP Server (BUILD THIS FIRST)

> Build order: **this file first**, then `02-local-harness.md` (Goose), then `01-cloud-agent.md` (Google ADK). The two agents are just clients of this server.

## Session orientation (read first)
You are working inside the **Alice** repo (`/Users/theo/Desktop/DNHacks/Alice`). Per `CLAUDE.md`, read `AGENTS.md` and `current.md` before doing anything. Conventions that matter here:
- Python code runs in the repo `.venv`. Config comes from `.env` (see `.env.example`).
- Alice already runs a **local Ollama** (`OLLAMA_BASE_URL=http://127.0.0.1:11434`) and has simulated systems under `protected_systems/`. Do **not** couple to those yet (see "Machines are config-driven" below).
- Existing services live in `services/*` (e.g. `services/backend/server.py`, `services/biometrics/`) with a `services/systemd/` folder for deploy units. This new server follows that pattern.

## Goal
A standalone MCP server that controls "machine" indicator lights on a PCB (simulating machines at a base / power plant). Two agents — a Google ADK **cloud** agent and a Goose **local** agent — connect to it as a shared tool layer.

## Two hard design decisions (already made — keep them)
1. **Transport = Streamable HTTP**, not stdio. One long-running HTTP service serves the local harness over the network *and* a possibly-remote/cloud-deployed agent. (A stdio subprocess can't be reached by a cloud agent.)
2. **Driver swap seam.** Hardware sits behind a `LightDriver` interface. Ship a `MockDriver` now (in-memory + logs); a `SerialDriver` is dropped in later with **zero change** to the server or either agent. The PCB wiring is not known yet — that is fine and expected.

## Machines are config-driven
The set of machines is **not** hardcoded and its real-world meaning is intentionally undecided. Define machines in a config file so they can be renamed/remapped later (to `protected_systems`, to power-plant equipment, whatever) without touching code.

## Location
```
Alice/services/light_mcp/
├── __init__.py
├── server.py        # FastMCP server + tool definitions (the contract below)
├── drivers.py       # LightDriver (ABC) + MockDriver (now) + SerialDriver (stub, later)
├── machines.yaml    # config-driven machine list (placeholder defaults)
└── README.md        # run + test instructions
```

## The tool contract (STABLE — both agents depend on these names/shapes)
Implement exactly these tools. Do not rename without updating files 01 and 02.

| Tool | Signature | Returns |
|---|---|---|
| `list_machines` | `()` | `{"machines": [{"id": str, "state": str, "allowed_states": [str]}]}` |
| `get_status` | `(machine_id: str \| None = None)` | one machine's state, or all if omitted |
| `set_machine` | `(machine_id: str, state: str)` | `{"machine_id", "state", "ok": bool}` — error if state not in that machine's `allowed_states` |
| `blink` | `(machine_id: str, count: int = 3, interval_ms: int = 300)` | `{"machine_id", "ok": bool}` — transient effect, returns to prior state |

Default `allowed_states = ["on", "off"]`. Config may extend per machine later (e.g. `["green","amber","red"]`).

## Implementation notes
- Use the official **MCP Python SDK** (`pip install mcp`) with `FastMCP`. Pattern:
  ```python
  from mcp.server.fastmcp import FastMCP
  mcp = FastMCP("light-control", host="127.0.0.1", port=8790)

  @mcp.tool()
  def set_machine(machine_id: str, state: str) -> dict: ...

  if __name__ == "__main__":
      mcp.run(transport="streamable-http")   # serves at http://127.0.0.1:8790/mcp
  ```
  > The FastMCP `run`/settings surface shifts between SDK versions — verify host/port/path wiring against the installed `mcp` version and pin it in `requirements`. The canonical URL other files expect is **`http://127.0.0.1:8790/mcp`**.
- Port **8790** is chosen to avoid clashes (backend, `adk web`→8000, biometrics→8765, feed→8787). Make host/port env-overridable.
- `drivers.py`:
  ```python
  class LightDriver(ABC):
      def set(self, machine_id: str, state: str) -> None: ...
      def get_all(self) -> dict[str, str]: ...
      def blink(self, machine_id: str, count: int, interval_ms: int) -> None: ...

  class MockDriver(LightDriver):   # in-memory dict + logging.info on every call
  class SerialDriver(LightDriver): # STUB: pyserial; TODO wire real protocol later
  ```
  `SerialDriver.__init__(port, baud)` should exist but its methods may `raise NotImplementedError("wire PCB protocol here")` with a documented placeholder wire format (e.g. write `f"{machine_id}:{state}\n"`). Selection via `LIGHT_DRIVER=mock|serial`.
- `server.py` loads `machines.yaml`, instantiates the driver from env, validates `set_machine` against `allowed_states`, and keeps the driver as the single source of truth (tools call the driver; never hold a second copy of state).
- `machines.yaml` placeholder (rename later):
  ```yaml
  machines:
    - {id: machine-01, allowed_states: [on, off], default: off}
    - {id: machine-02, allowed_states: [on, off], default: off}
    - {id: machine-03, allowed_states: [on, off], default: off}
    - {id: machine-04, allowed_states: [on, off], default: off}
  ```

## Env (append to `.env.example`)
```
LIGHT_MCP_HOST=127.0.0.1
LIGHT_MCP_PORT=8790
LIGHT_DRIVER=mock            # mock | serial
LIGHT_SERIAL_PORT=           # e.g. /dev/tty.usbmodem* (later)
LIGHT_SERIAL_BAUD=115200
LIGHT_MACHINES_CONFIG=services/light_mcp/machines.yaml
```

## Acceptance / verification (must pass before building the agents)
1. Server starts: `python -m services.light_mcp.server` (from repo root, `.venv` active) and logs `streamable-http` listening on `127.0.0.1:8790`.
2. Inspect it with the MCP Inspector: `npx @modelcontextprotocol/inspector` → connect to `http://127.0.0.1:8790/mcp` (Streamable HTTP). Confirm the four tools are listed.
3. Call `set_machine("machine-01","on")` → returns `ok:true`; `get_status()` shows `machine-01: on`; MockDriver logged the call. `blink("machine-01")` returns and leaves state `on`.
4. `set_machine("machine-01","banana")` → clean error (not a crash).
5. Optional: add a `services/systemd/light-mcp.service` unit mirroring existing units.

## Handoff to the agent files
Both agents connect to **`http://127.0.0.1:8790/mcp`** (Streamable HTTP) and use the tool names above. Nothing about the agents depends on `MockDriver` vs `SerialDriver`.
