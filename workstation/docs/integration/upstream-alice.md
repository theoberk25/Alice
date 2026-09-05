# Console contract reference for upstream ALICE

This is the migrated console's executable-contract reference, subordinate to the main [architecture](../../../docs/prds/ALICE-DCAMR-Architecture.md), [PRD](../../../docs/prds/ALICE-DCAMR-PRD.md), and [console integration requirements](../../../docs/integration/technician-console.md). Paths below are relative to `workstation/`. The [migration assessment](main-repository-migration.md) records contract ownership and unresolved differences. Shared schema promotion and real wiring are not part of the source migration. The console owns identity, explanation, presentation, request-scoped technician controls, and a local record. It does not own ALLOW/HOLD/DENY generation or protected action execution.

```text
ALICE upstream/core (agent/, dcamr/, cloud/, common/)
        ↕ structured contracts — real authenticated transport pending
workstation/ (packages/contracts/, domain and transport boundary)
        ↕
ALICE Technician Console (apps/desktop/, services/biometrics/)
```

## Current product authority and legacy compatibility

ONLINE means enterprise systems control execution directly. OFFLINE means local ALICE authority after controlled transfer and readiness checks. Reconnection is a workflow; the Pi synchronizes directly with enterprise systems. Existing console DDIL/CONNECTED/DEGRADED fields, mock/remote transport and mock/arcface identity are separate concepts, not an authority handshake. Current schemas do not define authenticated ownership/generation, transfer, or treatment of pending approvals. Preserve legacy payloads and require an agreed versioned protocol before connecting real control.

## Inbound events

All payloads are validated against version 1.0 Zod schemas before state changes. The supplied legacy `dcamr.decision`, `dcamr.status`, and `dcamr.reconciliation` remain supported through the compatibility adapter. New events use ALICE names.

| Event                  | Required binding and behavior                                                                                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `alice.decision`       | `decision_id` is immutable; `request.request_id` identifies the exact proposed action. Includes full policy, anomaly, evidence, system-at-decision, source packages, available actions, and biometric flag. |
| `alice.status`         | Current node, mode, connection flags, package state, engine state; independent of historical decision facts.                                                                                                |
| `alice.reconciliation` | `original_decision_id`; evidence results and discrepancy status. `original_decision_changed` must be false.                                                                                                 |
| `alice.agent_status`   | `agent_id`, `agent_type`, `model`, `status`, `mission_id`, `current_activity`, `health`. Model names are data.                                                                                              |
| `alice.service_status` | `service_id`, `label`, `status`, optional concise `detail`. No model-private reasoning.                                                                                                                     |
| `alice.agent_response` | Exact `decision_id`, `request_id`, `challenge_id`, `agent_id`, and structured response fields.                                                                                                              |

Use `packages/contracts/src/alice/events.ts` or the generated JSON Schemas as the executable definition. Examples are under `fixtures/legacy`, `fixtures/alice`, and `fixtures/scenarios`.

## Outbound automatic clarification

```json
{
  "schema_version": "1.0",
  "event_type": "alice.context_request",
  "command_id": "unique-idempotency-key",
  "timestamp": "2026-09-05T15:42:19Z",
  "decision_id": "DEC-20260905-000184",
  "request_id": "REQ-88291",
  "agent_id": "diagnostic-agent-04",
  "challenge_id": "CTX-441",
  "requested_fields": [
    "mission_justification",
    "expected_effect",
    "evidence_references",
    "alternatives_considered"
  ],
  "question": "Explain why the destination is required, the expected effect, verifiable evidence, and alternatives."
}
```

The first context request is automatic only on HOLD with `context_challenge.required=true` and does not depend on Ollama. The outbound adapter routes it to the appropriate agent. The agent response is a claim, not evidence verification and not a revised authorization. If the initial decision omitted a challenge ID, the console generates one; the upstream team must echo the issued challenge ID. A missing challenge ID response workflow should be agreed before remote integration.

## Outbound technician action

```json
{
  "schema_version": "1.0",
  "event_type": "alice.technician_action",
  "action_id": "unique-idempotency-key",
  "timestamp": "2026-09-05T15:45:00Z",
  "decision_id": "DEC-20260905-000185",
  "request_id": "REQ-88291",
  "technician_id": "TECH-001",
  "action": "APPROVE_ONCE",
  "biometric_verification_id": "native-single-use-grant-id",
  "note": "",
  "mode": "remote"
}
```

Actions are `APPROVE_ONCE`, `HOLD`, `RESEARCH`, or `REJECT`. The inbound capability `APPROVE` maps to the explicit outbound one-request `APPROVE_ONCE`. A verification ID is required when the upstream biometric flag is true; a prior login does not satisfy it. The UI cannot supply a `PASS` flag in an action instead of a valid native grant. A failed face match leaves the action held.

Expected receipt:

```json
{
  "action_id": "unique-idempotency-key",
  "status": "ACCEPTED",
  "execution_status": "NOT_EXECUTED",
  "message": "Technician request recorded; execution pending upstream confirmation."
}
```

Receipt status may be ACCEPTED, PENDING, or REJECTED. ACCEPTED acknowledges the technician request, not execution. A response must echo the action ID. Retrying a timed-out command must retain its action ID. The final edge implementation must verify console identity and the signed/bound approval attestation; a UUID is only a local reference, not a cryptographic proof that a remote node should trust on its own.

