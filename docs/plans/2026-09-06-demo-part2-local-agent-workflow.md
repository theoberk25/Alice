# Plan — Part 2: local agent workflow (ALLOW×3 → anomaly HOLD → technician reject)

Updated: 2026-09-06. Read [AGENTS.md](../../AGENTS.md) and [current.md](../../current.md)
first. Story: [docs/demo.md](../demo.md) "Part 2 — local agents and contextual HOLD"
and the runbook's "Sequential local-agent scene". This plan runs the **OFFLINE /
DDIL** beat: two locally-authenticated agents drive the governed fan, three normal
`+10` steps ALLOW and apply, an abnormal full cut HOLDs, and the technician rejects
it on the live console.

Discovery-verified 2026-09-06; re-check each ✓.

## Outcome / definition of done

1. `cooling-agent-01` submits `set_fan_speed` 60→70, 70→80, 80→90 — each returns
   **ALLOW** and applies (fan_target reaches 90).
2. `power-agent-01` submits `set_fan_speed` **0** — the fan model scores it `HIGH`,
   ALICE returns **CHALLENGE / `ANOMALY_REVIEW_REQUIRED`** and records a HOLD; the
   fan target does **not** change.
3. The technician console shows the immutable request + assessment; a **fresh
   ArcFace face check** + signed **REJECT** is recorded by the Pi; fan stays at 90.
4. All four requests + outcomes are in the USB ledger (and Wazuh). LEDs track it:
   blue (fan) and yellow (power) accelerate, red follows temperature, white
   (battery) drains once fan > ~79% (supply 450 W, `energy-time-scale 60`).

## Decision: no containers

Per Theo, **do not** use containers/VMs for the local agents. Run **one process per
agent identity**, each carrying only its own bearer token, over an SSH tunnel to the
Pi. That already gives the "distinct authenticated identities" the story requires.

## Topology (verified live)

| Host | Address | Role | State |
| --- | --- | --- | --- |
| This Mac | `192.168.50.10` | runs the agent processes + tunnels + technician console | on LAN ✓ |
| Pi | `192.168.50.20` | `light-mcp.service` `:8790` → `alice-thermal-demo.service` `:8080` (both loopback); USB ledger; ESP serial lights; Wazuh sync | active ✓ |

Everything the governed path needs is already provisioned **on the Pi**: reviewed
`fan-model.json`, `agent-keys.json` (cooling/power/observer), per-agent MCP tokens,
`console-trust.json`, USB ext4 ledger, ESP XIAO 8-light board, `--energy-time-scale 60`.

## Step 0 — clear conflicting Mac processes

These are running and will collide with the tunnel or mislead the demo. Stop the
ones you don't need:

- Mac local `light_mcp.server` on `:8790` (a dead end — no thermal backend, and it
  occupies the port the tunnel needs). **Stop it.**
- `test-simulation/demo.py` (`:8792`, ungoverned prototype) and the stray
  `http.serve` (`:8123`) — stop unless separately wanted.
- `goose_chat.py` (`:8791`) — keep only if you want the LLM "agentic thoughts"
  visual (Step 4b).

## Step 1 — open the tunnels (Mac → Pi loopback)

One SSH process, two forwards: MCP for the agents, `:8080` for operator + console
feed.

```bash
ssh -N -o ServerAliveInterval=15 -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:8790:127.0.0.1:8790 \
  -L 127.0.0.1:18080:127.0.0.1:8080 \
  pi@192.168.50.20
```

After this, Mac `127.0.0.1:8790/mcp` **is** the Pi's governed MCP (matches the fixed
URL the Goose/ADK config already use), and `127.0.0.1:18080` is the Pi thermal API.

## Step 2 — secrets (keep out of chat / git / transcript)

- Per-agent MCP bearer tokens live in the Pi's `/etc/alice/metrics-mcp.env`
  (`THERMAL_AGENT_TOKENS` = JSON of `cooling-agent-01` / `power-agent-01` /
  `observer-agent-01` → token). Retrieve the two you need onto the Mac as env vars
  (`COOLING_AGENT_TOKEN`, `POWER_AGENT_TOKEN`); never print them.
- The operator token (`THERMAL_OPERATOR_TOKEN`) lives in the Pi's
  `/etc/alice/thermal-demo.env`. Prefer running operator actions (Step 3) **on the
  Pi over SSH loopback** so the operator token never lands on the Mac.

## Step 3 — configure + start the plant (operator)

The service was restarted during setup, so the in-memory run is UNCONFIGURED. Set
the reviewed start state and run it. Do this on the Pi (loopback) with the operator
token:

```bash
# on the Pi (operator token in $OP):
curl -s -H "Authorization: Bearer $OP" -H 'Content-Type: application/json' \
  -d '{"temperature_f":90,"fan_pct":60,"battery_pct":60}' http://127.0.0.1:8080/demo/configure
curl -s -H "Authorization: Bearer $OP" -d '{}' http://127.0.0.1:8080/demo/start
curl -s -H "Authorization: Bearer $OP" http://127.0.0.1:8080/demo/state   # status=RUNNING, power≈421.6 W
```

