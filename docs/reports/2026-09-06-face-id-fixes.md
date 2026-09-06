# Face ID fixes and Dock app update

Date: 2026-09-06 EDT. Baseline `5bb092a`, branch `codex/dashboard-visual-refinements`.
Follow [working rules](../../AGENTS.md). This follow-up extends the previous
[visual refinements](2026-09-06-dashboard-visual-refinements.md) with functional
fixes explicitly authorized by the user. Changes remain local and uncommitted.

## Findings and implementation

- Read-only metadata inspection confirmed the reported identity had no saved face,
  activation intent or removal intent. The service held successful removal receipts.
  The old UI offered Discard pending enrollment for **every** unenrolled identity,
  including after successful removal. Native technician metadata now reports actual
  pending activation/removal state; the UI shows discard only when pending, reports
  success prominently, and retains a retry after a lost acknowledgment. The native
  generation-bound removal protocol, admin checks and identity records are preserved.
- Pose hysteresis carried diagonal labels into valid cardinal observations. At the
  native 4Hz evidence cadence this shortened the time available to capture cardinal
  samples during a circle. Hysteresis now applies near neutral only. Final-angle
  instructions use accepted native pose evidence to distinguish looking toward the
  remaining angle from holding it. Rejected/paused evidence clears the hold cue.
  Seven regions, two distinct samples per region, 500ms separation, limits,
  neutral calibration, identity consistency, PAD, sample and session bounds remain.
- Enrollment opens a dedicated native dialog. Login removes the large account
  introduction during capture. Camera, accepted coverage, explanation and Cancel
  remain visible without scrolling; optional diagnostics follow the controls.
  Enrollment now shows the confirmed saved state before its finite acknowledgment
  closes the dialog. Cancellation and failed completion are preserved.
- Selected open-source style: **rdev/liquid-glass-react** (MIT), adapted from its
  frosted backdrop and masked edge-highlight layers into the biometric stylesheet.
  The native WebKit-compatible treatment uses separate decorative layers, sharp
  camera pixels, soft shadows and rounded corners, with existing Motion fades and
  finite evidence strokes. Reduced motion and reduced transparency are supported.
  Source, adaptation boundaries and license: [visual sources](../guides/console/visual-sources.md).
- The top-right account menu offers Change user and Sign out. Change user awaits
  native logout before opening a blank claim form; errors retain the old user.
  Existing authenticated identity dialogs expose session actions only. Native
  LOGIN rejects an already valid technician session; expired sessions may sign in.
  Focus returns to the replacement Sign in trigger after the dialog closes.

## Verification actually run

- `npm run check`: typecheck, lint, **167 frontend tests**, **8 script tests** and
  production web build passed. Initial expected UI assertions were updated for
  explicit pending state, the new account menu and asynchronous cancellation.
- `npm run test:rust`: **61 passed, 2 opt-in ignored**. Includes authenticated-login
  refusal, expired-session eligibility and pending-removal metadata across lost ACK.
- `npm run test:python`: **177 passed**. Includes cardinal transitions after diagonal
  views and each possible non-center final-angle direction/hold/completion sequence.
- `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e`: **26 passed (21.0s)**.
  Actual enrollment/login dialog fixtures fit at **760×640, 1280×720, 390×844** with
  zero dialog scrolling, camera and Cancel fully in view. Previous lifecycle,
  preview geometry, reduced-motion, HOLD/DENY and runtime-review regressions pass.
  Account menu/change-user/focus restoration covered. Camera/identity IPC is synthetic.
- Screenshots inspected under ignored `artifacts/console/face-id-fixes/`.
- `npm run biometrics` started the updated configured service at loopback port8766
  with existing environment and stores. Authenticated `/live/readiness` returned
  HTTP200, READY, policy `alice.live-face.v3`, identity/pose/PAD PASS.
- `npm run build:app`: release build and app bundle succeeded (19.73s native build).
  Previous bundle retained at `/tmp/alice-before-face-id-fixes-20260906.app`.
- `npm run launch:app`: rebuilt Dock-linked bundle reopened with existing settings;
  native `tauri://localhost` identity form observed. At04:25, the native UI showed
  an authenticated account summary after the user independently used the app.
  The separate runtime feed reported its bridge unavailable; this task did not
  reconfigure that bridge. No user enrollment was deleted
  or created by these checks. No push, merge or remote deployment.

Build retains the existing bundle-size and Zod annotation warnings; Python reports
three existing dependency/optional network-check warnings. Browser fixtures and
unit tests do not establish real-camera angle accuracy or physical PAD acceptance.
The user must exercise the updated head-circle flow on their camera to validate
that physical behavior; this session does not claim that acceptance.
