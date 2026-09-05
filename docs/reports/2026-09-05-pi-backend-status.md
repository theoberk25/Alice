# Pi backend status — first-light slice (2026-09-05)

Status report per the working agreements in [AGENTS.md](../../AGENTS.md).
Branch: `first-light-test` (local). This describes the Pi-side backend as
implemented for the first integration test — one OFFLINE terminal action
(`set_light_state -> ESP-LIGHT-01`) — not the full runtime plan.

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
  exercised. Hardware acceptance on the Pi is pending (code has run on Mac
  only so far; the Pi itself is still being provisioned).
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
