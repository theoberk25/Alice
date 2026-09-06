# Combined team layout review

Date: 2026-09-05. Baseline: GitHub main at 3330a07.
Working branch: codex/integrate-team-layout. No follow-up push is implied.

## Sources and preservation

- ce617cf: Jared's relocation of ML/enterprise tooling under scripts/lab/.
- 056251e: Alex's consolidation of the technician console into shared roots.
- 3330a07: merged GitHub main containing both migrations.
- 011abf1: our earlier staged documentation cleanup saved as a local commit on
  codex/centralize-subsystem-docs before integrating the team work.

Rather than replay obsolete workstation-based paths, this follow-up starts from
3330a07 and reapplies the remaining documentation requirements to the owners'
current layout. The earlier checkpoint is retained. Existing owners' docs under
shared topic folders take precedence over our proposed docs/workstation/ layout;
we do not create duplicate versions. The earlier root npm formatter adjustment
is unnecessary because Alex supplied a new root manifest and explicit targets.

## Findings and disposition

| Finding | Disposition |
| --- | --- |
| Biometric setup uses Path but lost its pathlib import during relocation | Restored the import; two copied-checkout tests reproduce the original NameError and pass after the fix |
| Upstream current.md still describes an unpublished local migration and its author's private environment | Replaced with combined GitHub baseline, current task and locally verified evidence |
| Eight Markdown docs remain outside docs/ | Moved with link rebasing; source, fixtures and schema locations retained |
| Earlier local doc proposal assumes npm runs from workstation/ | Superseded by root commands and the owners' shared topic folders |
| Top-level overview omits implemented assessment/ledger boundaries or mixes target design with current delivery | Rewrote README and added architecture.md with explicit target/implemented distinctions |
| Pi assessment, console decisions and enterprise/ledger audit envelopes differ | Recorded as existing integration work; did not invent an adapter or change contracts |
| Private .env, environments, identity data and models are not supplied by git pull | Documented fresh-checkout setup; did not read, copy, reset or provision private state |

## Documentation moves in this follow-up

| Original path on 3330a07 | New path |
| --- | --- |
| `scripts/README.md` | `docs/scripts/README.md` |
| `scripts/lab/README.md` | `docs/lab/README.md` |
| `scripts/console/README.md` | `docs/scripts/console.md` |
| `scripts/biometrics/README.md` | `docs/scripts/biometrics.md` |
| `scripts/packages/README.md` | `docs/scripts/packages.md` |
| `services/biometrics/README.md` | `docs/guides/biometrics-service.md` |
| `tests/fixtures/anomaly/README.md` | `docs/tests/fixtures/anomaly.md` |
| `tests/fixtures/features/README.md` | `docs/tests/fixtures/features.md` |

Root architecture.md is an explicitly requested entry-point exception to the docs/
placement rule. Root README.md, AGENTS.md, CLAUDE.md and current.md are the other
project/session entry points. All detailed docs remain in docs/. Archive contents
were excluded from reading, searching and delegated context throughout this review.
Historical links inside the untouched archive can be interpreted using move maps.

## Verification

- Pulled baseline: 257 Python tests passed, zero skips, in 14.121 seconds.
- Reproduced both model provisioning cases failing with NameError before the fix.
- Fixed tree: .venv/bin/python -m unittest discover -q passed 259 tests, zero skips,
  in 13.406 seconds. Tests use temporary copied checkouts, stub inference and no
  private models or enrollment data. These are entry-point/path checks, not inference.
- npm ci installed the committed lockfile dependencies; npm run check passed:
  TypeScript, ESLint, 64 Vitest tests, four launcher tests and production build.
- The build emitted dependency annotation warnings from Zod; it completed.
- All three public lab replays passed: 8 anomaly fixtures / 7 score cases,
  5 feature vectors and 6 contextual ledger cases including sealed restart/retry.
- Final preservation checks found all 374 upstream files at original or mapped
  paths. The only original executable edit is the restored pathlib import.
  Eight Markdown files moved. All 588 active local Markdown links and checked
  heading anchors resolve. Archive contents were excluded.
- Independent final review found no material issues after the provisioning fix;
  corrected its small launcher-path wording finding in the script catalog.
- Browser tests initially could not start the Vite server inside the sandbox;
  after granting local-server access, the pinned Chromium binary was missing.
  Its download was stopped after slow progress. The same five tests passed
  with installed Chrome and a temporary config/profile in 12.9 seconds. The
  repository config is unchanged; the pinned downloaded Chromium was not exercised.

No native Rust suite, real camera, live enterprise service or Pi hardware
acceptance is claimed by this follow-up. Earlier owners' results remain in their
respective handoffs and must not be confused with this checkout's environment.

## Remaining product work

The layout is not an end-to-end runtime. Trusted permission resolution and release
activation, authenticated request/assessment/response transport, final application
response enforcement, live ledger producers/sender, controller fencing/execution,
model export/load and actual sensor/Pi acceptance remain in the tracker. Existing
empty scaffolds are retained; neither directory names nor passing mock scenarios
establish those implementations.

