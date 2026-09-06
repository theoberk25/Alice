# Current

Updated: 2026-09-06 UTC (September 5 EDT).
Baseline: merge `bf6fee0` combines main `d3502e3` and local SIEM work.
Objective: publish ESP handoff with verified eight-light mapping and grid guidance.
Teammates own Pi ↔ technician approval transport and enterprise cache publication.

## Implemented and observed

- Main adds XIAO USB-serial transport/firmware, signed SQL input snapshots and
  technician acceptance tools. Local SIEM UI, operator and cache downloader retained.
- Physical light-on: ALLOW / COMPLETED / on; Jared visually confirmed the D0 LED.
  Seven events uploaded; 104 total, all 97 original canonical events unchanged.
  Operator http://127.0.0.1:8789; physical configuration in linked handoff.

- Enterprise UI redesigned locally: security overview, threat hunting, endpoint
  evidence and actual Wazuh Pi stream. Browser interactions and five backend tests pass.
  Earlier query: 259 alerts / 8 critical / 97 Pi records; endpoint inventory labelled demo.

- Enterprise permissions generation 44 / revocation epoch 8 downloaded from Wazuh
  and signature/hash verified on USB. Timer polls about every 30 seconds.
  Cache path `/mnt/alice-usb/enterprise-cache/permissions`; not runtime activation.

- Created enterprise login `ssgt.a.okafor` and scoped ESP operator profile; reads
  83 ledger events, denied user administration.
  No new Pi grants or speculative voltage controls activated; three profile tests pass.

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
Physical XIAO uses stable USB by-id path; 60-physical-esp.conf overrides transport.
Backup: ~/first-light/pre-serial-backup/. Idle-low firmware flashed. Mock idle.

## Evidence and blockers

Historical merged Python suite: **357 passed plus 261 subtests**.
npm check: typecheck/lint, 73 frontend + 5 script tests, build passed.
Changed Markdown links and file placement checked against README/AGENTS.md.
Live outage test was previously staged but not run: approval review rejected SSH
execution because of account usage limits. No network mapping was changed by it.
Live outage/reboot/unplug/power-loss tests remain; do not claim them passed.
Real ML, semantic reconciliation, evidence-blob upload,
full snapshot activation and technician accept/prevent commands remain.
Uploader connectivity never changes first-light execution authority.

Eight colors confirmed; idle-low firmware deployed; D7 dark confirmed; runtime active.

## Next steps

1. Complete the staged live outage/recovery test; publication does not imply acceptance.
2. Test service restart and missing-USB fail-closed behavior in a maintenance window.
3. Publish the preserved integration and ESP mapping; retain all private data.
4. Teammates integrate authenticated, request-bound technician accept/prevent responses.
5. Integrate full enterprise permission semantics and compatible baseline/model activation.

[ESP handoff](docs/integration/esp-handoff.md) ·
[Sync runbook](docs/integration/wazuh-audit-sync.md) ·
[Backend guide](docs/integration/live-dashboard.md) · [Rules](AGENTS.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](docs/scripts/README.md)
