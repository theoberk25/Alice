# Script catalog

This is the repository-wide entry point for developer scripts. New independent
helpers belong in scripts/<area>/, with purpose, working directory, command,
dependencies and output locations documented beside them. Runtime modules and
tests remain in their owning packages.

Existing location-dependent tools are linked here, not relocated: changing their
location would change __file__/import.meta.dirname roots, imports or launch paths.
Run them from the documented working directory. Do not execute them through a
new symlink path or assume scripts/ is their working directory.

| Area | Existing scripts / modules | Working directory and instructions |
| --- | --- | --- |
| Biometrics | [Catalog](biometrics/README.md) | workstation/ |
| Desktop and Rust | [Catalog](workstation/README.md) | workstation/ |
| Lab / simulation | [Catalog](lab/README.md) | Repository root |
| Package tooling | [Catalog](packages/README.md) | Empty placeholders; not runnable tools |

Physical consolidation is deferred where it conflicts with the no-code-change
requirement. The [organization handoff](../docs/handoffs/2026-09-05-repository-organization.md)
records why. Do not duplicate existing scripts to populate this directory.
