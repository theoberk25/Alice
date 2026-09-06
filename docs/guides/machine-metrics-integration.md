# One machine-metrics interface

Upstream `237c307` supplies the preferred agent interface. Both cloud ADK and local
Goose keep Streamable HTTP at **:8790/mcp** and these tools:

- `get_metrics()` reads `fan_speed`, `server_temperature`, `power_consumption` and
  the governed backend's `battery_pct`.
- `set_fan_speed(value)` proposes fan percent **0–100**, with 0.01% precision.

The integrated path is **agent → MCP → ALICE/thermal service → simulated fan →
LED projection**. `services.thermal_demo` owns the one live plant. MCP delegates to
it; it never writes a competing fan state file, signs decisions, or owns USB serial.
Integer `fan_basis_points` and the private signed request format stay behind this
adapter. Existing signed ledger and native review code are unchanged by this merge.

## Meaning and outcomes

`fan_speed` is **actual** ramping fan percent. `fan_target_speed` is the authorized
target. `server_temperature` is **Fahrenheit** and `power_consumption` **watts**;
`units` makes these explicit. The teammate's file seed of 45 did not establish a
unit contract and is not imported into the plant. Initial inputs still belong to
the operator. There is no automatic restore or zeroing of the simulation.

`get_metrics` adds run ID, actuator revision, status, battery, acceleration metadata
and actual request outcomes to the original three names. Before configuration,
values are null, never fabricated zeroes. The JSON poller files are read-only
observations of this same state, not actuator-command inputs.

A fan result retains `ok`, `fan_speed`, `metrics` and adds decision, review,
application, execution and request bindings. `ok:true` means a confirmed applied
request, or an explicitly marked UNCHANGED read-only no-op when the target already
matches. Actual fan speed may still be ramping. HOLD/CHALLENGE, DENY and UNKNOWN
return `ok:false`, not a successful write. Read the request outcomes in subsequent
metrics to observe signed review completion; an original CHALLENGE stays immutable.

For a normal one-argument call, the adapter reads and binds the current run/revision
and derives a stable per-agent request ID. Repeating an applied target does not
execute again. A lost response returns request ID/run ID/expected revision. For
reconciliation use all three optional arguments unchanged:

```
set_fan_speed(value=90, request_id="…", run_id="…", expected_revision=0)
```

Do not issue a new unbound call after an uncertain result or use a fresh ID to
bypass a pending request. Old-run retries are rejected. Operator setup and signed
native review remain on the existing backend contract; agents have no approval tool.

## Configure and run

Start the [thermal backend](environmental-demo.md) first. Its default port is now
**8795**, avoiding the teammate's external agent-loop console on **8792**.
`--port` still overrides it. Then configure the metrics MCP:

```
MACHINE_BACKEND=thermal
THERMAL_DEMO_URL=http://127.0.0.1:8795
THERMAL_AGENT_TOKENS=<private JSON mapping of agent IDs to distinct bearer tokens>
```

Use exactly the backend's agent-token mapping. The generated demonstration release
contains cooling-agent-01, power-agent-01, observer-agent-01; each client receives
only its own token as `LIGHT_MCP_TOKEN`. Do not reuse the operator token. Agent IDs
come from authenticated bearer credentials, not tool arguments, labels or prompts.
Tokens are preprovisioned; no interactive OAuth registration service is provided.

```
python -m services.light_mcp.server
python -m services.light_mcp.poller --agent cloud --once
```

The cloud agent and poller send `Authorization: Bearer <LIGHT_MCP_TOKEN>`. Configure
the same header on Goose's Streamable-HTTP extension. The poller `--agent` value is
an output label, not an authorization identity. Its usual 0.1 second cadence is
retained. Snapshots include `ts`, `available`, and `max_age_seconds:1`; consumers
must reject unavailable samples or ages outside 0–1 seconds, including after process
or connection failure. Tool failures are never presented as valid metric samples.

All services bind loopback. For remote hosts use SSH forwarding; do not expose
plaintext bearer credentials on a public listener. The existing service templates
now read private environment files for MCP and per-agent poller credentials. No
services were installed or started on a Pi by this code change.

## Retained standalone file test

`MACHINE_BACKEND=file` explicitly selects the teammate's `MachineState` with its
existing `MACHINE_STATE_FILE`, bounds and seeds. It is an isolated, ungoverned test
store, **not** a second actuator for the integrated demo. Its mutation receipt says
`standalone_test:true`, `governed:false`. It neither feeds the thermal plant nor
controls LEDs. No file is seeded in the default thermal mode. Do not deploy file
mode beside the integrated demo and describe its fan value as the live plant.

The old light driver files and channel map remain for historical/bench consumers;
they are dormant in the metrics MCP. The cloud smoke command now reads metrics
only; it does not call Gemini during automated tests or command a fan by default.

The plant snapshot drives Xavier's telemetry display: yellow is derived power, blue
is actual fan speed, red is server temperature and white is two-segment battery
remaining. Agents do not set LED states, temperature, power or battery directly.
Fan changes affect the other values through the simulated plant equations.

## Evidence

See [reconciliation report](../reports/2026-09-06-metrics-reconciliation.md).
The full simulation and physical-acceptance limits remain those of the
[environmental contract](../contracts/environmental-demo-v1.md). No new camera,
firmware or console behavior is part of this reconciliation.
