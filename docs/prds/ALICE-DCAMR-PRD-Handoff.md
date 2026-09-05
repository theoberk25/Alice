# ALICE / DCAMR — Developer Handoff

Updated: 2026-09-05. This handoff coordinates the current two-mode product and
the next integration increments; it does not claim that the full system runs.

- [Parent PRD](ALICE-DCAMR-PRD.md): current product scope and authority.
- [Architecture](ALICE-DCAMR-Architecture.md): components, trust and data flow.
- [Technician console integration](../technician-console-integration.md): the
  external console's reported contracts, implemented behavior and upstream gaps.
- [Implementation tracker](../implementation-tracker.md): all 118 original tasks.

The latest user-confirmed authority model takes precedence over older examples
that placed the Pi in every connected action path. The supplied technician
console `HANDOFF.md` describes the separate `ALICE_TechnicalReview` repository,
audited September 5, 2026. It is implementation evidence for that subsystem;
its older upstream assumptions do not redefine the current product modes.


## Current decision boundary — technician application

The [Pi assessment contract](../decision-assessment.md) supersedes earlier
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


## 1. Product boundary: exactly two modes

| Product mode | Execution authority | ALICE responsibility |
| --- | --- | --- |
| **ONLINE** | Existing enterprise systems control execution directly. | Synchronize trusted authorized permissions, normal behavior and relevant SIEM/EDR/mission caches; observe and audit upstream/downstream activity and agent-to-user accountability. |
| **OFFLINE / DDIL** | ALICE governs local agent requests using the last trusted caches, local ML, telemetry/history and IT technician review. | Evaluate requests, enforce permitted local actions through the protected controller, and record every request, decision, execution attempt and result. |

ONLINE synchronization and auditing do not require every enterprise action to
pass through the Pi for approval. Audit ingestion must distinguish enterprise
commands, observed device effects and missing information; observing an event
does not make ALICE the authority that authorized it.

During OFFLINE / DDIL operation, hard permission prohibitions remain binding.
A low anomaly score, persuasive agent response, local LLM explanation or facial
match cannot independently authorize an action or override a prohibition.
Every agent must remain attributable to its responsible user through a trusted
identity mapping; an agent-supplied username is not that mapping.

Reconnection is a handover and synchronization workflow, not a third product
mode. The Pi communicates directly with the cloud: publish the full DDIL audit,
flag risk/discrepancy findings, append reconciliation, and verify and atomically
activate updated caches. The technician is not a manual data relay.

Before transferring authority, the team must define a single-authority fence:
who currently controls the protected system, how that state is acknowledged,
and how old commands and outstanding approvals become unusable. Network
reachability alone must not switch execution authority. While ownership is
unresolved, the execution path must not accept competing or stale commands.
The handover protocol is a requirement; no epoch, lease or equivalent mechanism
has been selected or implemented by this documentation update.

## 2. Owners and deliverables

| Workstream | Owner(s) | Current handoff responsibility |
| --- | --- | --- |
| Dashboard and technician experience | Alex | External console, native identity/approval controls, event display, action submission and local explanations; coordinate the real core boundary. |
| Anomaly-model integration | Jared | Feature/result contracts, bounded model work, calibration evidence and anomaly provenance; keep behavioral observations separate from authorization. |
| Pi and hardware integration | Xavier | Pi provisioning, USB readers/storage, protected controller, local network, sensor feedback and hardware acceptance; coordinate workstation camera requirements with Alex. |
| Core integration and demo | Merek and Theo | Authority/synchronization design, shared contracts, permissions, fusion, enforcement, audit, reconciliation and integrated demo orchestration. |

The whole team participates in the demo. Ownership identifies the next reviewer
and dependency; it does not grant exclusive control of a folder or imply that
another workstream's missing component has already been delivered.

Each workstream increment should provide a short PRD or implementation note with:

1. The user-visible behavior and its ONLINE or OFFLINE authority boundary.
2. Exact repository files and the consumed/produced contract versions.
3. Implemented, simulated and proposed behavior stated separately.
4. Failure behavior, trust assumptions and required owner agreements.
5. Runnable component evidence and the integration acceptance still outstanding.

## 3. What exists now

### Alice core repository

