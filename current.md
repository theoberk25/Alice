# Current

Updated: 2026-09-06 UTC (September 5 EDT).
Published baseline: `44f4d73` on `origin/main`; fetched this session, no newer commits.
Includes architecture `417b9de` and teammate updates through `7081b6a`.
Local branch: `codex/live-dashboard`; snapshot increment is uncommitted.
No push, deployment or physical USB operation performed this session.

## Active objective

Continue backend/Pi integration and Alex's existing live technician dashboard.
[Snapshot commands and boundaries](docs/integration/release-snapshot.md) ·
[Live-feed runbook and mappings](docs/integration/live-dashboard.md).

## Implemented scope and design

- USB carries synchronized inputs into DDIL and retains new offline audit events.
  Original events survive reconciliation and snapshot changes without rewriting.
- Existing guarded SQLite/hash-chain/Ed25519 ledger and off-USB signing key retained.
- New immutable SQL container packages the existing signed first-light release;
  bounded read-only loading reuses verification. Explicit snapshot startup requires
  existing history unless initialization is explicit. No overwrite publication.
- This is first-light JSON in SQL, not general enterprise policy synchronization,
  automated activation, freshness/rollback protection or a SIEM delivery worker.
- Runtime → authenticated bridge → remote transport → existing dashboard remains.
  Missing scores/verification stay unknown; fixture assessment/mock labels remain.
- Pi classifies; Mac resolves held accept/deny after biometrics; Pi checks execution
  prerequisites. Remote response delivery remains unavailable.

## Evidence and limits

Final Python run: **281 passed, 230 subtests passed**. Console: **73 tests**, five
script tests, typecheck, lint and build passed. Existing live browser acceptance:
**one passed**. SQL runtime tests cover restart/replay, changed release permissions,
original event preservation and queued history; browser uses the JSON release.
Rust command failed because Cargo is absent. Pi SSH timed out again.
No physical Pi/USB, real ML/controller or biometric response acceptance claimed.
[New evidence and handoff](docs/handoffs/2026-09-06-release-snapshot.md) preserves
prior checkpoint evidence and links to the original live-dashboard handoff.

## Blockers and next steps

1. Theo/Jared verify Pi `alice-pi-01` (`pi@192.168.50.20`), USB `6C1A-C6EA`,
   filesystem/mount (proposed `/mnt/alice-usb`) and protected signing key setup.
2. Jared/Merek agree full enterprise SQL schema, revocations/identity, freshness,
   rollback anchors and activation before extending the bounded snapshot slice.
3. Connect real Pi feed, run physical storage/controller acceptance and native Rust.
4. Implement durable SIEM delivery when destination/authentication/receipts are agreed.
5. Agree and implement the bound biometric accept/deny response path with Alex.

Merek owns backend integration; Theo/Jared configure Pi; Xavi hardware; Alex dashboard.
[Rules](AGENTS.md) · [Architecture](architecture.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](docs/scripts/README.md)
