# Current
Updated: 2026-09-06.
Branch: `codex/led-display`; baseline `608f107`, upstream `origin/main` `e1e7506`.

## Active objective

Complete and push the user-authorized environmental demo software, following the
[scope handoff](docs/handoffs/2026-09-06-environmental-demo-context.md).
The user explicitly reauthorized pull and push after reviewing the scope.
The pre-publication pull of `origin/codex/led-display` was already up to date.

## Current state

- Thermal/energy backend, lifecycle, state/history and agent proposal API implemented.
- Real ALICE signed fan requests, policy decisions, ledger execution and native
  signed review integrated; first-light request schema remains unchanged.
- Read-only Pi renderer and v3 firmware generate phase-preserving eight-LED patterns
  with stale leases, readback, recovery and legacy SET compatibility.
- Agent client, signed demo release generator and frontend contract delivered.
- Operator page design remains with the teammate. No real fan control or deployment.

## Evidence and limits

Final Python integration: 459 passed, 30 skipped, 246 subtests; details in
[validation](docs/reports/2026-09-06-environmental-demo-validation.md).
Console checks: 135 tests and eight script tests, typecheck, lint and build passed.
Eight browser tests passed. Actual firmware host tests passed. Rust fan-validator
extraction: one passed; full native build blocked by unchanged Swift camera code
and this machine's SDK. No camera use, board build, flashing or physical acceptance.

## Next steps

1. Teammate implements the operator page using the [contract](docs/contracts/environmental-demo-v1.md).
2. Resolve existing native camera/SDK build compatibility in its owning workstream.
3. Separately provision and verify physical Pi/XIAO operation; owner unassigned.

[Run guide](docs/guides/environmental-demo.md) · [Tracker](docs/implementation-tracker.md)
