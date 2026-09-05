# Deterministic HOLD workflow and reassessment lineage

The Technician Console never performs the policy/anomaly reassessment itself. Policy, anomaly scores, evidence status and ALLOW/HOLD/DENY come only from immutable upstream decisions. Agent responses are claims; receiving one is not a revised decision.

```text
Technician Console
    | alice.context_request
    v
ALICE Core / Agent
    | alice.agent_response
    v
Technician Console: REASSESSMENT_PENDING

ALICE Core reassesses (outside this workstation subsystem)
    | NEW alice.decision with explicit reassessment lineage
    v
Technician Console: preserve previous decision, select current assessment
```

`packages/domain/src/hold.ts` defines allowed transitions; invalid transitions throw. The automatic path is:

```text
DEC-184: HOLD_RECEIVED → AUTO_CONTEXT_REQUEST → AWAITING_AGENT_RESPONSE
         → [CONTEXT_RECEIVED] AGENT_RESPONSE_RECEIVED
         → [REASSESS] REASSESSMENT_PENDING
         (wait for another immutable alice.decision; no automatic REVIEW)
         → [REASSESSMENT_RECEIVED] SUPERSEDED

DEC-185: HOLD with context_challenge.required=false → AWAITING_TECHNICIAN
         HOLD with context_challenge.required=true  → HOLD_RECEIVED → automatic context
         ALLOW or DENY                             → RESOLVED

AWAITING_TECHNICIAN → RESEARCHING | HELD_BY_TECHNICIAN | REJECTED
AWAITING_TECHNICIAN → APPROVAL_REQUESTED
    → BIOMETRIC_REQUIRED → BIOMETRIC_VERIFYING → BIOMETRIC_PASSED
    → APPROVAL_SUBMITTED
```

Only `HOLD && context_challenge.required` starts an automatic clarification. A valid response must match decision, request, agent and issued challenge. The response handler stops at REASSESSMENT_PENDING. Existing explicit human controls remain available while awaiting context/reassessment; a deliberate human action is separate from automatic reassessment. Late context does not regress a human action or completed submission. Receipt of a valid successor supersedes its parent even if review or biometric verification is in progress.

## Immutable lineage and current assessment

`packages/domain/src/lineage.ts` checks that each reassessment has a new ID, a known current parent, the same request ID, agent ID, mission ID, action and target, the original root ID, and the parent's sequence plus one. An original has no reassessment object. First reassessment sequence is 1. This implementation accepts a linear chain; forks, missing ancestors, extra originals for one request, changed identity fields and conflicting duplicate IDs are rejected. A changed request identity requires a new request ID.

Decisions remain in `decisions[decision_id]`. `requestDecisionHistory` stores ordered IDs, and `latestDecisionByRequest` points to the current one. Selection advances when the current request receives a successor; another selected request is not interrupted. Historical records remain inspectable, labelled ORIGINAL/HISTORICAL ASSESSMENT, with actions disabled. The lineage panel compares supplied root/current risk, verified evidence and decision result deterministically. Its context/response/reassessment/review track uses actual state, not fabricated completed steps.

## Approval and race handling

APPROVE, HOLD, RESEARCH and REJECT must address the latest decision for the request. The approval dialog captures its decision ID when opened. Supersession blocks that dialog and requires a new confirmation/verification. The store checks currentness again after awaiting persistence; Rust independently checks currentness before verification, on grant issuance after inference, and on action submission. Cache insertion and lineage audit records share a transaction; superseding a decision revokes its outstanding native grants.

A DEC-184 proof cannot authorize DEC-185 even though both have REQ-88291. Rust retains the existing enabled-session, HOLD/policy/capability, exact technician/decision/request, provider, PASS, 60-second expiry and one-use checks. Login is never an approval grant. Failed verification permits a controlled fresh retry or cancellation. A decision without the biometric flag still requires explicit human confirmation. No natural-language intent can approve or reject.

An action accepted before supersession may return its receipt afterwards. That receipt remains associated with the old decision, without reactivating its SUPERSEDED workflow. An identical recorded action ID is idempotent while its assessment remains current. Retries against superseded assessments are refused. No protected action executes in mock mode; APPROVAL_SUBMITTED records a request, not execution confirmation.

## Persistence and operational record

Native SQLite preserves all immutable decision snapshots, actions, agent responses and reconciliation annotations. Hydration normalizes the full snapshot set, validates every lineage, and reconstructs both indexes without relying on transient maps or timestamps. Decisions are not truncated to a 500-row window that could omit an ancestor. Superseded flows are rebuilt; a current required-context HOLD with a saved response remains REASSESSMENT_PENDING unless a saved human action establishes its later state. Reconciliation never changes original evidence or authorization.

Local append-only audit records include REASSESSMENT_PENDING, REASSESSMENT_RECEIVED, DECISION_SUPERSEDED and CURRENT_ASSESSMENT_UPDATED with decision/request IDs. The UI/export retains its existing latest-500-event window; storage is not rewritten. Issued context IDs, receipts, outbox delivery and the complete transient workflow lifecycle still require future durable recovery work. Development scenario reset clears simulated actions/annotations/grants, but retains immutable decisions and audit. It is distinct from ordinary restart/hydration.

Scenario `04_hold_context_rejustification` replays a response after 1.2 seconds and predetermined DEC-185 after another 1.2 seconds. See the scenario guide for replay instructions and persistence behavior. Real delivery, ordering/replay negotiation, execution-confirmation events and remote approval attestation remain team integration work; no endpoints or ACK protocol have been invented.
