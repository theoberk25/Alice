# Full environmental demo — user intent and implementation context

Date: 2026-09-06. This document consolidates the conversation's current scope.
It is a handoff/specification, not evidence that all described functionality exists
and not authorization to merge, deploy, flash hardware, or operate a real server.

## What the user wants

Build one configurable server-overheating demo, from backend state through physical
LED indicators. The operator types starting values, starts the run, and watches
those values evolve through a thermal/energy simulation. Agents observe the state
and propose changes. ALICE supplies real ALLOW/DENY/HOLD decisions. Approved fan
changes affect the simulation; the lights merely display its resulting state.

The user explicitly wants the complete light implementation, not just a function
that calculates blink rates. Mapping-only was an intermediate deliverable and must
not be described as complete physical implementation.

Only Demo 1 is active. Cloud reconnection, synchronization backlogs, bandwidth,
multiple competing scenarios and the earlier fire investigation/camera-fetch story
are paused. White no longer means bandwidth; it means remaining battery energy.
Yellow no longer means cloud traffic; it means calculated power consumption.
No ML is required for this slice. Do not fabricate model scores or timed decisions.

## Frontend setup and observations

Someone else will design the technician page. Supply a documented backend contract
for these three editable starting inputs:

| Input | Units | Example |
| --- | --- | --- |
| Server temperature | degrees Fahrenheit | 140 |
| Initial fan speed | percent, 0–100 | 60 |
| Battery remaining | percent, 0–100 of configured capacity | 75 |

Power consumption is derived, never a fourth editable starting input. Display both
commanded/authorized fan target and actual fan speed, because the latter ramps.
The frontend should expose Start, Pause, Resume and Stop, the current state, and
actual request/decision outcomes. A new configuration creates a new run ID.

Earlier user sensor name: `Ambient Temperature-Server room`. The subsequently
proposed fan/thermal model is for a server component, not whole-room ambient air.
Use `Server Temperature` as the technical variable/label; confirm presentation
wording before frontend design. Room ambient is a separate fixed 72 F boundary.
160 F is approximately 71 C, a fictional overheating condition, not proof of fire.

Other decorative readings, if retained, may waver slightly (e.g. ambient 70–71 F)
and must not drive actions in this version. Camera is green NORMAL text, explicitly
simulated, with no live feed. Do not add a real video pipeline.

## Environmental relationships

These coefficients are already in the isolated prototype. They are deliberately
accelerated demo tuning, not a calibrated server or battery engineering model.

Let T be server temperature in F; f actual fan fraction between 0 and 1.

```
fan actual approaches authorized fan target with a 1-second time constant
k = 0.004 + 0.030 * f^3
change in T per simulated second = 1.97 - k * (T - 72)
power_w = 400 + 100 * f^3
battery_draw_w = max(0, power_w - 450)
energy_lost_wh = battery_draw_w * elapsed_seconds / 3600
battery_pct = 100 * remaining_wh / capacity_wh
```

Default capacity is 100 Wh. The initial percentage determines initial Wh. The
450 W simulated supply covers demand first; the battery supplies only the deficit.
Below that limit the battery holds its level; charging is not implemented.
The cubic cooling expression is a chosen approximation, not a universal fan law.
Power has a fixed 400 W server contribution plus a fan contribution. Changing heat
input independently does not create an energy-calibrated workload model.

At 160 F and default heat input:

| Fan % | Temperature change, F/s | Power W | Battery draw W |
| --- | --- | --- | --- |
| 60 | +1.05 | 421.6 | 0 |
| 80 | +0.27 | 451.2 | 1.2 |
| 85 | approximately 0 | 461.41 | 11.41 |
| 90 | -0.31 | 472.9 | 22.9 |
| 100 | -1.02 | 500 | 50 |

The user wants stabilization around 80–85% and slow cooling at 90% near the hot
condition. Do not make 90% always cool regardless of temperature/workload: the
simulation approaches a fan-dependent equilibrium. Battery draining begins near
79.37% for these parameters. Zero fan remains possible in the plant, even if a
permission or agent policy disallows requesting it under particular conditions.

