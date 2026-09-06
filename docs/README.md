# Documentation map

Start each session with [working rules](../AGENTS.md) and [current status](../current.md).
Do not read docs/archive/ or follow its links unless the user explicitly requests
archived context. Exclude its contents from routine searches and agent context.

The [implementation tracker](implementation-tracker.md) retains detailed task IDs
and evidence. Read only the detailed documents relevant to the task.

| Purpose | Location / entry point |
| --- | --- |
| Product requirements | [PRD](prds/ALICE-DCAMR-PRD.md), [anomaly PRD](prds/anomaly-model-prd.md) |
| Architecture | [Whole-system overview](../architecture.md), [detail index](architecture.md), [canonical system design](prds/ALICE-DCAMR-Architecture.md), architecture/ |
| Component contracts | contracts/; executable schemas remain in ../common/schemas/ |
| Setup and operation | guides/; [demo runbook](guides/demo-runbook.md) |
| Integrated transition | [Wireless, agents, Pi, SIEM, lights and technician runbook](guides/demo-runbook.md) |
| Integration boundaries | [Technician console](integration/technician-console.md), [Pi → Wazuh](integration/wazuh-audit-sync.md), [release snapshots](integration/release-snapshot.md) |
| Accepted decisions | [Data direction](decisions/2026-09-05-data-direction.md) |
| Implementation plans | plans/; [Theo’s older runtime reference](plans/2026-09-05-theo-pi-runtime-reference.md) (historical proposals; use the corrected root architecture) |
| Team responsibilities | [Developer handoff](prds/ALICE-DCAMR-PRD-Handoff.md) |
| Current status and detailed task evidence | [Current checkpoint](../current.md), [implementation tracker](implementation-tracker.md) |
| Experiment evidence | [Published reports](reports/anomaly-lab/README.md) |
| Technician console documentation | [Subsystem README](guides/technician-console.md), [contributing rules](guides/console-contributing.md) |
| Completed / superseded context | [Archive index and rules](archive/README.md) |
| Core runtime | [DCAMR index](dcamr/README.md) |
| Lab and simulation | [Lab guide](lab/README.md) |
| Test fixture explanations | [Anomaly](tests/fixtures/anomaly.md), [features](tests/fixtures/features.md) |
| Native live backend | [Parity checklist](plans/native-live-backend-parity.md), [validation report](reports/2026-09-06-native-live-backend-validation.md), [operator setup](guides/native-runtime-review.md), [review contract](contracts/technician-runtime-review.md), [continuation](handoffs/2026-09-06-live-backend-after-biometric-delivery.md), [workspace recovery](handoffs/2026-09-06-native-live-backend-workspace.md) |
| Live facial delivery | [Integration report](reports/2026-09-06-live-face-main-integration.md), [setup](guides/console/facial-verification-quickstart.md) |
| Biometric service | [Service API](guides/biometrics-service.md) |
| Developer tools | [Script catalog](scripts/README.md) |

Existing architecture and ownership documents in prds/ retain their published
paths. New detailed architecture documents go in architecture/. All substantive
Markdown docs, including script catalogs and fixture explanations, live under docs/. Historical handoffs retain their evidence and
limitations; they do not supersede the current PRD or authorize implementation.

Completed session handoffs and superseded runbooks move to `archive/`; they are not
required for current implementation work.
