> **Scope reconciliation:** the implemented governed environmental slice uses [metrics MCP :8790 → thermal service :8795](guides/machine-metrics-integration.md). Port :8792 remains reserved for the external agent-loop console. The cold-start/restore and cloud-outage storyline below is a future concept, not an instruction to zero or overwrite operator-entered values. LEDs in the environmental slice are telemetry indicators, not independently switched supplies.

# Demo script

The live demo, scripted beat by beat. This document is written in show order —
Part 1 is the opening; the DDIL main act follows (Part 2, below).

> **One-line thesis:** with connectivity, a real cloud agent runs the hardware
> and everything is fine. Cut the network and the cloud agent dies — but the
> local agents keep the systems regulated and ALICE governs them. Part 1 sets up
> the "before" so the cord-cut in Part 2 lands.

---

## Part 1 — "Wake up the system" (first ~5 seconds)

**Purpose:** show, in one breath, that a **real Google agent (ADK + Gemini)**
**wakes the whole system up**. The plant starts *cold* — every metric reads `0`
/ `n/a` and all 8 LEDs are off. The one cloud message brings it online: it
**restores each value to its last-known reading**, and the visible proof is the
LEDs illuminating. No governance drama, no explanation — just "the cloud wakes
the plant, it's fine."

> **⚠ Concept only — NOT implemented yet (blocked on others).** The cold-start →
> restore-last-known-values behavior below is the **target**, captured here so we
> don't lose it. It depends on wiring we don't own: the metrics MCP / Pi state
> file (the running session's `services/light_mcp/`) must support a defined zeroed
> boot state **and** a persisted "last-known" snapshot to restore from. **Don't
> build this yet** — it needs those metrics/state changes to land first. What runs
> **today** (verified — see below) is the stand-in: the agent calls
> `startup_check()` and the 8 LEDs sweep on from off. The lights-going-on visual is
> real; the "restore last-known metric values" part is future work.

### The beats (target)

| t | On screen | Operator | Cloud agent (Gemini) | System state |
| --- | --- | --- | --- | --- |
| 0s | Dashboard **cold** — metrics `0` / `n/a`, all 8 LEDs off | Types one line: *"Wake up the system."* | — | Asleep: values zeroed, lights off |
| 1s | Trace shows a single tool call | — | Calls the wake tool once *(today: **`startup_check()`**)* | — |
| 1–4s | Metrics populate to last-known values | — | — | Values restored; LEDs sweep on in sequence |
| ~5s | Agent's reply line | — | Replies: *"Systems online — all supplies nominal."* | Live: metrics at last-known, all racks energized |

That's the entire opening. Cut to Part 2.

### What it establishes (say it in one sentence, or let it be silent)

Real cloud agent + connectivity = the system comes to life. The wake-up populates
the very metrics (`fan_speed`, `server_temperature`, `power_consumption`) the local
agents will regulate in Part 2 — so this opener is also the **setup** for the
cord-cut: the audience watches the cloud bring the plant online, then lose it.

### The 8 lights (asset framing)

From [`services/light_mcp/machines.yaml`](../services/light_mcp/machines.yaml) —
address them by role, not LED color, when narrating:

- Primary utility feed · Backup generator feed
- Server rack A supply · Server rack B supply
- Cooling plant supply · Auxiliary maintenance load
- Communications rack supply · Security monitoring rack supply

---

## The runnable stand-in lives in the standalone example folder

The verified Part-1 stand-in — a **real** Gemini agent calling a **real** MCP tool
that drives the (mock) lights — is **not kept in this repo**. It lives in the
standalone prototype rig **`test-simulation/cloud_agent/`** (at the workspace root,
outside this git repo), next to the local-agent test simulation. That folder holds
`lights_intro_server.py` (light-intro MCP on `:8794`, in-memory driver, canned
`startup_check()` + `list_machines`/`get_status`), `intro_agent.py` (the ADK/Gemini
agent `machine_ops_cloud_intro`), `run_intro.py` (headless runner that asserts the
tool fired), and its own `README.md` with run steps.

**Why there and not here:** `startup_check` is a **placeholder** — it sweeps the
LEDs on but does not restore last-known metric values. The real integration
(`wake_system` restoring the persisted snapshot, below) belongs in the product once
the metrics/state hooks land; until then the fake stays in the example rig, not the
git-tracked product.

Design choices carried in the example: `startup_check()` runs the whole 8-light
sweep itself (canned, so a live model can't fumble a multi-step sequence on stage)
and is **idempotent** (a Gemini 503 + model fallback re-ran it once, no ill effect).
For the Pi, swap the in-memory driver for the real `EspSerialDriver` over the XIAO,
or route through the governed ALICE ledger — agent and prompt unchanged.

**Ports (when the pieces run together):** `:8790` metrics MCP · `:8791` Goose ·
`:8792` agent-loop web / test-sim console · `:8793` Decision-Brief MCP · `:8794`
lights intro · `:11434` Ollama · `:8000` `adk web`.

## To reach the target (wake-up / restore) — blocked on others

The cold-start → restore-last-known opener needs work we don't own yet:

1. **Zeroed boot state.** The metrics MCP / Pi state file needs a defined cold
   state — `fan_speed` / `server_temperature` / `power_consumption` at `0` (or
   `n/a`), lights off — that the dashboard renders as "asleep."
2. **A persisted last-known snapshot** to restore *from*, plus a single wake action
   that writes those values back **and** turns the lights on.
3. Only then does `startup_check` graduate into a real `wake_system` that restores
   state instead of just sweeping the LEDs on.

Push the metrics/state changes first; then this is a small follow-up on top of the
stand-in above.

---

## Transition → Part 2

After "systems normal," **the cloud crashes** — simulated by cutting the network
(unplug the Wi-Fi router). In the seconds before it drops, **server activity
skyrockets**: a surge of load that spikes power draw and drives
`server_temperature` up in the bay. Then the Gemini cloud agent, which needs the
internet, goes dark; the two local Qwen agents keep regulating on localhost. That
pre-crash heat spike is exactly what the local thermal agent reacts to in Part 2.
This is the hinge of the whole demo.

## Part 2 — DDIL: local agents hold the line

The governed backend path is implemented. Configure the simulated room at 100 F
and 60% fan, then use the cooling agent for small +10 point proposals. The current
model classifies 60→70, 70→80 and 80→90 as normal in that context, so ALICE permits
and applies them. Use the power agent to propose a full cut to 0%; its combination
of direction, magnitude, temperature and power is outside normal support, so ALICE
records a HIGH assessment and an eligible **HOLD** without changing the fan target.
The technician sees the exact proposal and score, completes a fresh face scan and
selects **Reject**. The signed rejection is recorded and the fan stays on.

The local agent trigger loop and physical Pi/LED acceptance remain separate live
steps. See [`docs/agent-build/06-agent-loops.md`](agent-build/06-agent-loops.md).