Normal energy depletion is small in a 15-second demonstration. An optional explicit
energy-only time multiplier exists in the prototype (default 1). At 90% for 15 s,
normal loss is about 0.0954 Wh; 60x compression gives about 5.725 Wh. Any acceleration
must appear in metadata/UI; never present compressed depletion as a measurement.
When reserve reaches zero and supply cannot cover demand, stop with ENERGY EXHAUSTED.
A real shutdown, thermal throttling or brownout model is outside this slice.

## Progression and randomness

Temperature evolves from the equations, not a predetermined animation. Repeated
runs with identical settings can be deterministic for debugging. Small seeded
workload variation can later make repeats differ; never let noise override the
thermal equation, permissions, or user-entered starting values. The operator's
starting configuration must not be silently randomized.

The earlier approximately 15-second duration is a presentation goal, not permission
to force the curve or ALICE decisions. Pause simulation time when paused. Held fan
requests do not pause the running environment: temperature/battery continue to change.
Use elapsed monotonic time and bounded integration steps. Unexpected long scheduling
gaps should be surfaced, not hidden by fabricated intermediate observations.

## Agents and ALICE boundary

The user's friend is building the LLM/agent behavior. Provide current state, history,
run ID and revision for those agents. Do not replace their work with a parallel LLM.
A research-inspired deterministic FanAgent prototype exists for standalone testing.
Its temperature curve is an example proposal policy, not ALICE policy or an agreed
hardware operating limit:

| T, F | Requested curve fan % |
| --- | --- |
| 80–90 | 10 |
| 110 | 30 |
| 130 | 50 |
| 145 | 70 |
| 155 | 85 |
| 160 | 90 |
| 175+ | 100 |

Ordinary prototype proposals rise by at most 10 percentage points, every 2 simulated
seconds; reductions are slower with hysteresis. This reflects the user's example
of successive +10 percentage-point requests. Real server fan floors are device
specific; 0/10% is a demo choice, not a safe hardware recommendation.

The required production-of-demo boundary is:

```
state -> agent proposal -> ALICE evaluation/review -> authorized execution
      -> applied simulation fan target -> evolving state -> display projection
```

ALLOW applies only the exact currently authorized request. HOLD/CHALLENGE leaves the
fan target unchanged until a valid later decision. DENY leaves it unchanged. Unknown
results require reconciliation, not optimistic execution. Bind requests to run ID,
request ID, agent identity, exact fan target and appropriate state/version. Recheck
held approvals before execution; stop/reset invalidates old-run actions. Deduplicate
retries. Preserve the distinction between assessment, authorization and execution.

Do not hardcode three ALLOWs followed by a HOLD. Do not expose an unauthenticated
`approve` endpoint or trust decisions supplied by the agent/frontend. Existing ALICE
ledger, signed review and audit semantics should be reused through an agreed fan
adapter. A light on/off authorization is not a fan-percentage authorization.

At reviewed upstream e1e7506, signed native review exists, but the first-light signed
execution schema still accepts set_light_state/on/off on eight ESP targets. Its
assessment path still uses a fixture. The new environment fan contract is a specific
integration gap; it must be implemented and tested, not claimed to already work.

## Physical light specification

LEDs are read-only indicators. Their changes neither operate a fan nor require an
agent request or ALICE decision. An approved fan setting changes the simulation;
the display follows actual fan speed, not an unapproved proposal.

Verified repository channel/color ordering from services/light_mcp/machines.yaml:

| Channels / targets | Color | Variable |
| --- | --- | --- |
| ESP-LIGHT-01, ESP-LIGHT-05 | Yellow 1, 2 | Power consumption W |
| ESP-LIGHT-02, ESP-LIGHT-06 | Blue 1, 2 | Actual fan % |
| ESP-LIGHT-03, ESP-LIGHT-07 | Red 1, 2 | Server temperature F |
| ESP-LIGHT-04, ESP-LIGHT-08 | White 1, 2 | Battery % in two segments |

Red: linear 0.5–5 complete flashes/s across 80–175 F, clamped outside.
Blue: 0% OFF; positive values linear 0.5–5 Hz across 0–100%, clamped.
Yellow: linear 0.5–5 Hz across 400–500 W, clamped. It consumes supplied power telemetry;
it does not calculate power from fan speed. Matching colored pairs blink together.
BLINK duty cycle is 50%. These are display endpoints, not safety thresholds.

