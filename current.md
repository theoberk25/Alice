# Current
Updated: 2026-09-06 EDT. Owners unassigned.
Branch: `codex/main-redesign-integration`.
Team baseline: `45312778b802b95488015b673ba1bd30b0b15f88` (freshly fetched main).
Preserved redesign: `db730710750787af9064b495c6a236e0b504b2fe`.

## Active objective

Integrate the complete local redesign onto Theo's current main while preserving
all teammate content, contracts and behavior. Local merge and validation in progress.
Worktree: `artifacts/console/main-redesign-integration` within the original checkout.
[Integration evidence](docs/reports/2026-09-06-main-redesign-integration.md).

## Scope and preservation

- Source commit includes closed/unmerged PR #6 and all later tracked/untracked work.
- Motion/Anime, themes, responsive shell, device clock, account/Face ID presentation
  and the existing narrow biometric/rehearsal fixes are carried forward.
- Team context-request guards/fifth action, fan review/schema/native additions and
  all newer thermal, enterprise, runtime and firmware implementation are preserved.
- The original checkout, private settings/models/stores and running services remain
  separate. No push, deployment, or replacement of the Dock-linked app is authorized.

## Evidence and blockers

Integrated checks are running; prior source/team test results are historical only.
Real-camera, physical Pi and native visual acceptance remain outside automated tests.
The pre-merge checkpoints are preserved for both
[source](docs/handoffs/2026-09-06-before-redesign-integration-source.md) and
[team](docs/handoffs/2026-09-06-before-redesign-integration-team.md).

## Next steps

1. Finish semantic conflict review and verify all source/team paths survived.
2. Complete integrated frontend, browser, native, biometric and runtime checks.
3. Commit the local integration and record results/remaining acceptance.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Design sources](docs/guides/console/visual-sources.md) ·
[Original transfer handoff](docs/handoffs/2026-09-06-new-repository-merge.md)
