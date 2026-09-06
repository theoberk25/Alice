# Script catalog

Developer tools live in scripts/<area>/. Runtime modules and tests remain in
packages, services and tests. Follow each catalog for dependencies and outputs.

| Area | Tools | Commands |
| --- | --- | --- |
| Technician console | [Catalog](console.md) | npm commands from repository root; direct launchers work from any directory |
| Biometrics | [Catalog](biometrics.md) | Repository-local Python environment and model/service tools |
| Lab / simulation | [Catalog](../lab/README.md) | python -m lab.* from root; absolute checkout path to scripts/lab/run.py from any directory |
| Pi → Wazuh delivery | [Maintenance guide](../integration/wazuh-audit-sync.md) | Runtime --wazuh-sync-config for automation; lab.wazuh_sync only with service stopped |
| Integrated demo acceptance | [Runbook](../guides/demo-runbook.md) | lab.first_light.check_pipeline is read-only; run on Pi beside the existing service |
| Package tooling | [Catalog](packages.md) | Empty placeholders; not runnable tools |

The [console migration](../handoffs/2026-09-05-console-layout.md) includes all
former workstation files, path repairs and verification. The
[lab migration](../handoffs/2026-09-05-lab-script-relocation.md) preserves
public lab.* imports. Neither migration changes product integration status.

Offline ledger quota maintenance: `python -m lab.audit_resize` (runtime stopped,
new backup required, increase-only). See the [hardware runbook](../guides/first-light-hardware.md).