## Step 4 — drive the two local agents

Path per the story: **agent → MCP (`:8790`) → thermal (`:8080`)**. Each agent uses
its own token as `LIGHT_MCP_TOKEN`. Read metrics before each proposal; act on the
returned decision, don't assume the fan moved.

### 4a — scripted client (recommended: deterministic, reliable)

For `cooling-agent-01`, three times: `get_metrics` → propose current
`fan_target_speed + 10` via `set_fan_speed(value)` → confirm `decision=ALLOW`,
`execution=COMPLETED`, wait for the applied revision before the next step
(60→70→80→90). Then for `power-agent-01`: `get_metrics` → `set_fan_speed(0)` →
expect `ok:false`, `decision=CHALLENGE`, review pending (the HOLD). Use
`services.thermal_demo.client.DemoClient` or the MCP `set_fan_speed` tool directly.
Do **not** mint a new request id to bypass the HOLD.

### 4b — LLM agents (optional, for the "agentic thoughts" visual)

Goose local (`qwen2.5-tools`, config already points at `127.0.0.1:8790/mcp`) with
`LIGHT_MCP_TOKEN` set to the acting agent's token. Non-deterministic wording — pair
with 4a for the reliable state changes, or accept variance. One agent identity per
process; do not share a token.

## Step 5 — live technician console for the HOLD / reject

The HOLD beat needs the console on the **live Pi feed** (it is currently in
mock/saved-feed mode). Bring up the runbook bridge on the Mac:

- [ ] `services.runtime_feed` bridging the console to the Pi via the `:18080`
      tunnel, with `ALICE_UPSTREAM_TOKEN` = operator token and controller `mock`
      (fan is simulated). See [environmental-demo.md](../guides/environmental-demo.md)
      and [demo-runbook.md](../guides/demo-runbook.md) "Start the current
      presentation services".
- [ ] Point the technician app (native `apps/desktop`, or web `:1420` in `remote`
      mode) at the bridge; enable login.
- [ ] Provision/confirm the **review signing key** (`scripts/console/provision_review_key.py`)
      and the ArcFace face-verification service on this Mac (see
      [native-runtime-review](../guides/native-runtime-review.md)).
- [ ] On the HOLD: console shows the immutable request + assessment; technician does
      a **fresh** face check → **REJECT**; a short-lived, one-use proof bound to that
      exact request is sent to the Pi, which re-checks and records the signed
      rejection. Fan remains at 90.

If the live console is not ready in time, the fallback is to show the HOLD from the
Pi (`GET /events` / `/review/<id>` on `:18080` with the operator token) — but the
signed human REJECT is the intended beat, so prioritise wiring the console.

## Verify (acceptance)

- [ ] Three ALLOWs applied; `get_metrics` shows `fan_target_speed=90`.
- [ ] One CHALLENGE/HOLD (`ANOMALY_REVIEW_REQUIRED`) rejected; fan still 90.
- [ ] Four requests + outcomes in the USB ledger; Wazuh worker delivered them.
- [ ] LEDs: blue + yellow blink faster with fan/power, red tracks temperature,
      white drains once fan > ~79%. Optional accelerated run reaches `EXHAUSTED_OFF`.
- [ ] Cross-check one request across runtime/USB/Wazuh with
      `python -m lab.first_light.check_pipeline` (runbook "Acceptance sequence").

## Risks / watch-outs

1. **Port 8790 collision.** The tunnel needs Mac `:8790` free — stop the local MCP
   first (Step 0), or forward to a different local port and repoint the agent config.
2. **Stale run / revision.** `set_fan_speed` binds the current run_id + revision. If
   the plant was reconfigured mid-run, decisions return UNKNOWN/stale — re-read
   metrics and use the returned ids; never fabricate them.
3. **HOLD vs DENY.** The demo fixtures make fan-off *eligible for review* (HOLD), not
   a hard DENY. If you see DENY, the permissions/threshold fixture is wrong — do not
   weaken hard-deny precedence to "fix" it; check the release.
4. **Two writers.** Never run a second ledger/serial owner beside
   `alice-thermal-demo.service`; `alice-runtime.service` must stay inactive.

## References

- Story: [docs/demo.md](../demo.md) · Runbook: [docs/guides/demo-runbook.md](../guides/demo-runbook.md)
- Launch/contract: [docs/guides/environmental-demo.md](../guides/environmental-demo.md) ·
  [docs/guides/machine-metrics-integration.md](../guides/machine-metrics-integration.md)
- Runtime: [services/thermal_demo/](../../services/thermal_demo/) ·
  fan model + decision: [dcamr/anomaly_engine/fan_model.py](../../dcamr/anomaly_engine/fan_model.py)
- Client: [services/thermal_demo/client.py](../../services/thermal_demo/client.py) ·
  MCP: [services/light_mcp/server.py](../../services/light_mcp/server.py)
- Native review: [docs/integration/upstream-alice.md](../integration/upstream-alice.md)
