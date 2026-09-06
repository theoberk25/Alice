# Environmental demo v1

Implements the [authorized handoff](../handoffs/2026-09-06-environmental-demo-context.md).
Demo 1 only; no physical fan, camera feed or scripted ALICE outcomes. A reviewed,
data-only fan anomaly model supplies the pre-action behavioral score.
The plant is deliberately accelerated and uncalibrated. Frontend page design remains
with the teammate; existing native request review accepts this additional contract.

## Operator and agent API

`python -m services.thermal_demo.server` binds loopback only. Use a local SSH tunnel
for a Pi. Every request requires a bearer token; tokens map to server-configured
identities. Operator and individual agent tokens must be distinct. No browser CORS
is enabled; use a trusted local proxy. Never put signing keys or operator tokens in
agent prompts or browser bundles.

| Method/path | Role | Body/result |
| --- | --- | --- |
| POST /demo/configure | operator | Exactly `temperature_f`, `fan_pct`, `battery_pct` |
| POST /demo/start | operator | `{}`; READY → RUNNING |
| POST /demo/pause | operator | `{}`; RUNNING → PAUSED |
| POST /demo/resume | operator | `{}`; PAUSED → RUNNING |
| POST /demo/stop | operator | `{}`; invalidate outstanding action |
| GET /demo/state | either | `thermal-demo-v1` snapshot, requests, history, events, display status |
| POST /demo/fan-requests | agent | `request_id`, `run_id`, `expected_revision`, `fan_pct` |
| GET /demo/review/{audit_request_id} | operator | Existing `alice-runtime-review-v1` |
| POST /demo/review | operator | Existing signed native proof envelope; bearer alone cannot approve |
| GET /demo/events?after=0 | operator | At most 64 ledger events after cursor |

`/review`, `/review/{id}`, `/events?after=…` are compatible aliases for the existing
native feed bridge. Invalid JSON, duplicate fields and invalid transitions return
400; wrong roles 403; unavailable governance 503 or a retained request marked
RECONCILIATION_REQUIRED when submission may already have happened. There is no
unsigned approval endpoint and no raw arbitrary signed-action endpoint on this API.

Configuration creates a fresh run. Starting temperature accepts 32–250 F, fan and
battery 0–100%; finite JSON numbers only. Power is always derived. Capacity and
energy-only acceleration are startup settings, reported in `metadata`; defaults
100 Wh and 1. Ambient is fixed 72 F. The three initial values are never randomized.
A reconfigured run requires Start. Restart loses the in-memory plant and starts
UNCONFIGURED; it retains the durable ledger and never resumes historical commands.

State `values` includes `temperature_f`, `fan_target_pct`, `fan_actual_pct`,
`power_w`, `battery_pct`, `battery_remaining_wh`, `battery_draw_w`, `supply_w` and
explicit simulated camera NORMAL. Show **Server Temperature**, authorized target
and actual fan separately. Show `metadata.energy_time_scale` whenever not 1.
Statuses: UNCONFIGURED, READY, RUNNING, PAUSED, STOPPED, EXHAUSTED. Present EXHAUSTED
as **ENERGY EXHAUSTED**. A monotonic gap over 10 seconds or a backward clock pauses
and emits CLOCK_GAP_PAUSED. Pausing freezes simulation time; HOLD does not.

`revision` increments when an authorized fan target executes. It is an actuator
revision, not a temperature observation version. `observation_sequence` advances
with elapsed plant integration; history retains 600 observations, events 256, and
requests at most 256 per run. History and snapshots are detached copies. Agent
proposals must include the current run and actuator revision. Stale versions are
rejected; only one unresolved proposal is admitted at a time. Request IDs accept
1–64 ASCII letters/digits/underscore/hyphen. Same-run exact retries return the
original record; conflicting reuse is rejected. Fan proposals support 0.01% steps.

`services.thermal_demo.client.DemoClient` provides `state()` and
`request_fan(snapshot, fan_pct, request_id)` for the teammate's agent. Observation
history is in the snapshot. It never approves, automatically retries or runs an LLM.
The standalone `lab.thermal_demo` proposal policy remains an isolated prototype;
its `--auto-apply` option is explicitly simulated and is not integration acceptance.

## ALICE binding and execution

The private [fan schema](../../services/thermal_demo/fan-request.schema.json) does
not widen `common/schemas/action_request.json`. On the wire the target is
DEMO-SERVER-01 and action `set_demo_fan_pct`. `fan_basis_points` is an integer
0–10000 (8500 means 85%); the integer-only signed ledger never rounds a float in an
authorization record. The wire request retains `run_id`, `client_request_id`,
`expected_revision` and verified `agent_id`. Its audit request ID is the SHA-256 of
`run_id + "." + client_request_id`, isolating retries across runs.

Server-configured agent keys sign the exact request. Existing verified release,
exact grant resolution, `decide`, immutable ledger, native console trust, fresh-face
proof binding, nonce/epoch checks and durable one-use review are reused. Assessment
records a live run-validity check, retained environment evidence and a contextual
model score over the requested change, temperature and power. Missing permission
DENYs; a permitted current request ALLOWs when the score is LOW and CHALLENGEs for
ELEVATED/HIGH. The demo release permits cooling-agent-01 and power-agent-01 across
0–100%; observer-agent-01 has no grant. These are local demonstration choices, not
production operating limits or a predetermined decision sequence.

The executor commits EXECUTION_ATTEMPT before applying the exact fan target and
records receipt, result and observed simulation target separately. It rechecks run,
revision, pending request and RUNNING status immediately before applying. Paused,
stopped, exhausted, reset and old-boot runs cannot execute held approvals. Signed
review never changes the original CHALLENGE decision; UI must also show review and
execution states. Unknown results require reconciliation; a decision alone never
causes client-side execution. Historical execution is not replayed after restart.

## Display boundary

The fixed presentation mapping is yellow=power, blue=actual fan speed,
red=temperature and white=battery remaining. Yellow, blue and red are duplicated
pairs. White is a two-segment 0–100% gauge. This mapping is independent of the
anomaly model and does not make the LEDs writable plant actuators.

[Serial v3](esp-serial-protocol.md#version-3-environmental-patterns) sends settings,
not edges. The runtime owns one serial controller, opened with POSIX exclusive
ownership; do not run the existing first-light service concurrently on that port.
The renderer does not require an agent proposal or signed light action. Actual fan
speed and derived power feed the existing mapper. Stopped/exhausted/missing or
older-than-one-second telemetry becomes UNAVAILABLE. A 2-second MCU lease handles
host crashes. Physical unavailable indication is two 75 ms flashes, 75 ms apart,
every 2 seconds; it is distinct from zero/OFF and all normal 50% duty patterns.

Changed settings transmit at the nominal 10 Hz sampling rate. Unchanged settings
get a keepalive at most twice a second per group. Lost ACKs trigger GET
reconciliation, then later newly sampled telemetry; no failed frame is replayed.
Boot changes clear the setting cache. Readback means configured output, not measured
illumination. Firmware compilation on the host does not establish board acceptance.

The reconciled agent interface is the teammate’s [machine-metrics MCP](../guides/machine-metrics-integration.md): `get_metrics()` and `set_fan_speed(value)` on :8790. The HTTP client is the internal adapter path to the same plant; no second fan state file is authoritative.
