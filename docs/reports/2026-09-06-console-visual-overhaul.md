# Technician console visual overhaul

Date: 2026-09-06 EDT. Baseline: `e1e75068bee7f5f990284b4f0e727571d0d288f0`,
freshly fetched `upstream/main` (`https://github.com/theoberk25/Alice.git`).
Original `main` was clean and exactly equal to team main. All implementation
occurred in `/Users/alexdaoud/Documents/alice-dashboard-visual-overhaul` on
`codex/dashboard-visual-overhaul`. No original-checkout source was changed during development.

## Presentation and functional boundary

No intentional business/security behavior changes. Existing handlers, enablement,
required/value/input bounds, biometric lifecycle/timers, cancellation, request/decision
bindings, native submission and acknowledgment behavior remain authoritative.
An independent source/AST review found no removed or changed existing action handlers
or enablement expressions. No Rust, Python, domain, state, contract, service, database,
transport, camera security, hardware, network or environment configuration was changed.
There were no compatibility exceptions. No existing behavioral assertion was weakened.

Typography uses locally bundled IBM Plex Sans for navigation, headings, body, forms
and controls; IBM Plex Mono remains for machine identifiers, timestamps and hashes.
Barlow is no longer loaded by the console. Four surfaces use graphite luminance:
canvas `#0d1014`, workspace `#13171c`, raised `#1a2027`, floating `#20262e`.
Borders are quiet 1px separators. The spacing scale is 4/8/12/16/20/24/32px;
control/panel/dialog radii are 6/9/13px. Cyan marks interaction/live focus, amber
marks HOLD/review, red marks rejection/errors, and green marks verified/healthy.
The static grid is faint. No background, particle, glow, tilt or parallax motion.

## Implemented motion

| Area | Actual implementation |
| --- | --- |
| Navigation | Separate shared Motion hover and selected surfaces, 200ms selection, stable controls and accessible current page. |
| Recent decisions | Shared moving selected surface/rail in fixture and runtime histories; stable row identities and unchanged selection. |
| Page changes | AnimatePresence with 220ms opacity/y10 entrance. Outgoing owners clean up immediately; exits do not delay camera/security lifecycle. |
| Identity and biometric dialogs | Native dialog retained; Motion opening morph uses existing trigger geometry. Native top layer, Escape, focus return and explicit Tab/Shift+Tab wrapping retained/improved. |
| Biometric stages | Persistent TransitionPanel measures/interpolates real height via ResizeObserver; camera image/ref remains mounted. Descriptive stages derive from existing state only. |
| Biometric SVG | Specialized Anime.js finite accepted-coverage interpolation; authoritative completion resolves perimeter to a restrained success mark; failure dissolves. No timed success/progress. |
| Counts and UTC clock | Independent changed-digit animation. Audit filter summary keeps its exact plain count text. |
| Processing edge | BorderTrail only for genuine in-flight language/request/loading/sending/reconciliation/verification operations. Indefinite reassessment waiting stays static. |
| Command rail and buttons | Raised fixed tonal rail with quiet blur/separator and short entrance; existing actions/enabled checks preserved. Motion button press scale .988 over 100ms. |
| Tooltips | Original Motion tooltip, accessible description, focus/hover, Escape and edge alignment; no paid Skiper code. |
| Reduced motion | Global MotionConfig user preference plus explicit guards for geometry, digits, imperative effects, SVG and trails; CSS removes transitions/animation. |

Dialog closing remains immediate: reverse morphs were deliberately omitted to keep
existing cancellation and cleanup timing. No separate challenge state or fake telemetry
was invented. Evidence-list arrival stagger and Haikei decoration were omitted; they
were optional and did not improve this console's density.

## Sources and dependencies

- `motion` 13.2.0, MIT: primary presentation engine.
- `animejs` 4.5.0, MIT: biometric SVG/timeline only.
- Motion Primitives: selectively adapted local MIT components, not another installed
  runtime framework. Retained notice and exact sources in [visual sources](../guides/console/visual-sources.md).
- Refero, Layers, Footer.design, Manus, 10x, Haikei and Skiper public references were
  researched for composition only. No template, Pro component or unclear-license asset copied.
- Installation audit reported zero vulnerabilities. Existing dependencies were not
  broadly upgraded; the lockfile adds only the animation dependencies/transitives.