The [enterprise simulation](../enterprise-sim-handoff.md) adds a deterministic
Sentinel AFB generator, signed demonstration permissions generations 42–44,
Wazuh configuration, cyber baselines, separate synthetic PRE_ACTION/POST_ACTION
voltage datasets and a local enterprise console. Regenerate the ignored datasets
on a Python 3.12 development machine before fitting. The enterprise console is
separate from the technician review application. Its audit history is authored
fixture data, not decisions captured from a live Pi.

Next, agree the permissions `resolve()`/fusion seam with core integration and
implement trusted package synchronization and durable audit delivery. USB ext4,
internal-authoritative audit storage and the voltage envelope remain proposals;
no electrical limits are approved by these fixtures. Model export to a verified
data-only artifact and resource measurements on the 2 GB Pi remain pending.

The anomaly implementation baseline for this revision is commit `18174cc` on
`main`; no `dev` branch was present in the inspected checkout. It contains the
bounded anomaly output contract, the Web-01 feature
builder, deterministic fixtures and the Mac synthetic training/comparison lab.
That baseline suite passed **103 tests**; the [tracker](../implementation-tracker.md)
records the current expanded suite. These are component/lab
checks, not proof of connected execution, DDIL governance or console integration.

The real Mac lab fits a small Isolation Forest in memory and records measured
synthetic results. Separate diagnostic/state-change calibration was compared
using unchanged raw scores and independent source lineage. No model is saved
for Pi loading, and neither candidate is accepted for deployment.

Policy/permissions evaluation, full decision fusion, package verification,
authority transfer, live transports, protected execution, persistent audit and
cloud reconciliation remain integration work. The `workstation/` files in this
repository are placeholders, not the external console's implemented application.

The new [contextual behavior model](../contextual-behavior-model.md) adds separate
PRE_ACTION/POST_ACTION profile validation, per-context forests and frozen normal
references, with source/time checks and explicit unavailable results. It consumes
supplied named features; actual ESP ingestion/voltage conversion and normal data
remain future work. Wazuh is selected as a planned permissions-related/audit
integration, with ALICE-specific mapping and adapters still to be agreed.

### External `ALICE_TechnicalReview` console

The supplied handoff reports a native macOS console with validated event
ingestion in mock transport, immutable decision history, reassessment lineage,
HOLD review, automatic clarification, native one-use approval grants and local
Ollama explanations. A later immutable decision supersedes an older assessment;
the console blocks stale dialogs/actions/grants rather than rewriting history.

It also reports real ArcFace inference, real camera enrollment and successful
facial login, corroborated there by operator confirmation and native audit.
Live camera **approval step-up** and its negative cases remain unconfirmed.
An earlier native step-up integration test used public test images; that is
different evidence from a person completing the packaged camera approval flow.

“Face ID” in this project means local ArcFace-based facial verification, not
Apple Face ID. Face login and fresh approval verification are separate checks.
Liveness, camera replay resistance and deepfake detection are not implemented.
The console's local verification ID is not a remotely verifiable attestation.

Real native edge transport, durable delivery/receipts and remote approval proof
are still pending. The current demonstration combines real biometrics with mock
edge events; it is not a connected ALICE deployment. The console's `mock`/`remote`
transport configuration and biometric provider choices are testing/integration
settings, not additional product modes.

## 4. Shared contracts: implemented versus proposed integration

There is no accepted complete wire payload in this handoff. The old illustrative
raw decision mixed incompatible score and band semantics and is removed. Use the
actual component schema for anomaly validation, then agree an explicit adapter
with the external console's executable schemas before publishing full examples.

