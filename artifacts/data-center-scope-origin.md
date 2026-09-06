# Data-Center Infrastructure Scope & Real-Event Origin

Created 2026-09-06. Explains **why** the ALICE / DCAMR demo now centers on a
**data hall / data center** as the governed infrastructure — the energy and
thermal loop it models — and the **real-world outages** that origin-story is
grounded in. This is a scope/origin memo, not a spec: for the story see
[`deliverables/pitch-narrative.md`](../deliverables/pitch-narrative.md), for the
beat-by-beat script see [`docs/demo.md`](../docs/demo.md), and for the broader
energy/base-ops landscape this sits inside see
[`agentic-ai-energy-base-ops.md`](../../agentic-ai-energy-base-ops.md).

No-overclaim guardrail carries through this whole doc: the demo is **modeled on
the same failure pattern** as the incidents below. We do not claim to have
recreated them or that ALICE would have "solved" them.

## The scope shift

The project began as agentic AI for **industrial/energy & base operations**
broadly — microgrids, utilities, HVAC, real-property/maintenance
([background](../../agentic-ai-energy-base-ops.md)). That framing is correct but
diffuse; it doesn't give a demo one concrete plant a judge can watch.

The current scope narrows to a **data hall** as the governed physical system:
server racks drawing power and shedding heat, a cooling plant fighting that
heat, a power/battery budget bounding both, all under DDIL (disconnected,
degraded, intermittent, limited) connectivity. Concretely, the eight modeled
supplies ([`services/light_mcp/machines.yaml`](../services/light_mcp/machines.yaml))
are the data-hall assets themselves — primary/backup feeds, **Server rack A/B
supply**, **Cooling plant supply**, comms and security racks.

**Why a data center specifically:**

- **It is where the energy problem is most acute right now.** Compute buildout
  (AI accelerators, dense racks) is the fastest-growing electrical and thermal
  load in the infrastructure world; rising rack density shrinks thermal
  headroom, so a cooling interruption becomes critical *faster*, with less time
  to respond before protective shutdown.
- **It gives one demoable, self-contained plant.** Server temperature (°F), fan
  speed (%), power draw (W), and battery reserve (Wh) are a tight, legible
  control loop with visible tradeoffs — unlike a sprawling microgrid.
- **It keeps the defense-relevant DDIL thesis intact.** A base data hall / edge
  compute node must keep regulating when the cloud oversight is gone — the same
  offline-first requirement as microgrid islanding, but on infrastructure every
  judge already understands.

## The energy + thermal loop the demo models

The physical chain the scenario turns on:

```
server activity ↑  →  power draw ↑  →  heat output ↑  →  server temperature ↑
        ↑                                                         │
        └──────────────── cooling plant / fans ───────────────────┘
                          (bounded by the power + battery budget)
```

- **Activity → power → heat.** Dynamic power scales steeply with utilization;
  that power is dissipated as heat at the silicon. More load, hotter chips.
- **Cooling vs. power tension.** Raising fan speed removes heat but *adds* power
  draw. Two local agents embody the tension: a **thermal** agent that raises
  `fan_speed` as temperature climbs, and a **power** agent that cuts it as draw
  crosses threshold. Their conflict — resolved under ALICE governance — is the
  demo's core.
- **The trigger (new mod).** The heat rise is caused by a **simulated cloud
  crash**: in the seconds before the cloud goes down, **server activity
  skyrockets**, spiking power draw and driving `server_temperature` up. The same
  event both removes cloud oversight and creates the thermal emergency the local
  agents must handle alone.

## Real-event origin

The scenario is anchored in three documented failure classes. Each backs a
different piece of the story.

### 1. Heat can take servers offline — data-center thermal event

