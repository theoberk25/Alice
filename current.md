# Current

Updated: 2026-09-05
Upstream baseline: `d6e7e55` (main: shared layout plus first-light runtime/report).
Review branch: `codex/integrate-team-layout`; latest-main runtime plus documentation follow-up.
Documentation checkpoint `56f0f3f` preserves the follow-up before merging first-light.
Earlier checkpoint `011abf1` remains separate; do not replay its obsolete layout.

## Current objective

Review the combined architecture and placement follow-up against latest main.
The review branch preserves both team migrations and first-light work. Start with [AGENTS.md](AGENTS.md).

## Current state

- Root [architecture](architecture.md) covers deployment, modes, request flow,
  implemented components, contract/trust boundaries, storage/models and source placement.
- First-light now wires signed terminal requests, verified demo releases, exact grants,
  fixture assessments, durable ledger events and a mock ESP HTTP light client.
  Authority is hard-coded OFFLINE; real scoring/review and physical acceptance remain.
- Console stays in apps/desktop, shared packages and services/biometrics. Remote
  transport remains disconnected; first-light GET /events is a read-only CLI feed.
- Eight documentation moves finish centralization. All 384 latest-main files survive;
  no extra moves were needed. Empty legacy scaffolds and private state are preserved.
- Biometric provisioning retains the Path import fix and two isolated regressions.
  Active docs now reflect the console migration, ledger and first-light scope.
- Tracker: 12 done components, 38 partial and 68 planned tasks; 118 IDs preserved.
  First-light's upstream status changes are retained. Archive contents remain excluded.

## Next steps

1. Review the combined codex/integrate-team-layout follow-up for integration into main.
2. Agree physical ESP HTTP/sensor contracts and Pi acceptance; owner unassigned.
3. Connect real assessment and authenticated console transport/response bindings.
4. Extend trusted permissions/cache activation, audit delivery and execution authority.
5. Complete frozen-model export/load and operator/recovery acceptance.

## Verification and limits

Fresh integrated check: 265 Python tests passed, zero skips (16.872 seconds), including
first-light and path regressions. Mock ESP required permitted local-loopback access.
Four console launcher tests passed. Active documentation links/headings, mapped
preservation, runtime-byte comparisons and Git whitespace checks passed.
Earlier npm check (64 frontend tests, typecheck/lint/build), lab replays and five
Chrome browser scenarios remain historical; unchanged frontend suites were not rerun.
No new native/camera/live-enterprise/Pi acceptance or private model provisioning.
[Combined evidence](docs/handoffs/2026-09-05-team-layout-review.md) ·
[First-light scope](docs/reports/2026-09-05-pi-backend-status.md).

## Start here

[Rules](AGENTS.md) · [README](README.md) · [Architecture](architecture.md) ·
[Docs](docs/README.md) · [Tracker](docs/implementation-tracker.md) ·
[Scripts](docs/scripts/README.md)
