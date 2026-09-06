# Current
Updated: 2026-09-06 EDT. Owners unassigned.
Branch: `codex/main-redesign-integration`.
Team baseline: `4f98a14d4ef3cd16355de9d48847211ad08c91ca` (latest fetched main).
Initial integration checkpoint: `4b1f67e`, based on previous team main `4531277`.
Preserved redesign: `db730710750787af9064b495c6a236e0b504b2fe`.

## Active objective

Integrate the complete local redesign onto Theo's current main while preserving
all teammate content, contracts and behavior. Integration is complete; [PR #7](https://github.com/theoberk25/Alice/pull/7) is open for user merge. The user
requested the live-runtime app after testing. The rebuilt app is now open in
remote/ArcFace mode with the original saved database and feed. Popup profile is preserved.
[Popup setup/evidence](docs/reports/2026-09-06-popup-testing-app.md).
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
  separate. The rebuilt integration app now uses the saved live-runtime profile;
  the original Dock-linked bundle and live profile remain unchanged. No deployment.

Latest team Pi deployment, USB/Wazuh and exhausted-light behavior are retained
unchanged. [Team checkpoint](docs/handoffs/2026-09-06-before-pr-thermal-deployment-merge.md).

## Evidence and blockers

Latest upstream merge: repository Python543 and266 subtests passed.
Latest popup build: frontend192/scripts8/check and app build passed; default
browser31 plus the opt-in popup case passed. Historical popup app validation complete; real Face ID service READY.
Live profile restored and app reopened at sign-in. Saved feed HTTP200/22 events,
local-runtime with mock controller; physical Pi connection is not established.
Historical integration: frontend190/scripts8/browser31/native62 passed;
biometrics176 passed (1 model skip), repository Python541 and266 subtests passed.
Native2 opt-in tests ignored. Typecheck/lint/web build/native app build passed.
No software blocker remains; prior source/team results remain historical.
Real-camera, physical Pi and native visual acceptance remain outside automated tests.
The pre-merge checkpoints are preserved for both
[source](docs/handoffs/2026-09-06-before-redesign-integration-source.md) and
[team](docs/handoffs/2026-09-06-before-redesign-integration-team.md).

## Next steps

1. Sign in to the reopened live-runtime app to connect to the saved feed.
2. Perform real-camera/native appearance and physical-Pi operator acceptance.
3. User reviews/merges PR #7; keep the Dock app unchanged.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Design sources](docs/guides/console/visual-sources.md) ·
[Original transfer handoff](docs/handoffs/2026-09-06-new-repository-merge.md)