**AWS us-east-1, May 2026.** A data-center thermal event: cooling failed and,
per reporting, *"servers automatically shut down when the temperatures exceeded
the operating thresholds… to protect the hardware."* This is the real-world
backing for the demo's setup — heat forcing machines offline.
[Network World](https://www.networkworld.com/article/4168878/aws-hit-by-us-east-1-outage-after-data-center-thermal-event.html)

**Google Cloud, London, July 2022.** Multiple redundant cooling systems failed
during a 40 °C heatwave, causing VM terminations across a zone — heat as a
first-class outage cause.
[Google status](https://status.cloud.google.com/incidents/XVq5om2XEDSqLtJZUvcH) ·
[DatacenterDynamics](https://www.datacenterdynamics.com/en/news/googles-london-data-center-outage-during-heatwave-caused-by-simultaneous-failure-of-multiple-redundant-cooling-systems/)

### 2. An activity surge can precede/cause a crash — load spike / retry storm

**GitHub, Aug 2026.** A retry bug amplified traffic ~10× (a token service went
from ~7–9K RPS to 70–100K RPS), prolonging an 8-hour outage — the real mechanism
behind "activity skyrockets right before it goes down."
[GitHub Blog](https://github.blog/news-insights/company-news/the-august-17-outage-and-the-work-ahead/)

**AWS us-east-1, Dec 2021.** A "large surge of connection activity" drove retries
and "persistent congestion" — classic retry-storm congestion collapse.
[AWS post-mortem](https://aws.amazon.com/message/12721/)

### 3. An *authorized* action can be the catastrophe — the ALICE failure mode

**Meta, Oct 2021.** A permitted maintenance command took Facebook, Instagram,
and WhatsApp offline for ~6 hours; Meta's own audit tool, built to catch exactly
that kind of command, had a bug and let it through. This is ALICE's failure mode
precisely — not malice, not a broken rule, an authorized action that is
catastrophic in context with nothing local to hold it. ALICE is the boundary
that was missing, and unlike a cloud audit tool it keeps working with the
network gone.
[Meta Engineering](https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/)

## Honest caveats (state these if a technical judge probes)

- **Room air does not spike in seconds.** Silicon/junction temperature reacts in
  milliseconds–seconds; rack/aisle/room air moves over minutes. "The bay
  instantly got hot" is a compression.
- **Modern gear throttles, then protective-shuts-down, before it "burns up."** A
  heat-related outage is a clean protective shutdown, not thermal destruction;
  throttling would also *reduce* the activity spike on the way there.
- **The big cloud thermal outages were cooling-failure-driven,** not pure
  compute-demand-driven. High load is the standing condition that makes lost
  cooling critical faster. The most literal "surge → crash" path is software
  (retry storms), while heat is the more cinematic one — the demo deliberately
  couples both.
- **What ALICE does and doesn't cover.** ALICE holds a discrete agent action
  against a learned local baseline. It is **not** a traffic-surge, DDoS, or
  retry-storm mitigator, and it would not have prevented Meta's BGP outage. The
  honest tie is the *shape* of the failure plus the DDIL twist that makes it
  ours.

## Sources

Full sourced realism brief on file with the team (research, 2026-09-06). Key
references:

- Network World — AWS us-east-1 thermal event (May 2026): https://www.networkworld.com/article/4168878/aws-hit-by-us-east-1-outage-after-data-center-thermal-event.html
- Google Cloud status — europe-west2-a cooling failure (2022): https://status.cloud.google.com/incidents/XVq5om2XEDSqLtJZUvcH
- DatacenterDynamics — Google London heatwave cooling failure: https://www.datacenterdynamics.com/en/news/googles-london-data-center-outage-during-heatwave-caused-by-simultaneous-failure-of-multiple-redundant-cooling-systems/
- GitHub Blog — The August 17 outage and the work ahead (2026): https://github.blog/news-insights/company-news/the-august-17-outage-and-the-work-ahead/
- AWS — Summary of the Dec 7, 2021 us-east-1 event: https://aws.amazon.com/message/12721/
- Meta Engineering — More details about the October 4 outage (2021): https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/
