# Checkpoint before presentation-only Face ID redesign

Preserved on 2026-09-06 before the scoped Motion/Anime.js redesign.
See [working rules](../../AGENTS.md) and [current status](../../current.md).

# Current
Updated: 2026-09-06 EDT.
Baseline: local `5bb092a`; origin/main `e1e7506`; upstream/main `237c307`.
Branch: `codex/dashboard-visual-refinements` in the original checkout.

## Active objective

Runtime bridge outage diagnosed and restored at user request. The Dock app now
shows FEED LIVE with its existing user still signed in. Previous Face ID/glass,
account-menu, visual and device-clock work remains in place. Owners unassigned.
No push, merge, remote deployment or physical hardware action.

## Current state

- The configured feed is the earlier local rehearsal with a mock controller.
  Its runtime/bridge had stopped while the Dock app retained their address.
- Added safe `native_review_demo --resume` for existing private sessions: fixed
  ports/keys/history, no new requests, and no dependency on open stdin.
- Existing rehearsal resumed on runtime56255/bridge56256. All22 events and the
  session descriptor are unchanged; native displays4 requests and ledger22.
- Fresh mock controller starts off with zero commands. Old observations remain
  historical; no controller commands were replayed. `.env` is unchanged.
- Face service8766 remains configured; native app was not rebuilt or restarted
  for bridge recovery. Prior changes stay uncommitted on the same local branch.

## Evidence and limits

Recovery helper suite15 passed; compilation/whitespace checks passed. Authenticated
feed HTTP200, exact retained-event comparison and SQLite quick_check passed.
Native FEED LIVE verified04:37. [Recovery evidence](../reports/2026-09-06-runtime-bridge-recovery.md).

Historical Face ID validation: frontend167/scripts8/Rust61 (2ignored)/Python177,
all26 browser regressions and native build/launch passed. [Face ID evidence](../reports/2026-09-06-face-id-fixes.md).
Real-camera head-circle/PAD and physical-Pi acceptance remain untested. This local
backend must be resumed after process/Mac restart; no system startup service added.

## Next steps

1. User checks enrollment and login on their actual camera.
2. Review local changes; configured rehearsal is available.
3. Connect physical Pi or publish/merge/deploy only when explicitly requested.

[Rules](../../AGENTS.md) · [Tracker](../implementation-tracker.md) ·
[Resume guide](../guides/native-runtime-review.md#resume-a-stopped-local-rehearsal) ·
[Previous checkpoint](../handoffs/2026-09-06-before-runtime-recovery.md)
