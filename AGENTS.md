# Working agreements

## Start every session

1. Read this file and [current.md](current.md) before planning or changing files,
   including when resuming after a context reset. Subsystem instructions supplement
   these rules; explicitly link back here from any new agent instruction file.
2. Check the branch, working-tree changes and available upstream revision. Preserve
   other contributors' work. Read the relevant PRD, tracker rows and subsystem guide.
3. Use [docs/README.md](docs/README.md) and [script catalog](docs/scripts/README.md)
   to find existing work before creating another implementation or document.
4. Explicit user instructions govern the current task. Historical handoffs do not
   grant permission to publish, deploy or implement unrelated roadmap items.

## Archive is excluded from session context

Do not read docs/archive/ (sometimes referred to as docs/archived/) unless the
user explicitly asks to consult archived material. Do not follow archive links
by default, include archived contents in search results, or pass them to agents.
Exclude docs/archive/** from recursive content searches and context gathering.
Seeing an archive link or a historical reference is not permission to read it.
Filename inventories may list archived paths without opening their contents.
Use current.md and active documentation for normal work; if historical contents
are necessary, explain why and request explicit permission before reading them.

## Keep current.md small

- Hard limit: 80 lines and 800 words; prefer 40-60 lines. Maximum five next steps.
- It is a current snapshot, not an append-only session log. Replace stale entries.
- Include date, baseline commit, active objective, evidence scope, blockers, next
  steps and links. Assign owners only when agreed; otherwise say unassigned.
- Keep detailed task progress in docs/implementation-tracker.md. Preserve its IDs.
- Before removing useful historical detail from current.md, preserve it in a dated
  docs/handoffs/YYYY-MM-DD-topic.md or the relevant tracker entry, then link to it.
- Do not paste logs, transcripts, PRDs, inventories or implementation plans here.
- At the end of each session that changes work/status, update affected tracker rows
  and current.md. Read-only sessions report findings without writing unless asked.
- Record commands actually run, results and limitations. Historical test results
  must be labeled historical; component success is not integrated acceptance.

## File placement

- Developer scripts belong under scripts/<area>/ for new independent helpers.
  Technician console tools live in scripts/console/ and scripts/biometrics/.
  Frontend applications belong in apps/, shared console packages in packages/,
  local services in services/, and console tests in tests/console/.
  Before creating a helper, inspect the script catalog.
- Python runtime modules remain in their owning packages (dcamr/, agent/, common/,
  cloud/, protected_systems/, services/). Tests remain with tests.
  A .py extension alone does not make a file a standalone script.
- Implemented lab development tools and reusable simulation/training logic now
  live in scripts/lab/ after the authorized path migration. Preserve the public
  python -m lab.* namespace through lab/__init__.py; do not duplicate modules under
  a second import name. Pi runtime modules remain in dcamr/.
- PRDs: docs/prds/. Architecture: docs/architecture/. Contracts: docs/contracts/.
  Guides: docs/guides/. Integration: docs/integration/. Decisions: docs/decisions/.
  Plans: docs/plans/. Session records: docs/handoffs/. Evidence: docs/reports/.
  Completed/superseded context: docs/archive/; do not read it without permission.
- All substantive Markdown documentation belongs under root docs/, including
  script catalogs, subsystem guides and fixture explanations. Use topic folders
  and subsystem indexes; do not add README copies beside runtime code or data.
- Root README.md, architecture.md, AGENTS.md, CLAUDE.md and current.md are the
  intentional project/session entry points. Scoped agent instruction files are
  the only additional discovery exception. Link to detailed docs rather than
  copying them. Archive contents require explicit permission to read.
- Use snake_case.py and kebab-case.md for new files. Date historical records.
  Preserve existing public paths until a coordinated migration is authorized.

## Preserve behavior and history

- Archive clearly superseded/completed documents with a date, reason and active
  replacement link. Preserve active portions of mixed documents and all history.
- Never delete or overwrite files as cleanup. Move with a recorded old/new map;
  preserve historical material and label it rather than silently discarding it.
- Before a script move, inspect imports, __file__, import.meta.dirname, working
  directory assumptions, manifests, launch commands, fixtures and data locations.
  If relocation requires code changes, keep its original path and record the
  exception. Do not bypass this with unverified symlink execution or copied code.
- Update documentation links with moves and verify every original tracked file
  survives. Compare non-document hashes for a documentation-only reorganization.
- Preserve runtime data, ignored local files, models, keys and environments.
- Do not create empty implementation files to suggest progress. Existing empty
  placeholders remain until their owners authorize a separate change.
- Maintain one authoritative source per topic. PRDs define intended behavior;
  source, schemas and observed verification establish implemented behavior.
- Coordinate cross-system contract changes with the affected owners. Follow
  docs/guides/console-contributing.md for console work and preserve its trust boundaries.

## Finish a session

Summarize changes, verification and remaining work. Keep changes reviewable on a
branch. Do not push or deploy without explicit authorization. Before handing off,
check current.md against both size limits and confirm its links resolve.
