# Presentation-only Face ID redesign — 2026-09-06

Scope: only Face ID login and enrollment, following the user's final clarified
request. Work remains uncommitted on `codex/dashboard-visual-refinements`, baseline
`5bb092a`. All previous authorized changes were retained. No push or remote deployment.
[Working rules](../../AGENTS.md) · [Sources/licenses](../guides/console/visual-sources.md).

## Result

Both interfaces share a larger 16:9 camera, quieter dark glass chrome, multilayer
scanner, vignette and short changing status copy. Motion supplies layout, counters,
AnimatePresence copy transitions and a local Motion Primitives Morphing Dialog/Popover
adaptation. Transition Panel resizes persistent content without keying the camera.
A blank noninteractive surface morphs from the initiating control and reverses where
that control remains visible; it never contains camera frames. Closing/cancellation
immediately removes capture, independently of any remaining decorative chrome.

Anime.js draws eight sparse illustrative contour points only after native quality
PASS, then fades them inward and morphs the completed ring into a check. The contract
contains no camera-space landmark coordinates; these are explicitly decorative,
not measured tracking. The success sequence finishes in400ms inside the existing450ms
acknowledgement (60ms reduced motion). Animation completion never authenticates,
accepts evidence, retries, cancels, or closes the application flow.

Enrollment displays all seven required poses, exact accepted regional counts,
accepted observations, angles/7 and samples/14. Only count2 completes a pose.
Required-region emphasis follows native LOOK/HOLD prompts or the existing initial/
last required region. Login has no pose indicators; its ring reflects discrete
native states, not a confidence percentage. Moving highlights exist only during
EVALUATING. Green appears only on authoritative SUCCEEDED. Reduced motion uses
static results; errors fade/retract and retain all existing recovery actions.

## Behavior preservation

A before-edit snapshot is retained privately at
`/private/tmp/alice-premium-face-id-baseline-20260906` (116 files).
CameraCapture's entire lifecycle effect compares byte-identical with that snapshot:
SHA256 `6d912a26379ea370de68c5e79d72cb2bec8d4eddabf4af245aace48621bb63c0`.
Independent AST review found all existing CameraCapture, IdentityPanel and AdminPanel
handlers/effects unchanged. Hash comparison confirms34 native, biometric-service and
contract source files unchanged. Original approval scanner and presentation remain
unchanged; shared TransitionPanel size animation is opt-in only for these two flows.

No detector, camera acquisition, preview polling, mirroring/containment, pose policy,
backend state, authentication decision, cancellation rule or success timer changed.
No configuration, identity database, enrollment, model, token or runtime data was edited.

## Verification actually run

- `npm run check`: typecheck, ESLint,177 frontend tests,8 script tests, production web
  build passed. Final log `/tmp/alice-premium-check-final.log`.
- `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e`: all28 integrated browser
  regressions passed in26.0s. Final log `/tmp/alice-premium-browser-28.log`.
- Browser tests verify both actual dialog components fit without scrolling at
  760×640,1280×720 and390×844; retained image DOM identity; exact native evidence;
  no success from full coverage alone; cleared preview on terminal/cancel; failure,
  retry, native-result-before-parent-completion, reduced motion and Escape while
  opening. Existing approval/review/account regressions remain included.
- Synthetic screenshots were visually inspected in `artifacts/console/premium-face-id/`.
  They contain generated fixture pixels, no camera photos or biometric data.
- `npm run build:app` passed, native release18.51s; bundled binary matches release
  binary with `cmp`. Final log `/tmp/alice-premium-native-build.log`.
- Dock preference verified the exact bundle below. Existing app backed up under
  `/private/tmp/alice-before-premium-face-id-20260906/ALICE.app` in a private directory.
  Rebuilt app reopened; fresh native AX at05:08 shows the normal signed-out screen.
  Process82870 verified running from that bundle, start05:08:00.
- Local face service8766 and rehearsal runtime56255/bridge56256 remain listening,
  same preexisting processes. No service restart or runtime request was submitted.
- `git diff --check` and final source-preservation comparisons passed.

Dock bundle:
`apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`.

The existing Vite large-chunk warning remains non-failing. Browser visual evidence
uses synthetic native IPC and camera imagery. Real-camera enrollment/login acceptance
and native WKWebView animation appearance require the user's next normal use; no
biometric session was started on the user's behalf. Rust/Python suites were not
repeated for this presentation-only change; source hashes are unchanged and native
compilation passed. Their earlier results are historical in the preceding report.

[Previous Face ID fixes](2026-09-06-face-id-fixes.md) ·
[Runtime recovery](2026-09-06-runtime-bridge-recovery.md) ·
[Previous checkpoint](../handoffs/2026-09-06-before-premium-face-id.md).
