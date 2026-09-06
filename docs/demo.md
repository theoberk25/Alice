# Demo script

The authoritative integrated path is [machine metrics MCP](guides/machine-metrics-integration.md)
→ [governed thermal runtime](contracts/environmental-demo-v1.md) → ALICE decision and
review → simulated plant → Xavier's eight-light telemetry display. The lights visualize
one plant snapshot; agents do not command individual LEDs in this story.

## What each pair means

| Pair | Metric | What the audience sees |
| --- | --- | --- |
| Yellow 1/2 | Total power draw | Blink rate rises from 0.5–5 Hz across 400–500 W. |
| Blue 1/2 | Actual fan speed | Off at 0%; blink rate rises from 0.5–5 Hz across 0–100%. |
| Red 1/2 | Server-room temperature | Blink rate rises from 0.5–5 Hz across 80–175 F. |
| White 1/2 | Battery remaining | Two 50% segments: full is solid, partial blinks faster as it empties, empty is off. |

These are telemetry indicators. The XIAO schedules their patterns, while the thermal
runtime remains the source of `fan_actual_pct`, `temperature_f`, `power_w` and
`battery_pct`. The display never grants permission or executes a fan action.

## Data relationships

The simulated plant makes the visual changes coherent:

- An authorized fan target makes actual fan speed ramp toward it, changing blue.
- Fan power is `400 W + 100 W × (fan_actual_pct / 100)^3`, changing yellow.
- Higher fan speed increases cooling, so red reflects the resulting temperature over
  time rather than the requested target itself.
- The configured supply is 450 W. Consumption above that draws the simulated battery,
  so white declines only when the plant exceeds its supply. Use the documented energy
  acceleration when a visible battery change is needed during the short demo.

This is an accelerated demonstration model, not a calibrated facility or hardware
safety model. There is no server-load control in the current API, so the narrative
must not claim that a real or simulated workload spike caused the initial heat.
Configure the hot starting condition explicitly.

## Part 1 — connected enterprise operation

1. Configure the plant at **100 F, 60% fan, 60% battery**, then start it. At the initial
   state power is about **421.6 W**. Do not begin from fabricated zero readings.
2. Keep the Opal router and enterprise/Wazuh host online. Show the cloud agent reading
   the plant through `get_metrics()` with its own bearer identity.
3. Submit one ordinary governed request through the enterprise ingress. Preserve the
   agent ID, responsible user, mission, request ID and signature from ingress through
   Wazuh and ALICE.
4. Show the same correlated receipt and outcome in the enterprise view and technician
   console. Online enterprise execution and the Pi's offline authority transfer remain
   separate control modes.

The committed Google ADK agent has `get_metrics()` and `set_fan_speed()` plus an
opt-in enterprise submission tool. Its automated smoke command is read-only. A prompt
or scripted client must deliberately submit the demo action; autonomous thermal
trigger loops are still integration work.

## Transition — enterprise connectivity is lost

Unplug the wireless router and remove the enterprise host from the demo LAN as described
in the [integrated runbook](guides/demo-runbook.md). The Pi, technician workstation and
local-agent host stay on the wired switch. The starting temperature is already high;
no unimplemented load-spike event is required. Complete the explicit offline authority
transfer before local actions can execute.

## Part 2 — local agents and contextual HOLD

Use distinct authenticated identities even if one laptop runs both clients:

1. `cooling-agent-01` reads the current metrics and proposes 60→70% fan.
2. Repeat 70→80% and 80→90% with fresh request IDs and current revisions. The fitted
   demo model treats these context-consistent +10 point steps as normal, so ALICE
   ALLOWs and applies them.
3. Blue accelerates as the actual fan ramps. Yellow accelerates because fan power rises.
   Red follows the temperature response. Above roughly 79% fan, consumption exceeds
   the simulated 450 W supply and the battery begins to drain; white represents the
   remaining reserve.
4. `power-agent-01` reads the high power draw and proposes a full fan cut to 0%.
5. Permission makes the proposal eligible, but the model evaluates agent profile,
   prior and requested fan speed, change magnitude, temperature and power. The hot-room
   full cut is outside normal support, producing `HIGH` and `ANOMALY_REVIEW_REQUIRED`.
   ALICE records a CHALLENGE/HOLD and does not change the fan target.
6. The technician console shows the immutable request and assessment. The workstation
   LLM may explain why the combination is unusual; it cannot approve it.
7. The technician completes the fresh face check and rejects the request. ALICE records
   the signed rejection, leaves the fan at its prior target, and retains the complete
   event chain for later Wazuh synchronization.

The request-more-context pipeline is available as a separate challenge beat. Keep it
out of this short thermal sequence unless rehearsed end to end; the anomaly HOLD already
provides the human decision moment.

## Honest implementation boundary

The governed metrics adapter, synthetic model, ALLOW/HOLD decision paths, signed native
review, plant equations and display mapping exist in the repository and have automated
tests. The physical Pi still needs the integrated thermal service and serial-v3 firmware
deployed and accepted together. Local autonomous triggers, enterprise authority
handover, real sensor calibration and a visible battery-drain rehearsal remain open.
Use [the runbook](guides/demo-runbook.md) for host addresses, credentials, startup,
outage and reconciliation steps.
