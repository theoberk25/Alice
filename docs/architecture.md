# Architecture guide

Current implementation update: main at `d6e7e55` adds the
[first-light slice](reports/2026-09-05-pi-backend-status.md): signed terminal request,
verified demo release, exact grant resolver, fixture assessment, durable ledger
producer and mock ESP HTTP execution. Full permission semantics, real scoring/review,
authority transfer and physical acceptance remain. Requirements below describe
the full product; use the [current source map](../architecture.md) for implemented scope.

Start with the root [high-level architecture](../architecture.md) for the current
component map, runtime boundaries and implemented-versus-planned distinction.

The canonical design is [ALICE — architecture and integration
boundaries](prds/ALICE-DCAMR-Architecture.md), revised September 5, 2026. It
supersedes the earlier design in which every online and offline request passed
through DCAMR.

ALICE has two product modes:

- **ONLINE:** enterprise systems control execution directly. The Pi synchronizes
  bounded, trusted permissions, normal-behavior and relevant enterprise context;
  consumes authenticated activity feeds; and uploads local audit/findings.
- **OFFLINE / DDIL:** after a controlled transfer of execution authority, the Pi
  governs local-agent actions using accepted caches, behavioral scoring, local
  evidence and technician review. It records every request and outcome.

The Pi handles enterprise synchronization directly. Reconnection includes audit
delivery, evidence reconciliation, cache validation and transfer back to enterprise
control; it is not a third product mode. Upload backlog, cache freshness and
execution ownership are separate status facts.

## Read by integration boundary

| Work area | Primary document |
| --- | --- |
| Product behavior and acceptance | [Product PRD](prds/ALICE-DCAMR-PRD.md) |
| Components, authority transfer, cache/audit lifecycle and Pi limits | [Architecture](prds/ALICE-DCAMR-Architecture.md) |
| Team ownership and contract handoffs | [Developer handoff](prds/ALICE-DCAMR-PRD-Handoff.md) |
| Native Mac console, facial verification, reassessment and remote proof | [Console integration](integration/technician-console.md) |
| Normal data, removable storage, motor decisions and compatibility | [Data direction](decisions/2026-09-05-data-direction.md) |
| Tested anomaly output and cyber features | [Output contract](contracts/anomaly-contract.md), [feature builder](contracts/anomaly-features.md) |
| Current model and calibration evidence | [Mac training lab](guides/anomaly-training.md) |
| Trust boundaries and verification scenarios | [Threat model](architecture/threat-model.md), [demo runbook](guides/demo-runbook.md) |
| Implementation status and next work | [Tracker](implementation-tracker.md) |

The core implements anomaly components, Pi assessment packets and a local durable
ledger, with synthetic Mac experiments and a mock-driven technician console.
Two-mode orchestration, full permissions enforcement, real assessment audit
producers, enterprise connectors, physical controller acceptance and live console
integration remain planned beyond the first-light fixture/mock slice. A
diagram or contract requirement is not evidence those services are running.

The protected endpoint must enforce one current execution authority. A network
outage or face match alone cannot confer that authority. Exact transfer messages,
remote approval proofs and execution-result contracts remain team agreements.
