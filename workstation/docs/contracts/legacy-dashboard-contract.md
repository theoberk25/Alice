# Legacy dashboard compatibility

`fixtures/legacy/dashboard-contract.original.txt` is the supplied contract file, unchanged. `decision.json`, `status.json`, and `reconciliation.json` are extracted objects with normalized JSON whitespace. Tests assert that all three validate and normalize successfully. Migration preserves the original and extracted fixtures unchanged. Their DDIL/CONNECTED/DEGRADED vocabulary does not implement the main product's ONLINE/OFFLINE authority-transfer protocol; see the [migration assessment](../integration/main-repository-migration.md).

| Legacy payload         | Internal payload       | Changes                                                              |
| ---------------------- | ---------------------- | -------------------------------------------------------------------- |
| `dcamr.decision`       | `alice.decision`       | `system.dcamr_node` → `system.node`; known node prefix becomes ALICE |
| `dcamr.status`         | `alice.status`         | `dcamr_node` → `node`; known node prefix becomes ALICE               |
| `dcamr.reconciliation` | `alice.reconciliation` | Event type only                                                      |

The adapter accepts unknown input and validates it before producing a domain event. Out-of-range risk/confidence and invalid enum values are rejected. Unknown fields on inbound records are stripped; strict outbound schemas reject unknown keys. Existing policy, anomaly, evidence, IDs, timestamps, and execution fields are retained. `original_decision_changed` must be false for reconciliation.

The display never shows legacy branding. No knowledge of Isolation Forest scoring internals, OPA, Rego, or external evidence service internals is needed by the dashboard.
