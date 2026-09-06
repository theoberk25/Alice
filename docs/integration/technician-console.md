# Technician console integration

Updated: 2026-09-06 UTC (September 5 EDT). This is the active boundary between the
Pi/runtime and the technician workstation. Use the [integrated demo runbook](../guides/demo-runbook.md)
for network and launch steps and [upstream-alice.md](upstream-alice.md) for executable
event/action shapes.

## Current deployment

The React web app is the interim technician viewing surface. An authenticated
device on the isolated `192.168.50.0/24` LAN can open the hosted dashboard, load
the Pi's existing USB-backed event history and receive incremental events. The web
proxy keeps the feed bearer token server-side, uses an eight-hour in-memory session
and exposes no technician write endpoint.

The web app is intentionally read-only. Reject, Research, Hold and Approve once
remain disabled for physical Pi requests. A login proves access to the demo viewer;
it does not prove a technician identity or grant protected-system authority.

## Final workstation role

Integrate the native Tauri application when it is finished. Its source lives in
`apps/desktop/`; shared schemas and state live in `packages/`; ArcFace and Ollama
remain local workstation services. The 2 GB Raspberry Pi runs permissions,
behavioral scoring, fusion, enforcement and authoritative audit work. It does not
run the face model or language model.

The workstation owns:

- authenticated technician session and facial step-up;
- local LLM explanation of supplied scores, factors, policy results and evidence;
- display of immutable decisions, lineage, source versions and execution results;
- a human accept/reject choice for an eligible current HOLD;
- submission of a bound response and local record of that submission.

The workstation does not evaluate permissions, train or rescore the Isolation
Forest, invent missing evidence, override hard prohibitions, select execution
authority or directly command the ESP.

## Authority and modes

| Mode | Execution owner | Console behavior |
| --- | --- | --- |
| ONLINE | Enterprise control systems | Display attributed state and synchronization; do not route an offline approval into enterprise execution. |
| OFFLINE | ALICE after confirmed authority transfer | Explain local assessment, collect eligible human review and submit a bound response to the Pi. |

Connectivity, transport mode and execution authority are separate. A router,
successful HTTP poll, face match or Wazuh upload cannot establish the control owner.
Pending grants must be invalidated or revalidated when authority or assessment
generation changes.

## Inbound display contract

The native app should consume the same immutable stream already used by the web
app, then add richer decision payloads as producers become available:

| Information | Required behavior |
| --- | --- |
| Request | Exact request ID/digest, agent, responsible user, mission, action, target and parameters |
| Permission result | Rule/grant IDs, hard prohibitions, approval requirement and verified package metadata |
| Anomaly result | Status, normalized score, calibrated percentile/classification, factors, model and baseline metadata |
| Evidence | Source, digest, verification, freshness and availability without invented trust |
| Decision | Immutable outcome/reason, context challenge and available technician actions |
| Execution | Separate attempt, controller receipt, completion/failure/unknown and observed state |
| System state | Mode, authority generation, cache readiness, connectivity and storage health |

The current compact runtime feed omits full request parameters and numeric anomaly
scores. Display those as unavailable until a versioned producer supplies them.
Never map fixture risk numbers into live model scores by assumption.

## Local LLM boundary

The LLM receives bounded structured evidence only after the Pi calculates policy
and anomaly outputs. It may explain why factors contributed to a HOLD, summarize
agent context and help the technician inspect alternatives. It returns structured
prose or informational intents. It cannot change the outcome, fabricate source
verification, approve an action, call protected tools or expose private reasoning.

If Ollama is unavailable, the console must retain the raw factors and human review
controls. An explanation failure must not become ALLOW or DENY.

## Anomalous fan-shutdown review

For the fan demonstration, show three completed `+10%` ALLOW requests followed by
one current shutdown HOLD. The HOLD must retain the power agent, responsible user,
exact `0%` request, permission result, `ELEVATED` or `HIGH` Isolation Forest result,
score/factors, recent action sequence, current temperature/trend, power-threshold
observation, evidence freshness and confirmed execution owner. Raw evidence remains
available if Ollama fails.

The LLM may recommend rejecting shutdown only from those supplied facts and must
label missing or stale measurements. Its recommendation remains advisory. The
technician chooses REJECT for the current shutdown assessment. Disable the action
if the assessment is superseded, authority is unknown or a hard blocker appears.
Show the bound rejection, absence of an execution attempt and unchanged fan state.

## Human approval boundary

Unusual actions require human approval. A reusable login session is insufficient:
approval requires a fresh one-use native grant, normally expiring after 60 seconds,
bound to the active technician, exact request digest, latest assessment/decision,
action parameters and authority generation.

The outbound response includes a unique action ID, technician ID, decision/request
bindings, `APPROVE_ONCE` or `REJECT`, proof reference/attestation, timestamp and
optional note. The Pi independently authenticates the console, verifies proof,
checks current HOLD eligibility and permission, and writes the response before
execution. Hard DENY is never overridable.

`ACCEPTED` means the Pi recorded the technician response. It does not mean the
controller accepted the command or the physical action completed. Those later
events must retain the same request/execution bindings.

## Reassessment and currentness

Only a HOLD with a required context challenge starts automatic push-back. Agent
responses are claims. The core verifies available evidence, rebuilds features,
rescoring and permissions, then emits a new immutable decision with lineage. The
console must not perform this reassessment itself.

A successor decision supersedes its parent for future action. Open dialogs and
unused biometric grants bound to the parent are invalidated. Missing ancestors,
competing branches, changed request identity and stale responses fail closed.
Historical decisions and late receipts remain visible under their original IDs.

## Transport requirements for the native app

1. Authenticate both ends of the Pi/workstation channel; keep trust material out
   of renderer JavaScript.
2. Validate every inbound event before updating native authoritative storage.
3. Resume by cursor with bounded history, duplicate/conflict detection and explicit
   stale/unavailable states.
4. Submit context and technician actions with idempotency keys, finite timeouts and
   request-bound receipts.
5. Keep renderer requests separate from native proof creation and consumption.
6. Never fall back to mock data when remote transport fails.

The current Vite proxy implements only authenticated read-only `GET /events`.
Do not extend it with approval writes. Connect writable review through the native
boundary after the Pi endpoint and proof contract are agreed.

## Acceptance gates

- A second LAN device can log into the web app, see a newly submitted Pi request,
  refresh without losing its session, log out, and receive no action capability.
- Native login and face enrollment work with the actual technician and camera.
- Wrong/disabled identity, expired session, stale decision and replayed proof fail.
- An eligible HOLD can be accepted or rejected once; the Pi records the response.
- Rejection produces no controller command. Approval produces at most one command
  and separately reports receipt, execution result and observed state.
- Tunnel loss retains history and recovers without simulation fallback.
- Authority transfer invalidates incompatible pending approvals.
- Three normal fan increments appear separately from the anomalous shutdown HOLD;
  rejecting shutdown produces no command and preserves the last approved fan state.

Current web viewing has passed against the physical Pi. Native remote response,
live facial approval, real LLM explanation against Pi model factors and full
authority-transfer acceptance remain pending.