## Owner migration records

- [Lab relocation](2026-09-05-lab-script-relocation.md)
- [Console relocation](2026-09-05-console-layout.md)
- [Current workflow integration](core-workflow-wip-handoff.md)
- [Full task tracker](../implementation-tracker.md)

Final state: changes prepared locally on codex/integrate-team-layout. No follow-up
commit has been pushed. current.md remains within its 80-line / 800-word limits.
The prior local docs checkpoint at 011abf1 remains available separately.

## Architecture and placement follow-up

The user requested a clearer, more complete root architecture, a full placement
check and subsequent branch publication. Reworked architecture.md around deployment,
ONLINE/OFFLINE lifecycle, request sequencing, implemented components, trust/contracts,
storage/model lifecycle, the complete source map and integration acceptance.
Source checks included the assessment wrapper, contextual-to-ledger replay, native
commands, remote transport skeleton, contract generator and repository path helpers.

Corrected active documentation that still placed the console under workstation/,
called it external, or described durable audit as wholly unimplemented. Historical
verification is explicitly attributed; product requirements and tracker task IDs,
statuses and totals are unchanged. Fixed the biometric guide's launch directory and
the stale enterprise handoff path in the .gitignore comment.

Placement findings:

- All 374 files from baseline 3330a07 survive at original or mapped paths. The eight
  moves above remain the complete move map; this follow-up needed no further moves.
- All active Markdown is under docs/ except the five documented root entry points.
  Scoped archive instructions remain untouched. Existing PRD architecture paths,
  generated console JSON schema exports and service/native/launcher test locations
  are intentional. The root architecture explains each exception.
- Empty legacy app/service, package-tooling and lab scaffolds remain under the
  preservation rule. They are labelled explicitly, not counted as working features.
- Dependency manifests/requirements stay with their owning build/service. Generated
  USB text markers and the byte-preserved legacy fixture are data artifacts.
- Runtime bytes relative to baseline differ only in the previously verified
  pathlib import repair. No new runtime change was introduced in this follow-up.
- Archive paths have no diff; archive contents were excluded from reads/searches.
  No ignored environments, identity data, credentials or model assets were moved.

Fresh verification for this documentation/layout follow-up:

- A temporary Python inventory/link checker examined 378 tracked files, 58 active
  Markdown documents and 706 local links/heading targets: zero errors. It excluded
  archive targets and code spans/fences from link parsing, checked the eight-path
  preservation map and compared existing non-document source bytes to baseline.
- `.venv/bin/python -m unittest tests.test_script_locations tests.test_biometric_script_locations -q`:
  six tests passed in 4.690 seconds, exercising copied checkouts and unrelated cwd.
- `node --test scripts/console/tests/*.test.mjs`: four launcher tests passed.
- `git diff --check`: no whitespace errors. current.md satisfies both size limits.

The earlier full suites and browser runs above remain historical implementation
verification; they were not rerun for documentation-only edits. No new native,
camera, live enterprise or Pi hardware acceptance is claimed.

## Latest-main integration before publication

A pre-publication fetch found main advanced from 3330a07 to d6e7e55: first-light
implementation, its session record and backend status report. Local checkpoint
56f0f3f preserves the completed documentation/layout follow-up before that merge.
Merged latest main while preserving its runtime bytes; resolved only current.md
and tracker documentation conflicts. First-light task evidence and statuses are
retained; recomputed totals are 12 done components, 38 partial and 68 planned.

The root architecture, README, lab/core indexes and product architecture references
now include first-light signed request admission, demo release verification, exact
grants, fixture assessment, durable audit producer, mock ESP HTTP transport, read-only
event feed and verified USB export. They explicitly retain fixture/demo-trust,
hard-coded authority, transport-hardening and physical acceptance limits. The
runtime's import of lab.first_light.assessment_fixture is a test-slice dependency;
it was not moved or substituted with production scoring. First-light commands use
python -m lab.first_light.*; the existing run.py allowlist is unchanged.

The new runtime/builder writes private .seed files to caller-selected directories.
Added *.seed to .gitignore and checked representative generated paths are ignored.
No private key or model data was opened, moved or provisioned by this review.

Fresh integrated verification:

- Initial full Python run hit a sandbox PermissionError binding the mock ESP;
  no code fix was needed. With permitted loopback access,
  `.venv/bin/python -m unittest discover -q` passed **265 tests, zero skips**,
  in 16.872 seconds. This supersedes earlier suite counts for this checkout.
- Updated inventory/preservation checks use d6e7e55: all 384 upstream files survive
  at original or eight mapped paths. No further relocation was necessary. Existing
  runtime bytes match latest main except the preserved biometric Path import fix.
- Documentation links/heading targets, current.md limits, archive exclusion,
  unchanged upstream runtime bytes, tracker IDs/statuses and whitespace were checked
  again after the merge. Four console launcher tests passed earlier in this turn;
  no frontend/native code changed in the merge, so those broader suites were not rerun.

This is branch publication, not a merge into main or deployment. Prior native,
camera, enterprise and hardware reports retain their original evidence scope.
