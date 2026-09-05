# Documentation map

Start each session with [working rules](../AGENTS.md) and [current status](../current.md).
Do not read docs/archive/ or follow its links unless the user explicitly requests
archived context. Exclude its contents from routine searches and agent context.

The [implementation tracker](implementation-tracker.md) retains detailed task IDs
and evidence. Read only the detailed documents relevant to the task.

| Purpose | Location / entry point |
| --- | --- |
| Product requirements | [PRD](prds/ALICE-DCAMR-PRD.md), [anomaly PRD](prds/anomaly-model-prd.md) |
| Architecture | [Guide](architecture.md), [canonical system design](prds/ALICE-DCAMR-Architecture.md), architecture/ |
| Component contracts | contracts/; executable schemas remain in ../common/schemas/ |
| Setup and operation | guides/; [demo runbook](guides/demo-runbook.md) |
| Integration boundaries | [Technician console](integration/technician-console.md) |
| Accepted decisions | [Data direction](decisions/2026-09-05-data-direction.md) |
| Implementation plans | plans/ |
| Team responsibilities | [Developer handoff](prds/ALICE-DCAMR-PRD-Handoff.md) |
| Session records and detailed checkpoints | handoffs/; [workflow checkpoint](handoffs/core-workflow-wip-handoff.md) |
| Experiment evidence | [Published reports](reports/anomaly-lab/README.md) |
| Workstation documentation | [Subsystem README](../workstation/README.md), [contributing rules](../workstation/CONTRIBUTING.md) |
| Completed / superseded context | [Archive index and rules](archive/README.md) |
| Developer tools | [Script catalog](../scripts/README.md) |

Existing architecture and ownership documents in prds/ retain their published
paths. New architecture documents go in architecture/. Subsystem docs and fixture
READMEs stay near their owners. Historical handoffs retain their evidence and
limitations; they do not supersede the current PRD or authorize implementation.

See the [organization record](handoffs/2026-09-05-repository-organization.md) for
all moves and the constraints on physically relocating scripts.
