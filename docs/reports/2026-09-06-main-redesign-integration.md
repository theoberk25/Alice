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
- First `git fetch upstream main` returned `45312778b802b95488015b673ba1bd30b0b15f88`.
  The initial integrated checkpoint is `4b1f67e`.
- Final remote recheck found a newer team commit; it was fetched and merged too:
  `d5a0d56f69b007e388b5a4c49b00b363b7bd0f25` (17 team commits after PR #5).
  Remote is `https://github.com/theoberk25/Alice.git`.
- Isolated branch: `codex/main-redesign-integration`, retaining both team revisions.
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

The late `d5a0d56` update preserves battery percentage/units, fixed LED roles,
agent tool descriptions, all revised team guides and tracker row 035. Its prior
[current checkpoint](../handoffs/2026-09-06-before-telemetry-redesign-merge.md)
is retained verbatim. No frontend/native/dependency bytes changed after `4b1f67e`.

One pre-existing test setup issue became visible when optional MCP was installed:
`test_metrics_integration.py` imported `integrated` without its dependent
`thermal_model_file` fixture. Importing that existing fixture fixes discovery;
all team test assertions, including the new battery checks, remain intact.
No runtime behavior was changed to satisfy tests.

## Preservation audit

Relative to PR #5, source changed 75 paths and latest team main changed 118;
seven overlap. Every path survives. Byte/mode comparisons and independent
TypeScript AST review establish:

- 110/111 teammate-only paths are exact; the sole exception is that test import.
- 66/68 source-only paths are exact; the exceptions are five-action rail CSS and
  registration of the new integrated browser test.
- All 447 paths unchanged by either side remain exact (archive contents excluded).
- App retains all source/target controller declarations/effects and handler/
  disabled/value bindings. RuntimeReview retains every business handler/binding.
- Motion/Anime add only two dependency declarations and 90 lockfile lines. The
  team had no package/lock changes to reconcile. No extra runtime dependency added.

The new fifth action uses the shared CommandButton. Its rail layout is scoped to
the dashboard footer, with two rows on narrow screens and three at 360px or less;
RuntimeReview's separate action group retains its original responsive behavior.
New browser coverage checks nine widths (320–1512px), context disablement,
fan context, action-specific face binding, cancellation and signed rejection flow.

## Verification

Commands ran in the integration worktree with Node 22.23.1, Python 3.11 and the
existing local stable Rust toolchain. Node dependencies were installed from the
exact lockfile. Python environments/toolchains are reused through ignored local
symlinks; MCP 1.29.1 and dependencies were installed only under ignored
`.tools/integration-mcp` using the repository's `requirements-light-mcp.txt`.

| Command / check | Integrated result |
| --- | --- |
| `npm run check` | PASS: TypeScript, ESLint, 190 frontend tests, 8 script tests, web build |
| `npm run test:rust` | PASS: 62 tests, 2 explicitly opt-in ignored |
| `npm run test:python` | PASS: 176 biometric tests, 1 exact-model-dependent skip |
| `.venv/bin/python -m pytest` with the nine selected runtime/context/thermal/resume files | PASS: 125 tests; MCP initially skipped because not installed |
| `PYTHONPATH="$PWD/.tools/integration-mcp" .venv/bin/python -m pytest tests/test_metrics_integration.py -q -ra` | PASS: all 8 real MCP tests after fixture import repair |
| Same `PYTHONPATH` and `.venv/bin/python -m pytest tests -q -ra` | PASS on latest `d5a0d56` integration: 541 passed, 266 subtests (including all 8 MCP tests) |
| `ALICE_TEST_BROWSER_CHANNEL=chrome npm run test:e2e` | PASS: all 31 browser regressions, including 3 added integration cases |
| `npm run build:app` | PASS: separate optimized ALICE.app built in this worktree |
| `git diff --check`, preservation audit, checkpoint link/size checks | PASS; no missing files or unresolved content conflicts |

All frontend/native/browser/build results apply to the final tree: those inputs
are byte-identical after the late telemetry merge. The final Python rerun covers
that update's battery assertions and configuration. Desktop, mobile and synthetic
Face ID screenshots were visually inspected; no missing fifth action or clipped
rail controls were observed.

Initial native/resume test attempts hit sandbox loopback-server denials; reruns
with local test networking passed. The first full optional-MCP run had 535 passing
tests and six missing-fixture setup errors; these were repaired as described above.
An intermediate frontend build saw a nullable test-fixture field during concurrent
test editing; the fixture guard was corrected and the complete check rerun passed.
No test was weakened or skipped to conceal these failures.

Warnings remaining: existing frontend chunk over 500 kB, MCP client deprecation,
and biometric dependency/update-check warnings. They did not fail validation.
The exact model-dependent biometric test was not run; no model was copied from the
private store. Raw logs and preservation inventory are under ignored
`artifacts/console/integration-evidence/` in the worktree.


## Remaining acceptance

Browser camera/native IPC fixtures are synthetic. Real camera angle/PAD checks,
native visual acceptance and physical Pi integration need operator acceptance.
No push, deployment or Dock app replacement was performed.


## PR preparation and latest upstream deployment

The user subsequently authorized publishing a PR to `theoberk25/Alice:main` and
will perform the merge. A fresh fetch found `4f98a14`, the team's integrated Pi
thermal deployment. It was merged into the redesign branch; only `current.md`
conflicted. The team's current checkpoint is preserved in
[deployment checkpoint](../handoffs/2026-09-06-before-pr-thermal-deployment-merge.md).
All nine newly changed upstream code/test/guide/service paths match that commit
byte-for-byte; tracker rows 086, 108 and 112 retain the team's updated evidence.
Frontend, native and biometric inputs did not change in this final upstream merge.
The current checkpoint passes its line/word limits and local link checks.

Final `PYTHONPATH="$PWD/.tools/integration-mcp" .venv/bin/python -m pytest tests -q -ra`: 543 passed, 266 subtests passed, 12 MCP deprecation warnings.
