# Main repository redesign integration

2026-09-06. Follow [working rules](../../AGENTS.md) and [current status](../../current.md).

## Exact revisions and preservation

The user authorized committing the complete local redesign, fetching Theo's latest
main and integrating presentation over newer teammate behavior. This supersedes
preparation-only language in the earlier handoff; it does not authorize publication.

- Common ancestor / merged PR #5: `e1e75068bee7f5f990284b4f0e727571d0d288f0`.
- Original local HEAD: `5bb092a17215111c3277492cde1b3ed0a22ef783`.
- Complete source preservation commit: `db730710750787af9064b495c6a236e0b504b2fe`.
  It commits all 60 previously modified/new files, including the 21 untracked files.
- Fresh `git fetch upstream main` returned `45312778b802b95488015b673ba1bd30b0b15f88`.
  Remote is `https://github.com/theoberk25/Alice.git`; 16 team commits after PR #5.
- Isolated branch: `codex/main-redesign-integration`, based on that team revision.
  Worktree: `/Users/alexdaoud/Documents/Alice/artifacts/console/main-redesign-integration`.
- Source branch `codex/dashboard-visual-refinements` preserves the complete design.
  Older overhaul worktree is clean, with no additional visual bytes missing from it.

This is a true merge retaining both ancestries. The original checkout, ignored
configuration, models, identity stores, generated artifacts and running services
were retained. The integration has separate Node dependencies and build outputs;
ignored symlinks reuse only existing Python environments and Rust toolchains.
No private configuration, models, stores or build bundles are committed.

## Reconciliation

Seven paths changed on both sides. Textual conflicts occurred in App, current and
tracker. Source/team checkpoints were retained as dated handoffs before reconciling
status. Both documentation indexes and all original tracker IDs/history survive.

The complete visual system is carried: Motion and Anime dependencies, typography,
shared semantic controls and motion primitives, shell/workspace styles, dashboard
clock, administration/account controls and latest login/enrollment Face ID surfaces.
The original component inventory and MIT license notices remain authoritative in
[visual sources](../guides/console/visual-sources.md).

App retains the team's context action, eligibility and request handler. Console
state differs from the team revision only by optional `enrollment_pending`; all
context-request guards, audit, challenge binding and failure rollback survive.
RuntimeReview retains version-dependent issued/fan/run/revision fields and anomaly
result, score and model content, with shared redesigned review controls/dialogs.
Its business handlers remain unchanged from the team revision.

Existing source functional fixes are preserved: local device time, pending
activation/discard handling, safe account switch/native second-login guard,
cardinal pose/final-angle coaching and private rehearsal resume. Authentication
still requires authoritative success, and animations do not invoke business actions.
The team's thermal/fan/enterprise/firmware/backend implementation is not redesigned.
Newer MD proposals for additional dashboard pages are context, not implementation scope.

## Verification

Integrated validation is in progress. Source/team historical results are not
acceptance for this merge. Commands, results and limitations will be recorded here.

## Remaining acceptance

Browser camera/native IPC fixtures are synthetic. Real camera angle/PAD checks,
native visual acceptance and physical Pi integration need operator acceptance.
No push, deployment or Dock app replacement was performed.
