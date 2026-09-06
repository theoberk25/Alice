# ALICE dashboards — significance & front-end integration guide

**Audience:** a front-end engineer wiring this data viz into the real ALICE
technician console (`apps/desktop`, `packages/ui`).

This doc explains what the two demo screens are, *why they matter to the ALICE
story*, the exact data they bind to, and how to re-implement them against the
**real** contracts instead of the prototype's `/state` endpoint. The demo screens
are the **target UX**; the real system emits a richer, event-sourced feed, so you
build **selectors over the store**, not direct bindings to a flat snapshot.

> TL;DR for the impatient: the prototype gives you a free "current values"
> snapshot at `GET /state`. The real console gets **no snapshot** — it folds a
> hash-chained audit feed into a zustand store and *derives* the current values
> itself. Keep the demo's visuals; swap the data source for store selectors.

---

## 1. What these two screens are, and why they matter

The prototype (`test-simulation/`) fakes a base data-hall: a live environment
plus two conflicting agents (**Thermal** raises the fan to cool; **Power** lowers
it to save the battery). There is deliberately **no ALICE decision layer** — a
drastic fan cut is *flagged* ("ALICE would hold this") but not applied, so a run
drains to `ENERGY EXHAUSTED`. That absence is the whole pitch: the screens show
the exact moment a human-in-the-loop arbiter is needed.

Two screens, two jobs — mirroring ALICE's **"Decides vs Explains"** split
(`ALICE-DCAMR Architecture.md` §System Overview):

| Screen | Route | Role | The point it makes |
|---|---|---|---|
| **Agentic-thoughts console** | `/` (`webui/demo.html`) | *Explains* — the human-readable narrative | You can watch two autonomous agents reason, propose, and collide. The **seam** where ALICE would `HOLD` a consequential action is rendered as a red flagged card. |
| **Environment dashboard** | `/dashboard` (`webui/dashboard.html`) | *Observes* — the ground-truth plant state | Big, glanceable current values (temp / fan / power / battery) with threshold coloring. This is what actually goes wrong when nobody arbitrates. |

Both are what a technician stares at. In the real product the "environment" is a
protected cyber system and the "drastic fan cut" is a consequential agent action
(e.g. `disable_edr(Server-04)`), but the **UX shape is identical**: live telemetry
tiles + an agent-reasoning feed + a highlighted human-decision seam.

---

## 2. Screen-by-screen: what to render

### 2a. Environment dashboard (`/dashboard`)

Four tiles, refreshed ~2 Hz. Each tile = a big value + a sub-label + (fan/battery)
a progress bar.

- **Server temperature** — `server_temperature_f` °F. Sub: `room 72°F · setpoint ~150°F`.
  Turns **red** (`.over`) at `>= 150`.
- **Fan speed** — `actual_fan_pct` %, bar width = actual fan. Sub shows `target_fan_pct`.
  Actual chases target with a ~1 s lag (that lag is meaningful — show both).
- **Power draw** — `power_consumption_w` W. Sub: `supply 450W · over-supply draw <battery_draw_w>W`.
  Turns **red** when `power_consumption_w > supply_w` (battery is now draining).
- **Battery reserve** — `battery_remaining_pct` %, bar width = %. Sub: `<battery_remaining_wh> Wh / 100 Wh`.
  Bar color: `> 50` green, `> 25` amber, `<= 25` red. Tile `.over` at `<= 25`.

Header status pill reflects `status`: `idle / running / paused / exhausted / stopped`
(color map in the HTML). `exhausted` is the failure state the whole demo builds to.

### 2b. Agentic-thoughts console (`/`)

Top: a 5-metric strip (same values as the dashboard, condensed) + config inputs
(`server_temp_f`, `initial_fan`, `battery_pct`) + Start / Pause / Resume / Stop.

Below: a reverse-chronological **feed of event cards**. Each card has an
agent badge, a source tag (`model` vs `fallback`), a timestamp, the agent's
first-person `thought`, and — when it proposed a change — a chip `fan X% → Y%`
plus an **outcome**:

| Outcome | Meaning | Visual |
|---|---|---|
| `applied` | change executed | green |
| `hold` | agent chose not to move | muted |
| `flagged` | **drastic** change (Δ ≥ `drastic_step`, default 25) — *not applied* | red card, red left border |
| `seam` | the paired ALICE card: "would HOLD this for a technician" | purple `alice` badge |
| `start` / `exhausted` / status | system lifecycle notes | purple `system` badge |

Agent color legend: Thermal `#38bdf8`, Power `#f59e0b`, System `#a78bfa`,
ALICE-seam `#ef4444`. The `flagged` + `seam` pair is the money shot — style it to
stand out.

---

## 3. The prototype data contract (what the viz binds to today)

Both screens poll one endpoint and are otherwise static HTML. No build step.

```
GET /state  →  { sim: <snapshot>, events: [...], agent_interval, drastic_step }
```

Poll cadence: dashboard 500 ms, console 700 ms (`setInterval` in each HTML file).
Controls are `POST /start` (JSON body of the three inputs), `/pause`, `/resume`,
`/stop`.

**`sim` snapshot fields** (`sim/engine.py::Simulation.snapshot`):

| Field | Type | Notes |
|---|---|---|
| `run_id` | str/null | 8-hex id per run |
| `revision` | int | increments every physics tick (~10 Hz) |
| `status` | enum | `idle\|running\|paused\|exhausted\|stopped` |
| `server_temperature_f` | float | °F |
| `target_fan_pct` / `actual_fan_pct` | float | actual lags target ~1 s |
| `power_consumption_w` | float | `400 + 100·(fan/100)³` |
| `battery_remaining_pct` / `_wh` | float | of 100 Wh capacity |
| `battery_draw_w` | float | `max(0, power − supply)` |
| `room_f` / `supply_w` | float | constants (72 / 450) |
| `energy_accel` | float | **labeled demo speed-up, ×120** (see §6) |
| `recent_changes` | str[] | ring buffer of authorized changes |

**`events` items** (`demo.py::_event`): `{ ts, agent, color, thought, reason?,
action?, from?, to?, outcome, source? }`.

---

## 4. Mapping the prototype onto the real system

**Important:** this standalone rig is a stripped copy of code that already lives in
the real repo. `services/thermal_demo/` and `services/light_mcp/` are
the *same* plant + agent path, wired into the real DCAMR runtime. So the demo's
`run_id` / `revision` / `apply_authorized` / fan-target-vs-actual names are **not
lookalikes — they are the real plant-tier contract.** What differs is that the
technician **console** doesn't bind to that plant snapshot; it binds to a third,
governed tier. Know which tier you're targeting.

### 4.0. Three tiers — pick your data source deliberately

| Tier | Where | Vocabulary | Who reads it |
|---|---|---|---|
| **Plant snapshot** | `services/thermal_demo/environment.py::snapshot()` (`schema_version:"thermal-demo-v1"`) | `run_id`, `revision`, `status`, `values:{temperature_f, fan_target_pct, fan_actual_pct, power_w, battery_pct, battery_remaining_wh, battery_draw_w, supply_w}`, `expected_revision`, `apply_authorized()` | the executor & the demo. **This is what the standalone `/state` mimics** (it just renames a few: `server_temperature_f`, `power_consumption_w`). |
| **Agent/MCP projection** | `services/light_mcp/thermal_state.py::metrics()` | renamed: `server_temperature`, `fan_speed`(=actual), `fan_target_speed`, `power_consumption`, `battery_pct`, `units:{…}` — agent may READ all, WRITE only `fan_speed` | the autonomous agent / MCP tools |
| **Governed console feed** | `packages/contracts/src/alice/runtime.ts` + `events.ts` | `OBSERVED_STATE` audit events (`property`/`value`/`unit`/`quality`), `alice.decision`, hash-chained `sequence` | **the technician console you're building** |

The real console reads the **governed feed** tier — event-sourced and
hash-chained, not a free snapshot. The rest of this section is the honest mapping
from prototype (plant-snapshot shape) to that governed tier. Read it before you
copy any binding.

### 4a. Transport: snapshot polling → cursor-based audit feed

