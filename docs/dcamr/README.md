# DCAMR documentation

Runtime source remains in dcamr/ at the repository root. No Python package has
moved in this documentation cleanup. All new DCAMR-specific guides belong here;
shared product, contract and architecture documents retain their central homes.

- [Architecture and authority](../architecture.md)
- [Pi assessment contract](../contracts/decision-assessment.md)
- [Anomaly result contract](../contracts/anomaly-contract.md)
- [Feature construction](../contracts/anomaly-features.md)
- [Contextual behavior model](../architecture/contextual-behavior-model.md)
- [Decision Evidence Ledger](../architecture/decision-evidence-ledger.md)
- [Workflow status](../implementation-tracker.md)
- [Implementation tracker](../implementation-tracker.md)

The first-light slice now implements `dcamr.main`, signed release verification,
exact-match permissions and HTTP light transport. The general service lifecycle
is still incomplete. See the [source map](../../architecture.md#repository-map)
and [first-light report](../reports/2026-09-05-pi-backend-status.md) for the fixture,
demo-trust and mock-hardware limits.
