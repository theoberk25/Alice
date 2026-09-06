# Current

Updated: 2026-09-06 EDT.
Integration baseline: `origin/main` `d57c660`.
Objective: deliver the online cloud/SIEM view and offline anomalous fan-shutdown
demo across the Opal, enterprise Mac, wired agents, Pi and technician application.

## Implemented and observed

- Main includes the Light-Control and Decision-Brief MCP services, cloud-agent
  scaffolding and build documentation. Their actual deployment remains separate.
- Native live biometrics now includes automatic camera capture, multi-pose
  enrollment, ArcFace gallery login, presentation checks, encrypted generations
  and stale/replay guards. Live HOLD delivery to the Pi remains unfinished.
- The signed first-light runtime uses ext4 USB storage, physical eight-light serial
  execution and automatic Wazuh audit delivery. Existing records and backups remain.
- GL.iNet Opal `192.168.50.1` supplies DHCP `.100-.199`; Pi `eth0` now routes
  through it. Pi direct venue Wi-Fi is disconnected with autoconnect disabled.
  Wireless-to-wired SSH, Pi-to-router, external IP, DNS, runtime and sync checks pass.
- Wazuh `https://wazuh.indexer:9200` resolves to Jared's Mac at `.50`; index
  `alice-ledger-v1`, service account `alice_ledger_sync`. USB is mounted at
  `/mnt/alice-usb`; Pi data is `pi-data` and the signed release is `release`.
- Target demo is documented: ONLINE simulated cloud activity; Opal/enterprise
  removal; three normal `+10%` fan requests; one permission-eligible shutdown
  classified `ELEVATED`/`HIGH`; workstation HOLD explanation; human REJECT; no
  fan-off command; durable reconciliation after enterprise returns.

## Evidence and limits

Latest main delivery reports 117 frontend, 8 script, 166 biometric-service and
44 native Rust tests passing; one live Ollama test is intentionally ignored.
Core reports 362 passed plus 266 subtests and one optional serial check initially
skipped; follow-up scope is in the delivery report. Five console E2E tests and one
real mock-runtime feed E2E passed. Typecheck, lint, web build and macOS app build pass.

Physical light control and Pi/USB/Wazuh delivery have separate live evidence.
No integrated human camera acceptance, cloud gateway deployment, real Pi forest,
fan/sensor adapter, automatic control transfer, native HOLD response or complete
router-loss/reconciliation acceptance is claimed. Synthetic examples are not
production normal behavior or electrical safety limits.

## Next steps

1. Give enterprise, technician and local-agent machines stable static DDIL addresses.
2. Provision cloud, cooling and power-agent identities and deploy the gateway/MCP path.
3. Generate fan training/calibration/evaluation data and deploy the selected forest.
4. Connect enterprise offline status and native LLM/face-gated HOLD rejection to Pi.
5. Run online, router-power-loss, fan-shutdown and reconciliation acceptance.

[Demo runbook](docs/guides/demo-runbook.md) ·
[Biometric delivery](docs/reports/2026-09-06-live-face-main-integration.md) ·
[Technician integration](docs/integration/technician-console.md) ·
[Tracker](docs/implementation-tracker.md) · [Rules](AGENTS.md)
