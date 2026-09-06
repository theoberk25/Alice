# Xavier serial integration and push preparation

Date: 2026-09-06 UTC (September 5 EDT). Follow [AGENTS.md](../../AGENTS.md).
Local branch `codex/live-dashboard`; integration parents `8d8bdcc` (our snapshot,
Wazuh and acceptance work) and `290699b` (Xavier's fetched main).
No push, Pi deployment, USB changes or board flashing performed this session.

## Merge result and fixes

Xavier added the XIAO ESP32-S3 firmware, USB-serial adapter, simulator, tests and
protocol/hardware guides. Contrary to the initial expectation of disjoint areas,
`dcamr/main.py` and `current.md` overlapped. Both were merged by retaining all
options: JSON/SQL release inputs, HTTP/serial controller selection, USB guards,
owner-integrated Wazuh worker and existing dashboard feed. Private state remained
untouched; no dependency was installed into a private environment.

Independent review identified bounded fixes, reproduced in failing tests:

- Unbounded serial `flush()`/`readline()` could stall the runtime owner lock and
  therefore its feed/uploader. The adapter now uses one-byte reads under the
  absolute write/reply deadline, bounded frame storage, no flush, and finite
  `(0, 10]`-second timeout configuration. Short writes fail without retransmission.
- Malformed matching replies could claim success: boolean version/missing or bad
  boot ID, plus duplicate fields. Replies now require the declared version/types,
  field inventory and eight-hex boot identity. Unproven exchanges stay UNKNOWN.
- Firmware accepted leading-zero versions, raw string controls and embedded
  NUL/trailing data; the frame boundary also omitted the newline. These are rejected
  before GPIO writes, and newline is included in the 256-byte frame budget.
- Review of the fixes caught a late-newline resynchronization issue. The consumed
  newline now clears discard state even when late; a fresh valid exchange works.

The serial simulator rejects boolean versions/duplicate fields and supports bounded
byte reads. Host C++ tests compile the actual firmware loop with test-only Arduino,
serial and GPIO stubs. The combined serial/snapshot/Wazuh test verifies preserved
snapshot provenance, exact event delivery, no HTTP fallback and restart replay
without another serial write. Firmware source was changed but not board-compiled
or flashed: `arduino-cli` is absent here.

## Evidence

The final full suite passed **344 tests and 261 subtests** in 33.56 seconds,
including the late-newline regression. No test skipped when the
optional serial dependency was supplied. Commands:

```sh
PYTHONPATH=/tmp/alice-live-deps:/tmp/alice-xavier-serial-deps .venv/bin/python -m pytest tests -q
ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e:runtime
npm run check
```

`pyserial==3.5` was installed with `--no-deps --target /tmp/alice-xavier-serial-deps`;
pytest dependencies were already in the other temporary directory. The pyserial
PTY test passed and exercises real serial-library framing, not an attached board.
Host compiler tests passed for actual firmware input parsing and recovery.

Live local dashboard browser acceptance: **one passed**. Console checks:
**73 frontend tests, five script tests**, typecheck/lint/build passed. Existing
Node color and Zod/Rollup comment annotation warnings remained. These tests still
use fixture assessment and simulated devices; no new physical acceptance is claimed.
Native Rust remains unverified without Cargo (prior session command failed).

## Updated team guidance

Xavier's hardware guide reports real development-Mac LED tests but explicitly says
the Pi run remains undone. The handoff table was corrected so it does not imply
serial was already deployed on the Pi. The checked-in systemd unit still uses the
HTTP mock. Jared/Xavier must retain its storage, signing and Wazuh configuration
while deliberately switching only the controller flags during a coordinated restart.
The hardened firmware needs Xavier's rebuild/flash and physical re-verification.

The XIAO is on USB, has no network address, and reports actuator feedback rather
than measured illumination. The technician Mac separately needs network access to
the Pi's HTTP service through the SSH tunnel/authenticated bridge. The existing
live dashboard contract and layout remain compatible.

Follow the [joint acceptance guide](../integration/pi-technician-acceptance.md).
Current implemented directions remain Pi → USB → Wazuh and Pi → technician Mac.
Enterprise/SIEM → Pi permissions/cache synchronization is still separate unfinished
input work. No upload receipt is treated as permission, biometric proof or semantic
reconciliation. Jared can test the connected outputs after the user publishes.

Prior evidence and detailed lifecycle remain in the
[Jared integration handoff](2026-09-06-jared-main-integration.md). All 118 tracker
IDs/labels are retained. Future pushes can race with another teammate update, so
fetch/check again if main advances after this integration's dry-run validation.

## Publication

User authorized pushing after successful tests and the push dry-run. Integration
`2aaf021` was pushed to `origin/main` and independently confirmed by `git ls-remote`.
Main was re-fetched before the fast-forward push. This publication performs no
Pi deployment or firmware flashing; joint physical acceptance remains pending.
