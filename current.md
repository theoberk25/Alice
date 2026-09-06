# Current

Updated: 2026-09-06 UTC (September 5 EDT).
Published integration: `2aaf021` on `origin/main` (push and remote SHA confirmed).
Local branch: `codex/live-dashboard`; includes Xavier's `290699b`.
Our snapshot/Wazuh work is preserved in `8d8bdcc`; serial integration is verified locally.
User authorized publication; no remote deployment, Pi service or network changes.

## Active objective

Verify the published serial/snapshot/Wazuh pipeline with Jared and Xavier on the
configured Pi, USB and live technician Mac.
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
- Optional XIAO serial adapter and firmware added; HTTP controller remains available.
  Xavier reports real development-Mac LED testing; Pi serial deployment is pending.
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

Fresh combined checks: **344 Python tests/261 subtests**, **73 frontend tests**, five
script tests, typecheck/lint/build and one live local browser test passed.
[Serial review fixes and evidence](docs/handoffs/2026-09-06-xavier-serial-integration.md).
Rust remains unverified without Cargo; physical joint acceptance remains for Jared.

1. Jared/Xavier pull published main while preserving private state.
2. Xavier rebuilds/flashes updated firmware; Jared coordinates serial selection
   without replacing USB history, keys or Wazuh config; run the request/retry check.
3. Technician Mac joins demo network and connects tunnel/bridge; verify automatic
   appearance of the same request alongside matching USB/Wazuh records.
4. Coordinate controlled outage/restart/storage-loss and real ESP acceptance.
5. Agree biometric response and general enterprise input synchronization contracts.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Sync runbook](docs/integration/wazuh-audit-sync.md) · [Scripts](docs/scripts/README.md)
