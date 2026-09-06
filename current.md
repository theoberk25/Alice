# Current

Updated: 2026-09-06 UTC (September 5 EDT).
Fetched Jared's `origin/main` at `ef413b6`. Local branch: `codex/live-dashboard`.
Our snapshot work is preserved in `73dfa91`; Jared integration is verified locally.
No push, remote deployment, Pi service or network configuration changes this session.

## Active objective

Integrate Jared's automatic USB → Wazuh worker with our signed SQL snapshot and
live technician feed. Prepare scripts for Jared to run on the configured Pi.
[Joint acceptance](docs/integration/pi-technician-acceptance.md) ·
[ESP/technician handoff](docs/integration/esp-technician-handoff.md).

## Combined implementation

- Existing single-writer SQLite/hash-chain/Ed25519 ledger and mount guards retained.
- Automatic Wazuh worker shares the runtime owner lock; HTTPS happens outside it.
  Exact remote records are checked before durable ACK. No semantic reconciliation.
- Signed first-light SQL input snapshots remain supported alongside JSON releases;
  no overwrite publication or audit reset. General enterprise SQL cache sync,
  revocations/freshness/rollback/activation remain outside this bounded slice.
- Pi → authenticated bridge → technician dashboard supplies live history/updates
  and reconnect recovery. Missing facts stay unknown; fixture/mock labels remain.
- Read-only check_pipeline script compares an existing request across runtime, USB
  SQL and optional Wazuh GET. It never commands hardware or creates another writer.
- Pi classifies; Mac resolves held accept/deny after biometrics; Pi validates execution
  prerequisites. Remote biometric response path and real scoring remain incomplete.

## Reported deployment and current access

Jared reports active `alice-runtime.service` on `pi@192.168.50.20`, ext4 USB UUID
`0742aa3f-38fe-44aa-a382-9be9c4d9bb52`, `/mnt/alice-usb/pi-data`, release
`/mnt/alice-usb/release`; internal private key/config retained. His test delivered
seven new USB events, reaching 83 Wazuh records, with no duplicate mock actuation.
[His evidence](docs/reports/2026-09-06-automatic-usb-wazuh-sync.md).
This Mac's SSH timed out; its active network is 192.168.10.x, Ethernet inactive.
User directed local development; Jared will run physical checks after publication.
No live outage, reboot/unplug, physical actuator or new Pi acceptance claimed here.

## Evidence and next steps

Fresh merged checks: **312 Python tests/237 subtests**, **73 frontend tests**, five
script tests, typecheck/lint/build and one live local browser test passed.
[Review fixes and evidence](docs/handoffs/2026-09-06-jared-main-integration.md).
Rust remains unverified without Cargo; physical joint acceptance remains for Jared.

1. User publishes the reviewed integration; Jared pulls while preserving private state.
2. Jared runs read-only acceptance on the current Pi, then a signed request/retry.
3. Technician Mac joins demo network and connects tunnel/bridge; verify automatic
   appearance of the same request alongside matching USB/Wazuh records.
4. Coordinate controlled outage/restart/storage-loss and real ESP acceptance.
5. Agree biometric response and general enterprise input synchronization contracts.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Sync runbook](docs/integration/wazuh-audit-sync.md) · [Scripts](docs/scripts/README.md)
