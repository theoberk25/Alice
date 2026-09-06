# Handoff — cloud agent: governed thermal request + "all systems on" spin-up

Date: 2026-09-06 EDT. Branch `feat/cloud-agent-enterprise-ingress` (at `87fe559` = origin/main).
Rules: [AGENTS.md](../../AGENTS.md). Story: [demo.md](../demo.md) "Part 1".
Supersedes the approach in [the Part 1 plan](../plans/2026-09-06-demo-part1-cloud-governed-ingress.md).

## Discovery (why the original Part 1 plan does not run as written)

Working the Part 1 plan (provision the cloud agent, fire one `set_light_state
ESP-LIGHT-01 on` through the `.50` enterprise ingress) surfaced a hard,
static contract mismatch — not a runtime glitch:

- The **enterprise ingress** (`services/enterprise_ingress.py`) validates every
  request against `common/schemas/action_request.json` (first-light: actions
  `set_light_state`/`set_fan_speed`, targets `ESP-LIGHT-0x`/`SERVER-ROOM-FANS`,
  requires `issued_at`) and forwards the exact bytes to the Pi.
- The **live Pi** runs the **thermal** runtime; its `/request` only accepts
  `alice-demo-fan-v1` (`set_demo_fan_pct`/`DEMO-SERVER-01`/`fan_basis_points`,
  plus `run_id`/`expected_revision`/`client_request_id`, no `issued_at`). Both
  schemas are `additionalProperties:false`, so **no single request satisfies
  both**. A lights request passes the ingress but the Pi rejects it (schema
  violation); a fan request fails the ingress.
- Git shows the bridge is **one-third built**: `92c65dc` (Jared) added
  `ThermalRuntime.submit_envelope` (Pi accepts a signed `alice-demo-fan-v1`
  envelope, proven by `test_enterprise_signed_envelope_uses_request_route...`),
  but the ingress schema and the cloud client were never migrated off lights.
- The Pi runtime binds **`127.0.0.1:8080` (loopback)**; reachable from this Mac
  only via the existing SSH tunnel `127.0.0.1:18080 → Pi:8080`. So the `.50`
  ingress could not reach the Pi directly either (plan Risk 1 was real).
- `.50` is unreachable to fix (SSH `:22` down; only HTTP `:8790` exposed; SIEM
  console `:8787` refuses connections) and Jared is unavailable. So the
  enterprise-ingress-first hop cannot be completed for this demo.

Trusted, fan-permitted agent ids in the signed release: `cooling-agent-01`,
`power-agent-01` (grant `DEMO-FAN-PERMIT`). `observer-agent-01` is trusted but
**not** in the fan grant (would DENY). `elec-agent-01` from the docs is **not
trusted** at all. Minting a new id needs a release re-sign + redeploy (Jared).

## Decision (approved by Theo)

Pivot the cloud agent to the **thermal fan contract, direct to the Pi via the
tunnel**, dropping the externally-blocked `.50` ingress hop. Sign as
`cooling-agent-01`. Additionally, make the cloud agent bring the plant online on
a natural-language cue.

## What was built (this session)

| Piece | Path | Notes |
| --- | --- | --- |
| Governed fan client | [cloud/thermal_governed_client.py](../../cloud/thermal_governed_client.py) | build→sign→POST `alice-demo-fan-v1` to `/request`; no hardcoded dest; `--dry-run`; optional `/demo/state` auto-fetch. Reuses `canonical_bytes`; wire mirrors `ThermalRuntime.wire`. |
| Operator lifecycle client | [cloud/thermal_operator_client.py](../../cloud/thermal_operator_client.py) | `bring_all_systems_online` / `all_systems_off` / `plant_state` via operator token. Designated levels 90 °F / 60 % / 60 % (env-overridable). |
| Agent tools | [cloud/adk_light_agent/agent.py](../../cloud/adk_light_agent/agent.py) | opt-in `submit_governed_fan_request`, `bring_all_systems_online`, `all_systems_off`; instruction maps "good morning, all systems on!" → spin-up. Lights/ingress tool disabled. |
| Tests | [test_thermal_governed_client.py](../../tests/test_thermal_governed_client.py), [test_thermal_operator_client.py](../../tests/test_thermal_operator_client.py) | 10 tests; incl. byte-for-byte `wire == ThermalRuntime.wire` drift guard. All green (with the existing enterprise test: 15). |

Local provisioning (gitignored, mode 600; values never printed):
`~/.alice/keys/cooling-agent-01-k1.seed` (pubkey verified vs release),
`~/.alice/keys/thermal_operator_token` (from Pi `/etc/alice/thermal-demo.env`
via passwordless sudo). `cloud/adk_light_agent/.env` (gitignored) sets
`ALICE_AGENT_ID=cooling-agent-01`, the seed path,
`ALICE_THERMAL_REQUEST_URL=http://127.0.0.1:18080`, the operator token file, the
designated levels, and disables `ALICE_ENTERPRISE_INGRESS_URL`.
(`observer-agent-01-k1.seed` was also copied earlier but is unused — not fan-permitted.)

## How to run (all steps below are ACTUATING — get Theo's go first)

1. Restart `adk web` from `cloud/` (venv) so the new tools attach.
2. Send the agent **"good morning, all systems on!"** → `bring_all_systems_online`
   → configure 90/60/60 + start → `RUNNING` (~421.6 W at the initial state).
3. Governed change: agent calls `get_metrics` then
   `submit_governed_fan_request(fan_pct, run_id, expected_revision)` →
   expect **ALLOW/applied** for an ordinary step (e.g. 70 %).
4. CLI equivalents (need the env exported, or pass flags):
   `python -m cloud.thermal_operator_client on|off|state`;
   `python -m cloud.thermal_governed_client --fan-pct 70 --state-url http://127.0.0.1:18080 --state-token <tok>`.

## Not done (pending Theo's go — chose "nothing live yet")

Setting the OFF baseline (plant is currently `PAUSED` at 90 % fan), restarting
`adk web`, the live spin-up, and any real governed submit. No enterprise-ingress
receipt is produced on this path (that hop stays blocked until `.50`'s ingress
accepts `alice-demo-fan-v1` — a coordinated change with Jared).
