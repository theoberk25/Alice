# Merge handoff: all local changes since included PR #5

2026-09-06. Start here after [AGENTS.md](../../AGENTS.md) and
[current.md](../../current.md). This condenses the task context; source and tests
remain authoritative. User requested preparation only. No merge, fetch, commit,
push, deployment or repository replacement was performed for this handoff.

## Exact boundary and complete transfer

- Source: `/Users/alexdaoud/Documents/Alice`, branch `codex/dashboard-visual-refinements`.
- Last merged PR carrying this console work: [team PR #5](https://github.com/theoberk25/Alice/pull/5),
  merged2026-09-06T06:00:47Z, baseline `e1e75068bee7f5f990284b4f0e727571d0d288f0`.
- [PR #6](https://github.com/theoberk25/Alice/pull/6), the visual redesign, was CLOSED,
  **not merged**, at07:14:02Z; its head was `79c26506c4146f9ebe2b73367c279dd143f36044`.
  Include its entire implementation, not just changes made after it closed.
- Local HEAD: `5bb092a17215111c3277492cde1b3ed0a22ef783`:15 local commits after baseline.
  Most later work is **uncommitted**, with essential **untracked** files. A HEAD-only
  cherry-pick/diff or tracked-files-only copy is incomplete.
- Inspected team ref: `upstream/main` pinned at
  `45312778b802b95488015b673ba1bd30b0b15f88`:16 team commits after the same merge-base.
  Remote `upstream` is `theoberk25/Alice`; `origin` is `Adaoud03/Alice` and its cached
  main is still the PR #5 baseline. Target checkout/path has not been selected.
  Verify the actual target revision again when integration is authorized.

Portable export (ignored, copy it explicitly when moving repositories):
`artifacts/console/merge-handoff/20260906/alice-since-pr5-20260906.zip`.
It includes the complete cumulative patch, every changed/new file's current bytes,
checksums, Git base/HEAD blob IDs, all15 local commit records and this guide.
`manifest.json` is the exhaustive file inventory; there are no secrets, environments,
models, database contents, build products or archived-document contents in the export.

Use **since-pr5.patch** to inspect/port the cumulative result. **after-local-head.patch**
is a separate provenance alternative; do NOT apply it after the cumulative patch.
The export is a snapshot, not a commit: later edits require regeneration. Originals
remain intact in this checkout. Never overwrite newer files wholesale to resolve conflicts.

## Change groups to carry

| Group | Final behavior and principal paths |
| --- | --- |
| Committed PR #6 redesign | `package.json`/lock add Motion and Anime.js; `packages/ui/src/{index,motion,motion-tokens}.tsx/ts` supply shared primitives. `main.tsx`, tokens/shell/workspace CSS, App, navigation, command rail, agents/history/audit, decisions/research/evidence, runtime/status and identity/approval surfaces have coordinated visual changes. Preserve all paths in the manifest, including those unchanged since local HEAD. |
| Dashboard refinements + clock | `layout/dashboard-clock.ts` and Header use device IANA timezone, consistent date/time/DST label, static digits and refresh on tick/focus/pageshow/visibility. Other audit/event timestamps retain existing semantics. App/styles quiet duplicate selection/motion, improve contrast, responsive admin rows and rail clearance. |
| Enrollment discard correctness | Native `security.rs` Technician adds serde-default `enrollment_pending`; `commands.rs` derives it from activation/removal intents. Mirror optional field in `state/console.ts` and strict `packages/contracts/src/biometrics.ts`. Admin offers discard only for real pending state, gives success feedback and preserves lost-ACK retry. Keep generation-bound removal protocol and technician records. |
| Pose/final-angle fix | `services/biometrics/app/pose.py` limits diagonal hysteresis retention to near-neutral CENTER, preserving valid cardinal views. `sessions.py` tracks current accepted region and sends LOOK_/HOLD_ for the last missing region; interruption clears hold cue, not enrollment progress. Preserve all thresholds and security checks. |
| Signed-in account behavior | Header offers Change user/Sign out. Change user awaits native logout, commits the replacement trigger and restores focus before opening a blank claim form; failed logout retains user. IdentityPanel exposes session actions when already authenticated. `biometric_commands.rs` rejects LOGIN while a valid technician session exists, permits expired-session reauthentication. |
| Runtime resume | `scripts/lab/first_light/native_review_demo.py --resume /absolute/session.json` validates and reuses an existing private rehearsal's ports, keys, descriptor and ledger. No requests/keys/history reset or replay. SIGINT/SIGTERM wait survives stdin EOF. Fresh mock controller starts off/zero commands. This fixes a stopped local development bridge; it is not physical-Pi connectivity. |
| Latest Face ID presentation | New `FaceIdMorph.tsx`, `FaceIdPresentation.tsx`, `FaceIdScan.tsx`, `face-id-morph.css`, `face-id-scan.css`, `face-id.css`; integrated in CameraCapture, IdentityPanel and AdminPanel. LOGIN/ENROLLMENT only: larger fixed16:9 contained/mirrored camera, quieter liquid-glass-derived chrome, Motion Primitives morph/Transition Panel, AnimatePresence copy, native-driven rings/pose counters, Anime contour/check drawing. Approval keeps the earlier scanner. |
| Tests/docs | Include all new/modified console unit/e2e files, Playwright test registration, Python biometric/helper tests, native inline tests, design licenses and dated evidence. Reconcile target docs index/current/tracker; retain SUP-04/SUP-12 history rather than replacing newer rows. |

The latest Face ID request supersedes older visual restrictions on decorative
contours/scanning **only for login/enrollment**. It does not revert the earlier
functional fixes or authorize new biometric logic. Motion13.2.0 and Anime.js4.5.0
are installed (MIT); no additional framework or paid component was introduced.
Keep the full Motion Primitives and liquid-glass-react license notices in
[visual sources](../guides/console/visual-sources.md).

## Invariants during conflict resolution

- Renderer never captures/selects authentication frames, grants authority or infers
  acceptance from animation/time. SUCCEEDED is authoritative; full coverage alone is
  insufficient. Login has no head-turn requirement or pose UI.
- Enrollment retains Center/Left/Right/Up/Down/Upper left/Upper right, two accepted
  samples each,500ms spacing, calibration, identity consistency, PAD and all limits.
  Coverage sum/14, count-of-regions-at2/7 and backend accepted_samples are distinct.
- CameraCapture starts once per intent/attempt, preserves its img node, uses independent
  sequential preview/status polling, rejects stale/wrong-session results, clears src
  on stop/terminal, cancels late-created sessions and cleans up immediately on hide/unmount.
- Existing onComplete runs immediately on authoritative success. Existing visual
  acknowledgement450ms/60ms reduced and IdentityPanel's120ms close remain; animations
  never call authentication, retries, cancellation or completion handlers.
- New contour points are explicitly illustrative: contract has no landmark coordinates.
  Reveal only on native quality PASS; moving highlight only EVALUATING; green only
  SUCCEEDED. Anime success ends400ms; reduced motion is static.
- Morph chrome contains no camera/text/controls. Capture unmount is never deferred by
  AnimatePresence. Native dialog focus/Escape/disabled rules remain caller-owned.
- Preserve backend decision immutability, exact action/target/identity binding,
  replay/uncertain-delivery reconciliation and fail-closed authorization.

Latest presentation-only pass left34 native/service/contract source files unchanged
against its private116-file snapshot at `/private/tmp/alice-premium-face-id-baseline-20260906`.
CameraCapture lifecycle comparison was byte-identical; existing handlers/effects were
also checked independently. This is evidence about that pass, not permission to
replace newer target controllers with older ones.

## Known conflicts in the inspected newer team tree

Seven overlapping paths across the cumulative source changes and team delta:
App.tsx, state/console.ts, RuntimeReview.tsx, tests/console/e2e/runtime-review.spec.ts,
current.md, docs/README.md and docs/implementation-tracker.md. No new-file path
collisions at pinned4531277. Recompute this against the eventual target.

Retain the team's **Request more context** action/handler, contextRequests/requestContext
state, current-HOLD/non-DENY/auth/challenge/duplicate/remote guards and rollback.
Our console state field is additive. Check the command rail with all five actions;
new team global.css context-button rules must survive our later shell.css cascade.

Retain newer fan-request schema unions, schema_version-dependent ISSUED versus
SIMULATED FAN/RUN display, assessment/model/reason-code fields, Rust runtime review
and team tests. Taking our entire RuntimeReview would lose fan support and can break
issued_at typing. Team already includes native prerequisites7e2b977/5c9644b through
PR #5, but lacks our Motion/Anime dependencies and shared motion modules.

## Integration and acceptance

When authorized: choose/pin the actual newer target, preserve both dirty checkouts,
create an isolated `codex/` integration branch, port cumulative changes by the groups
above, and resolve behavioral/contract conflicts against the newer target. Reconcile
package dependencies/lockfile; do not replace a newer lockfile blindly. Apply current
presentation atop newer handlers rather than downgrading them. Inspect the complete
manifest afterward so no new files/tests/licenses are missed.

Run Node22+, Python3.11 and Rust stable checks on the integrated tree:
`npm run check`; `npm run test:rust`; `npm run test:python`;
`.venv/bin/python -m pytest tests/test_native_review_demo.py -q`;
`ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e`; `npm run build:app`.
Use the target's corresponding commands if its tooling has legitimately changed.

Historical source-checkout results:177 frontend +8 script tests, all28 browser
regressions, typecheck/lint/web/native build passed; earlier functional Rust61 passed
(2 opt-in ignored), Python177 passed; runtime-resume15 passed. These are **not merged-tree
acceptance**. Browser camera/IPC are synthetic. Real-camera angle/PAD and native
animation appearance still need user acceptance. Existing bundle-size warning is non-failing.

## Local operations; do not migrate as repository data

Dock currently points into this old checkout:
`apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`.
A build in another repository will not update that Dock target automatically.
Latest app was rebuilt/reopened05:08; prior bundle backup is private under
`/private/tmp/alice-before-premium-face-id-20260906/ALICE.app`.

At last check, face service8766 and local rehearsal runtime56255/bridge56256 were
running. Rehearsal descriptor: `/private/tmp/alice-native-personal-20260906-01/session.json`;
resume through the existing helper/runbook only if needed, with no reseeding.
Keep local `.env`, Library/Application Support identity DB, models, keys and environments
out of patches and intact on this Mac. Port1421 belongs to another checkout; do not
stop it. Process IDs/temporary files may expire; inspect before acting.

Detailed evidence: [initial redesign](../reports/2026-09-06-console-visual-overhaul.md),
[refinements/clock](../reports/2026-09-06-dashboard-visual-refinements.md),
[functional Face ID](../reports/2026-09-06-face-id-fixes.md),
[runtime recovery](../reports/2026-09-06-runtime-bridge-recovery.md),
[latest presentation](../reports/2026-09-06-premium-face-id.md).
