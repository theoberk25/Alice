# Checkpoint before popup-testing rebuild

Historical snapshot from integration commit `498ebcd`.
[Working rules](../../AGENTS.md) apply; see [current status](../../current.md).

# Current
Updated: 2026-09-06 EDT. Owners unassigned.
Branch: `codex/main-redesign-integration`.
Team baseline: `d5a0d56f69b007e388b5a4c49b00b363b7bd0f25` (latest fetched main).
Initial integration checkpoint: `4b1f67e`, based on previous team main `4531277`.
Preserved redesign: `db730710750787af9064b495c6a236e0b504b2fe`.

## Active objective

Integrate the complete local redesign onto Theo's current main while preserving
all teammate content, contracts and behavior. Local integration and validation complete.
Worktree: `artifacts/console/main-redesign-integration` within the original checkout.
[Integration evidence](docs/reports/2026-09-06-main-redesign-integration.md).

## Scope and preservation

- Source commit includes closed/unmerged PR #6 and all later tracked/untracked work.
- Motion/Anime, themes, responsive shell, device clock, account/Face ID presentation
  and the existing narrow biometric/rehearsal fixes are carried forward.
- Team context-request guards/fifth action, fan review/schema/native additions and
  all newer thermal, enterprise, runtime and firmware implementation are preserved.
- Late telemetry alignment is included: battery units, LED roles and updated team
  docs/tracker row 035. [Team checkpoint](docs/handoffs/2026-09-06-before-telemetry-redesign-merge.md).
- The original checkout, private settings/models/stores and running services remain
  separate. No push, deployment, or replacement of the Dock-linked app is authorized.

## Evidence and blockers

Validated integrated tree: frontend190/scripts8/browser31/native62 passed;
biometrics176 passed (1 model skip), repository Python541 and266 subtests passed.
Native2 opt-in tests ignored. Typecheck/lint/web build/native app build passed.
No software blocker remains; prior source/team results remain historical.
Real-camera, physical Pi and native visual acceptance remain outside automated tests.
The pre-merge checkpoints are preserved for both
[source](docs/handoffs/2026-09-06-before-redesign-integration-source.md) and
[team](docs/handoffs/2026-09-06-before-redesign-integration-team.md).

## Next steps

1. Review `codex/main-redesign-integration` against pinned team main `d5a0d56`.
2. Perform real-camera/native appearance and physical-Pi operator acceptance.
3. Publish or replace the Dock app only on explicit user authorization.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Design sources](docs/guides/console/visual-sources.md) ·
[Original transfer handoff](docs/handoffs/2026-09-06-new-repository-merge.md)
