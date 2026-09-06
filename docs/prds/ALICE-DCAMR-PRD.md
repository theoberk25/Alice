# ALICE — Product Requirements Document

Current implementation includes signed terminal requests, exact grants, guarded
ext4 USB storage, physical eight-light serial control, automatic Wazuh audit delivery
and authenticated LAN web viewing. Full permissions/baseline activation, real Pi
scoring, native review responses and authority transfer remain. Requirements below
describe the full product; use the [current source map](../../architecture.md) for scope.

**Status:** Updated product direction; implementation and integration remain incremental

**Updated:** September 6, 2026

**Audience:** Product, Pi/runtime, anomaly, hardware, and technician-console contributors
**Scope:** Controlled demonstration of accountable agent operations across connected and disconnected conditions


## Current decision boundary — technician application

User clarification (2026-09-05): **ML classification runs on the Pi; the local
Mac resolves a held action to accept or deny after biometric verification.**
The backend transports the bound response; the Pi checks proof, currentness,
permissions, authority and audit prerequisites before hardware execution. Theo's
older Pi-owned final fusion does not govern this held-action choice. Existing
approval-only implementation evidence does not establish biometric gating of both
response paths. See the [corrected architecture](../../architecture.md) and
[technician integration contract](../integration/technician-console.md).

The [Pi assessment contract](../contracts/decision-assessment.md) supersedes earlier
Pi-owned final-fusion descriptions for the current increment. The Pi supplies
permission findings, contextual Isolation Forest scores, source provenance,
review signals and approval blockers. The technician application's local LLM
interprets those facts and explains Approve/Hold/Reject handling. **Unusual
actions require human technician approval**; neither LLM prose nor a facial
match overrides a hard prohibition or missing execution prerequisites.

`alice-decision-assessment-v1` is implemented, with decision and explanation null
and execution_authorized false. It is not a drop-in `alice.decision` event or an
execution token. The app must enforce the structured blockers outside the LLM
prompt. Transport/response binding, permission resolution and lightweight Pi
forest loading remain integrations. Existing historical decisions and scores
remain immutable; reassessments and subsequent app decisions are new records.
Automatic context push-back is not implemented by this slice.


## 1. Product purpose

ALICE — Authenticated Local Identity & Cyber Enforcement — is the complete product.
It keeps trusted information available for local agent governance when enterprise connectivity is lost, records agent activity, and gives an IT technician an accountable review path.

The product has exactly two operating modes: **ONLINE** and **OFFLINE/DDIL**.
Enterprise systems directly control execution ONLINE; ALICE synchronizes trusted information and observes authenticated activity feeds.
After a controlled handover, the Pi governs local execution OFFLINE/DDIL using the last trusted caches, local observations, a small anomaly model, and technician review.

The latest user decision explicitly selects direct enterprise execution ONLINE.
ALICE is not a mandatory online action gateway or an additional independent online preventive gate.
This supersedes earlier descriptions that placed the Pi inline for every action regardless of connectivity.

Returning online includes synchronization and reconciliation work; it does not introduce a third operating mode.
Distinguish the selected mode from whether execution authority, synchronization, or a particular service is ready.
The transfer of authority is a required future integration capability, not functionality already delivered by this document.

## 2. Terminology and compatibility

| Term | Meaning in this product |
| --- | --- |
| ALICE | The whole product: edge runtime, trusted caches, audit, and technician experience. |
| Permissions | User-facing name for mission/action authorization rules, previously called policy. |
| Normal behavior | Externally governed operational baseline against which local behavior is compared. |
| Enterprise | Authoritative online permissions, identity, security context, execution control, and central activity records. SIEM/EDR supply relevant context within that boundary. |
| OFFLINE/DDIL | One mode covering disconnected, disrupted, intermittent, or limited connectivity where local governance is required. |
| DCAMR | Legacy runtime/component name retained in existing paths, identifiers, and contracts where needed. |
| Facial verification | Local ArcFace identity matching; the user's informal “FaceID” does not mean Apple Face ID or an implemented liveness check. |

Use ALICE and permissions in product explanations and new user-facing copy.
Existing `policy` machine fields, `dcamr.*` events, and repository paths remain until their owners coordinate versioned adapters and tests.
The integrated console adapter provides legacy event normalization to `alice.*`; this does not establish compatibility with every schema in this repository.
Do not rename executable keys or reinterpret their meaning through documentation alone.

