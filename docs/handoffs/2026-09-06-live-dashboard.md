# Live dashboard / USB SQL handoff

Date: 2026-09-06 UTC (September 5 EDT). Follow [AGENTS.md](../../AGENTS.md).
Review branch: `codex/live-dashboard`. Base `417b9de`; teammate main updates through
`7081b6a` merged locally in `8e1154d`. The user authorized publishing this reviewed
checkpoint to main. No deployment is included.

## Delivered slice

- Existing Pi runtime / USB-configurable SQLite ledger → validated authenticated
  loopback bridge → RemoteAliceTransport → Alex's existing dashboard layout.
- Initial history, automatic incremental updates, request/event/digest correlation,
  immutable decisions, separate late execution outcomes, overlap cursor checks,
  duplicates/conflicts, full-history reconnect validation, timeout/stale state and
  no fixture fallback in remote mode. Unknown values remain unavailable.
- USB mount identity/writability/path guards; private ledger key stays off USB.
  Missing USB history is not replaced by an empty ledger unless first provisioning
  is explicitly requested. Durable event/evidence writes precede execution;
  storage failure blocks execution and does not invent post-failure outcomes.
- One-command `npm run demo:live`: synthetic signed inputs to a real SQLite ledger
  and runtime, fixture assessment, mock ESP, private temporary session credentials,
  and the actual dashboard. `on`, `off`, `deny` submit new requests via stdin.
- [Runbook, field map, security boundary and limitations](../integration/live-dashboard.md).

## Verification actually run

- `PYTHONPATH=/tmp/alice-live-deps .venv/bin/python -m pytest tests -q`:
  **276 passed, 226 subtests passed**. pytest was installed into a temporary
  directory; the repository's private Python environment was not modified.
- `npm run check`: typecheck, lint, **73 frontend tests**, **5 script tests**, and
  production build passed.
- `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e:runtime`: **1 passed**.
  A process fixture runs real first-light runtime and bridge with test keys and
  mock ESP. Browser verifies history, new signed request arrival without refresh,
  correlation, observed state, idempotent retry, reload, disconnect and recovery.
- Existing `tests/console/e2e/console.spec.ts`: **5 passed** using an isolated
  port 1423 and installed Chrome via temporary Playwright config. Covers mock HOLD,
  biometric failure/retry, denial non-override, reconciliation, mobile layout and
  reassessment currentness. This is not real biometric/remote approval acceptance.
- Visible synthetic session on port 1422: initial ALLOW and denied request loaded
  from SQLite; a newly submitted `off` request appeared automatically. Read-only
  SQL query independently confirmed **16 events across 3 requests**, including
  separate ACCEPTED receipt, COMPLETED result and observed `0 bool`. The earlier
  denial remained in history. User confirmed the visible update worked.
- Independent code review found a request ID prototype-name collision and nested
  evidence symlink escape. Both reproduced in failing tests, then fixed and
  covered by passing regressions.
- `git diff --check` passed. Tracker IDs/labels preserved; 082 changes to Partial.
- `npm run test:rust` **could not run**: `cargo` is absent. Rust feed command was
  inspected but not compiled. This is an explicit merge-review limitation.

## Jared / Pi handoff

User-supplied Pi: `alice-pi-01`, SSH `pi@192.168.50.20`. USB `/dev/sda`, partition
`/dev/sda1`, UUID `6C1A-C6EA`; proposed mount `/mnt/alice-usb`, **not mounted yet**.
Read-only SSH/`lsblk -f` check timed out. No remote files, mount or filesystem were
changed. Verify actual filesystem/mount/device identity and SQLite fsync/locking
behavior before populating the physical drive. Do not infer the filesystem from
its UUID. Do not copy the local demo signing keys into production trust.

Use the runbook's USB runtime arguments, private Pi key, SSH forwarding, bridge
and dashboard environment configuration. The local synthetic session is useful
for validating the feed independently while the Pi is being provisioned.

## Remaining product integrations

This is ready for bounded code review, not a claim of complete Pi deployment.
The enterprise SQL snapshot publisher/activation and general SQL-backed policy
loader, SIEM delivery/reconciliation worker, real Pi ML, real ESP interface,
physical USB power-loss/removal acceptance and native build remain. First-light
still loads its signed JSON permissions release. USB holds its runtime SQL ledger
and evidence; a complete enterprise snapshot is not being fabricated.

The local Mac remains responsible for held accept/deny after biometric verification.
The Pi must validate proof/currentness/permissions/authority/audit readiness before
execution. Remote response methods remain explicitly unavailable; no successful
approval delivery or protected execution receipt is synthesized.

## Prior current.md checkpoint (historical)

The following preserves the prior session snapshot before it was replaced. Its
publication authorization and test results apply to that historical checkpoint.

# Current

Updated: 2026-09-05
Local baseline: `33b35cf`; includes main `d6e7e55` and prior documentation/layout work.
Review branch: `codex/integrate-team-layout`; architecture correction and handoff.
User authorized branch publication to github.com/theoberk25/Alice after the correction.
Earlier checkpoint `011abf1` remains separate; do not replay its obsolete layout.

## Current objective

Use the corrected architecture and next-session handoff to begin backend setup
in the next session. The current task publishes the review branch and prepares
the session prompt; it does not implement the backend. Start with [AGENTS.md](../../AGENTS.md).

## Confirmed architecture and coordination

- **Pi: ML classification. Local Mac: held-action accept/deny after biometric
  verification. Pi: validate the bound response and enforce execution prerequisites.**
  A hard prohibition remains binding; LLM prose/biometrics cannot override it.
- Theo and Jared are configuring the Pi; Xavi is working on hardware.
- Merek will build end-to-end backend data flow after architecture alignment;
  Alex will adapt workstation scripts/transport/dashboard to the agreed live contract.
- Root architecture now defines target pipeline, backend flows, storage/model and
  reliability requirements, current implementation limits and the source map.
- Theo's older plan is preserved as reference, not executable instructions. CBOR,
  codebooks, signing-library changes and removable audit storage require agreement.
- First-light remains a signed-request/fixture-assessment/mock-ESP slice; the console
  has working fixture workflows but its remote transport is not connected.
- All 118 tracker IDs/statuses stay unchanged: 12 done components, 38 partial, 68 planned.

## Next session

1. Confirm request/classification, Mac accept/deny proof and hardware-result bindings
   with Alex and the Pi/hardware team, preserving the confirmed decision ownership.
2. Check Theo/Jared's Pi readiness and Xavi's device interface; select backend host,
   transport, authentication and replay/currentness contracts before implementing.
3. Merek builds the backend connection using the existing runtime/ledger boundaries.
4. Alex connects workstation scripts and the live dashboard, preserving native
   identity, immutable lineage and stale-response guards.
5. Validate one connected request/review/result flow and both biometric-gated held
   responses, then extend context, recovery and enterprise synchronization.

## Verification and limits

Documentation checks passed: 713 local links/headings, byte-identical reference copy,
118 tracker rows preserved, current.md within limits and no runtime/archive changes.
Prior 265 Python tests (zero skips), launcher and console checks are historical;
no new runtime, native, camera, Pi/hardware or live-enterprise acceptance is claimed.
[Alignment and next-session handoff](../../docs/handoffs/2026-09-05-theo-architecture-alignment.md) ·
[Previous verification](../../docs/handoffs/2026-09-05-team-layout-review.md).

## Start here

[Rules](../../AGENTS.md) · [Architecture](../../architecture.md) · [Docs](../../docs/README.md) ·
[Tracker](../../docs/implementation-tracker.md) · [Scripts](../../docs/scripts/README.md)
