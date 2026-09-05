# Current

Updated: 2026-09-05
Upstream baseline: `3330a07` (Alex and Jared's migrations merged on GitHub main).
Working branch: `codex/integrate-team-layout`; changes are staged, uncommitted and unpushed.
Local documentation checkpoint retained separately at `011abf1`; do not replay it
over the integrated layout. Resume from this checkout and the linked team review.

## Current objective

Finish the combined layout follow-up: a source-grounded architecture map, correct
active documentation paths, verified file preservation and a reviewable branch.
Start each session with [AGENTS.md](AGENTS.md).

## Where work belongs

Read [File placement](AGENTS.md#file-placement) before creating files.
Docs: docs/<area>/. Utilities: scripts/<area>/. UI: apps/. Services: services/.
Core packages remain in dcamr/ and common/; lab.* resolves into scripts/lab/.
Tests stay with their owning test suites. Archive contents require explicit permission.

## Current state

- Jared's lab migration and Alex's console migration are integrated locally.
  Npm commands now run at root; the old workstation source layout is superseded.
- Fixed a missing Path import that broke biometric model provisioning; added
  isolated default/override path regressions without downloading models.
- Architecture now covers lifecycle, contracts, storage/model ownership and every
  source area. Stale console/ledger descriptions and setup paths are corrected.
- All substantive Markdown is under docs/ except the documented root entry points.
  Legacy empty scaffolds and published data paths are intentionally preserved.
- Core, lab and console components exist; trusted live transport, permissions,
  authority transfer and execution remain incomplete. [Architecture](architecture.md).
- Tracker retains 12 done components, 35 partial and 71 planned product tasks.

## Next steps

1. Publish/review the combined follow-up on codex/integrate-team-layout.
2. Agree normalized request, assessment and application-response bindings.
3. Implement trusted permissions/cache activation and assessment-to-ledger adapters.
4. Connect authenticated console transport and protected execution/authority transfer.
5. Complete model export, real sensor contracts and Pi/operator acceptance.

## Verification and limits

Prior implementation checks: 259 Python tests passed, zero skips; npm run check passed with
64 frontend tests, four launcher tests, type-check, lint and production build.
Prior browser checks: all five scenarios passed with installed Chrome via a temporary config.
Architecture/layout follow-up: six Python path regressions and four launcher tests
passed; active doc links, baseline preservation and placement were checked.
The provisioning regressions use a stub model dependency, not real inference.
Native/camera/Pi acceptance has not been rerun in this checkout.
[Combined review and commands](docs/handoffs/2026-09-05-team-layout-review.md).

## Start here

[Rules](AGENTS.md) · [README](README.md) · [Architecture](architecture.md) ·
[Docs](docs/README.md) · [Tracker](docs/implementation-tracker.md) ·
[Scripts](docs/scripts/README.md)
