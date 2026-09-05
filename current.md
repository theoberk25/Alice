# Current

Updated: 2026-09-05
Baseline: `ce617cf` (main and locally available origin/main at session start).
Delivery: user authorized commit to local main; not pushed or deployed.
Implementation branch: `codex/technician-console-layout`.

## Current objective

Technician-console migration into the shared repository layout is complete;
workstation/ is removed. Start with [AGENTS.md](AGENTS.md).

## Current state

- Console source now lives in apps/desktop, packages and services/biometrics.
- Scripts are in scripts/console and scripts/biometrics, with checkout discovery.
  npm commands run at the root; tests are under tests/console.
- Console docs use the shared topic folders. Legacy empty scaffolds are preserved
  under apps/dashboard, services/backend and services/face_verification.
- Private settings, dependencies, environments, models and runtime data moved
  safely; ignored local files remain uncommitted. All 369 tracked files survive.
- Lab tools remain in scripts/lab with public lab.* imports; Pi runtime in dcamr.
- Product totals remain 12 done components, 35 partial and 71 planned tasks.
  [Tracker](docs/implementation-tracker.md); live integration remains unfinished.

## Next steps

1. Review the [complete move map](docs/handoffs/2026-09-05-console-layout.md).
2. Use root npm commands and the [console guide](docs/guides/technician-console.md).
3. Connect trusted permissions, technician transport and execution to assessments.
4. Bind the assessment contract to the durable ledger adapter.
5. Complete model export and real sensor/Pi acceptance; owners unassigned.

## Blockers and decisions

- No layout blocker. Live camera acceptance, remote approval proof, authority
  transfer and protected execution remain separate integration work.
- Local core venv lacks cryptography; regression used the existing biometric
  Python 3.11 site-packages via PYTHONPATH, without installing dependencies.

## Verification

64 Vitest, 4 relocation, 14 default Rust, 11 biometric Python, 5 Playwright and
257 core tests passed. Real public-image ArcFace and isolated native identity
checks passed. Frontend and native ALICE.app builds passed. Nine generated
schema/fixture objects match the original; published bytes remain unchanged.
[Commands, limitations and move map](docs/handoffs/2026-09-05-console-layout.md).
Prior lab migration evidence is [historical](docs/handoffs/2026-09-05-lab-script-relocation.md).

## Start here

[Rules](AGENTS.md) · [Docs](docs/README.md) · [Scripts](scripts/README.md)