## 3. Two operating modes

| Responsibility | ONLINE | OFFLINE/DDIL |
| --- | --- | --- |
| Execution authority | Enterprise controls execution directly. | ALICE's Pi controls local execution after a verified handover. |
| Primary security context | Enterprise permissions, identity, and security services. | Last trusted, locally valid caches plus trusted local history and telemetry. |
| ALICE activity | Synchronize bounded caches, ingest authenticated activity, upload local records, show status. | Evaluate requests, challenge for context, route review, enforce and record outcomes. |
| Technician | Inspect status, decisions, exceptions, and reconciliation. | Review eligible held requests and provide scoped approval or rejection. |
| Connectivity recovery | Continue synchronization, reconciliation and acknowledged uploads after safe handback. | Reauthenticate recovered services, prepare handback and retain local records until acknowledged upload is possible. |

### 3.1 ONLINE behavior

Enterprise remains the source of truth and primary online security authority.
ALICE downloads permissions, normal-behavior summaries, identity/accountability mappings, and relevant enterprise/SIEM/EDR context needed for local operation.
Only bounded, selected context belongs on the Pi; ALICE is not a mirror of the enterprise's full event history.

ALICE receives authenticated enterprise/controller activity events and uploads its own activity records.
Because online execution bypasses ALICE, complete online visibility depends on the agreed enterprise feed, its coverage, delivery guarantees, and replay support.
Missing events, unknown coverage, stale feeds, and cursor gaps must remain visible; connectivity alone does not prove a complete audit.

### 3.2 OFFLINE/DDIL behavior

The Pi evaluates each local request using trusted permissions, the accepted behavioral baseline/model, cached evidence, and trusted local observations.
Permissions remain deterministic; anomaly scores describe unusualness and do not themselves grant execution authority.
The technician can review eligible holds without an external model API or enterprise service being available.

The local boundary must record every admitted request, decision, context exchange, technician action, and execution attempt/outcome.
Requests rejected before admission also need bounded audit/error records where the intake recorder is available; invalid input must not disappear as a successful operation.
Every request must be traceable to the authenticated agent and its responsible user or recorded assignment authority.

### 3.3 Transfer of execution authority

Exactly one authority may control a protected endpoint at a time.
The endpoint/controller contract must fence stale enterprise commands before offline local execution and stale local commands before enterprise execution resumes.
Agreement on transfer acknowledgements, ownership generations/epochs or equivalent fencing, deadlines, and recovery is still required.

A lost connection is not proof that enterprise commands have stopped executing.
A restored connection is not permission to replay queued local actions.
If ownership cannot be established, affected execution remains blocked while status and recoverable audit information remain available.

Held requests, in-flight requests, and unused approvals must be invalidated or explicitly revalidated against the new owner, current permissions, latest decision, and exact parameters.
Transition/readiness details are operational status within the two modes, not additional product-mode values.

### 3.4 Contextual fan-control sequence

The demonstration establishes three small fan-speed increases as synthetic normal
behavior. `cooling-agent-01` submits three separate `+10%` requests; each must be
authenticated, independently evaluated, executed only after ALLOW and recorded
with its resulting state. This fixture is demo data, not a production safety limit.

After the configured power threshold wakes `power-agent-01`, that agent requests
an abrupt fan shutdown. The request is permission-eligible, but the Isolation
Forest must classify it `ELEVATED` or `HIGH` relative to the recent cooling sequence
and fresh overheating telemetry. The Pi assessment therefore requires human
approval and the technician application presents HOLD. The workstation LLM may
recommend rejection from those bounded facts, while only the technician chooses
REJECT. No fan-off command executes and the final observed fan level remains the
last approved value. A hard prohibition still produces DENY; the fixture must
exercise review without weakening hard-deny rules.

## 4. Users and trust boundaries

