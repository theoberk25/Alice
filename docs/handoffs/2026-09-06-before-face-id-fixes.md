# Checkpoint before Face ID fixes

Preserved on 2026-09-06 before the user-authorized functional follow-up.

# Current
Updated: 2026-09-06 EDT.
Baseline: local `5bb092a`; available `upstream/main` / `origin/main`: `e1e7506`.
Branch: `codex/dashboard-visual-refinements` in the original checkout.

## Active objective

Approved [visual refinements](../handoffs/dashboard-visual-refinement-spec.md)
and device-local dashboard clock implemented and verified locally, ready for review.
Existing security/business behavior, biometric lifecycle/dismissal timing and other
timestamps preserved. Dock-linked app updated at user request; no push, merge or
remote deployment. Owners are unassigned.

## Current state

- Stable camera viewport, instruction/remaining-pose hierarchy, exact neutral/cyan
  ring feedback and immediate result presentation without controller changes.
- Restrained navigation/dialog motion, clearer history/admin surfaces and rail clearance.
- Dashboard clock uses current device time/zone, h23 midnight, automatic DST and
  immediate resume refresh. No dependencies added; Motion/MIT patterns reused.
- Changes remain uncommitted on the local feature branch. Prior redesign stays on
  local main/in its separate worktree; PR #6 remains closed. Main was not pushed.
- Dock-linked native ALICE.app rebuilt and reopened at user request. Native UI
  verified device-local EDT / America/New_York and live feed. Existing configuration
  and enrollment stores were not edited. Synthetic screenshots and geometry remain
  under ignored `artifacts/console/visual-refinements/`.

## Evidence and limits

Prior refinement checks: frontend 163 + scripts 8; typecheck/lint/build passed. Rust 60 passed,
2 opt-in ignored; Python biometrics 166 passed. All 20 browser regressions passed.
Viewport/instruction/Cancel stable within 1 px at five window sizes through tested
startup/live/processing/results. [Validation](../reports/2026-09-06-dashboard-visual-refinements.md)
records commands, source invariants, synthetic scope and build/dependency warnings.
No recording, real-camera/physical-Pi acceptance, real Ollama run, physical OS
sleep/zone change or remote deployment was performed. Native `npm run build:app`
and `npm run launch:app` succeeded; native clock verified through accessibility.

## Next steps

1. Review the local branch; no implementation blocker remains.
2. Perform real-camera/native/physical acceptance separately when requested.
3. Publish, merge or deploy only with explicit authorization.

[Rules](../../AGENTS.md) · [Tracker](../implementation-tracker.md) ·
[Live state](../handoffs/dashboard-visual-refinement-live-state.md) ·
[Previous checkpoint](../handoffs/2026-09-06-before-visual-refinements.md) ·
[Visual sources](../guides/console/visual-sources.md)
