# SQL input snapshot continuation

Date: 2026-09-06 UTC (September 5 EDT). Follow [AGENTS.md](../../AGENTS.md).
Base and fetched `origin/main`: `44f4d73`. Work remains uncommitted on
`codex/live-dashboard`; no push, deployment or physical USB operation performed.

## Delivered increment

- Immutable SQLite packaging of the exact existing signed first-light release
  documents; shared Ed25519/digest verification, bounded read-only SQL loading,
  atomic no-overwrite publication, file/directory fsync.
- Explicit runtime `--release-snapshot`, requiring existing history unless initial
  provisioning is explicit. Existing `--release` directory operation is preserved.
- Existing ledger, signing, policy resolver, request replay and controller path
  reused. Snapshot provenance names signed release content. No second audit store.
- Regression coverage for tampering, wrong trust, missing/extra documents, format
  version, missing snapshot, overwrite refusal, publisher CLI, restart/replay and
  release changes preserving original events and an explicitly queued test entry.
- [Commands, format, team handoff and limitations](../integration/release-snapshot.md).

This is first-light JSON in SQL, not a completed enterprise synchronization system.
Jared's general permissions examples remain incompatible by design: their full
prohibition/revocation/identity semantics cannot safely be reduced to first-light.
General schema agreement, freshness and rollback anchors, validated activation,
SIEM destination/authentication/receipts, Mac biometric response binding and actual
hardware/ML integration remain. There is no SIEM worker or fabricated delivery.

## Verification actually run

- Fetch succeeded after the sandbox DNS restriction was escalated; no newer
  teammate commits were available. The four pre-existing tracked document edits
  and untracked backend continuation were retained; no private environments,
  runtime data, credentials or keys were edited. Current status/tracker/runbook
  were updated to reflect this increment.
- Read-only `ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5
  pi@192.168.50.20 lsblk -f`: connection timed out again. No physical evidence.
- Baseline focused Python runtime/feed/USB checks: **17 passed**.
- New tests first failed because snapshot implementation was absent. Initial
  expanded continuity test incorrectly assumed events were automatically queued;
  inspecting `AuditLog.pending/queue` established otherwise. The test now explicitly
  queues a sealed event to a test destination before restart; no production
  delivery behavior was added to satisfy that assumption.
- `PYTHONPATH=/tmp/alice-live-deps .venv/bin/python -m pytest tests -q`:
  **281 passed, 230 subtests passed**, final run. Focused snapshot tests:
  **5 passed, 4 subtests passed**. Existing temporary pytest dependencies were
  reused; plain `.venv/bin/python -m pytest` lacked pytest. HTTP test servers
  require sandbox escalation in this environment.
- `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e:runtime`: **1 passed**,
  reproducing live local request → dashboard, history/replay and bridge recovery.
  This uses the existing JSON release setup, fixture assessment and mock ESP;
  the SQL path is covered by the Python runtime tests, not a separate browser run.
- `npm run check`: **73 frontend tests, 5 script tests**, typecheck, lint and build
  passed. Build emitted a dependency comment-annotation warning in Zod; Node also
  reported the existing color-environment warning during browser testing.
- `npm run test:rust`: unavailable, `spawn cargo ENOENT`; native compilation remains
  unverified. No toolchain or private environment was modified.
- Independent review found no actionable correctness/security regressions; its
  sandbox blocked the socket test, which the primary session ran with escalation.
- `git diff --check`, current.md size/link checks and tracker ID/label checks passed.

## Prior checkpoint evidence retained

The initial current.md recorded historical `44f4d73` verification: 276 Python tests
plus 226 subtests, 73 frontend and 5 script tests, typecheck/lint/build, one live
browser and five existing mock-review browser tests. The user had seen synthetic
SQLite activity update Alex's actual dashboard. That was not physical acceptance.
Architecture `417b9de`, teammate updates through `7081b6a`, and the approved USB
lifecycle remain the baseline; details stay in the [live handoff](2026-09-06-live-dashboard.md).

## Next work

1. Theo/Jared verify Pi `alice-pi-01`, `pi@192.168.50.20`, actual USB filesystem and
   mount (`6C1A-C6EA`, proposed `/mnt/alice-usb`) plus off-USB key provisioning.
2. Jared/Merek agree general enterprise SQL coverage/identity/revocation and
   activation/freshness/rollback contracts, then extend the snapshot slice.
3. Connect actual Pi history/new request to Alex's dashboard through the runbook;
   retain fixture/mock labels until real producers are verified. Run native Rust.
4. Implement durable SIEM delivery only against an actual agreed destination and
   receipt contract; preserve the original events and pending entries.
5. Agree the Mac biometric accept/deny proof with Alex and Pi enforcement checks
   before enabling remote actions. Fresh authorization is required for publication
   or deployment, including any physical snapshot installation.