| Actor/component | Responsibility | Authority boundary |
| --- | --- | --- |
| Autonomous agent | Propose actions and supply bounded context/evidence references. | Cannot grant itself permissions, edit trusted caches, rewrite history, or impersonate the responsible user. |
| Responsible user | Own or be accountable for an agent's assigned activity. | Mapping comes from authenticated assignment records, not an agent's claim. |
| Enterprise/controller | Control online execution and supply trusted data and activity. | Direct online authority; participates in the single-owner handover contract. |
| ALICE Pi runtime | Govern offline requests and produce authoritative local records. | Offline authority after handover; no permission increase caused by an outage. |
| IT technician | Inspect evidence and take an eligible review action. | Scoped approval; no hard-denial override or permanent privilege increase. |
| Technician console | Display immutable supplied facts, collect review actions, verify local identity. | Does not own permission rules, anomaly training or protected execution; enforces review controls around app decision handling. |
| Workstation LLM | Interpret Pi assessments and explain decision handling. | Cannot fabricate evidence, rewrite historical decisions, clear hard blockers, approve unusual actions without a human, or execute tools. |

The user responsible for an agent and the technician reviewing a request are separate accountability fields, even if the same person fills both roles.
Unknown or stale ownership must be labelled and handled through the agreed identity/permissions rule rather than filled in from prose.

## 5. Functional requirements

All requirements below describe target behavior unless Section 10 identifies a narrower implemented component.

### FR-1 — Mode and authority status

Expose exactly ONLINE and OFFLINE/DDIL, plus current execution owner, handover readiness, cache freshness, synchronization progress, and audit-feed health.
Do not display an unknown/unreceived service state as confirmed offline or imply execution readiness from a selected mode.

### FR-2 — Online synchronization

Authenticate the enterprise source and synchronize selected permissions, normal behavior, agent/user assignments, and relevant SIEM/EDR context into bounded caches.
Record source, scope, version, integrity identity, received time, and applicable validity/freshness rules.
Synchronization must not trigger automatic training, adaptive normalization, or silent model replacement.

### FR-3 — Online activity coverage

Agree an authenticated enterprise/controller feed for requests, authorization outcomes, execution events, and agent/user accountability.
Persist feed identity, coverage, stable event identifiers, cursors, acknowledgements, and detected delivery gaps.
ALICE must not claim it observed every online operation until feed completeness and recovery have been demonstrated.

### FR-4 — Controlled handover

Implement endpoint fencing so an ownership change cannot leave enterprise and ALICE both able to execute commands.
Reject stale-owner commands and handle partial transfers, lost acknowledgements, restart, and already executing actions.
Existing holds, approvals, and queued actions must not cross ownership changes automatically.

### FR-5 — Offline request normalization and accountability

Bind each request to authenticated agent identity, responsible-user assignment, mission, action, target, exact bounded parameters, and evidence references.
Allocate stable request identifiers and preserve the trusted assignment/source known at decision time.
Separate claimed identity, rejected input, and missing accountability from verified facts.

### FR-6 — Offline permissions

Evaluate accepted permissions deterministically for allowed, review-required, and prohibited actions.
A hard prohibition produces `DENY` without a context or technician-approval bypass.
Missing, invalid, expired, or unsupported authority must not create an automatic allow path; offline validity/grace policy requires explicit agreement.

### FR-7 — Local anomaly contribution

Use a frozen, compatible local model and baseline with bounded local history and selected telemetry for otherwise eligible requests.
Keep score direction, failure/null semantics, versions, and observation provenance explicit.
Preserve independent novelty flags even when the learned score is low; a model failure never produces a benign zero score.

### FR-8 — Offline fusion outcomes

Produce `ALLOW`, `REQUEST_CONTEXT`, `HOLD`, or `DENY` in the authoritative offline decision record.
Only a current authorization accepted by the active execution owner can permit execution; all other outcomes remain blocked.
Machine outcomes differ from technician actions and enterprise submission/execution receipts.

### FR-9 — Context and reassessment

Request schema-defined context within a bounded attempt/time budget and verify references independently.
Evaluate the final permitted response before holding an unresolved request; persuasive prose cannot override permissions or rewrite observations.
Reassessment creates a new immutable upstream decision linked to the prior/root decision for the same exact request; original decisions remain available.
The console waits for that new decision and must not generate its own risk, anomaly result, or fused outcome.

### FR-10 — Local audit coverage

Durably record request intake/admission or rejection, decisions, reasons, context, review, execution attempts, confirmed results, and ownership changes.
Include stable event/request/decision identifiers, agent-to-user accountability, reviewer identity, timestamps or explicit clock uncertainty, and source/cache/model identities.
Distinguish not executed, requested/submitted, confirmed executed, failed, and unknown results; a missing completion event is not proof of success.

