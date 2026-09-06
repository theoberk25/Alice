# Pi backend status — first-light slice (2026-09-05)

Status report per the working agreements in [AGENTS.md](../../AGENTS.md).
This describes the Pi-side backend as implemented for the first integration
test — one OFFLINE terminal action (`set_light_state -> ESP-LIGHT-01`) — not
the full runtime plan. Test evidence and the network runbook live in the
[test log](2026-09-05-first-light-test-log.md).

**Update, end of day:** the slice is now **proven on hardware and live over
the network**, not just on the Mac. The Pi (`alice-pi-01`, 192.168.50.20 on
the offline switch) runs the runtime + mock ESP; all 6 first-light tests pass
on the Pi; nine signed requests from three SIEM-provisioned identities
(SSgt Okafor, MSgt Reyes, and the denied apprentice account) were decided,
executed, ledgered and rendered live on the ALICE workstation console, whose
remote transport now consumes the Pi's read-only `GET /events` feed. Jared's
enterprise SIEM console gained a clearly-labelled live-edge lab tab. Idempotent
retry and the deny path were both demonstrated end to end.

## Subsequent local integration

The [live dashboard/USB configuration](../integration/live-dashboard.md) supersedes
the original Pi-internal-only storage assumption: the user approved USB-backed
SQL history and offline writes. The local bridge/display slice and mount guards
are implemented; this report's original first-light results remain historical.
Enterprise SQL snapshot publication and SIEM reconciliation workers remain pending.

## Completed and ready now

**Request pipeline (`dcamr/main.py`)** — a stdlib HTTP runtime implementing
the complete first-light flow:

1. **Authentication** — the terminal envelope's Ed25519 signature is verified
   over the request's canonical bytes against the release's registered terminal
   keys; identity derives from the verified key, and a claimed `agent_id` that
   does not match the key binding is rejected. Malformed, unsigned or
   schema-invalid requests append a `REJECTION` event and fail closed.
2. **Release verification (`dcamr/packages/package_verifier.py`)** — at
   startup the signed permissions release is verified (manifest Ed25519
   signature plus per-payload sha256 digests). Any mismatch aborts startup.
3. **Permission resolution (`dcamr/policy_engine/policy_engine.py`)** —
   deterministic exact-match over PERMIT grants (agent, action, target,
   parameter bounds). Default deny; no model involvement in denial paths;
   `approval_required` grants resolve to `REVIEW_REQUIRED` (denied in this
   auto-only slice). Emits the shared `PermissionFinding` type.
4. **Assessment wiring** — an explicitly labelled fixture assessment
   (`fixture_mode` in its retained context) is projected through the existing
   `contextual_projection` contract; the exact bytes are retained as evidence
   with their sha256 bound into the `ASSESSMENT` event.
5. **Decision (`dcamr/decision_model.py`, additive `decide()`)** — ALLOW only
   when identity is verified, the finding is `PERMITTED` (no approval needed)
   and the assessment status is OK; everything else is DENY with a reason code.
6. **Durable audit** — every step appends to the existing tamper-evident
   `AuditLog` (unchanged; the runtime is a producer only). The
   `EXECUTION_ATTEMPT` is durably committed before the ESP is commanded, and
   the ledger is sealed after each request. Admission is refused unless ledger
   headroom covers the request's full event set.
7. **Execution (`dcamr/enforcement/enforcement_gateway.py`)** — HTTP command
   to the ESP light; the controller receipt (transport ack), execution result
   and an independent observed-state readback are recorded as separate events.
8. **Idempotency** — a retried `request_id` returns the recorded outcome and
   never re-decides or re-executes (one ESP command total); the outcome index
   is rebuilt from the ledger on restart. Reuse of a `request_id` with
   different content is refused.
9. **Technician feed** — read-only `GET /events` projection of ledger events,
   correlated by request id; no approval verbs exposed. Consumed today by the
   CLI `technician_view`; the seam the workstation console can adopt later.
10. **USB export (`lab.first_light.usb_export`)** — queue → NDJSON write →
    per-record hash verification → acknowledge, using the ledger's delivery
    bookkeeping; the Pi-internal ledger remains the source of truth.

**Contracts and tooling** — strict
[`action_request.json`](../../common/schemas/action_request.json) (one
action/target, signed envelope); workstation release builder, terminal client
(`--repeat` retry demo) and mock ESP under `scripts/lab/first_light/`.

