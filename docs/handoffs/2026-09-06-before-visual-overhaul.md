# Pre-redesign checkpoint

Preserved 2026-09-06 before the presentation-only redesign. This is the previous
session snapshot, including its historical tests and then-pending publication status.
Team PR #5 is now merged at `e1e7506`; use [current status](../../current.md) and
[visual validation](../reports/2026-09-06-console-visual-overhaul.md).

# Current
Updated: 2026-09-06 EDT.
Baseline: freshly fetched Theodore Berk `upstream/main` at `966632e`.
Everyday checkout: `/Users/alexdaoud/Documents/Alice`; branch `codex/native-live-backend`.

## Active objective

Native backend integration is the active major project. Locally implemented: collected request
and audit visibility, exact supplied details, immutable decisions, fresh-face
approve/reject of eligible OFFLINE ALICE-owned HOLDs, and separate acknowledgment,
execution and observation. No deepfake work or device-output adjustments.

## Current state

- Root is the sole registered worktree. Original biometric/WIP and verified source
  snapshots remain on named backup branches; private settings/models are preserved.
- Biometric PR #4 merged at `d57c660`; local commits now include the subsequent
  upstream wireless/fan roadmap and pitch deliverables. No duplicate biometric commits.
- Published to `Adaoud03/Alice:main` at the user's request; upstream [PR #5](https://github.com/theoberk25/Alice/pull/5)
  contains the implementation, evidence and limitations. Upstream merge is pending.
- Native/web share collected history, evidence and explicit freshness. Native adds
  exact retained requests and signed fresh-face approve/reject through the existing
  bridge, Pi ledger and execution path, with durable uncertain-delivery reconciliation.
- The built app is open for a local personal rehearsal with the existing enrollment;
  real facial service is ready. Controller/assessment are labeled mock/fixture.
  Dock/Finder launches now use the same saved remote settings; sign-in starts the feed.
  `npm run demo:hold -- --session /private/tmp/alice-native-personal-20260906-01/session.json`
  sends another signed, unexecuted test HOLD; final helper checks: 12 passed.
- Working scope is first-light `set_light_state`, fixed OFFLINE ALICE authority.
  Enterprise handover/reads, live brief/model factors and fan adapters remain upstream
  integration work. Device adjustments stay deferred. Owners are unassigned.

## Evidence and limits

Core: 435 passed and 266 subtests. Biometrics: 166 passed. Rust: 60 passed plus
one opt-in real Rust→Python bridge/runtime test; approve/reject/replay produced one
mock command. Frontend: 134 tests plus eight script checks; eight UI E2E and one
real web/runtime E2E passed. Typecheck, lint, web/native builds passed.
Cross-language proofs, cancellation, replay, restart, concurrency and uncertainty
have automated evidence. No human camera→Pi/hardware acceptance or live Ollama test.
Telemetry covers collected ALICE request/audit traffic, not every network packet.
Verified preservation includes the concurrent Desktop auto-stash recovery; tracked
source is committed and published to the fork. No upstream merge, deployment,
remote trust provisioning or hardware operation was performed.

## Next steps

1. Personally test fresh login, approve, reject and cancellation in the local rehearsal.
2. After separate authorization, configure reviewed Pi trust and record physical acceptance.
3. Coordinate enterprise authority/feed, real model/context and fan contracts before
   implementing the broader [upstream demo](../guides/demo-runbook.md).

[Rules](../../AGENTS.md) · [Tracker](../implementation-tracker.md) ·
[Workspace recovery](2026-09-06-native-live-backend-workspace.md) ·
[Ready handoff](2026-09-06-native-live-backend-ready.md) ·
[Parity](../plans/native-live-backend-parity.md) ·
[Validation](../reports/2026-09-06-native-live-backend-validation.md)
