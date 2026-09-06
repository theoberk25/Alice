# Jared main integration and joint acceptance preparation

Date: 2026-09-06 UTC (September 5 EDT). Follow [AGENTS.md](../../AGENTS.md).
Branch: `codex/live-dashboard`. Integration parents: preserved local snapshot
checkpoint `73dfa91` and Jared's fetched `origin/main` checkpoint `ef413b6`.
The user intends to push, then have Jared run the configured-device tests.
No publication, remote deployment, network change or Pi writer was started here.

## Integration and preservation

Fetched commits `9ea52d5`, `4eb6238`, `ef413b6`. Jared added direct HTTPS Wazuh
delivery, the runtime-owned worker and lock integration, `/sync-status`, a demo
systemd unit, and deployment/interface evidence. His additions use the same ledger
and preserve original canonical events. No conflicting second backend database.

Our original uncommitted changes were checkpointed first in `73dfa91`, including
all existing handoff/status edits and the SQL snapshot slice. Merge conflicts were
resolved in runtime startup, current.md, tracker and lab catalog by retaining both
features. JSON directory and explicit SQL snapshot startup both retain automatic
Wazuh support. Existing guards, private key placement, signed-content validation,
request replay and technician feed remain. No private keys, databases, credential
files, model weights or environments were edited or included in the commits.

Active docs now use Jared's provisioned ext4 UUID
`0742aa3f-38fe-44aa-a382-9be9c4d9bb52` and `/mnt/alice-usb/pi-data`, replacing the
stale unmounted/old-UUID status. Historical reports retain their original evidence.
Jared's runtime still uses its existing JSON release. The merge does not deploy
our optional SQL container to the physical Pi or change the installed unit.

## Review fixes and scripts

Independent review identified two concrete Wazuh recovery bugs, reproduced in
failing tests before fixes:

- `HTTPException` during opening/reading an indexer response (including truncated
  bodies) escaped delivery handling and permanently stopped the worker. It now
  becomes `TRANSPORT_UNAVAILABLE` and follows the existing retry/probe path.
- A malformed nested `_shards` value in a create receipt raised AttributeError;
  booleans/floats could also masquerade as zero failures. Strict dictionary/integer
  validation now yields `INVALID_CREATE_RECEIPT`. Exact-content 409 retry remains.

`WazuhAuditSink.verify_stored(event)` reuses exact-content GET verification without
uploading or mutating outbox state. The new `lab.first_light.check_pipeline` helper
checks a selected request's hash-validated runtime chain against read-only SQL and
optional Wazuh records. It is safe to run beside the existing ledger owner because
it never opens AuditLog, submits a request, writes SQL, or delivers events.
It reports skipped dashboard/physical/replay checks explicitly. Both early and
assessment-stage DENY chains are tested. No successful physical actuation is inferred.

New combined tests cover SQL snapshot runtime operation while upload is blocked,
HTTP requests/feed/status remaining responsive, exact Wazuh payload preservation,
outage probes not exhausting attempts, restart recovery and no duplicate replay
execution. Controller and enterprise transport in these tests are simulated;
runtime, ledger, worker, receipt checking and bridge validation are real code.

## Verification actually run

- Focused combined runtime/snapshot/Wazuh checks before fixes: **45 passed, four
  subtests passed**. Additional failure regressions reproduced both review issues.
- Final `PYTHONPATH=/tmp/alice-live-deps .venv/bin/python -m pytest tests -q`:
  **312 passed, 237 subtests passed** in 34.65 seconds. Existing temporary pytest
  dependencies reused; private Python environments not modified. Local HTTP tests
  required sandbox escalation; review-agent socket tests were blocked there.
- `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e:runtime`: **one passed**.
  Existing dashboard automatically receives actual local runtime events, preserves
  history/replay and recovers its disconnected bridge. Fixture/mock producers;
  no physical Pi dashboard acceptance is claimed by this browser result.
- `npm run check`: **73 frontend tests, five script tests**, typecheck, lint and
  production build passed. Existing Zod/Rollup annotation and color-env warnings.
- Native Rust remains unavailable when Cargo is absent; no toolchain changes made.
- `git diff --check`, no conflict markers, all 118 tracker IDs/labels and current.md
  size/links checked. New/changed active documentation links resolve.

Prior evidence is retained in the [snapshot handoff](2026-09-06-release-snapshot.md)
(281 Python tests/230 subtests) and Jared's [automatic USB report](../reports/2026-09-06-automatic-usb-wazuh-sync.md)
(297 Python tests/226 subtests; seven live USB events delivered, Wazuh total 83).
Those physical observations are Jared's historical evidence, not this session's run.

## Access and next joint test

Read-only SSH to `pi@192.168.50.20` timed out. Local route inspection found
192.168.10.17 on en0 via the default gateway, with Ethernet interfaces inactive.
The user confirmed the Pi address and directed local development; Jared will test
after pulling. No further live access attempts, service restarts, formatting,
mounting, actuation or Wazuh outage injections were performed.

Follow the [joint acceptance guide](../integration/pi-technician-acceptance.md):
first check existing Pi/USB/Wazuh history, then connect the technician Mac's SSH
bridge and display. Submit one provisioned signed request/retry, verify automatic
dashboard appearance and exact matching records. Observe execution count separately.
Then test denial and technician reconnect. Coordinate outage/restart/storage-loss
and real ESP tests separately; never launch the maintenance CLI beside systemd.

The currently implemented directions are Pi → USB → Wazuh and Pi → technician Mac.
Enterprise → Pi cache publication and Mac → Pi bound biometric decisions remain
separate unfinished integrations. No UI redesign or fake remote action was added.
