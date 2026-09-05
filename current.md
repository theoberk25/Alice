# Current

Updated: 2026-09-05
Product baseline: `84a06db` (GitHub main pulled before this migration).
Delivery: migration approved for main; see Git history for the publishing commit.

## Current objective

Consolidate ML and enterprise development tools under scripts/lab while preserving
public lab.* imports. Start each session with [AGENTS.md](AGENTS.md).

## Current state

- Implemented lab tools moved to scripts/lab; lab/__init__.py preserves imports.
- Pi anomaly/decision runtime stays in dcamr, as explicitly confirmed by Jared.
- Shared checkout-root lookup replaces fixed parent counts. Runtime schemas use
  package resources. A single launcher works from any working directory.
- Artifacts, datasets, keys and environments remain in their original locations.
- Product totals remain 12 done components, 35 partial and 71 planned tasks.
  End-to-end integration remains unfinished. [Tracker](docs/implementation-tracker.md).

## Next steps

1. Use the scripts/lab catalog and launcher for further developer tooling.
2. Connect trusted permissions, technician transport and execution to assessments.
3. Bind the assessment contract to the existing durable ledger adapter.
4. Complete lightweight model export and real sensor/Pi acceptance.

## Blockers and decisions

- No migration blocker. Use scripts/lab/run.py from outside the repository;
  python -m lab.* remains supported from the root.
- Live authority, application decision/enforcement contracts and sensor limits
  remain integration work. [Workflow](docs/handoffs/core-workflow-wip-handoff.md).

## Verification

`python3 -m unittest discover`: 257 tests passed, zero skips. New tests use a
copied checkout with spaces and an unrelated cwd, verify replay/training paths,
console assets and byte-identical generation of 28 published enterprise payloads.
No live deployment was performed. [Move map](docs/handoffs/2026-09-05-lab-script-relocation.md).

## Start here

[Rules](AGENTS.md) · [Docs](docs/README.md) · [Scripts](scripts/README.md)