### FR-11 — Audit integrity and capacity

Preserve original records and append later findings, acknowledgements, and reconciliation events.
Design tamper-evident records and a durable bounded outbox; neither exists merely because JSON fixtures or local console logs exist.
Reserve storage and stop admitting/executing consequential work before required audit durability is lost; surface disk-full, corruption, and retention failures.
Anomaly history may be bounded independently, but pruning must not silently delete required mission audit or unacknowledged uploads.

### FR-12 — Technician review and facial verification

This local authorization path applies to eligible OFFLINE held requests while ALICE owns execution.
During ONLINE, the console may display historical reviews but cannot independently authorize enterprise-controlled actions through this path.
Show permissions, anomaly/evidence facts, provenance, original/latest decisions, and eligible actions from authoritative supplied state.
Where biometric approval is required, obtain fresh local ArcFace verification for the exact latest decision/request and active technician; the current console grant lifetime is 60 seconds.
Prior facial login is not that approval check; a superseded decision must invalidate its old review/verification path.
ArcFace matching must not be represented as Apple Face ID, liveness, anti-spoofing, or proof that the camera saw a live scene.

### FR-13 — Approval delivery and execution confirmation

For an eligible OFFLINE hold, submit `APPROVE_ONCE` using authenticated, request-bound, expiring, one-use proof checked independently by the Pi while it remains the execution authority.
Keep submission acknowledgement, accepted approval, and actual execution confirmation separate.
A local verification UUID or renderer boolean is not remote proof; real proof transport, redemption, and execution receipts remain integration work.

### FR-14 — Returning ONLINE

Restore authenticated communication and complete the fenced ownership handback before assuming direct enterprise execution is safe.
The Pi synchronizes directly with enterprise; the technician reviews exceptions and is not required to relay the data through the console.
Resume uploads, request missing feed ranges, reconcile evidence, and refresh caches without changing original offline decisions.

### FR-15 — Durable uploads and priority alerts

Upload all DDIL audit with stable idempotency identifiers, durable retry state, bounded backoff, and acknowledged progress across restarts.
Prioritize risk, unresolved holds, discrepancies, and delivery failures while ensuring ordinary activity is also eventually uploaded.
Repeated delivery must not duplicate central activity or execute an old request; acknowledgement does not authorize log deletion outside the agreed retention policy.

### FR-16 — Cache activation and removable storage

Verify source authenticity, integrity, scope, compatibility, and validity before atomically activating coherent permissions/normal-behavior/model data.
Reject a bad candidate while retaining a still-valid active set; never combine incompatible versions or silently substitute stale authority.
Support the proposed single-USB layout without giving the agent write access to authoritative inputs or audit history.

### FR-17 — Workstation explanation

Keep local language-model interpretation on the Mac, separate from authoritative records and control paths.
Label original decisions, later responses, and reconciliation distinctly; unavailable interpretation must not prevent raw review.

## 6. Data placement and resource constraints

The target is a Raspberry Pi 4 Model B with **2 GB RAM**, running Raspberry Pi OS Lite.
The reported **64 GB is treated as storage**; OS bitness still needs confirmation.
Train and evaluate candidates on the Mac; the Pi is intended to run bounded frozen inference, permissions, state, audit, and integration services.

The proposed USB folders are `permissions/`, `normal_behavior/`, and `audit_logs/` on one device.
They have different write/trust rules: enterprise-governed inputs stay protected; ALICE appends audit through a controlled writer.
Legacy policy/ops-baseline names and earlier two-card/SD references need documented aliases or adapters, not an assumption that two physical media are still required.
Existing source folders `packages/mission_policy/` and `packages/ops_baseline/` are not renamed by this PRD.

Cache authenticated inputs locally so media removal or a lost link has an explicit outcome under their validity rules.
Sharing one device is not isolation by itself; ownership, filesystem access, full-storage behavior, and recovery need tests.
Keep large SIEM/EDR history, training corpora, model downloads, and unrestricted queues from overrunning the Pi.

The anomaly slice proposes 256 MiB steady worker RSS and 384 MiB load peak, one scoring worker, and bounded histories/payloads.
These are unmeasured budgets for one component, not proof that combined services fit or meet a deadline.
Measure total memory, latency, storage growth, temperature/throttling, and recovery with all intended services running.