| Boundary | Verified here or reported by the console | Integration still required |
| --- | --- | --- |
| Normalized request / trusted feature input | Core [feature-input schema](../../common/schemas/anomaly_feature_input.json) binds a request and trusted snapshot. | Public authenticated admission, user accountability, shared canonical action digest and authority binding; the generic action schema remains a skeleton. |
| Normal behavior payload | Core [baseline schema](../../common/schemas/anomaly_baseline.json) and byte-digest validation exist. | Signed package envelope, issuer/expiry/version checks, USB activation and model/reference compatibility. Payload validation is not package authentication. |
| Anomaly result | Core [nested anomaly schema](../../common/schemas/anomaly_result.json), [validator](../../dcamr/anomaly_engine/contract.py) and [contract guide](../anomaly-contract.md) exist. | A live evaluator and agreed embedding/adapter into the complete decision/event record. |
| Final decision | Console reports `alice.decision`, immutable snapshots, capabilities and optional reassessment lineage. | Exchange the console's executable schemas/fixtures and agree the core producer; [core decision schema](../../common/schemas/decision_record.json) is still a skeleton. |
| Status and activity | Console reports separate `alice.status`, `alice.agent_status` and `alice.service_status` events. | Authenticated producers, ONLINE audit/sync status versus OFFLINE authority status, freshness and unknown-value semantics. |
| Context exchange | Console reports `alice.context_request` and `alice.agent_response`, currently driven by mock routing. | Core-owned challenge policy, agent/user identity, correlation, bounded attempts, timeout/retry rules and fresh reassessment production. |
| Technician action | Console reports `alice.technician_action` with `APPROVE_ONCE`, `HOLD`, `RESEARCH` or `REJECT`; grants are locally bound and short-lived. | Authenticated native delivery, independent approval-proof validation, exact parameters/current assessment/authority binding and durable idempotency. |
| Submission receipt / execution | Console receipt reports `ACCEPTED`, `PENDING` or `REJECTED` and currently `NOT_EXECUTED`. | Separate controller-confirmed attempt/result events; accepted submission must never be displayed or audited as completed execution. |
| Reconciliation | Console reports append-only `alice.reconciliation` annotations against an original decision. | Direct Pi/cloud delivery of all DDIL audit, discrepancy rules, replay/order recovery and receipt-backed synchronization. |

Read the [console integration note](../technician-console-integration.md) for the
reported field names and compatibility gaps. The supplied handoff describes
Zod sources and generated JSON Schemas in the external repository; their full
payloads were not supplied as accepted core contracts. Do not invent replacements
from a prose summary or assume similarly named fields are already interchangeable.

### Rules the adapter must preserve

- The core anomaly score is a finite relative rank in `[0,1]`, not a probability
  of compromise or the console's overall risk display. Status, score and band
  are separate; non-OK results carry null scores and `UNKNOWN` results.
- Canonical anomaly objects require their complete metadata and valid field
  combinations. A thin legacy `{result, score, source}` object is insufficient.
  `FIXTURE` results remain confined to explicit lab paths.
- The fixed cyber feature flags are independent observations, not model
  attribution. Preserve novelty even when a conditional score is low; agree
  versioned mapping into the anomaly result instead of copying unknown enums.
- The core's four OFFLINE machine outcomes are `ALLOW`, `REQUEST_CONTEXT`,
  `HOLD` and `DENY`. The console currently automates context for a supplied HOLD
  with `context_challenge.required=true`. Agree this mapping without silently
  collapsing machine outcomes or creating a second challenge authority.
- A console `REASSESSMENT_PENDING` state is a workflow state, not a product mode
  or a newly authorized action. Only a fresh authoritative core decision can
  complete reassessment; technician/agent prose and Ollama cannot produce it.
- Console lineage currently assumes a linear parent-before-child chain with
  the same request/agent/mission/action/target. Exact remaining parameters and
  their digest, competing/missing parents and authority changes require agreement.
- Preserve original decisions and later annotations separately. A receipt,
  technician approval or reconciliation finding does not rewrite the original.
- Keep `policy` keys and legacy `dcamr.*` compatibility coordinated at the wire
  boundary. Renaming product terminology must not silently break existing parsers.

## 5. Trusted caches, USB and audit handoff

The desired removable-drive layout is:

```text
permissions/       authorized permissions and related trusted package data
normal_behavior/   normal-operation summaries and bound model/reference metadata
audit_logs/        ALICE-generated activity, decisions, attempts and results
```

**Authorized permissions** is the current product name replacing “policy.”
Existing code paths such as `packages/mission_policy/`, `dcamr/policy_engine/`
and wire fields named `policy` remain legacy identifiers until a coordinated
schema/path migration. The new `permissions/` layout is a requirement, not an
implemented loader or a reason to relabel unverified bytes as trusted.

ONLINE synchronization must maintain verified, versioned permissions, baseline
and relevant SIEM/EDR/mission caches for later disconnected operation. Required
cache coverage, validity under uncertain time, update cadence and storage bounds
need owner agreement. The agent cannot modify these trusted inputs or the audit.

