# Current
Updated: 2026-09-06 UTC (September 5 EDT).
Implementation baseline: local `26c2be1`, based on `origin/main` `3bceeac`.
Objective: preserve the working wired path while adding wireless access, local and
cloud agents, enterprise input sync and the full native technician application.

## Implemented and observed

- Main adds XIAO USB-serial transport/firmware, signed SQL input snapshots and
  technician acceptance tools. Local SIEM UI, operator and cache downloader retained.
- Physical light-on: ALLOW / COMPLETED / on; Jared visually confirmed the D0 LED.
  Seven events uploaded; 104 total, all 97 original canonical events unchanged.
  Operator http://127.0.0.1:8789; physical configuration in the hardware runbook.
- Web dashboard at `http://192.168.50.50:1420` now requires a server-side login.
  An authenticated browser loaded 608 events and received seven new physical-Pi
  events incrementally. Feed source is SSH tunnel / physical serial; the web app
  is read-only. Native LLM, face identity and accept/reject integration remains.

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
Wazuh `https://wazuh.indexer:9200` maps to Jared's Mac on the Pi; index
`alice-ledger-v1`, private service account `alice_ledger_sync`.
USB `/dev/sda1`, ext4 UUID `0742aa3f-38fe-44aa-a382-9be9c4d9bb52`.
Data `/mnt/alice-usb/pi-data`; signed release `/mnt/alice-usb/release`.
Key and private sync config remain on Pi internal storage. Original internal
ledger and `~/first-light/pre-auto-sync-backup/` remain inactive backups.
Stop systemd before maintenance; do not start a second tmux runtime or CLI writer.
Physical XIAO uses stable USB by-id path; 60-physical-esp.conf overrides transport.
Backup: ~/first-light/pre-serial-backup/. Idle-low firmware flashed. Mock idle.

## Evidence and blockers

Current Python core suite: **363 passed plus 266 subtests**.
Current npm check: typecheck, lint, 74 frontend tests, 7 script tests and build pass.
Active transition docs consolidated into the demo, hardware, Wazuh and technician
guides; superseded live/ESP/checklist documents moved intact to `docs/archive/`.
Live outage test was previously staged but not run: approval review rejected SSH
execution because of account usage limits. No network mapping was changed by it.
Live outage/reboot/unplug/power-loss tests remain; do not claim them passed.
Real ML, semantic reconciliation, evidence-blob upload,
full snapshot activation and technician accept/prevent commands remain.
Uploader connectivity never changes first-light execution authority.

Eight-light production deployed: 16 signed ON/OFF tests and 8 replays passed.
Ledger quota expanded 8→256 MiB with unchanged history; Wazuh resumed.

## Next steps

1. Bridge the wireless access point onto `192.168.50.0/24`; test Wi-Fi locally before WAN.
2. Provision distinct signed local/cloud agent identities and an enterprise gateway.
3. Integrate native LLM/face-gated, request-bound accept/reject; keep web read-only.
4. Activate verified enterprise permissions/baseline/model generations on USB.
5. Run the integrated request, outage/recovery and authority-transfer acceptance flow.

[Integrated runbook](docs/guides/demo-runbook.md) ·
[Sync runbook](docs/integration/wazuh-audit-sync.md) ·
[Hardware](docs/guides/first-light-hardware.md) · [Rules](AGENTS.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](docs/scripts/README.md)