**Evidence** — 263 tests pass (6 new end-to-end first-light tests; 30
pre-existing skips) plus a multi-process local dry run; `validate()` passes
after seal and reopen. Details:
[first-light handoff](../handoffs/2026-09-05-first-light-test.md).

## Limitations still to build

- **Physical ESP** — no real firmware exists; the HTTP contract
  (`POST/GET /light`) is an open coordination item and only the mock has been
  exercised. (The Pi itself is now provisioned and proven; the ESP is the
  last physical piece.)
- **Real assessment** — the assessment is a wiring fixture, not detection. No
  model export/loading, feature extraction, scoring or anomaly-driven review
  runs on the Pi.
- **Approval paths** — no HOLD/REQUEST_CONTEXT/technician approval states;
  anything not auto-permitted is simply denied. The technician feed is
  read-only; the console's remote transport is not connected.
- **Policy breadth** — exact-match PERMIT grants only: no prohibitions,
  conditions, validity windows, revocations, generations, staging/activation,
  rollback protection, or ONLINE policy pull. Issuer trust is a demo key
  provisioned by file copy, not a real trust root.
- **Modes and authority** — OFFLINE-only with a hard-coded confirmed authority
  interval; no ONLINE mode, authority transfer/fence, reconnection or
  enterprise synchronization.
- **Hardening** — no watchdog, TLS/transport auth on the runtime HTTP surface,
  rate limiting, clock trust (time is recorded as UNCERTAIN), USB discovery/
  automount, or retention/reconciliation workers. Request intake is
  single-threaded by lock; ledger scale assumptions are test-scale.
- **Schema breadth** — the request schema pins the single first-light
  action/target; widening to the general action catalog is a coordinated
  contract change.

## Roadmap: from first light to autonomous agents, fully automated

Ordered so each step is independently demoable and none rewrites what exists.

1. **Real ESP + observed-state truth.** Land the firmware HTTP contract, point
   `--esp-url` at hardware, and treat the readback as an independent sensor
   (today it is actuator feedback). This closes the physical loop.
2. **Widen the action catalog.** Grow `action_request.json` and the audit
   REQUEST detail (coordinated `audit_event.json` change with the ledger
   owner) so events carry action/target/parameters explicitly — removing the
   dashboards' display-only echo — then add grants for the enterprise-sim
   actions (`read_meter`, `set_voltage_setpoint`, …) with real parameter
   bounds, prohibitions evaluated before grants, conditions, validity windows
   and revocations from Jared's bundle format.
3. **Real agents instead of the terminal client.** Give each LLM/automation
   agent a provisioned key and have it submit signed requests through the same
   `POST /request` pipeline — the runtime already derives identity from the
   key, so agent autonomy adds no new trust. An MCP/A2A adapter in front of
   the envelope builder makes any agent framework a client.
4. **Real assessment.** Export the contextual Isolation Forest to the Pi,
   replace `assessment_fixture` with live scoring behind the same
   `contextual_projection` call, and route `ELEVATED/HIGH` (and
   `REVIEW_REQUIRED` grants) to a HOLD state instead of deny.
5. **Technician approval path.** Add HOLD/REQUEST_CONTEXT decision states and
   an authenticated technician action endpoint; the workstation console
   already has the Approve/Hold/Reject UI and biometric gate — its transport
   needs the write half, gated by technician identity, every action ledgered
   as TECHNICIAN_ACTION.
6. **Automate the lifecycle.** systemd units for the runtime and export on
   the Pi (replacing tmux), USB auto-discovery for release staging/activation
   with generation and rollback checks in `package_verifier`, a scheduled
   `usb_export`/delivery worker draining the ledger outbox, and a watchdog.
7. **ONLINE mode + reconnection.** Authority transfer with an endpoint-held
   fence, enterprise sync of releases/baselines on reconnect, publishing the
   DDIL ledger upstream (the SIEM console's edge-node view already reads that
   record), and reconciliation findings — completing the two-mode product
   loop.
8. **Hardening throughout.** Real trust roots instead of demo keys, TLS and
   client auth on the runtime surface, trusted-clock evidence, quota/retention
   policy, and concurrency beyond the single-request lock.

Steps 1–3 produce "agents acting under governance, automated" — the demo
narrative extended to real actors. Steps 4–5 make the review loop real, and
6–8 make it a product rather than a lab bench.
