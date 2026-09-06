# Current

Updated: 2026-09-06 UTC (September 5 EDT).
Baseline: `417b9de`; main teammate updates through `7081b6a` merged in `8e1154d`.
Working branch: `codex/live-dashboard`. User authorized publication to main;
no deployment is included.

## Active objective

Review the implemented USB SQL / live technician dashboard slice and hand its
configuration to Jared and Alex. [Runbook and mappings](docs/integration/live-dashboard.md).

## Confirmed design and implemented scope

- **USB carries the current synchronized SQL snapshot into DDIL; the Pi writes
  new offline events to USB.** SIEM reconciliation preserves original events and
  appends findings/acknowledgements. This corrects the former internal-only assumption.
- Existing SQLite/hash-chain/Ed25519 ledger retained. Runtime now guards the USB
  mount, keeps its signing key outside USB, and fails closed on lost storage.
- Real runtime `/events` → authenticated local bridge → remote transport → Alex's
  existing dashboard. History/incremental updates/reconnect and late results work.
- Missing scores/mission/request fields, connectivity and verification stay unknown.
  Fixture assessment and mock controller labels persist. No live-mode demo fallback.
- Pi owns classification; Mac resolves held accept/deny after biometric verification;
  Pi validates execution prerequisites. Remote response delivery remains unavailable.
- Merek owns backend integration; Theo/Jared configure Pi; Xavi hardware; Alex dashboard.

## Evidence and limits

276 Python tests plus 226 subtests; 73 frontend tests; 5 script tests; typecheck,
lint and production build passed. Live browser acceptance: 1 passed; existing
mock review browser tests: 5 passed. User saw synthetic SQLite events update the
actual dashboard automatically. Rust tests could not run because cargo is absent.
Physical Pi/USB, real ML/controller and biometric response acceptance are not claimed.
[Detailed evidence and prior checkpoint](docs/handoffs/2026-09-06-live-dashboard.md).

## Current configuration / blockers

Pi `alice-pi-01`, SSH `pi@192.168.50.20`; read-only connection attempt timed out.
USB `/dev/sda1`, UUID `6C1A-C6EA`, not mounted; proposed `/mnt/alice-usb`.
Filesystem and physical durability unverified. Enterprise SQL snapshot publication,
general policy SQL loading and SIEM reconciliation worker remain unimplemented.

## Next steps

1. Publish the reviewed checkpoint to main under the user's explicit authorization.
2. Jared verifies Pi reachability, USB filesystem/mount, release and private key setup.
3. Run native Rust checks and physical Pi/USB/controller acceptance from the runbook.
4. Integrate the enterprise snapshot publisher and SIEM reconciliation independently.
5. Agree and implement the bound biometric accept/deny response path with Alex.

[Rules](AGENTS.md) · [Architecture](architecture.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](docs/scripts/README.md)
