# Current

Updated: 2026-09-06 UTC (September 5 EDT).
Baseline: main `44f4d73`, merged at `4eb6238` on `codex/wazuh-log-sync`.
Objective: automatic Pi USB audit-ledger delivery into enterprise Wazuh.
Teammates own Pi ↔ technician approval transport and enterprise cache publication.

## Implemented and observed

- Existing AuditLog retained. Automatic in-process worker shares the owner lock;
  HTTPS runs outside it. Bounded scanning, retry/backoff and persistent receipts.
- Initial 76 events uploaded using maintenance mode, replayed without duplicates.
  [Historical proof](docs/reports/2026-09-06-wazuh-ledger-sync.md).
- User approved ext4 at `/mnt/alice-usb`; existing ledger/evidence/release migrated
  with backup. Private key stays internal. No local fallback writer.
- Runtime now uses USB and automatic delivery under enabled `alice-runtime.service`.
  New signed light request automatically uploaded **7 events**: Wazuh total **83**.
  Identical retry executed nothing extra; mock count 10 → 11.
  [Automatic USB proof](docs/reports/2026-09-06-automatic-usb-wazuh-sync.md).

## Current configuration

Pi `alice-pi-01`, SSH `pi@192.168.50.20`; Jared wired Mac `192.168.50.50`.
Wazuh URL `https://wazuh.indexer:9200` maps to Jared's Mac on the Pi.
Index `alice-ledger-v1`, private service account `alice_ledger_sync`.
USB `/dev/sda1`, ext4 UUID `0742aa3f-38fe-44aa-a382-9be9c4d9bb52`.
Data `/mnt/alice-usb/pi-data`; signed release `/mnt/alice-usb/release`.
Key `/home/pi/first-light/pi-data/ledger_key.seed`; private sync config
`/home/pi/first-light/wazuh-sync/config.json`. Original internal ledger retained
as inactive backup, along with `~/first-light/pre-auto-sync-backup/`.
Stop systemd before maintenance; do not start a second tmux runtime or CLI writer.
Mock ESP remains in its original tmux session and is not boot-persistent.

## Evidence and blockers

Fresh pre-publication Python suite: **297 passed plus 226 subtests** (22.18 s).
Changed Markdown links and file placement checked against README/AGENTS.md.
Live outage test was previously staged but not run: approval review rejected SSH
execution because of account usage limits. No network mapping was changed by it.
Live outage/reboot/unplug/power-loss tests remain; do not claim them passed.
Real ML/physical actuator, semantic reconciliation, evidence-blob upload,
enterprise snapshot publication and technician accept/prevent commands remain.
Uploader connectivity never changes first-light execution authority.

## Next steps

1. Complete the staged live outage/recovery test; publication does not imply acceptance.
2. Test service restart and missing-USB fail-closed behavior in a maintenance window.
3. Teammates pull the published main checkpoint and follow the connection handoff.
4. Teammates integrate authenticated, request-bound technician accept/prevent responses.
5. Enterprise owner completes trusted permissions/baseline cache publication.

[ESP/technician handoff](docs/integration/esp-technician-handoff.md) ·
[Sync runbook](docs/integration/wazuh-audit-sync.md) ·
[Backend guide](docs/integration/live-dashboard.md) · [Rules](AGENTS.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](docs/scripts/README.md)
