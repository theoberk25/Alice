# Current
Updated: 2026-09-06 EDT. Baseline commit: `24d32a1`.
Active checkout: `/Users/jaredviani/Desktop/Alice`, branch `codex/wazuh-log-sync`.

## Active objective

Complete the fan-control demo across signed agents, the Pi decision runtime,
synthetic normal-behavior model, USB state/audit storage, Wazuh and Merek's native
technician console. Preserve the proven eight-light path and other contributors'
work.

## Current state

- The Pi at `192.168.50.20` runs signed release generation 5. It preserves both
  existing light grants/keys and adds `cooling-agent-01` and `power-agent-01` for
  integer `set_fan_speed` requests against `SERVER-ROOM-FANS`.
- The Pi loads a 928 KB data-only hybrid Isolation Forest/nearest-normal model.
  It reads the decision-time metric snapshot from
  `/mnt/alice-usb/machine-state.json`; no sklearn or pickle loader runs on Pi.
- Live direct sequence 30→40→50→60% returned three `ALLOW` decisions. A subsequent
  enterprise-ingress 60→70% request ALLOWed; power-agent 70→0% returned
  `CHALLENGE/ANOMALY_REVIEW_REQUIRED`; USB stayed at 70%. Pending request:
  `82d209dc-a4b7-4489-bfc2-9165b6e704bf`.
- Native review snapshots add the exact fan request, decision reason codes and a
  bounded model summary. Existing light snapshots remain backward compatible.
  Human approval still requires the existing signed fresh-face, one-use proof;
  rejection never executes.
- The machine-metrics MCP submits signed requests to ALICE instead of writing fan
  state directly. Its canonical port is now `8795`, avoiding enterprise ingress
  on `8790`. Each deployed agent instance needs its own private identity/key.
- Pi TLS name `wazuh.indexer` maps to enterprise host `192.168.50.50`. The fresh
  wireless-ready request was receipted in Wazuh before Pi forwarding and cached
  on USB; its REQUEST/HIGH ASSESSMENT/CHALLENGE reached `alice-ledger-v1` as
  sequences 698–700. Sync returned IDLE without error.

## Evidence and limits

Python suite: 466 passed plus 266 subtests. Console suite: 135 passed; TypeScript
typecheck, ESLint, script checks and production web build passed. Fan console contract/UI: 15 passed. Data-only candidate
fresh synthetic evaluation: 3,000/3,000 anomaly detections and 32/3,000 normal false
positives; demo sequence normal/normal/normal/unusual. Rust checks are pending because
this Mac has no `cargo`. Biometrics use a separate venv and were outside this Python
run. The candidate remains synthetic pending
real sensor validation. Merek has not yet pulled this fan-aware console build or
accepted/rejected the live fan HOLD.

## Next steps

1. Commit/push this branch, then have Merek pull and run native Rust/console checks.
2. Have Merek open the pending fan HOLD and reject it; verify USB remains at 70% and
   Wazuh receives the signed technician action.
3. Queue a fresh fan HOLD, approve it with face verification and verify USB state,
   execution receipt, observed state and Wazuh records.
4. Provision each cloud/local agent's private signing seed outside Git and run its
   local MCP instance against the Pi.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Model PRD](docs/prds/anomaly-model-prd.md) ·
[Console contract](docs/integration/upstream-alice.md) ·
[Demo runbook](docs/guides/demo-runbook.md)
