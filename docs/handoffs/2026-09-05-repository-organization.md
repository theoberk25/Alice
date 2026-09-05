# Repository organization checkpoint

Date: 2026-09-05. Baseline: 2d0d32b from GitHub main.
Scope: documentation and session conventions only. No publication authorized.

## Approved design and execution plan

- [x] Check GitHub main and fast-forward the clean local checkout.
- [x] Establish AGENTS.md, CLAUDE.md and a compact current.md at the repo root.
- [x] Group existing documents by purpose and rebase their relative Markdown links.
- [x] Add a central scripts/ catalog with subsystem indexes.
- [x] Verify original file preservation, non-Markdown hashes, links and size limits.

Keep every existing file. Preserve code, configuration, manifests, fixture data,
script working directories and runtime paths. The root current.md is limited to
80 lines / 800 words with at most five next steps; detailed history goes here or
in the implementation tracker. Existing tracker IDs and task meanings survive.

## Moves

Paths below are repository-relative. Contents are retained except documentation
path/link updates. Commands in moved guides still run from the same working
directory they specified before the move, normally the repository root.

| Previous path | New path |
| --- | --- |
| `docs/anomaly-contract.md` | `docs/contracts/anomaly-contract.md` |
| `docs/anomaly-features.md` | `docs/contracts/anomaly-features.md` |
| `docs/decision-assessment.md` | `docs/contracts/decision-assessment.md` |
| `docs/anomaly-training.md` | `docs/guides/anomaly-training.md` |
| `docs/demo-runbook.md` | `docs/guides/demo-runbook.md` |
| `docs/workstation.md` | `docs/guides/workstation.md` |
| `docs/contextual-behavior-model.md` | `docs/architecture/contextual-behavior-model.md` |
| `docs/decision-evidence-ledger.md` | `docs/architecture/decision-evidence-ledger.md` |
| `docs/threat-model.md` | `docs/architecture/threat-model.md` |
| `docs/core-workflow-wip-handoff.md` | `docs/handoffs/core-workflow-wip-handoff.md` |
| `docs/enterprise-sim-handoff.md` | `docs/handoffs/enterprise-sim-handoff.md` |
| `docs/technician-console-integration.md` | `docs/integration/technician-console.md` |
| `docs/data-direction-2026-09-05.md` | `docs/decisions/2026-09-05-data-direction.md` |
| `docs/ALICE-ZERO-TRUST-ARCHITECTURE-AND-UPGRADE-CONTEXT.md` | `docs/handoffs/2026-09-05-zero-trust-upgrade-context.md` |
| `docs/superpowers/plans/2026-09-05-decision-evidence-ledger-handoff.md` | `docs/handoffs/2026-09-05-decision-evidence-ledger-handoff.md` |
| `docs/superpowers/plans/2026-09-05-decision-evidence-ledger.md` | `docs/plans/2026-09-05-decision-evidence-ledger.md` |
| `docs/superpowers/specs/2026-09-05-decision-evidence-ledger-design.md` | `docs/architecture/2026-09-05-decision-evidence-ledger-design.md` |

## Script placement exceptions

The user's no-code-change and no-broken-path requirements prevent physically
moving location-dependent scripts in this pass:

- workstation/scripts/*.py computes service/model roots using __file__.resolve().parents[1].
- workstation/scripts/*.mjs derives subsystem roots from import.meta.dirname.
- workstation/package.json invokes the existing script paths; native smoke checks
  invoke scripts/rust.mjs from workstation/.
- lab modules use the lab import namespace, module commands and source-relative
  fixture/artifact paths. The enterprise console also loads adjacent index.html.
- Runtime Python modules and tests are not standalone developer scripts.

The scripts/ directory provides categorized indexes to the original files.
No copies or executable symlinks were introduced. A future physical migration
needs explicit authorization to update code/configuration and verify commands.
Empty placeholders were retained, including packages/tooling scripts.

## Publication and verification

Changes are local on codex/repository-organization. Nothing pushed or deployed.
Upstream's 253-test result is historical; no application test run is claimed here.
Organization verification passed:

- All 353 original tracked files remain at their original or mapped paths.
- Every original non-Markdown file has an identical SHA-256 digest to baseline.
- All 550 checked local Markdown file links resolve.
- current.md is 47 lines and 242 words, within both limits.
- git diff --check passed. Application tests were not rerun: executable code,
  configuration, fixtures and their paths are unchanged.

These checks cover the checked-out main baseline and this local organization.
Teammates' other branches and future GitHub updates require a fresh comparison.

## Archive follow-up

On 2026-09-05, archived two completed/superseded ledger records. Their full text
remains, with historical notices and links to active status and guidance. Mixed
architecture/workstation documents remain active because they contain unresolved
requirements or unique integration context. No code or script paths changed.

| Previous organization path | Archive path |
| --- | --- |
| `docs/plans/2026-09-05-decision-evidence-ledger.md` | `docs/archive/plans/2026-09-05-decision-evidence-ledger.md` |
| `docs/handoffs/2026-09-05-decision-evidence-ledger-handoff.md` | `docs/archive/handoffs/2026-09-05-decision-evidence-ledger-handoff.md` |

Archive follow-up verification: all 353 original files preserved; all original
non-Markdown SHA-256 digests unchanged; 565 local Markdown file links resolve.
current.md remains within limits at 48 lines / 249 words. Staged whitespace
validation passed. Application tests were not rerun for these document moves.

## Pre-publication review

Reviewed against 2d0d32b; GitHub main was rechecked and still matched that baseline.
Independent review found no lost requirements, changed command behavior or broken
original Markdown targets. Fixed stale plain-text document references in prompt
instructions and the archived plan; clarified the design's historical awaiting-approval
status with links to its recorded approval and implemented component.

Fresh check: .venv/bin/python -m unittest discover -v passed 253 tests in 9.196s,
zero failures/errors/skips. All original non-Markdown Git blobs, modes and paths
are identical to baseline. Workstation native/camera/UI checks were not rerun;
no executable files, manifests, runtime paths or test fixtures changed.

The lab/workstation owners will handle any later physical script relocation and
associated imports/configuration/tests. This branch introduces no such path repair.
The .gitignore line 8 comment still names the historical enterprise handoff path;
its rules are untouched, and the move table above identifies the new location.
External bookmarks to old documentation paths are outside the local link check;
use the move map or a commit-pinned historical link for those references.

User-directed context rule: docs/archive/ contents must not be read, searched or
passed to agents unless the user explicitly requests archived material. Root and
archive-scoped AGENTS.md enforce this instruction; filename inventories remain
permitted. The earlier content/link review was completed before this restriction.

## Publication authorization

The user explicitly authorized committing and pushing this reviewed cleanup to
main on 2026-09-05. This supersedes the earlier local-only publication status
in this record. GitHub main was rechecked at 2d0d32b before publication. The
organization commit records the exact delivered tree; no code, configuration or
script relocation is included. Future lab/workstation path changes belong to
their owners and require separate verification.