OFFLINE audit must distinguish request receipt, context rounds, machine decision,
technician review, command attempt, acknowledgement and observed result, including
denials and failures. Keep event identity, user/agent attribution, correlation,
source/authority, time quality and provenance. Missing telemetry is an explicit
unknown; a requested movement does not prove the mechanism moved.

The Pi must publish the entire DDIL record set directly on reconnection, retain
the original history, flag risks and append reconciliation. Define durable upload
IDs, replay/deduplication, acknowledgements and recovery before treating a cloud
submission as delivered. Verified cache replacement must be atomic and compatible
with in-flight work and the authority fence. Nothing here implements that path.

USB removal, disk-full/corruption handling, local retention and permissions for
the audit output need a concrete runbook. Do not infer a safe continuation or
deletion rule merely from the selected folder layout.

## 6. Repository handoff and resource boundaries

Use paths that actually exist in this repository:

| Path | Responsibility |
| --- | --- |
| `common/schemas/` | Shared schemas; distinguish the implemented anomaly schemas from empty generic placeholders. |
| `dcamr/anomaly_engine/` | Implemented feature, baseline, history, result-validation and rank components; live evaluator remains pending. |
| `dcamr/` other components | Core permissions, fusion, APIs, packages, audit, state, reconciliation and enforcement integration. |
| `packages/` | Existing mission-policy/ops-baseline package skeletons and tooling; coordinate future permissions naming. |
| `lab/`, `tests/fixtures/`, `tests/` | Synthetic generation, replay/training/comparison and component acceptance. |
| `agent/`, `protected_systems/`, `cloud/` | Existing integration skeletons for request sources, controlled systems and external evidence. |
| `workstation/` | Placeholders here; do not claim the separate console was imported or implemented in these files. |
| `docs/` | Current PRDs, architecture, tracker, integration agreements and published lab evidence. |

Coordinate against an existing integration base; do not require a nonexistent
`dev` branch. Small branches/PRs should name the interface change and reviewers.
This documentation update adds no directory migration or branch policy.

The target Pi 4 has 2 GB RAM and Raspberry Pi OS Lite; OS bitness and combined
service footprint need hardware confirmation. Train on the Mac. Keep the LLM
and ArcFace on the Technician Mac, and plan a single bounded Pi scoring worker.
Current cyber measurements are Mac lab results, not Pi or motor acceptance.
The proposed 256 MiB steady/384 MiB load-peak anomaly budgets remain unmeasured.
Motor requests, feedback availability, physical limits and feature order require
their own contract; do not feed motor values into the Web-01 cyber model.

## 7. Next integration checkpoints

1. **Authority and cache synchronization:** define the ONLINE enterprise path,
   OFFLINE local path, trusted user/agent mapping, handover fence and compatible
   cache replacement. Demonstrate stale-command/approval rejection at transfer.
2. **Schema and adapter:** obtain external executable schemas and fixtures;
   agree decisions, context, status, permissions naming, full action binding,
   lineage and execution events. Validate both directions with real producers.
3. **Native transport and approval proof:** connect authenticated native console
   ingestion/submission; agree short-lived attestation or verification redemption.
   Exercise live camera step-up and reject fabricated, expired, replayed,
   superseded or cross-request approval proof at the core.
4. **Durable delivery and receipts:** implement context/action outboxes, stable
   IDs, bounded retries, grant-consumption transactions and receipt recovery.
   Distinguish submission acceptance from controller execution confirmation.
5. **Direct Pi reconciliation:** upload every DDIL event, recover after interrupted
   delivery, append risk/evidence findings and activate verified caches atomically.
   Exercise reconnect without manual technician relay or competing authority.
6. **Controller, telemetry and hardware acceptance:** agree motor command meaning,
   controller choice and independent feedback; bind execution to current authority
   and exact approvals, then measure actual Pi memory/latency and physical results.

These checkpoints are requirements, not code delivered by this handoff. Preserve
the cyber and contextual regression suites while adding real cross-component
tests. Complete the demo only when its authority, transport, identity provider,
audit delivery and independently observed execution are named in the evidence;
mock ACCEPTED events and successful face login do not establish that outcome.
