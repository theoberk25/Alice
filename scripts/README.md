# Script catalog

This is the repository-wide entry point for developer scripts. New independent
helpers belong in scripts/<area>/, with purpose, working directory, command,
dependencies and output locations documented beside them. Runtime modules and
tests remain in their owning packages.

ML and enterprise tools have been migrated into scripts/lab with a working-directory
independent launcher and preserved lab.* imports. Other subsystem tools remain
in their existing locations; follow each catalog for supported commands.

| Area | Existing scripts / modules | Working directory and instructions |
| --- | --- | --- |
| Biometrics | [Catalog](biometrics/README.md) | workstation/ |
| Desktop and Rust | [Catalog](workstation/README.md) | workstation/ |
| Lab / simulation | [Catalog](lab/README.md) | Repository root for python -m; any directory through lab/run.py |
| Package tooling | [Catalog](packages/README.md) | Empty placeholders; not runnable tools |

The separately authorized lab migration includes path/import repairs and tests.
Other physical consolidation remains deferred. The [organization handoff](../docs/handoffs/2026-09-05-repository-organization.md)
records why. Do not duplicate existing scripts to populate this directory.