## Transport integration

`AliceTransport` isolates UI/state from transport. `MockAliceTransport` emits fixtures and simulates context and action acknowledgments. `RemoteAliceTransport` is a fail-closed skeleton with explicit unavailable errors.

Implement the real boundary in Rust, then bridge it through this interface:

1. Authenticate the edge/console connection. Agree TLS or mutually authenticated local-channel details and enrollment of console trust.
2. WebSocket inbound messages must validate and populate the native authoritative cache, then emit normalized events to the renderer. The current `cache_decision` command is mock-only by design.
3. POST context/action requests from native code with timeouts, explicit acknowledgments, and idempotency keys. Never report success from a disconnected fake implementation.
4. Export a signed, short-lived, exact-request biometric attestation, or agree a secure verification-ID redemption protocol. Keep the signing secret outside the renderer.
5. Agree reconnect cursors, ordering, duplicate handling, missed-event replay and execution-confirmation events; confirm the implemented reassessment lineage contract below with the upstream team. Conflicting repeated decision IDs are currently rejected.
6. Preserve the existing UI, HOLD machine, identity gateway, and display schemas.

## What is implemented and what is mocked

| Capability                                             | Initial repository status                                                        |
| ------------------------------------------------------ | -------------------------------------------------------------------------------- |
| Legacy/native validation and normalization             | Implemented and tested                                                           |
| Dashboard / DDIL / history / evidence / reconciliation | Implemented with rich synthetic edge fixtures                                    |
| HOLD state machine / auto context / technician actions | Implemented; edge routing and acknowledgment simulated                           |
| Native session and admin password verification         | Implemented with Argon2id, expiry, failed-attempt cooldown                       |
| Technician metadata and enrollment                     | Implemented; operator supplies their camera and identity                         |
| ArcFace detection / enrollment / identity comparison   | Implemented; real inference smoke tested on a public test image                  |
| One-use fresh approval grant                           | Implemented in native memory; remote attestation protocol still to agree         |
| Liveness / deepfake protection                         | Not implemented; explicitly shown as not configured                              |
| Ollama semantic gateway                                | Implemented, model configurable, structured fallback on outage                   |
| Native SQLite and local audit export                   | Implemented; upstream audit remains authoritative                                |
| Real WebSocket/REST transport                          | Skeleton; not connected to team infrastructure                                   |
| Protected-system execution                             | Deliberately absent; upstream responsibility                                     |
| macOS bundle                                           | Configured; services provisioned separately; distribution signing not configured |

The original fixture's outbound-open request and outbound-block justification conflict. This is presented as a technician review issue, never silently “corrected.” Migration preserves this legacy behavior and does not implement the newer ONLINE/OFFLINE authority-transfer requirements.

## Reassessment exchange and delivery constraints

```text
Technician Console
    | alice.context_request (only HOLD with context_challenge.required=true)
    v
ALICE Core / Agent
    | alice.agent_response (same decision/request/agent/challenge)
    v
Technician Console waits: REASSESSMENT_PENDING

ALICE Core reassesses
    | NEW alice.decision (new decision_id, same request, explicit lineage)
    v
Technician Console supersedes the previous workflow and displays CURRENT ASSESSMENT
```

The Technician Console never performs the policy/anomaly reassessment itself. The real ALICE core will perform policy/evidence/anomaly processing. Mock transport replays fixed values; the local Ollama gateway may summarize the agent's claims but cannot choose the result, calculate risk, validate evidence or authorize an action. All review and lineage rendering works with Ollama offline.

The optional `DecisionSchema.reassessment` object contains `previous_decision_id`, `root_decision_id`, `trigger` and positive integer `sequence`. Refer to `docs/contracts/alice-events.md` and the generated schema for allowed triggers and exact validation. For REQ-88291, DEC-185 follows DEC-184 with root DEC-184 and sequence 1; another successor must follow DEC-185 with root DEC-184 and sequence 2. All five request identity fields (`request_id`, `agent_id`, `mission_id`, `action`, `target`) stay equal. Existing originals omit lineage.

Parents must arrive before children during live ingestion. The current implementation rejects unknown parents and competing branches; it does not buffer them or invent their meaning. Persistence may return unordered records because hydration reconstructs and validates the whole chain. The team still needs to confirm this linear ordering rule and agree missing-event replay, compatibility negotiation and retry semantics before real transport is implemented. Do not invent WebSocket URLs, HTTP endpoints, authentication or ACK behavior.

Once DEC-185 is accepted, every new technician action uses DEC-185 / REQ-88291. A DEC-184 biometric grant is revoked locally and cannot authorize DEC-185. A modal or capture already in progress for DEC-184 is invalidated; a fresh DEC-185 capture is required when its biometric flag is true. The future upstream must independently enforce currentness and binding through the agreed attestation protocol. No remote attestation or protected execution is implemented here.

Local audit records preserve REASSESSMENT_PENDING, REASSESSMENT_RECEIVED, DECISION_SUPERSEDED and CURRENT_ASSESSMENT_UPDATED with decision/request correlation. Old decisions, evidence-at-assessment facts, actions and reconciliation annotations remain historical records. A late receipt for an action accepted before supersession remains attached to that historical assessment.
