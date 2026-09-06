# Mock scenarios

Run `npm run demo` for native or `npm run dev` for browser preview. The development-only sliders button opens the scenario selector. Selecting or resetting a scenario clears simulated action state and active grants, retains immutable decisions, and appends a reset audit record. Real-mode history cannot be reset by this command.

| Scenario                          | Demonstration                                                               |
| --------------------------------- | --------------------------------------------------------------------------- |
| `01_normal_allow`                 | Read-only network diagnostics permitted, execution reported by the fixture  |
| `02_hard_policy_deny`             | EDR-disable request blocked by deterministic policy; no override buttons    |
| `03_hold_high_anomaly`            | Original supplied outbound HOLD, risk 94, local evidence 1/3                |
| `04_hold_context_rejustification` | Timed agent response → pending → immutable DEC-185 reassessment             |
| `05_hold_face_approval_pass`      | Fresh mock face PASS and exact-request structured approval                  |
| `06_hold_face_approval_fail`      | Forced mock failure leaves request held, no approval submitted              |
| `07_ddil_cloud_offline`           | Cloud/SIEM/EDR offline with local review still functioning                  |
| `08_reconnect_reconciliation`     | Current connectivity restored, EDR claim NOT_FOUND, original HOLD unchanged |
| `09_agent_failure`                | Network agent failure and operational error status                          |
| `10_llm_offline`                  | Language gateway unavailable while explicit review controls remain usable   |

Agent models in fixtures are illustrative strings; they are not hardware claims. The local gateway status separately reports the actually configured Ollama model. The structured language fallback is deliberately labeled. The mock PASS/FAIL UI captures no camera and is not usable in real biometric mode.

Suggested demo: explain the original HOLD; inspect missing references; watch automatic clarification; open Research; fail an approval; retry with PASS; inspect the audit; switch to DENY to show the absence of an override; reconnect to show evidence annotations without rewriting the decision.

## Primary reassessment demonstration: scenario 04

1. Open Development scenarios and select `04_hold_context_rejustification`.
2. DEC-20260905-000184 arrives for REQ-88291: HOLD, risk 94, evidence 1/3 verified, context required. Its record never changes.
3. Automatic clarification goes to diagnostic-agent-04. Its activity shows responding / WAITING_FOR_CONTEXT.
4. After 1.2 seconds the bound agent response arrives. The console displays REASSESSMENT PENDING; the agent panel reports that context was returned and upstream reassessment is awaited.
5. After another 1.2 seconds mock ALICE emits the full DEC-20260905-000185 fixture: parent/root DEC-184, trigger AGENT_CONTEXT_RESPONSE, sequence 1; same request/agent/mission/action/target. It is HOLD, risk 62, evidence 2/3 verified and 1 pending, technician required and biometric required. These are static simulated values, never calculated by this application.
6. DEC-184 becomes SUPERSEDED; DEC-185 becomes CURRENT ASSESSMENT and AWAITING_TECHNICIAN. The lineage shows original → automatic context request → agent response → reassessment/current, plus 94 → 62, 1 → 2 and HOLD → HOLD. Inspect either record using lineage/history; historical action controls are disabled. `context_challenge.required=false` on DEC-185 prevents another automatic loop.
7. Choose APPROVE, HOLD, RESEARCH or REJECT on the current assessment. APPROVE opens an explicitly DEC-185 / REQ-88291-bound dialog and requires a new face verification. Browser tests use Simulate pass; native ArcFace mode uses the configured real face service and camera. A previous DEC-184 grant cannot approve DEC-185.
8. Approval produces only a structured APPROVE_ONCE for DEC-185. The audit records the exact decision/request. No protected system action executes.

Only scenario 04 emits a timed successor; other scenarios retain their original fixture/response behavior. An agent response alone now remains pending rather than automatically returning to review. Existing deliberate human controls remain available while context/reassessment is pending. Disconnection/reset cancels old transport timers so they cannot leak a reassessment into a different scenario.

Browser preview is transient: reload for a fresh sequence with no camera or native database. Native restart restores persisted lineage, so an already-seen DEC-185 remains current immediately. Native scenario reset retains immutable decisions and audit while clearing simulated actions/annotations/grants; it does not erase DEC-185 to pretend it never existed. For a pristine timed native replay, use a separate disposable mock database through the existing ALICE_DATABASE_PATH setting; do not delete/reset the normal enrolled operator's database. A separate ArcFace-mode database requires its own console identity setup. Ordinary restart preserves agent responses, reconciliation and actions.

The sample evidence and risk changes are fixtures in `reassessedDecision()` and `fixtures/alice/reassessment.json`. No policy evaluator, anomaly algorithm, evidence verifier, agent reasoning engine or production transport has been added.

## Packaged popup rehearsal with real Face ID

For an explicitly requested local test build, set
`VITE_ALICE_MANUAL_CONTEXT_DEMO=true` before `npm run build:app`, and launch
with `ALICE_TRANSPORT_MODE=mock`, `ALICE_BIOMETRIC_MODE=arcface` and the existing
private biometric URL/token. Use a separate private console database so simulated
actions cannot change the normal console's history. Keep credentials and databases
out of Git. This is an opt-in build setting; `.env.example` leaves it false.

In that profile, a simulated HOLD waits for the technician to choose **Request
more context**, allowing time to sign in. The returned fixture context still leaves
the immutable decision HOLD and awaits upstream reassessment. **Approve once**
requires fresh native Face ID and records a simulated receipt; no protected action
executes. Remote mode and its existing context-delivery limitation are unchanged.

The sliders button exposes **Development scenarios → Reset scenario** in this
packaged test profile, so the same popup can be exercised again. Use the default
`03_hold_high_anomaly` for repeat context/approval tests. The normal build continues
to use automatic clarification and hides these controls in production.

Local setup and verification: [popup rebuild report](../../reports/2026-09-06-popup-testing-app.md).
