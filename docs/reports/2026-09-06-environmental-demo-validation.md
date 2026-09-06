# Environmental demo software validation

Date: 2026-09-06. Branch: `codex/led-display`. Starting display commit `608f107`;
upstream `origin/main` `e1e7506`. The user authorized implementing all identified
missing software areas and pushing, then explicitly requested pulling before push.
The first pull of `origin/codex/led-display` was already up to date.

## Delivered scope

- Integrated the separate thermal prototype and completed its backend: typed initial
  values, lifecycle, bounded monotonic integration/history, energy metadata and
  exhaustion, detached snapshots and run-bound request tracking.
- Added a real fan adapter using existing Ed25519 request verification, signed
  grants, ALICE policy decisions, durable ledger and signed native review. No ML
  assessment fixture or timed decision sequence is used by this demo.
- Added strict native Rust/TypeScript fan-review compatibility and authenticated
  feed forwarding. Existing first-light schema and behavior are retained.
- Added single-owner Pi serial pattern delivery and actual eight-channel firmware
  timing, phase-preserving pair updates, independent white segments, leases,
  stale indication, reboot/readback handling and legacy SET precedence.
- Added an agent client, local demonstration release generator, operator/frontend
  [contract](../contracts/environmental-demo-v1.md) and [run guide](../guides/environmental-demo.md).

The prior mapper-only state and eight passing mapping tests are historical evidence
for `608f107`; the context handoff now describes the intent behind this larger slice.
The source thermal checkout and its uncommitted backend originals were preserved.
No real fan, cloud scenario, live video pipeline or parallel LLM was added.

## Checks actually run

- Python 3.12 in an isolated temporary environment, repository audit/hardware
  dependencies: full `pytest -q tests --ignore=tests/console --tb=short`.
  Initial integrated run: **458 passed, 30 skipped, 246 subtests passed**. A final
  rerun follows the native bridge/client changes; its outcome is recorded below.
- `npm run check`: **135 tests passed**, eight script tests passed, TypeScript,
  ESLint and production Vite build passed.
- Playwright console/review regressions: **8 passed**, installed headless Chrome,
  isolated port 1429. Native IPC/face outcomes are synthetic test fixtures, not
  real camera qualification. Existing port 1420 was left untouched.
- Actual firmware compiled with the host C++ compiler and exercised by both C++
  assertions and the Python serial transport. Tests cover phase, pair agreement,
  5 Hz edges, uint32 rollover, stale leases, invalid frames, legacy compatibility,
  readback and lost-ack reconciliation.
- Real ALICE/plant tests cover ALLOW and ramps/energy, permission DENY, CHALLENGE,
  signed approve/reject, unchanged immutable decision, stale lifecycle bindings,
  tampering, request conflicts, restart and uncertain-delivery no-repeat behavior.
- `cargo test --locked` was attempted with an isolated Rust toolchain. The full
  native build is **blocked** by unchanged `biometric_camera.swift` and this Mac's
  SDK: `runtimeErrorNotification`, `wasInterruptedNotification` and
  `wasDisconnectedNotification` are unavailable. No camera source was modified.
- To check the new Rust validation despite that build blocker, the exact JSON
  canonicalization, Snapshot validation and request structs were extracted into
  a temporary independent crate, together with the new fan-binding test:
  **1 passed**. This is a validator check, not full native application acceptance.

Initial system Python 3.9 was unsuitable; all final Python checks use 3.12. Socket
checks required escalation because the sandbox refuses loopback binds. The serial
fixture uses host stdio/GPIO stubs, not a connected USB board. Skipped tests are
reported as skipped, not counted as passing.

## Remaining acceptance

No firmware flashing, Arduino target-board build, wiring work, Pi deployment,
physical illumination measurement or real camera session occurred. These remain
separate physical acceptance steps. The operator page design remains assigned to
the teammate. Existing native camera/toolchain compatibility remains a full-build
limitation; native fan request schema validation and web checks are separately
verified as above. Demo permissions are illustrative signed configuration, not
hardware operating limits. Physical fan actuation is outside this implementation.

Final Python regression result: **459 passed, 30 skipped, 246 subtests passed in 70.46s (0:01:10)**.

The user paused publication, then explicitly said yes to resume. The final
pre-publication pull of `origin/codex/led-display` was already up to date.
