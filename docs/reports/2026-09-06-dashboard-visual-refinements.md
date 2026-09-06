# Dashboard visual refinements: validation

Date: 2026-09-06 EDT. Baseline `5bb092a`; local branch
`codex/dashboard-visual-refinements`. Follow [working rules](../../AGENTS.md),
[scope](../handoffs/dashboard-visual-refinement-spec.md) and
[recovery state](../handoffs/dashboard-visual-refinement-live-state.md).

## Evidence boundary

Browser preview and native IPC adapters use mock/synthetic evidence. The supplied
request did not include its referenced recording, so checks use 1512×1040 and
smaller supported sizes. No human camera capture, biometric model calibration,
physical-Pi acceptance, real Ollama interaction, device setting change, publication,
deployment or installed native-bundle replacement occurred.

## Baseline and presentation comparison

Ignored local screenshots live under `artifacts/console/visual-refinements/`.
`baseline/` includes operations/history/administration/identity and a synthetic
enrollment sequence. `after/` holds the refined comparisons. The camera fixture
uses an explicitly labelled synthetic rectangle, never a real biometric image.

Baseline component measurements at 1512×1040: startup viewport 520×390, live
520×292.5, error 520×148. First preview shifted Cancel by 97.5 px; introduction of
the checks disclosure also changed height. These measurements establish the actual
source of the reported layout instability, without claiming recording parity.

Refined dashboard screens inspected at 1512×1040, 1024×844, 800×844 and 390×844.
History selection has a stronger neutral/cyan surface while HOLD/ALLOW/DENY colors
remain semantic. Dialog opening retains final dimensions; navigation has one
selection surface. A focused command suggestion stays above the rail at all three
smaller sizes. Browser clock under America/New_York showed EDT with the same local
instant/date and exposed IANA zone; other timestamps still showed their existing UTC.

Populated synthetic administration rows inspected at 1512, 520 and 390 pixels
wide: enabled/enrolled, pending/no-face and disabled rows preserve labels/action
availability with no horizontal overflow. A review caught the intermediate-width
grid minimum; moving its responsive fallback to 600 px resolved it.

All nine new biometric/administration browser regressions pass in the complete
20-test run. Across startup, live preview, last remaining angle, processing,
native terminal result with the parent callback pending, and saved result, preview
size/location, instruction baseline and cancellation row change by less than 1 px.
The same image DOM node and one begin/start remain throughout each tested session.
Terminal results clear `src` immediately; retry/cancellation never fabricate success.
Permission/disconnection error stability is verified at 1512 and 390 px; reduced
motion at 390 px has complete static feedback with no running decorative animations.

| Window | Constant biometric viewport |
| --- | --- |
| 1512×1040, 1024×844, 800×844 | 520×292.5 |
| 1280×720 (short-window rule) | 380×213.75 |
| 390×844 | 350×196.875 |

`after/geometry-<width>.json` records starting coordinates; the regression assertions
compare every subsequent stage. Screenshots depict synthetic fixtures and can catch
finite drawing/fade transitions in progress; they are not camera acceptance images.
Existing browser regressions cover HOLD/failure/fresh retry/approval, DENY, navigation,
focus containment/return, Escape, reduced motion, native IPC review cancellation,
late results and uncertain-delivery reconciliation.

## Commands and results

| Actual command/check | Result |
| --- | --- |
| `npm run dev` | Local preview on 127.0.0.1:1420; required sandbox escalation to bind localhost. |
| Playwright baseline/refined capture via installed Chrome | Captured/inspected dashboard and synthetic enrollment baseline; default bundled headless executable was unavailable. |
| `npm test -- tests/console/dashboard-clock.test.tsx` | 14 passed. Eastern winter/summer and both DST transitions, Tokyo/Kolkata, midnight/date agreement, wall-clock jumps, zone changes, focus/pageshow/visible refresh and listener cleanup. |
| `npx vitest run tests/console/ui-motion.test.tsx` | 8 passed. Existing controls, preserved child identity/form state, native cancellation/focus containment, tooltip behavior, reduced motion and measured height. |
| `npm run typecheck` | Passed after clock/shared presentation changes. |
| Focused clock ESLint | Passed. |
| `npm run check` | Final source passed typecheck, lint, 163 tests, 8 script checks and production build. Intermediate runs caught old presentation/DOM assertions and a strict mock-result type access; adapted tests retain all lifecycle/security assertions. |
| `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e` | 20 passed in 17.6 s: 11 existing interactions plus 9 new visual regressions. |
| Focused browser runs against existing Vite | All nine scenarios passed; one run interrupted by a concurrent HMR edit was repeated successfully before the clean complete run. |
| `git diff --check`; current/handoff link and size checks | Passed; no backend/schema/state/feature/manifest/lockfile differences. |
| `npm run test:scripts` | 8 passed. |
| `npm run build` | Passed; existing Zod comment-annotation and JavaScript chunk-size advisories. |
| `npm run test:rust` | Sandbox run: 51 passed, 9 failures caused by blocked localhost fixtures/poisoned fixture mutexes, 2 ignored. Rerun with localhost access: 60 passed, 2 opt-in tests ignored. |
| `npm run test:python` | 166 passed; existing Starlette/httpx/anyio deprecation warnings and blocked optional package-version lookup (3 warnings). |

## Behavior preservation review

The CameraCapture lifecycle effect and action-handler region were compared to
baseline and were byte-identical during review. Camera/image aspect-ratio changes
and presentation layout scaling are removed; no authentication controller, IPC,
schema, state store, backend, capture timer, grant or native camera implementation
is edited. Form/camera wrappers use immediate height sizing without clipping;
new controls do not wait for a surface animation. The existing 450 ms/60 ms acknowledgment timing is unchanged and occurs
after authority completion. Native SUCCEEDED can now render verified/captured text
while the unchanged parent completion callback is still pending.

Bar value remains sum of coverage counts /14; complete angles remain regions with
two accepted samples; backend `accepted_samples` stays separately displayed. Ring
arc geometry and count/2 mapping remain unchanged. No fabricated completion,
capture order or left/right semantics are introduced.

The dashboard clock is the only functional correction. New Intl formatting resolves
the device zone each tick, samples current system time, and formats all clock parts
from that one Date/zone. Tests simulate resume/zone changes; physical OS suspension
and device-zone switching were not exercised. No network time/location API is used.

Installed Motion 13.2.0 is reused for simple SVG and shared UI presentation; existing
Anime.js 4.5.0 remains installed but is no longer imported by the biometric ring.
No manifest/lockfile changes or new dependency. MIT license evidence and retained
local Motion Primitives notice are in [visual sources](../guides/console/visual-sources.md).

## Authorized Dock app follow-up

After the initial source-only delivery, the user explicitly requested updating the
Dock app. `defaults read com.apple.dock persistent-apps` resolved the original
checkout's `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`. The old
bundle was copied with `ditto` to `/tmp/alice-before-refinements-20260906.app`.
`npm run build:app` passed the frontend build, native release build and app bundling
(existing chunk advisory). The old process was quit and `npm run launch:app`
reopened the exact bundle with the existing local configuration. Native UI
accessibility verified the local EDT clock and America/New_York label plus live
feed. Settings/enrollment stores were not edited; no remote publication occurred.
This supersedes only the initial report's native-bundle-replacement limitation.
