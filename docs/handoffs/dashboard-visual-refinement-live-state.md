# Dashboard visual refinement live state

Updated: 2026-09-06 EDT. Follow [working agreements](../../AGENTS.md),
[approved specification](dashboard-visual-refinement-spec.md), and
[validation record](../reports/2026-09-06-dashboard-visual-refinements.md).

## Recovery and scope

Worktree: `/Users/alexdaoud/Documents/Alice`; local review branch
`codex/dashboard-visual-refinements`; starting baseline `5bb092a`.
Available local upstream/origin main revision: `e1e7506`; no fetch, push, merge or
publication performed. Prior redesign remains on local main/in its separate worktree;
PR #6 remains closed. Changes are uncommitted for review. Owners unassigned.
After interruption, reread instructions/specification/this handoff, inspect Git
status/diff and relevant current source before continuing.

## Completed decisions

- Stable responsive 16:9 viewport for startup/live/processing/results/errors; full
  image containment and mirroring. No frame retention or camera/controller remount.
- Instruction first with immediate text/160 ms presentation fade; remaining-pose
  label and stronger incomplete chips; neutral/cyan ring with finite 220 ms feedback.
- Exact arc mapping, coverage sum/14 and completed-angle count preserved. Backend
  accepted observations remain separate. Existing Face ID checks remain available.
- Terminal text appears immediately while unchanged parent completion proceeds;
  original 450/60 ms acknowledgment timing, cancellation and action handlers remain.
- Single 180 ms navigation surface, modest native dialog fade, no content/height
  tween or clipping around form/camera controllers. No moving border beams.
- Clearer secondary text/history selection, aligned admin identity/status/actions,
  solid rail separation and focus clearance. Admin fallback handles 520 px as well.
- Dashboard-only clock uses current system time/device-resolved zone every tick and
  focus/pageshow/visible refresh; h23 midnight, DST and consistent date/time/zone.
  Clock, confidence and evidence values use static digits; other timestamps unchanged.

## Changed files

- Clock: `apps/desktop/src/components/layout/{Header.tsx,dashboard-clock.ts}`.
- Biometrics: `components/biometrics/{CameraCapture.tsx,BiometricScan.tsx,biometrics.css,ApprovalModal.tsx}`
  within `apps/desktop/src/`; persistent identity wrapper: `components/technicians/IdentityPanel.tsx`.
- Dashboard: `apps/desktop/src/app/App.tsx`; technician `AdminPanel.tsx`, decision
  `DecisionWorkspace.tsx`, evidence `EvidencePanel.tsx`; `styles/{tokens,shell,workspace}.css`.
- Shared UI: `packages/ui/src/{index.tsx,motion.tsx,motion-tokens.ts}`.
- Tests: `tests/console/{dashboard-clock.test.tsx,live-biometrics.test.tsx,biometric-presentation.test.tsx}`,
  `tests/console/e2e/visual-refinements.spec.ts`, and `playwright.config.ts`.
- Documentation: this handoff/specification, dated validation report, visual-sources
  guide, docs index, tracker, current snapshot and preserved pre-refinement checkpoint.

## Verification and limitations

Final `npm run check`: typecheck/lint/build passed, frontend 163 and scripts 8 passed.
`ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e`: all 20 passed.
`npm run test:rust`: 60 passed/2 opt-in ignored after sandbox localhost retry.
`npm run test:python`: 166 passed. Exact intermediate failures/warnings are recorded
in validation. Camera effect/action regions compare byte-identical to baseline;
no backend, contracts, state, feature service or manifest/lockfile differences.
Motion 13.2.0/MIT and existing local MIT Motion Primitives reused; no new dependency.
Anime.js 4.5.0/MIT remains installed but is no longer imported by the biometric ring.

Baseline/after synthetic screenshots and geometry live in ignored
`artifacts/console/visual-refinements/`. Viewport/instruction/Cancel are stable within
1 px at 1512×1040, 1280×720, 1024×844, 800×844 and 390×844. Baseline camera switched
520×390 →520×292.5 →520×148 on error; the first switch moved Cancel 97.5 px.
No recording was attached; no human camera, physical Pi, real Ollama, OS sleep/zone
setting change, deployment or native bundle replacement was exercised. Installed
Chrome was used because Playwright's bundled headless executable is unavailable.

## Next action

Local review preview is running at `http://127.0.0.1:1420/` (mock browser mode).
Review this local branch. No implementation blocker remains; real camera/native and
physical acceptance remain separate from synthetic/component evidence. Publish,
merge or deploy only on a new explicit user instruction.

## Dock app update — user-authorized follow-up

On 2026-09-06, user requested these changes in the Dock-linked app. Confirmed Dock
path is `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app` in this checkout.
Preserved old bundle at `/tmp/alice-before-refinements-20260906.app`;
`npm run build:app` succeeded (release and app bundle), then quit old process and
reopened via `npm run launch:app` with existing configuration. Native accessibility
verified `tauri://localhost`, live feed and EDT with America/New_York at 03:58 EDT.
Existing settings/enrollment stores were not edited. User resumed interacting with
the app; no further UI actions performed. No push, merge or remote deployment.
