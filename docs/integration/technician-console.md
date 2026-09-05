# Technician console integration

Repository migration note (2026-09-05): the console source is now located in
[`workstation/`](../../workstation/README.md), with its executable contracts,
fixtures and tests. See the [migration assessment](../../workstation/docs/integration/main-repository-migration.md)
and [new verification record](../../workstation/docs/development/verification.md#main-repository-migration-verification).
The earlier handoff-based assessment below is retained as historical context;
source colocation does not implement the cross-system agreements described here.

Updated: 2026-09-05. This document connects the ALICE core work to the separate
`ALICE_TechnicalReview` technician-console project. It is an integration agreement
draft, not a declaration that the two systems are connected.

Source: the console team's **ALICE Technician Console — complete implementation
handoff**, audited September 5, 2026. Its full 427-line `HANDOFF.md` was reviewed;
the external repository, schema exports and underlying test logs were not inspected
here. References to console implementation below are **handoff-reported**. Commands,
local account details and workstation-specific setup from that handoff are not
portable installation instructions and are not reproduced.

## Current evidence and component placement

| Boundary | Evidence and limitation |
| --- | --- |
| Console application | Handoff reports a working native Mac build, validated fixture ingestion, review controls, local persistence, immutable reassessment lineage and request-bound approval recording. Remote edge transport remains a fail-closed skeleton. |
| Facial identity | Handoff reports real enrollment and facial login, confirmed by its user and native audit records. Live approval step-up and negative operator cases remain pending; automated step-up used test images. |
| Console checks | Handoff records 91 default tests plus separately executed real ArcFace/Ollama checks. These results were not rerun or independently audited in this repository. |
| ALICE core | This repository's recorded verification is 103 tests covering anomaly contracts, cyber features and synthetic Mac model/calibration experiments. These are component/lab results, not live edge, permissions or execution acceptance. |
| Cross-system integration | Authenticated console/Pi transport, remotely verifiable approval, authoritative execution confirmation and the new ONLINE/OFFLINE control model are not implemented here. |

The reported current demo combines real ArcFace identity matching with mock edge
events. It is not a connected deployment of the ALICE Pi.

| Component | Reported stack | Placement |
| --- | --- | --- |
| Console UI | React, TypeScript, Vite, Zustand, Zod | Technician Mac |
| Native boundary and storage | Rust, Tauri 2, SQLite | Technician Mac |
| Biometric service | Python/FastAPI, InsightFace/ArcFace `buffalo_l`, ONNX Runtime CPU, encrypted embedding store | Technician Mac, configurable loopback service |
| Explanation service | Local Ollama, currently `llama3.1:8b` | Technician Mac |
| Decision computation | Core anomaly components; permissions, fusion and enforcement still need integration | Confirmed Raspberry Pi 4 Model B, 2 GB RAM |

The biometric models, camera processing and language model stay on the Mac.
They are not additions to the 2 GB Pi's resource budget. The console bundle does
not itself provision Python, biometric weights or Ollama. Installed dependencies
do not establish current service readiness or a reproducible clean-Mac installation.

## Product authority: ONLINE and OFFLINE

The following is the user's current product direction and a **new integration
requirement**, not behavior established by the console's existing DDIL fixtures.

| Mode | Decision and execution authority | ALICE and console role |
| --- | --- | --- |
| **ONLINE** | Enterprise controls govern and execute actions directly. | ALICE synchronizes/audits the authenticated feeds available to it. The console displays their attributed state; it must not route an offline ALICE approval into enterprise execution by assumption. |
| **OFFLINE** | ALICE governs local-agent actions using cached permissions, the normal baseline, ML, available evidence/telemetry and technician review where required. | The Pi must establish local readiness and enforce the resulting authorization. The console reviews, explains and submits scoped technician responses; it never executes protected tools itself. |

Reconnection is a workflow across these two modes. The Pi connects directly to
enterprise systems for audit synchronization, findings and cache updates; the
Technician Mac is not the enterprise relay. Control transfer must be confirmed
before commands from the new authority can execute. Historical records remain
immutable, and a retained upload backlog can drain after the transfer.

Transport configuration (`mock`/`remote`), biometric configuration (`mock`/`arcface`)
and product authority (`ONLINE`/`OFFLINE`) are three different dimensions. Existing
configuration names do not establish an authority-transfer protocol. A reachable
router, cached status or successful face login cannot select the control owner.

**Required before integration:** identify an authenticated mode/control owner,
readiness checks, control-transfer acknowledgement and a way to bind decisions
and approvals to the active authority generation. No wire field name or protocol
for that generation is agreed by this document. Offline cache validity, missing
enterprise feeds and failed handover need explicit blocked/unknown behavior.

Pending decisions include treatment of actions already requested, approved or
dispatched when authority changes. Preserve their records, and invalidate or
revalidate pending grants/actions under an agreed transition rule before use;
do not silently carry an offline approval into ONLINE operation. A late receipt
must stay attached to its original authority and request. Avoid concurrent owners
or duplicate execution during recovery.

Use **permissions** in operator-facing language. Existing machine keys such as
`policy` and legacy event names remain intact until a versioned adapter is agreed.
A deterministic permissions denial cannot be overridden by face matching,
technician approval, a low anomaly score or generated explanation.

## Reported wire boundary; schema exchange still required

The handoff describes these console contracts. This table preserves their names
and stated meaning; it is not a substitute for their full executable schemas.

| Direction | Name | Handoff-described content |
| --- | --- | --- |
| Inbound | `alice.decision` | Immutable upstream decision, request, policy, anomaly, evidence, source packages, system-at-decision data, capabilities and biometric requirement. |
| Inbound | `alice.status` | Current node/connectivity/mode/package/engine state, separate from historical decision snapshots. |
| Inbound | `alice.reconciliation` | Original decision binding and later evidence/discrepancy annotations; no historical rewrite. |
| Inbound | `alice.agent_status` | Agent identity/type/model, mission, health, activity and status. |
| Inbound | `alice.service_status` | Concise service operation/detail, excluding private model reasoning. |
| Inbound | `alice.agent_response` | Decision/request/agent/challenge bindings and structured new justification. |
| Outbound | `alice.context_request` | Command ID, timestamp, decision/request/agent/challenge bindings, requested context fields and question. |
| Outbound | `alice.technician_action` | Action ID, timestamp, decision/request/technician bindings, `APPROVE_ONCE`, `HOLD`, `RESEARCH` or `REJECT`, optional verification ID, note and mock/remote mode. |
| Inbound receipt | Event name not specified in the handoff | Echoed action ID, `ACCEPTED`, `PENDING` or `REJECTED`, message and currently `NOT_EXECUTED`. |

Exchange the console's Zod schemas, generated JSON Schemas and representative
fixtures before implementing the adapter. Confirm versions, required fields,
size limits, timestamp rules, errors and compatibility negotiation together.
The core's outer decision/request schemas do not yet provide a working shared
wire implementation. Do not invent omitted payload fields from example prose.

The console reportedly normalizes legacy `dcamr.*` events to `alice.*`. Preserve
request, decision, agent, evidence and package identifiers while translating
branding. The source example's action and prose can disagree; display that
conflict without changing the action. Overlapping pending/unverified evidence
counts cannot be added as independent totals.

The implemented core [anomaly result](../../common/schemas/anomaly_result.json) uses
`schema_version="1.0.0-draft.1"`: independent `status` and behavioral `result`,
nullable failure scores, normalized `score` in `[0,1]`, exact provenance and
structured factors. The [contract guide](../contracts/anomaly-contract.md) describes validation
and binding. Console legacy risk examples/presentation on a 0–100 scale do not
define an equivalent quantity. Neither dividing a legacy risk by 100 nor showing
`100 * score` establishes calibration compatibility or an authorization outcome.
Agree a versioned mapping and labels; keep missing values unknown and never
manufacture model results or overwrite the authoritative outer decision.

## Reassessment, currentness and execution boundaries

The reported automatic sequence is:

```text
HOLD_RECEIVED → AUTO_CONTEXT_REQUEST → AWAITING_AGENT_RESPONSE
→ AGENT_RESPONSE_RECEIVED → REASSESSMENT_PENDING
```

Only a HOLD with `context_challenge.required=true` starts the automatic request.
Agent prose does not resume authorization. The authoritative upstream component
must produce a new immutable `alice.decision`; the console does not recalculate
permissions, evidence sufficiency or model scores. Reported successor handling
marks the parent `SUPERSEDED` and creates a distinct current assessment.

The optional `DecisionSchema.reassessment` contains `previous_decision_id`,
`root_decision_id`, `trigger` and positive `sequence`. Reported checks require a
known current parent, the original root, sequence incremented by one and unchanged
request, agent, mission, action and target identities. Those are the handoff's five
identity comparisons; exact nested field paths/types must come from the schema
exports. Changed identity requires a new request. Full action parameters are
preserved; canonical parameter-digest semantics remain an integration decision.

The console reportedly rejects branches/unlinked duplicate originals, rebuilds
lineage during hydration, checks currentness in both UI and Rust, and revokes
old grants when a successor arrives. An open dialog bound to an old assessment
is blocked rather than retargeted. Preserve these checks across asynchronous
inference, persistence, submission, logout, disable and selection changes.

Live parent-before-child delivery is currently an assumption. Missing ancestors,
competing assessments, late responses, cancellation and replay require agreed
recovery behavior; do not invent a parent or turn incomplete history into current
authority. Persisted decisions/annotations are not yet a durable event protocol.

`APPROVE_ONCE` records technician intent. `ACCEPTED` acknowledges submission;
`PENDING` is unresolved; the existing receipt explicitly reports `NOT_EXECUTED`.
Neither a machine ALLOW nor an accepted approval proves protected execution.
Define separate authoritative execution-result reporting, including failure and
unknown outcomes. A controller acknowledgement or last commanded position is
also distinct from independently measured motor position.

## Facial identity and approval proof

The user's “FaceID” means **local facial identity matching**, not Apple Face ID.
The reported service compares a claimed technician's face with enrolled ArcFace
embeddings. Liveness, camera replay resistance and deepfake detection are not
implemented; a fresh verification operation does not prove a newly captured live
person. Keep that limitation visible without calling simulated checks biometrics.

Face login establishes a native session, not an approval grant. When required,
approval needs a fresh, one-use native grant bound to the active technician and
latest exact decision/request, with a **60-second** expiry. The reported native
path checks cached HOLD/permissions/capabilities, identity, binding and expiry,
then consumes the grant after successful local action recording. A renderer
boolean PASS cannot replace it. Hard denial remains non-overridable.

The handoff reports native administrator password authentication with Argon2id,
a 15-minute administrator session, and username-first facial login granting an
8-hour technician session. Administrators manage technician metadata, enable/
disable state and face enrollment, re-enrollment and removal. These are reported
console settings, not permission to approve any mission action. Logout, disable,
expiry and supersession must revoke the appropriate session/grants; immediate UI
expiry synchronization and cross-store recovery still need acceptance. Changing
mock/remote transport selects separate console data and does not provision or
transfer identities automatically.

Real camera enrollment/login are reported complete. Live approval and wrong
identity, blank/multiple-face, poor-light, denied-camera, retry/cooldown and revoked
identity cases still need operator acceptance in the packaged native webview.
Browser or public-image tests do not establish that acceptance.

The reported cosine-match threshold defaults to `0.45`; calibrate it with
representative consenting operators, cameras and lighting before claiming useful
false-match/nonmatch performance. It is a biometric comparison threshold, separate
from the Pi's anomaly percentile and from liveness assurance.

For remote use, choose a signed short-lived attestation or authenticated
verification-ID redemption protocol. A local random verification UUID alone is
not remote cryptographic proof. Bind console identity, technician, exact
decision/request, issuance/expiry, provider and one-use replay restrictions; align
this with current authority and action-digest semantics. The Pi must independently
reject fabricated, expired, replayed, superseded or wrong-console proofs.

Enrollment/admin operations, images and private embeddings stay on the console.
Do not send face material to the Pi, LLM, shared repository or integration reports.
Native enrollment metadata and the separate encrypted Python store need recovery
for interrupted updates, removal and re-enrollment. Native audit is local and
not tamper-evident mission audit; its current display limit does not bound storage.

## Language, transport and recovery requirements

The Mac LLM now interprets the [Pi assessment](../contracts/decision-assessment.md) and
explains decision handling. Unusual actions require human approval enforced by
application code; LLM output alone cannot clear that requirement, hard permission
prohibitions or missing prerequisites. It cannot invoke protected actions, alter
numerical facts or infer verification, readiness or execution from prose. Build
its context from the immutable assessment and bound request plus separately
labelled latest response/reconciliation. The new assessment is not yet an
`alice.decision` transport event; the application/transport adapter remains work. Agent claims are data,
not instructions to the console or evidence of permission.

The handoff reports remaining stale-context/readiness retry gaps. LLM outage or
malformed output needs an explicit explanation failure while validated facts and
permitted manual review remain available. Missing infrastructure state must be
unknown/unreceived, not silently classified as offline or ready.

Implement real authentication and ingestion/cache validation in the native
boundary; do not replace the mock transport with renderer-originated unauthenticated
HTTP. Agree actual endpoints and source identities rather than deriving them
from the biometric service's configurable loopback address.

Required delivery work includes a durable outbox, stable idempotency IDs, bounded
retries, receipts, stream cursors, replay and restart recovery. Define transactions
around grant consumption, durable submission and acknowledgement so a timeout
cannot create another authorization. Persist context/challenge correlation and
handle duplicate/late agent responses. Keep local security audit, renderer events,
upstream mission audit and execution evidence distinguishable.

The new mode display must identify trusted control owner, cache/feed freshness,
transfer readiness, unavailable sources and simulation independently of legacy
DDIL/cached-state labels. Reconnection audit delivery, alert retrieval and updated
permissions/baselines are direct Pi-to-enterprise integrations, not console jobs.

## Focused operator acceptance and open agreements

| Check | Required evidence before claiming integration |
| --- | --- |
| Native identity | Live enrollment/login and separate approval capture; negative camera/identity cases block; disable/logout/expiry revoke authority visibly. |
| Exact approval | Hard denial stays blocked; expired, wrong-request, reused and superseded grants fail at the authoritative native/edge boundaries. |
| Reassessment races | Agent response stays pending; only a validated successor changes currentness; old dialogs/grants fail during asynchronous work and restart recovery. |
| Authenticated transport | Actual upstream events appear with validated source identity; mock injection cannot enter a real session; malformed/missing-parent events remain blocked. |
| Delivery recovery | Crash/lost ACK/retry preserves one action identity and original binding; acknowledgement is shown separately from authoritative execution evidence. |
| Mode transfer | Controlled uplink loss/recovery establishes one ready owner; unknown/stale authority blocks consequential actions; old pending approvals are handled explicitly. |
| Direct enterprise sync | Pi delivers audit and obtains available alerts/cache updates directly; missing or unauthenticated feeds remain explicit, and history is not rewritten. |
| Explanation failure | LLM outage, malformed response and hostile agent prose cannot change scores, permissions, evidence states or approval controls. |
| Reproducible Mac setup | Packaged camera/export, service restart and store recovery work with recorded runtime/model configuration and no private identity data in reports. |

Open team agreements: full schema/version exchange and anomaly mapping; trusted
mode owner and transfer protocol; in-flight approval/execution treatment; remote
proof and parameter-digest protocol; distributed lineage/cancellation rules;
execution confirmation and physical feedback; durable delivery/audit ownership;
and acceptable identity/liveness assurances for the intended demo.

The handoff defers a complete UI/animation redesign until functionality and
operator acceptance are established. This integration document does not select
a UI library, initiate that redesign or authorize unrelated console changes.
