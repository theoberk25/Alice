# ALICE-native events

All events carry `schema_version: "1.0"`, `event_type`, and an ISO UTC `timestamp`. The console's executable schemas live in `packages/contracts/src/alice/events.ts` relative to the repository root; generated JSON Schema files in this directory support non-TypeScript teammates. They have not been promoted into `common/` or reconciled with the core contracts. See the [technician integration contract](../integration/technician-console.md) for version, anomaly, and ONLINE/OFFLINE authority gaps.

| Event                  | Purpose / binding                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `alice.decision`       | Immutable original upstream result, request, policy, anomaly, evidence, source packages, context, available actions |
| `alice.status`         | Current node, DDIL/connected/degraded mode, connectivity, package signatures/versions, engine states                |
| `alice.reconciliation` | Later evidence results bound to `original_decision_id`; original authorization unchanged                            |
| `alice.agent_status`   | Agent identity/type/model/status/activity/health, tied to a mission                                                 |
| `alice.service_status` | Internal service ID/label/status/detail; no private reasoning                                                       |
| `alice.agent_response` | Clarification response bound to decision/request/challenge/agent IDs                                                |

The legacy payload adapter is additive. An upstream team may continue sending the supplied payloads while adopting native events for agents and clarification. Failure to validate produces a visible console error; invalid records do not replace valid state.

Execution-completion events require a future contract agreement; reassessment uses the optional lineage contract below. Do not modify the original decision ID's payload to report technician approval or reconciliation.

## Decision reassessment contract

An original `alice.decision` has no `reassessment` field. A successor is a full new immutable decision event with this optional object (strict fields):

```json
{
  "decision_id": "DEC-20260905-000185",
  "reassessment": {
    "previous_decision_id": "DEC-20260905-000184",
    "root_decision_id": "DEC-20260905-000184",
    "trigger": "AGENT_CONTEXT_RESPONSE",
    "sequence": 1
  },
  "request": { "request_id": "REQ-88291" }
}
```

This is a lineage excerpt, not a complete valid decision. See `fixtures/alice/reassessment.json` for the full deterministic example. Trigger is one of `AGENT_CONTEXT_RESPONSE`, `EVIDENCE_UPDATE`, `TECHNICIAN_RESEARCH`, `OTHER`. Sequence is a positive integer; originals are conceptually sequence 0. Existing version 1.0 originals and legacy fixtures remain valid without the optional field.

Zod/JSON Schema validate shape. Ingestion and native cache checks additionally require:

- A new decision ID and a previously known parent that is the request's current assessment.
- Unchanged `request_id`, `agent_id`, `mission_id`, `action` and `target` within `request`. Changes require a new request, not a reassessment.
- Root equal to the original root of the parent chain; first successor uses the parent ID as root.
- Sequence equal to parent sequence plus one. For 184 → 185 → 186, the latter points to 185, retains root 184 and has sequence 2.
- One linear chain per request. Unknown parents, branches, broken roots, skipped sequence numbers and a second unlinked original are rejected.

Identical repeated IDs are idempotent; different contents under an accepted ID are always rejected. Timestamps do not determine currentness. Request history indexes are rebuilt from validated immutable snapshots during native hydration.

An agent response leaves the old workflow REASSESSMENT_PENDING. Only an actual successor marks it SUPERSEDED. A successor HOLD with `context_challenge.required=false` awaits technician review; `true` starts another automatic challenge. ALLOW/DENY resolve that assessment. Neither agent prose nor Ollama output can supply these structured outcomes or evidence/risk updates. The Technician Console never performs the policy/anomaly reassessment itself.

Execution confirmation remains a separate, unagreed future contract. Reassessment is not execution confirmation or an edit to the previous decision.
