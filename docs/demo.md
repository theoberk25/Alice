> **Current scope:** the implemented path is machine-metrics MCP `:8790` ->
> governed thermal service `:8795` -> simulated plant -> eight LED telemetry
> channels. The automatic cloud-to-local authority transfer described below is
> still a target; loss of connectivity does not grant authority by itself.

# ALICE: three-minute industrial energy resilience demo

## The story

America cannot industrialize at scale if every intelligent system operating
physical infrastructure stops when its cloud connection disappears. ALICE is the
local governance layer that keeps authorized agents accountable at the edge.

We demonstrate that idea on an energy-and-cooling system. A cloud agent helps while
the internet is available. We remove the cloud connection, but the powered local
network, plant simulation, ALICE and local agents remain. Two local agents then
disagree: one wants more cooling, while the other wants to preserve limited battery
energy. ALICE holds the risky request for a technician instead of letting either
agent act unchecked.

> **Thesis:** the cloud session can fail without taking the local control loop,
> governance or decision history with it.

This is a simulation, not a production thermal controller. The fan, power curve
and battery drain are illustrative, and the LEDs are read-only telemetry.

## Why it fits industrial technology

Industrial AI crosses a boundary that ordinary software does not: its decisions
change machines, energy use and worker environments. Mining, drilling, agriculture,
industrial hazard detection and distributed energy all need the same foundations:
authenticated agents, bounded permissions, fresh local evidence, human review for
risky actions and an audit trail that survives poor connectivity.

This demo uses energy infrastructure as the first concrete wedge. The 450 W local
supply and battery reserve act as a tiny microgrid boundary: when cooling demand
exceeds local supply, stored energy covers the gap. Before producers can safely
sell excess solar power or coordinate decentralized energy markets, local systems
must be able to measure supply and demand, protect critical loads and resolve
conflicting automated objectives without depending on a round trip to the cloud.

The repository implements the thermal/energy example only. Other industrial
domains would require their own sensors, actions, permissions and safety controls;
the demo shows the reusable governance pattern, not completed mining, drilling or
agriculture products.

## The eight lights

The eight LEDs are four paired measurements:

| Color | Represents | Visual meaning |
| --- | --- | --- |
| Yellow pair | Total power draw | Faster blink = more watts |
| Blue pair | Applied fan speed | Faster blink = more cooling effort |
| Red pair | Server-component temperature | Faster blink = hotter |
| White pair | Battery reserve, split into two 50% segments | A partial segment blinks faster as it empties |

The audience only needs one sentence: **red is the heat, blue is the response,
yellow is its power cost, and white is the time remaining.**

## Three-minute run of show

### 0:00-0:20 - The industrial problem

Point to the running plant and lights.

Say:

> "America's next generation of mines, farms, factories and energy systems will
> use autonomous agents. But physical infrastructure cannot become unsafe or
> unaccountable when the cloud goes down. ALICE keeps trusted control local."

### 0:20-0:50 - Cloud connected

Start the simulation at **160 F, 80% fan and 60% battery**. At 80% fan the model
draws **451.2 W** from a **450 W** external supply, so the battery has just started
covering the gap.

1. The Gemini agent calls `get_metrics()` and describes the hot system.
2. It proposes 90% fan through `set_fan_speed(90)`.
3. In this environmental slice, the governed adapter checks the authenticated
   request and current plant revision before the target can be applied. Actual fan
   speed ramps rather than jumping instantly.
4. Blue and yellow speed up. Red begins to slow as the temperature responds.

Say:

> "This is the basic industrial tradeoff: cooling protects equipment, but cooling
> consumes energy. The agent requests a change; it never writes the fan directly."

### 0:50-1:15 - Remove the cloud, not the plant

Disconnect the Opal router's WAN/repeater uplink. If the full network-transition
setup is being used, power off the Opal only after the wired Pi, local-agent host
and technician workstation have the static addresses specified in the
[integrated runbook](guides/demo-runbook.md).

Do **not** unplug the display monitor: that only hides the evidence. The stage
action should remove internet access while leaving the local equipment powered.

Show the next Gemini call timing out or becoming unavailable, while local metrics
and LED patterns continue to update.

Say:

> "A similar loss of cloud access happened at Google in June 2025. A bad policy
> update spread globally and caused API failures, including the Vertex Gemini API.
> Some customers even lost cloud-hosted monitoring. Our cloud session is gone too,
> but this industrial system, its telemetry and ALICE are still running locally."

The target system now performs an explicit, authenticated handoff to local
authority. Until that fence is implemented, label this as an operator-controlled
demo transition; a dead network alone must never authorize a second controller.

### 1:15-2:35 - Local agents hold the line