## 7. Shared records and console integration

Coordinate versioned contracts for mode/authority status, requests, permissions, anomaly results, immutable decisions, context, technician actions/proofs, audit, uploads, and execution receipts.
Bind exact parameters and responsible-user assignment to the request; changing an action must not reuse old authorization.
Keep current operating status separate from status captured with a historical decision.

The integrated console defines `alice.decision`, status, agent/response, reconciliation, and technician-action schemas, with a linear reassessment chain and latest-decision guards.
Its current receipt declares `NOT_EXECUTED`; an `ACCEPTED` submission does not establish that a protected action ran.
Agree mappings for the four outcomes, permissions/legacy policy keys, score scales, challenges, lineage, remote proof, and execution results.

See [Technician console integration](../integration/technician-console.md) for the source-attributed handoff and unresolved protocol work.
The console's mock/remote transport and biometric settings are implementation settings, not extra product modes.

## 8. Demo scope and device direction

The latest likely device is an ESP with lights and a voltage sensor. Jared
selected before-action and after-action behavioral assessment and will supply
normal operating data later. The [general contextual model](../architecture/contextual-behavior-model.md)
now provides the bounded phase/profile interface. Actual sensor/action semantics,
source adapters, collected baselines and integrated execution remain pending.
Wazuh is the planned permissions-related context and auditing integration; its
ALICE action-permission mapping is still to be defined.

Demonstrate enterprise-controlled ONLINE activity and cache preparation, a fenced transition to OFFLINE governance, normal requests, a prohibition, context/reassessment, and technician review.
The primary DDIL story allows three normal `+10%` cooling changes, then holds one
power-agent shutdown request because it contradicts recent behavior and trusted
overheating evidence. The local LLM recommends continued cooling and the technician
rejects shutdown.
Return ONLINE to demonstrate acknowledged upload of every offline event, priority findings, appended reconciliation, and verified cache refresh.
Keep actions inside controlled synthetic/lab resources and label simulated enterprise feeds, decisions, proof, and execution separately.

The existing cyber cases remain regressions: diagnostics, occasional known-endpoint changes, new agents/endpoints, sequences, and bursts.
If a motor demonstration is retained, it needs a separate versioned profile and agreed commands, absolute/relative movement rules, physical limits, speed/duration, feedback, and safe-stop behavior.
Do not pass motor commands through the cyber model or claim a learned motor model/hardware control exists before implementation and measurement.

## 9. Team and repository boundaries

| Team member | Primary responsibility | Coordination boundary |
| --- | --- | --- |
| Alex | Technician dashboard and end-of-stream experience. | Consumes authoritative records; coordinates review and demo presentation. |
| Theo | Overall architecture, design, and product work. | Co-owns cross-component decisions and demo with Merek. |
| Merek | Overall architecture, design, and product work. | Co-owns cross-component decisions and demo with Theo. |
| Jared | Anomaly features, candidate evaluation, and result contract. | Supplies bounded contributions/provenance; does not redefine execution authority independently. |
| Xavier | Raspberry Pi and hardware. | Owns setup, storage/readers, physical constraints, and runbook. |
| Entire team | Integrated demonstration. | Shared acceptance and authority/contract agreements. |

