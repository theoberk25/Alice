# Trust boundaries and threat model

Updated: 2026-09-05. Scope follows the
[two-mode architecture](../prds/ALICE-DCAMR-Architecture.md). This is a design review
baseline. Most controls below are integration requirements, not implemented
security guarantees. It is not a certification or a claim of physical safety.

## Assets, principals and trust

Protect accepted permissions, baseline/model releases, user/agent delegation,
current execution ownership, exact-request approvals, local audit history,
enterprise credentials and technician identity material.

- Enterprise systems control execution directly ONLINE and provide authenticated,
  scoped context. A log entry is evidence, not automatically a permissions rule.
- ALICE governs local actions OFFLINE after a controlled authority transfer.
  Untrusted agents cannot choose their own authenticated identity, baseline,
  permissions, captured history or evidence-verification state.
- The protected controller enforces current authority, request binding and replay
  prevention. The LAN switch/router does not establish these properties.
- The Technician Mac verifies enrolled identity and submits scoped review intent.
  Native validation and remotely verifiable proof are separate from renderer state.
- The local LLM interprets supplied facts; it has no permission to authorize,
  recalculate authoritative decisions or invoke protected actions.
- Removable storage carries trusted inputs and generated outputs with different
  owners. An attached drive, valid JSON or matching content hash is not a trusted
  publisher identity.

## Threats and required responses

| Threat or failure | Required behavior | Current evidence / remaining boundary |
| --- | --- | --- |
| Both enterprise and Pi execute during an outage/recovery | Endpoint-enforced single authority; fence stale commands, approvals and retries; block ambiguous ownership. | Handover protocol/controller enforcement unimplemented. |
| Direct agent bypass while OFFLINE | Authenticate current-owner commands at the protected endpoint; bind exact parameters and execute once. | No executor or device-control integration. |
| Spoofed agent or user delegation | Resolve identity and agent-to-user/mission mapping from trusted credentials and permissions; retain unknown attribution. | Feature input assumes a trusted caller; authentication/permissions integration remains planned. |
| Malicious/expired/replayed cache release | Bound bytes; authenticate issuer and verify required signatures, versions, freshness and compatibility before atomic activation. | Baseline validation/digest binding implemented; issuer signatures, version activation and expiry enforcement remain planned. |
| Poisoning the normal baseline through recent logs or approvals | Use approved normal releases and frozen model/reference identities; never treat live actions or technician approval as training permission. | Mac synthetic lab is separated from inference; enterprise update path unimplemented. |
| Stale, fabricated or partial online activity feed | Authenticate source; keep stable IDs/cursors and explicit coverage/gaps. Do not claim complete observation of enterprise-controlled actions. | Online feed adapter and durable cursor recovery unimplemented. |
| Agent context or LLM prompt injection | Treat prose as claims; validate evidence locally; preserve binding; generated explanation cannot change permissions, scores or actions. | Core contract/features exist; full context/evidence loop planned. Console restrictions are handoff-reported. |
| Score mistaken for permission or compromise probability | Separate permissions, behavioral rank, explicit novelty and outer decision; preserve null failures. | Implemented anomaly contract; fusion still a skeleton and console score mapping unresolved. |
| Fake renderer PASS, stolen/replayed grant or wrong-request approval | Native identity/currentness checks plus short-lived remotely verifiable one-use proof; edge rechecks exact parameters, current assessment, authority and permissions. | Local native grant checks reported in console handoff; remote attestation/transport unimplemented. |
| Photo/video replay against facial matching | Do not claim liveness or anti-spoofing from ArcFace matching; define intended assurance and test live camera/negative cases before acceptance. | Real enrollment/login reported; liveness/anti-spoofing absent and live approval acceptance pending. |
| Superseded assessment approved during async work/restart | Preserve linear immutable lineage, reject stale dialog/grant use and associate late receipts with original records. | Console checks reported locally; distributed lineage, durable delivery and authority transitions pending. |
| Lost ACK causes duplicate motor action | Stable action/command IDs, durable outbox, idempotent receiving boundary and result recovery. Receipt is not execution proof. | Console current receipt says NOT_EXECUTED; end-to-end execution/recovery unimplemented. |
| Audit deletion, USB removal or disk exhaustion | Local durable retention/checkpoints and bounded quotas; explicit failure mode before unauditable consequential action; preserve unacknowledged events. | Mission audit/outbox writer unimplemented. Hash chaining alone cannot prevent complete deletion. |
| Cloud reconciliation rewrites history | Append new source-attributed findings; retain decision-time permissions, evidence availability, scores and outcomes. | Reconciliation schemas/services remain skeletons; console annotations reported separately. |
| False physical feedback | Distinguish command receipt, completion and independently measured state; label unavailable/simulated telemetry. | Controller/sensor selection and telemetry contract open. |
| Resource exhaustion or explanation-service failure | Bound inputs, queues/history/cache/outbox; make unavailable scoring explicit; keep LLM/face work on Mac and independent of protected execution. | Core input/history bounds implemented; worker deadlines, storage quotas and Pi measurements pending. |

## Identity material and audit separation

The supplied console handoff reports encrypted private embeddings in a separate
local service store, with native account metadata and audit in SQLite. Encryption
of embeddings is not a claim that the whole native database is encrypted or that
an attacker controlling the workstation cannot alter it. Interrupted enrollment,
re-enrollment and deletion need consistency/recovery across both stores.

Face images, embeddings, passwords and bearer tokens do not belong in Pi decision
records, enterprise uploads, LLM prompts or shared test reports. Use identity and
verification metadata with agreed access/retention. Distinguish console-native
security events from renderer events and from the Pi's durable mission audit.
The current console audit is not a tamper-evident mission record.

## Acceptance boundary

The demo must identify mocked sources and controls that are described but absent.
Host compromise, USB theft, unreliable clocks, source revocation and controller
loss need explicit assumptions; this draft does not claim resistance to all of
them. Select the proof, key-storage, expiry and fencing mechanisms as implementation
slices with their owners rather than treating this table as a completed design.

Use the [demo runbook](../guides/demo-runbook.md) for targeted outage, replay, supersession,
storage and recovery checks. Update evidence in the
[tracker](../implementation-tracker.md) only when the corresponding boundary is
implemented and tested; local component or public-image tests do not establish
end-to-end protection.