1. The local cooling agent reads the same fresh plant state and maintains or
   requests 90% fan. In the model, that is about **472.9 W**, so the battery supplies
   roughly **22.9 W** above the external source. Red starts slowing, but yellow is
   faster and white reserve is draining.
2. The local power agent sees that energy cost and proposes a large fan reduction
   to preserve the battery.
3. Under the current signed demo policy, every power-agent fan request requires
   review. ALICE records **CHALLENGE**; present that pending review as **HOLD**.
4. The local explanation states the tradeoff: reducing the fan saves energy, but
   removing cooling while the server is hot increases thermal risk. The LLM does
   not approve or reject anything.
5. The technician rejects the reduction. ALICE records the bound rejection and
   leaves the last authorized fan target in force.

Say:

> "The cooling agent wants airflow. The power agent wants battery endurance.
> This is what industrial autonomy looks like: multiple useful agents with
> conflicting objectives. ALICE checks policy, holds the risky request, and asks
> the technician."

Do not claim that an Isolation Forest created this HOLD. The current environmental
slice uses signed permissions and fresh plant evidence without a live contextual-
model score.

### 2:35-3:00 - Reconnect and close

Restore the uplink. The cloud agent reads the new current state; it cannot reuse a
stale pre-outage revision. The local record retains the cooling request, power-agent
HOLD, technician rejection and resulting fan state. Where the integrated Wazuh
path is configured, queued audit events upload without replacing local history.

Say:

> "The cloud returned to a system that never stopped accounting for its own
> decisions. Today this is a cooling-and-energy model. The same local trust pattern
> can support the mines, farms and factories America needs to operate at scale."

## Presenter background: why the story is credible

These examples enrich the narration; they do not need to be recited in full.

### Google cloud-control failure - June 12, 2025

Google reported that an invalid automated quota-policy change propagated globally
and sent Service Control binaries into crash loops. Many Google Cloud and Workspace
products returned API errors, including the Vertex Gemini API. Google also noted
that some customers' monitoring ran on the same affected cloud, leaving them without
a clear signal of what was happening. Most regions recovered within roughly two
hours, with longer residual impact for some services.

This is the model for the cable pull: we are not reproducing Google's root cause;
we are reproducing its operational consequence—the remote agent is unreachable.

[Google incident report](https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW)

### Google power-and-cooling failure - July 15, 2026

Google reported an upstream electrical fault at a data center serving
`europe-west4-a`. A backup-power transfer failed for part of the facility, a chiller
controller dropped offline, chilled-water pumps did not restart, and the data hall
reached **44 C**. Servers, storage systems and network devices were shut down to
protect equipment, and customer recovery continued for hours after cooling returned.

This incident supplies the energy context for the LEDs. Temperature, fan/cooling,
power, battery margin and network availability are not separate stories: a failure
in one can force decisions across all the others. Local control cannot survive a
total loss of all power, but it can remain available through a remote-cloud outage
for as long as the local network and energy reserve remain healthy.

[Google power-and-cooling incident report](https://status.cloud.google.com/incidents/3BvH3LVGcupoYqV6F4Nw)

### If judges ask how it expands

- **Energy:** the implemented example governs competing cooling and reserve goals;
  future adapters could add generation, storage, flexible loads and market signals.
- **Mining and drilling:** remote equipment has intermittent connectivity and
  expensive physical consequences, making local permissions and audit valuable.
- **Hazard detection and worker wearables:** alerts must remain available locally,
  while identity and evidence establish who or what triggered a response.
- **Agriculture:** autonomous field equipment operates far from reliable broadband
  and needs bounded local actions rather than unconditional cloud dependence.

These are applications of the architecture, not features already in this checkout.
Moving beyond the hackathon requires domain-specific hardware adapters, signed
permissions, safety interlocks, calibrated models and field acceptance for each one.

## Honest boundaries

Working now: one thermal plant, shared metrics tools, authenticated fan proposals,
signed ALICE decisions, review-required power-agent requests, local evidence and
the defined LED projection.

The environmental slice currently sends both cloud and local fan proposals through
that governed adapter. In the full product architecture, enterprise systems own
execution while ONLINE and ALICE becomes the local execution authority only after
a fenced OFFLINE/DDIL handoff. The short demo must not imply two simultaneous
controllers or present the slice's adapter topology as the completed handoff.

Still target work: automatic outage detection, exclusive cloud/local authority
handoff, the final operator page, full reconnection reconciliation and physical
acceptance of the complete thermal-to-LED path. See the
[environmental contract](contracts/environmental-demo-v1.md) and
[LED guide](guides/led-display.md) for the current implementation.

An older `startup_check()` prototype can sweep the eight lights after "Wake up the
system," but it does not restore persisted metrics and is not the integrated path.
For this three-minute plan, prefer the operator-configured live plant state.
