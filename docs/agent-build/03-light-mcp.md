# Build 03 — Governed machine-metrics MCP server

> Current implementation supersedes the original light-driver plan retained
> below as design history. The active contract is `get_metrics()` plus
> `set_fan_speed(value: int)`. Fan changes are signed and sent through ALICE;
> this service never writes protected fan state directly.

> Build order: **this file first**, then `02-local-harness.md` (Goose), then `01-cloud-agent.md` (Google ADK). The two agents are just clients of this server.

## Session orientation (read first)
You are working inside the **Alice** repo (`/Users/theo/Desktop/DNHacks/Alice`). Per `CLAUDE.md`, read `AGENTS.md` and `current.md` before doing anything. Conventions that matter here:
- Python code runs in the repo `.venv`. Config comes from `.env` (see `.env.example`).
- Alice already runs a **local Ollama** (`OLLAMA_BASE_URL=http://127.0.0.1:11434`) and has simulated systems under `protected_systems/`. Do **not** couple to those yet (see "Machines are config-driven" below).
- Existing services live in `services/*` (e.g. `services/backend/server.py`, `services/biometrics/`) with a `services/systemd/` folder for deploy units. This new server follows that pattern.

## Goal
A standalone MCP adapter that exposes current fan/temperature/power metrics and
submits governed fan requests. Each physical cloud/local agent deployment runs
its own loopback instance with its own private ALICE signing identity.

## Original light-driver design history
1. **Transport = Streamable HTTP**, not stdio. One long-running HTTP service serves the local harness over the network *and* a possibly-remote/cloud-deployed agent. (A stdio subprocess can't be reached by a cloud agent.)
2. **Driver swap seam.** Hardware sits behind a `LightDriver` interface. Ship a `MockDriver` now (in-memory + logs); a `SerialDriver` is dropped in later with **zero change** to the server or either agent. The PCB wiring is not known yet — that is fine and expected.

## Original machine-light configuration
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

## Active tool contract
Implement exactly these tools. Do not rename without updating files 01 and 02.

| Tool | Signature | Returns |
|---|---|---|
| `get_metrics` | `()` | Exact current `fan_speed`, `server_temperature`, and `power_consumption` from the state file |
| `set_fan_speed` | `(value: int)` | Signed ALICE result: ALLOW, CHALLENGE/HOLD, or DENY; HOLD never changes state before technician approval |

Default `allowed_states = ["on", "off"]`. Config may extend per machine later (e.g. `["green","amber","red"]`).

## Original light-driver implementation notes
- Use the official **MCP Python SDK** (`pip install mcp`) with `FastMCP`. Pattern:
  ```python
  from mcp.server.fastmcp import FastMCP
  mcp = FastMCP("light-control", host="127.0.0.1", port=8795)

  @mcp.tool()
  def set_machine(machine_id: str, state: str) -> dict: ...

  if __name__ == "__main__":
      mcp.run(transport="streamable-http")   # serves at http://127.0.0.1:8795/mcp
  ```
  > The FastMCP `run`/settings surface shifts between SDK versions — verify host/port/path wiring against the installed `mcp` version and pin it in `requirements`. The canonical URL other files expect is **`http://127.0.0.1:8795/mcp`**.
- Port **8795** is chosen to avoid clashes (backend, `adk web`→8000, biometrics→8765, feed→8787). Make host/port env-overridable.
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
LIGHT_MCP_PORT=8795
MACHINE_STATE_FILE=/mnt/alice-usb/machine-state.json
ALICE_RUNTIME_URL=http://192.168.50.20:8080
ALICE_AGENT_ID=cooling-agent-01
ALICE_AGENT_KEY_FILE=/private/path/cooling-agent-01-k1.seed
```

## Acceptance / verification (must pass before building the agents)
1. Start `python -m services.light_mcp.server` from the repo root and confirm
   Streamable HTTP is listening on `127.0.0.1:8795`.
2. Connect MCP Inspector to `http://127.0.0.1:8795/mcp`; confirm exactly
   `get_metrics` and `set_fan_speed` are exposed.
3. `get_metrics()` returns the three current numbers from the Pi state file.
4. A normal integer `set_fan_speed` request returns ALLOW and changes state only
   through ALICE. An anomalous request returns CHALLENGE and leaves state unchanged.
5. A non-integer or out-of-range value returns a clean error without a request.

## Handoff to the agent files
Each agent connects to its own **`http://127.0.0.1:8795/mcp`** instance. Configure
`ALICE_AGENT_ID` and `ALICE_AGENT_KEY_FILE` outside Git for that one identity.
Both instances use the same code and tool contract; they do not share a key-bearing
process.