| | Prototype | Real system |
|---|---|---|
| Endpoint | `GET /state` (whole world each call) | `GET /api/alice/events?after=<cursor>` (incremental) — `apps/desktop/src/lib/remote-transport.ts`; or Tauri IPC via `nativeCall` (`src/lib/native.ts`), which requires a signed-in technician |
| Shape | `{sim, events}` | `alice.runtime_feed` pages validated by `RuntimeFeedSchema` (`packages/contracts/src/alice/runtime.ts`) |
| Merge | none — replace on each poll | `mergeRuntimeFeed(prev, page)` folds pages into `RuntimeState` (`@alice/domain`) |
| Store | none (DOM only) | **zustand** `useConsole` (`apps/desktop/src/state/console.ts`); `ingest(event)` reducer routes each event to a slice |
| Health | implicit (poll works or doesn't) | explicit `FeedStatusSchema` state machine: `connecting\|live\|disconnected\|stale\|unavailable` — **render this**; the demo has no equivalent |

**Consequence for you:** don't bind a tile to `state.sim.server_temperature_f`.
Bind it to a **selector** over the store that derives "latest observed value for
this asset/property" from the runtime slice.

### 4b. Telemetry: snapshot fields → `OBSERVED_STATE` audit events

The real plant values aren't a snapshot object — each is an audit event
(`RuntimeEventSchema`, `event_type: 'OBSERVED_STATE'`) with
`detail.{asset_id, sensor_id, property, value, unit, quality, origin}` and a
`sequence` in a `previous_hash`/`event_hash` chain. So:

- Demo `server_temperature_f: 152.3` ⇒ real: an `OBSERVED_STATE` event with
  `property:"server_temperature"`, `value:"152.3"`, `unit:"F"`,
  `quality:"GOOD"`, `origin:"INDEPENDENT_SENSOR"`.
- Your tile shows the **latest** such event per property, and should honor
  `quality` (`DEGRADED`/`INVALID`/`UNAVAILABLE` → dim/annotate the tile, don't
  just show a stale number as if fresh).

### 4c. The agent feed & the HOLD seam → real decision contracts

The prototype's flagged/seam pair is a hand-drawn stand-in for the real decision
pipeline (`packages/contracts/src/alice/events.ts` + `.../commands.ts`):

| Prototype concept | Real contract |
|---|---|
| Agent `thought` / proposal card | agent activity via `alice.agent_status` (`current_activity.label`) and audit `REQUEST` / `ASSESSMENT` events |
| `outcome:"applied"` | decision `result:"ALLOW"`, `execution_status:"EXECUTED"` |
| `outcome:"flagged"` + `seam` ("ALICE would hold") | `alice.decision` with `decision.result:"HOLD"`, `technician_required:true`, `technician_actions.available:["APPROVE","HOLD","RESEARCH","REJECT"]` |
| (not modeled) hard-blocked | `decision.result:"DENY"` |
| `apply_authorized(target, request_id)` (idempotent) | `TechnicianActionSchema` (`APPROVE_ONCE`) → `ActionReceiptSchema` → `EXECUTION_ATTEMPT`/`EXECUTION_RESULT`, correlated by `request_id`/`action_id`/`execution_id` |

Watch the identifier tiers (see §4.0): `run_id`/`revision`/`apply_authorized` are
real at the **plant** tier (`services/thermal_demo/environment.py`), but the
**console/contracts** tier uses a different live-state vocabulary —
`ledger_id`/`node_id`/`event_id`/`sequence`/`event_hash`/`correlation.request_id`
/`OBSERVED_STATE`. `request_id` is the one name shared across both tiers (though
`ThermalRuntime.wire()` rewrites the on-wire id to `sha256(run_id + "." +
client_request_id)`). The real "buttons" are the four `technician_actions`, and
approvals can require biometric verification
(`decision.biometric_required_for_approval`, `VerificationSchema`) plus a signed
review proof to the Pi (`dcamr/technician_review.py`) — pieces the demo omits.

---

## 5. How to implement the viz in the real front end

1. **Live where the panels live.** Reusable, presentational tile/feed components
   go in `packages/ui`; the wired panels sit in
   `apps/desktop/src/components/runtime/` (see existing `RuntimePanels.tsx`,
   `RuntimeReview.tsx`) and read state via `useConsole`.

2. **Read from the store, add selectors — don't fetch.** The transport already
   polls and folds the feed. Add derived selectors (latest-value-per-property,
   over-threshold flags) either as `useConsole` selectors or in `@alice/domain`
   next to `mergeRuntimeFeed`, so both screens and any future view share them.

3. **Environment tiles** ← runtime slice `OBSERVED_STATE` events. Reuse the
   demo's threshold rules verbatim (temp ≥ 150 red; power > supply red; battery
   ≤ 25 red, ≤ 50 amber; fan bar = actual, show target as ghost). Gate each tile
   on `detail.quality` and on `feed.state` (dim + "stale" ribbon when
   `feed.state !== 'live'`).