White uses first segment 0–50%, second 50–100%:

| Battery | White 1 | White 2 |
| --- | --- | --- |
| 0% | OFF | OFF |
| 0–50%, exclusive | BLINK | OFF |
| 50% | SOLID | OFF |
| 50–100%, exclusive | SOLID | BLINK |
| 100% | SOLID | SOLID |

For a partial segment, rate = 0.5 + 4.5*(1 - segment_fill/50) Hz.
Thus at 60%, White 1 is solid and White 2 flashes at 4.1 Hz, as requested.
At 10%, White 1 flashes at 4.1 Hz and White 2 is off. White encodes depletion in
its active half, unlike the other colors' increasing-quantity convention.
Unavailable/stale telemetry must be distinct from zero. The mapper emits UNAVAILABLE;
physical stale behavior and timeout must be agreed in the renderer contract. Do not
silently leave a stale 100% battery display or describe unknown temperature as normal.

## Pi and XIAO timing — required remaining implementation

The Pi display component reads telemetry and sends changed pattern settings; the
XIAO should generate flashes independently. A nominal 10 Hz telemetry refresh is
compatible with 5 Hz blinking because it does not generate the on/off edges.
At 5 Hz, a half-cycle is 100 ms; a 200 Hz local timing loop gives 5 ms granularity,
20 steps per half-cycle. USB/Python timing is not a precision guarantee.

Implement a nonblocking monotonic firmware scheduler for eight channels. Maintain
phase between repeated input updates; synchronize each non-white pair. Avoid drift
from chained sleeps, flooding serial, or one signed action per flash. Preserve the
existing serial framing, errors, readback and on/off behavior. Agree versioned
pattern commands and their precedence with legacy control before changing firmware.
One process owns the serial port. No second display daemon may fight the runtime.
Pattern acknowledgments/readback report configured outputs, not measured illumination.
Flashing, wiring verification and deployment are separate from writing code.

## Existing work and locations

- Published `codex/led-display` through 608f107: pure dcamr/display/led_patterns.py,
  scripts/lab/led_preview.py, eight passing mapping tests and guide. It DOES NOT
  produce physical blinking. This context document is a later local addition.
- Separate `codex/thermal-demo` checkout: scripts/lab/thermal_demo model, controller,
  CLI and eight focused tests previously passed. Do not accidentally include it in
  a display-only PR.
- services/thermal_demo in that checkout is unfinished/uncommitted backend work.
  It offers initial configuration/state/lifecycle and an injected gateway interface,
  but has NO working ALICE fan adapter. Its HTTP test was blocked by sandbox socket
  binding; an escalated rerun was rejected by the user. Do not claim full validation.
- No firmware timing extension, physical acceptance, Pi deployment or completed
  environment-to-ALICE-to-frontend integration has been delivered in this session.

## Full implementation chunks and acceptance

1. Review these units, inputs and output meanings; freeze a versioned contract.
2. Finish/test backend lifecycle, validation, state snapshots, thermal/energy math,
   pause/resume, exhaustion, repeatable runs, and derived-only power.
3. Integrate real agent observation/request tools and exact ALICE fan authorization,
   signed review, execution binding, retries and audit. Test ALLOW/DENY/HOLD without
   using timed fake approvals as acceptance evidence.
4. Supply frontend handoff: editable three-field setup, read-only telemetry, current
   applied versus proposed fan speed, run status, errors and genuine decision events.
   Frontend design belongs to the teammate.
5. Implement complete Pi-to-XIAO pattern delivery and firmware timing. Existing
   mapping tests are necessary but not sufficient. Verify stale updates, independent
   channels, phase, readback, reconnect behavior and legacy on/off compatibility.
6. Run an end-to-end demo with actual ALICE decisions: approved fan increase changes
   target, fan ramps, cooling changes, power follows, reserve drains, LEDs match.
   Held/rejected requests never alter applied state. Record physical evidence before
   calling the full implementation complete.

No cloud reconnect demo, ML training, real fire-safety function, or automatic
publication/deployment is implied by this plan.