## Audit and visual evidence

Actual baseline app was started before visual edits on local port 1421. Operations,
history, audit, administration, identity, approval/failure and existing reusable
components/tokens were inspected. All six existing repository screenshot files were
reviewed. No screen recording or additional attachment was supplied or found.

Initial in-app full-page exports produced malformed oversized composites, while
on-screen captures remained useful for the audit. For reliable comparison, the exact
baseline commit's frontend was subsequently rendered from an ignored source snapshot
on port 1422. Matching 1512×1040 captures were generated for baseline/redesign:
Operations, Decision history, Audit trail, Administration, Identity, Research,
Connection settings, Approval and Approval failure. Finite transitions were allowed
to finish before capture; the app received no artificial delay.

Local images remain intentionally outside Git under
`artifacts/console/visual-overhaul/{before,after}/` in the retained feature worktree.
Additional existing E2E captures include reassessment and 390px layout, and the native
IPC fixture captures the facial review surface without personal camera images.
Browser checks cover 1024/800/390px, dialogs within viewport, unchanged actions,
focus containment/return, DENY, failed/retried approval and exact assessment binding.

The redesigned views share legible sans headings, quieter supporting panes, readable
technical metadata, strong semantic outcomes and consistent controls. History uses
a persistent list/decision composition; audit uses dense timestamp/type/detail rows.
Live runtime request parameters, evidence, immutable decision, acknowledgment and
execution remain separate. No fields were removed to simplify the presentation.

## Verification in the feature worktree

| Command | Actual result |
| --- | --- |
| `npm ci` | Existing locked baseline installed successfully. |
| `npm run check` before UI changes | 134 tests + 8 script checks; typecheck, lint and build passed. |
| Final `npm run check` | 145 tests in 16 files + 8 script checks; typecheck, lint and web build passed. |
| `npm run test:rust` | 60 passed, 2 pre-existing opt-in tests ignored (real Ollama/local Rust→Python rehearsal). |
| `PYTHONDONTWRITEBYTECODE=1 /Users/alexdaoud/Documents/Alice/services/biometrics/.venv/bin/python -B -m pytest services/biometrics/tests -q` | 165 passed, 1 existing opt-in test skipped; 2 dependency deprecation warnings. This is the repository `test:python` suite using the existing interpreter read-only because the new worktree has no Python venv. |
| `PLAYWRIGHT_BROWSERS_PATH=/private/tmp/alice-visual-overhaul/browsers npm run test:e2e` | 11 passed: 8 existing scenarios + 3 new visual/accessibility regressions. |
| `PLAYWRIGHT_BROWSERS_PATH=/private/tmp/alice-visual-overhaul/browsers npx playwright test --config artifacts/console/visual-overhaul/capture.config.ts` | 2 visual capture passes, exact baseline and redesign. Capture harness and source snapshot are ignored local artifacts. |
| `npm run build:app` | Native macOS ALICE.app bundle built successfully. |
| `git diff --check` | Passed. |

Intermediate failures were resolved without weakening behavior: native dialog layout
projection collapsed a closed dialog to zero size; explicit measured opening replaced
that projection. Initial zero opacity caused a visibility race; the morph stays
visible throughout. Audit animated duplicate text broke an exact count assertion;
plain count text was restored. Native keyboard focus could reach browser chrome;
explicit focus wrapping was added. The first E2E launch lacked its matching browser;
Chromium was installed into temporary storage and all tests then passed.

Build limitations: Vite reports a JavaScript chunk over 500kB and third-party Zod
annotation advisories. Build succeeds; warnings were not suppressed. Actual human
camera/enrollment→physical-Pi acceptance and real Ollama/hardware tests were not run.
These are presentation/automated regression results, not deployed-system acceptance.

## Team integration and publication

`upstream/main` remained `e1e7506` on the pre-integration fetch; no teammate conflicts
or behavioral reconciliation were required. The baseline already includes merged
native backend PR #5 and previous biometric PR #4. Their newer behavior was retained.
The verified account has WRITE permission on `theoberk25/Alice`, so publication can
use the identified `upstream` remote directly. Local integration and PR publication
are the remaining delivery steps; local main must not be pushed and the remote PR
must not be merged or deployed.