Use the [current repository map](../../architecture.md#repository-map): core code in `dcamr/` and `common/`, development tools in `scripts/lab/` through the `lab.*` namespace, and the integrated console in `apps/desktop/`, shared `packages/` and `services/biometrics/`.
The old `workstation/` source layout is superseded; preserved empty scaffolds do not replace the active console.
The project is published on `main`; this PRD does not invent a `dev` integration branch or prescribe an unapproved branching change.

## 10. Implementation evidence and limitations

| Area | Evidence available | What remains unimplemented or unverified |
| --- | --- | --- |
| This repository's anomaly slice | Strict result boundary, 11-feature cyber builder, fixtures, bounded Mac Isolation Forest training, and global/conditional calibration experiments; original cyber suite: 103 tests passed; current totals are in the [tracker](../implementation-tracker.md). | Pi model/runtime deployment, production detection quality, motor profile, permissions/fusion, and execution integration. |
| Conditional calibration | Synthetic fresh evaluation reduced elevated/high normal-change results from 32/68 to 2/68; diagnostics increased from 23/1,132 to 38/1,132. Novelty flags stayed intact. | No adoption/deployment; some challenge score sensitivity decreased, so low bands cannot suppress novelty controls. |
| ONLINE/OFFLINE integration | Requirements and component fixtures. | Enterprise execution/feed integration, ownership fencing, real handover, signed cache activation, durable uploads, and authoritative end-to-end audit. |
| Integrated technician console | React/Tauri source, ArcFace service, Ollama gateway, immutable reassessment display and authenticated read-only physical-Pi feed are in the shared layout. [Verification](../guides/console/verification.md) records local checks. | Native authenticated response transport/proof and authoritative execution confirmation remain. |

The console handoff reports 91 default tests plus separate real-service checks; these are attributed results, not additions to the core repository's test count.
It states that console audit is not tamper-evident and that the app bundle does not include every Python/model/Ollama dependency.
Live enrollment/login does not demonstrate fresh approval, liveness, a connected Pi, or a complete distributed security boundary.

Details belong in [Anomaly training](../guides/anomaly-training.md), [Feature contract](../contracts/anomaly-features.md), and the [Anomaly PRD](anomaly-model-prd.md).
This is a hackathon/lab product. Production identity/key governance, liveness, hardened capture, fleet availability, distribution, and enterprise connector robustness remain future work.

## 11. Product acceptance checklist

These checks are planned; component or mock tests do not automatically complete them.

- [ ] **AC-1:** Exactly two product modes are shown, with separate ownership, readiness, freshness, and feed-gap status.
- [ ] **AC-2:** ONLINE enterprise executes directly; its authenticated activity feed provides accountability and recoverable cursor coverage.
- [ ] **AC-3:** Permissions, normal behavior, identity mappings, and selected context are cached within bounds without online retraining.
- [ ] **AC-4:** Connectivity changes cannot produce two owners, accept stale-owner commands, or automatically replay queued actions.
- [ ] **AC-5:** Offline normal work, hard prohibition, context reassessment, and human-review hold produce the intended audited outcomes.
- [ ] **AC-6:** Every local request/decision/execution is accounted for with agent-to-user attribution; missing identity, recorder failure, and unknown results are explicit.
- [ ] **AC-7:** Unavailable caches/model or low scores cannot bypass permissions, ownership, novelty handling, or mandatory review.
- [ ] **AC-8:** Fresh facial approval binds the latest exact decision/request; expired, replayed, superseded, and cross-request proof is rejected.
- [ ] **AC-9:** The real owner validates approval proof and reports execution separately from submission acknowledgement.
- [ ] **AC-10:** Reconnection uploads all DDIL audit durably/idempotently, prioritizes unresolved risk, and resumes after upload interruption/restart.
- [ ] **AC-11:** Reconciliation appends findings; cache replacement is authenticated/atomic; failed candidates preserve valid authority and original history.
- [ ] **AC-12:** USB removal/tamper/full-storage, combined Pi limits, and workstation outages have observable bounded outcomes.
- [ ] **AC-13:** Motor use waits for its agreed profile/command/physical-limit tests; cyber regressions continue to pass.
- [ ] **AC-14:** Three separately signed `+10%` fan changes receive ALLOW in sequence; a later permission-eligible shutdown receives HOLD, the technician rejects it, no fan-off command executes and all four histories remain auditable.
- [ ] **AC-15:** Removing the wireless enterprise host produces an explicit stale/offline enterprise display while static wired Pi, agent and technician paths continue without DHCP.

## 12. Next decisions and delivery checkpoints

Direct enterprise execution ONLINE is settled; ownership-transfer/fencing and enterprise feed coverage/recovery are next integration decisions.
Agree cache validity/grace, responsible-user assignment sources, retention/acknowledgements, and single-USB writer/recovery boundaries before connecting their code.
Agree console adapters, fresh remote proof, context/reassessment ownership, and execution receipts with the console team.
Confirm Pi bitness and combined budgets; settle motor semantics and physical limits before introducing its feature profile.

Deliver one reviewable contract or runnable component at a time, test its failure paths, and record measured evidence.
Do not describe these two-mode requirements, imported console progress, or synthetic experiments as a completed integrated deployment.
