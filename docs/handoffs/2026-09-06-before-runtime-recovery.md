# Checkpoint before runtime recovery

Preserved before the user requested restoration of the disconnected runtime feed.

# Current
Updated: 2026-09-06 EDT.
Baseline: local `5bb092a`; available `upstream/main` / `origin/main`: `e1e7506`.
Branch: `codex/dashboard-visual-refinements` in the original checkout.

## Active objective

User-requested Face ID/discard fixes, focused glass dialogs and signed-in account
controls implemented locally; Dock-linked ALICE.app rebuilt and reopened.
Previous approved visual refinements and device-local clock preserved.
No push, merge or remote deployment. Owners are unassigned.

## Current state

- Discard appears only for native-reported pending enrollment; successful removal
  is acknowledged, while lost-ack recovery remains available. Identity records remain.
- Diagonal hysteresis no longer masks valid cardinal views during head circles.
  The last angle has direction/hold guidance; all evidence thresholds remain.
- Enrollment/login use compact Face ID dialogs adapted from MIT liquid-glass-react
  frosted/highlight layers, with Motion transitions and reduced-motion support.
- Signed-in users get Change user / Sign out in the top-right account menu.
  Change user logs out before opening login; native login rejects active sessions.
- Updated local face service reports READY with identity/pose/PAD PASS. Rebuilt
  native app reopened with existing configuration and enrollment stores.
- All prior and current changes remain uncommitted on this feature branch.

## Evidence and limits

`npm run check`: frontend167, scripts8, typecheck/lint/build passed. Rust61 passed
(2 opt-in ignored); Python177 passed; all26 browser regressions passed. Actual
camera dialogs fit without scrolling at760×640,1280×720,390×844. Native build/launch
passed; native identity form and then authenticated account menu observed. [Validation](../reports/2026-09-06-face-id-fixes.md)
records findings, commands, source choices and warnings. Browser camera evidence
is synthetic; real-camera head-circle/PAD and physical-Pi acceptance remain untested.
The separate runtime bridge currently reports unavailable; no bridge settings changed.

## Next steps

1. User checks enrollment and login on their actual camera.
2. Review local changes; no implementation blocker remains.
3. Publish/merge/deploy only with explicit authorization.

[Rules](../../AGENTS.md) · [Tracker](../implementation-tracker.md) ·
[Previous checkpoint](../handoffs/2026-09-06-before-face-id-fixes.md) ·
[Visual sources](../guides/console/visual-sources.md)