4. **Agent-thoughts feed** ← `alice.agent_status` + audit `REQUEST`/`ASSESSMENT`/
   `DECISION` events, newest first. Map `decision.result` → the outcome styling
   from §2b (`ALLOW`→green, `HOLD`→red seam card, `DENY`→hard-block). When a card
   is `HOLD`, surface the four `technician_actions.available` as buttons that
   dispatch `useConsole.act(...)` (it already builds a `TechnicianAction` and
   handles the biometric-required path).

5. **Render feed health.** Add the `FeedStatus` pill (connecting/live/stale/…) —
   the real system can lose connectivity (DDIL), and a frozen tile must never
   look live. This is the one screen element with no demo equivalent, and it's
   safety-relevant.

6. **Keep the visual system.** The demo's dark palette, `font-variant-numeric:
   tabular-nums`, big-number tiles, and card animation are a good baseline and
   match the console's aesthetic — port the CSS, not the data layer.

---

## 6. Fidelity notes (what's fake, so you don't ship it)

- **No ALICE layer.** The flagged/seam cards are scripted in `demo.py`, not a real
  decision. In production the `HOLD` comes from the Policy/Anomaly engines
  (`ALICE-DCAMR Architecture.md` §DCAMR), not a Δ ≥ 25 heuristic.
- **`energy_accel ×120`** compresses battery drain so it's watchable in ~15 s.
  It's labeled in the snapshot; set to `1.0` for true rate. Don't surface the
  accelerated number as a real reserve estimate.
- **Physics coefficients** in `sim/engine.py::Config` are tuned for a legible
  demo, not a calibrated server model.
- **Agent sentences** come from a local Ollama model (`qwen2.5-tools`) if running,
  else deterministic fallback (`sim/agents.py::_fallback`). The `source` tag on
  each card tells you which — worth keeping as a provenance signal.
- **No auth / hash chain / provenance.** The real feed events carry
  `previous_hash`/`event_hash`, `provenance.*`, and `source.confidence` — none of
  which exist here. Treat prototype data as untrusted display-only.

---

## Reference files

- Prototype server & routes: [demo.py](../../../test-simulation/demo.py)
- Physics + snapshot shape: [sim/engine.py](../../../test-simulation/sim/engine.py)
- The two agents + prompts: [sim/agents.py](../../../test-simulation/sim/agents.py)
- Screens: [webui/dashboard.html](../../../test-simulation/webui/dashboard.html), [webui/demo.html](../../../test-simulation/webui/demo.html)
- Real **plant** tier (mirrors this demo): `services/thermal_demo/environment.py`, `services/thermal_demo/runtime.py`, `services/thermal_demo/fan-request.schema.json`
- Real **agent/MCP** projection: `services/light_mcp/thermal_state.py`, `services/light_mcp/state.py`, `services/light_mcp/poller.py`
- Real **governed console** contracts: `packages/contracts/src/alice/{runtime,events,commands}.ts`
- Real store, transport & feed-merge: `apps/desktop/src/state/console.ts`, `apps/desktop/src/lib/{remote-transport,transport,native}.ts`, `packages/domain/src/{runtime-feed,hold}.ts`
- Feed bridge behind `/api/alice/events`: `services/runtime_feed.py`
- Authoritative decision engine (ALLOW/CHALLENGE/DENY → console HOLD): `dcamr/{decision_model,main,technician_review}.py`
- Product framing: [ALICE-DCAMR Architecture.md](../../../ALICE-DCAMR%20Architecture.md)
