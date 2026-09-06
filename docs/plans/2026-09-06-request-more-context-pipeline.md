# ALICE — "Request more context" pipeline

Status: build spec, not yet implemented. Baseline: branch
`feat/cloud-agent-enterprise-ingress` at `46d9759` (after the `origin/main`
merge). Owners unassigned. Follow [repository rules](../../AGENTS.md); this
feature is the human-decision beat in
[the pitch narrative](../../deliverables/pitch-narrative.md) and the HOLD step
of [the demo runbook](../guides/demo-runbook.md). Background on the hold flow:
[hold-workflow](../architecture/hold-workflow.md).

## Context — what we're building

When a **HOLD** occurs and the technician chooses **Request more context**:

1. Two things leave the technician's machine at once:
   1. a record that *more info was requested* → written to the **audit log DB
      of record**;
   2. a request **directly to the local agent** (the agent's poller must see
      it) — routed however is most efficient for the current architecture.
2. The local agent produces a **1–2 sentence blurb** (the same style as the
   stream-of-thought reasoning it already generates) and sends it to:
   1. the **DB of record** — *"this was the answer the agent gave when more
      info was requested"*;
   2. the **dashboard UI** — so the technician has more context before deciding.

The human still makes the call; the agent only explains. The blurb is a
**claim, not a re-decision** (a returned context response parks the flow at
`REASSESSMENT_PENDING`; only a fresh `alice.decision` changes the outcome).

## What already exists — do NOT rebuild

- **Dashboard display is built.** The "Agent clarification" panel already
  renders the blurb: `contextSummaries[decision_id] ?? response.response.mission_justification`,
  with an `AWAITING RESPONSE → RESPONSE RECEIVED` badge and the
  `ClarificationTrack` rail —
  [`DecisionWorkspace.tsx:217-270`](../../apps/desktop/src/components/decisions/DecisionWorkspace.tsx).
  The store ingests `alice.agent_response` and fills `contextSummaries` —
  [`console.ts:426-459`](../../apps/desktop/src/state/console.ts).
- **Command contract exists.** `alice.context_request` = `ClarificationSchema`
  ([`commands.ts:20-38`](../../packages/contracts/src/alice/commands.ts));
  builder `deterministicClarification(decision)` and the LLM-worded
  `createAgentClarification(decision)`
  ([`llm.ts:25-43,71-77`](../../apps/desktop/src/lib/llm.ts)).
- **Working reference flows.** Auto-context on HOLD
  ([`console.ts:385-411`](../../apps/desktop/src/state/console.ts)); the manual
  LLM "ask" path `ask()` → `requestClarification` + `log('CLARIFICATION_SENT')`
  ([`console.ts:628-644`](../../apps/desktop/src/state/console.ts)).
- **Mock transport does the entire round-trip today.** `requestClarification`
  emits an `alice.agent_response` ~1200 ms later
  ([`transport.ts:33-86`](../../apps/desktop/src/lib/transport.ts)) — so a
  button wired to it demos end-to-end with no backend.
- **Hold state machine** already has the states/events: `REQUEST_CONTEXT`,
  `CONTEXT_SENT`, `CONTEXT_RECEIVED`, `REASSESS`
  ([`hold.ts`](../../packages/domain/src/hold.ts)).
- **Ledger event types exist** in the schema: `CONTEXT_CHALLENGE`,
  `CONTEXT_RESPONSE`, and `technician_action.intent` includes `PROVIDE_CONTEXT`
  ([`common/schemas/audit_event.json`](../../common/schemas/audit_event.json)).
  There is **no producer** yet (`dcamr/challenge/challenge.py` is 0 bytes).
- **Blurb generator to port.** The only working stream-of-thought generator is
  the demo's local Ollama agent — `propose()` returning `{thought, reason}`
  with a deterministic `_fallback` — `test-simulation/sim/agents.py`.

## The gaps to close

1. **No technician-initiated control.** Only the auto-fire and the free-text
   ask box exist. Action bar (mock path)
   [`App.tsx:316-343`](../../apps/desktop/src/app/App.tsx); native review bar
   [`RuntimeReview.tsx:294-312`](../../apps/desktop/src/components/runtime/RuntimeReview.tsx).
2. **Write channel disabled in remote/native.** Both
   `RemoteAliceTransport.requestClarification` and `submitTechnicianAction`
   throw ([`remote-transport.ts:104-113`](../../apps/desktop/src/lib/remote-transport.ts)).
   Native writes go through Rust `submit_action`
   ([`commands.rs:598`](../../apps/desktop/src-tauri/src/commands.rs)) → Pi
   `POST /review` ([`dcamr/main.py:610-623`](../../dcamr/main.py)), which only
   accepts `REQUEST_APPROVAL`/`REQUEST_DENIAL`
   ([`technician_review.py:33,323-325`](../../dcamr/technician_review.py)).
3. **No local-agent responder.** `Alice/agent/*` is empty; the working blurb
   generator lives only in `test-simulation/sim/agents.py`.
4. **No Pi producer** for `CONTEXT_CHALLENGE` / `CONTEXT_RESPONSE`.

## Architecture decision

Build on the **real native path + Pi ledger** (the live demo path per
`current.md`) and **reuse the existing display**. Model the two records as
first-class ledger events (the schema types already exist):

- **Record 1 — "more info requested"** = a `CONTEXT_CHALLENGE` audit event
  (`detail.context_challenge = {challenge_id, outcome: "ISSUED", reason_codes:
  ["TECHNICIAN_REQUESTED_CONTEXT"]}`), attributed to the technician.
- **Record 2 — "the agent's answer"** = a `CONTEXT_RESPONSE` audit event
  (`detail.context_response = {challenge_id, outcome: "RECEIVED"}`) carrying the
  blurb, attributed to the agent. The runtime feed maps it to the console's
  `alice.agent_response` so the dashboard renders it with zero UI change.

**Routing the request to the local agent (the "poller checks for this"):** the
agent already runs a poll loop. Most efficient given current architecture —
expose pending challenges through an MCP tool the agent polls (mirror the
Decision-Brief MCP), e.g. `get_pending_context_requests` + `publish_context_response`,
rather than giving the agent write access to the ledger internals. Alternative:
the agent tails the read-only ledger feed for open `CONTEXT_CHALLENGE` events.

## Build in two slices

### Slice A — Mock-mode demo (fast; UI-only, works end-to-end today)
Enough for the pitch: a real button that fires the existing round-trip.

- **A1. Button.** Add **Request more context** to the action bar
  [`App.tsx:316-343`](../../apps/desktop/src/app/App.tsx), gated on
  `d.decision.result === 'HOLD' && d.context_challenge.required` and no response
  yet. Style alongside Reject/Research/Hold/Approve.
- **A2. Store action.** On click: (i) `log('CONTEXT_REQUESTED', 'Technician
  requested additional context', decision_id)` → this is Record 1 into
  `local_audit_events` via `append_audit`; (ii) call
  `transport.requestClarification(deterministicClarification(d))` (or the LLM
  variant) — reuse the `ask()` template at
  [`console.ts:628-644`](../../apps/desktop/src/state/console.ts).
- **A3. Display.** Nothing to build — the mock transport emits
  `alice.agent_response`; the panel flips to `RESPONSE RECEIVED` and shows the
  blurb.
- **Acceptance:** in mock mode a HOLD gains a working button; clicking it flips
  the panel and shows the blurb; `read_console_history` audit contains a
  `CONTEXT_REQUESTED` line.

### Slice B — Real native pipeline (production)
- **B1. Native button.** Add **Request more context** to the native review bar
  [`RuntimeReview.tsx:294-312`](../../apps/desktop/src/components/runtime/RuntimeReview.tsx).
  Recommend **no biometric** (it is not an execution — see Open decisions).
- **B2. Console → Pi write channel.** Un-stub
  `RemoteAliceTransport.requestClarification`
  ([`remote-transport.ts:104`](../../apps/desktop/src/lib/remote-transport.ts))
  to call a new Rust command `submit_context_request` (mirror `submit_action`
  at [`commands.rs:598`](../../apps/desktop/src-tauri/src/commands.rs)) that
  POSTs through the workstation bridge
  ([`services/runtime_feed.py`](../../services/runtime_feed.py), which already
  has `do_POST`/`forward_review` at lines 105-141) to a new Pi endpoint. Also
  write Record 1 to `local_audit_events` locally for the console's own history.
- **B3. Pi producer + intake.** Add a Pi handler for context requests that
  emits **Record 1** (`CONTEXT_CHALLENGE`) via `FirstLightRuntime._append`
  ([`main.py:247`](../../dcamr/main.py)); implement the missing producer in
  `dcamr/challenge/challenge.py`. Expose pending challenges to the agent (MCP
  tool or the ledger feed).
- **B4. Local-agent responder.** Port the demo blurb generator
  (`test-simulation/sim/agents.py` `propose()` → `{thought, reason}` via Ollama
  `qwen2.5-tools`, with the deterministic `_fallback`). On a pending challenge:
  read the held decision's factors, produce a **1–2 sentence** justification,
  and write **Record 2** (`CONTEXT_RESPONSE` + blurb) through a write tool that
  mirrors the Decision-Brief MCP `publish_brief`
  ([`services/brief_mcp/server.py:92-143`](../../services/brief_mcp/server.py)).
  Guardrail: keep it a claim, no chain-of-thought — `safeExplanation` rejects
  `<think>`/scratchpad ([`llm.ts:17-24`](../../apps/desktop/src/lib/llm.ts)).
- **B5. Feed mapping.** Where the runtime feed serializes ledger events for the
  console (`read_runtime_events` [`commands.rs:150`](../../apps/desktop/src-tauri/src/commands.rs)
  / [`services/runtime_feed.py`](../../services/runtime_feed.py)), map
  `CONTEXT_RESPONSE` → the console's `alice.agent_response` shape
  ([`events.ts:197-210`](../../packages/contracts/src/alice/events.ts)) so
  `console.ts:426-459` ingests it and the panel renders — no dashboard change.
- **B6. Reconnect/Wazuh.** Both new events ride the existing create-only sync
  ([`cloud/wazuh_audit.py`](../../cloud/wazuh_audit.py)) with no rewrites/dupes.
  No new work — just confirm they pass schema validation (the enum already
  lists both types).

## Data contracts (concrete)

- **Record 1 — `CONTEXT_CHALLENGE`** (Pi ledger): `event_type:
  "CONTEXT_CHALLENGE"`; `correlation.request_id`/`assessment_id`;
  `attribution.actor_kind: "TECHNICIAN"`, `attribution.technician_id`;
  `detail.context_challenge: {challenge_id, outcome: "ISSUED", reason_codes:
  ["TECHNICIAN_REQUESTED_CONTEXT"]}`.
- **Record 2 — `CONTEXT_RESPONSE`** (Pi ledger): `event_type:
  "CONTEXT_RESPONSE"`; same `correlation` + `challenge_id`;
  `attribution.actor_kind: "AGENT"`, `attribution.agent_id`;
  `detail.context_response: {challenge_id, outcome: "RECEIVED", reason_codes:
  [...]}`. The blurb text rides the console-facing projection as
  `response.mission_justification` (the field the panel renders).
- **Dashboard event — `alice.agent_response`**
  ([`events.ts:197-210`](../../packages/contracts/src/alice/events.ts)):
  `{decision_id, request_id, challenge_id, agent_id, response:{
  mission_justification /* = the blurb */, expected_effect,
  evidence_references[], alternatives_considered[]}}`.
- **Console audit lines** (`local_audit_events`): `CONTEXT_REQUESTED` and
  `CONTEXT_RESPONSE_RECEIVED` via `log()` → `append_audit`.

## Open decisions (settle before Slice B)

1. **Biometric on the request?** Reject/approve require face verification; a
   context request is lower-stakes. **Recommend: no biometric** (it is not an
   execution and does not change the HOLD).
2. **New intent vs reuse.** Model Record 1 as `CONTEXT_CHALLENGE` (type exists)
   rather than adding a `technician_action.intent`. **Recommend: reuse
   `CONTEXT_CHALLENGE`** — avoids an audit-schema change.
3. **Where the agent runs / how it writes.** Same host as the Pi runtime
   (direct `_append`) vs an MCP write tool vs enterprise ingress. **Recommend:
   MCP write tool** mirroring `brief_mcp` — keeps the agent out of ledger
   internals.
4. **Multi-round.** `context_challenge.attempt` exists. **Recommend: allow N
   attempts, surface `attempt` in the panel.**

## Verification

- **Slice A:** mock mode — click on a HOLD ⇒ panel `AWAITING → RESPONSE
  RECEIVED`, blurb shown; `read_console_history` audit has `CONTEXT_REQUESTED`.
- **Slice B unit:** producer emits schema-valid `CONTEXT_CHALLENGE` /
  `CONTEXT_RESPONSE` (validate against
  [`common/schemas/audit_event.json`](../../common/schemas/audit_event.json));
  responder returns ≤2 sentences and the deterministic fallback is covered
  (style of `tests/test_thermal_demo.py`).
- **Slice B integration:** technician click ⇒ ledger gains `CONTEXT_CHALLENGE`
  then `CONTEXT_RESPONSE` with the hash chain intact (replay via
  [`dcamr/audit/validation.py`](../../dcamr/audit/validation.py)); dashboard
  shows the blurb; on reconnect both reach Wazuh
  ([`cloud/wazuh_audit.py`](../../cloud/wazuh_audit.py) `verify_stored`) with no
  duplicates.
- **Frontend:** extend `tests/console/` (e.g. `runtime-review.test.tsx`) for the
  new button and the `AWAITING → RECEIVED` transition.

## File index

| Area | File | Note |
|---|---|---|
| Action bar (mock) | `apps/desktop/src/app/App.tsx:316-343` | add button (Slice A) |
| Native review bar | `apps/desktop/src/components/runtime/RuntimeReview.tsx:294-312` | add button (Slice B) |
| Store: clarify/act | `apps/desktop/src/state/console.ts:385-411, 426-459, 628-644` | request + response handling |
| Clarification builder | `apps/desktop/src/lib/llm.ts:25-43, 71-77` | reuse |
| Display panel | `apps/desktop/src/components/decisions/DecisionWorkspace.tsx:217-270` | already renders blurb |
| Mock transport | `apps/desktop/src/lib/transport.ts:33-86` | full round-trip reference |
| Remote transport (stubbed) | `apps/desktop/src/lib/remote-transport.ts:104-113` | un-stub for Slice B |
| Command contract | `packages/contracts/src/alice/commands.ts:20-38` | `alice.context_request` |
| Agent-response contract | `packages/contracts/src/alice/events.ts:197-210` | dashboard event |
| Native write | `apps/desktop/src-tauri/src/commands.rs:598` | mirror for `submit_context_request` |
| Workstation bridge | `services/runtime_feed.py:105-149` | POST forwarding |
| Pi review/intake | `dcamr/main.py:193, 610-623` | add context-request handler |
| Pi challenge producer | `dcamr/challenge/challenge.py` (0 bytes) | build `CONTEXT_CHALLENGE`/`RESPONSE` |
| Audit schema | `common/schemas/audit_event.json` | event types already present |
| Blurb generator to port | `test-simulation/sim/agents.py` | Ollama `propose()` + `_fallback` |
| Brief-publish pattern | `services/brief_mcp/server.py:92-143` | model the agent write tool on this |
| Wazuh sync | `cloud/wazuh_audit.py` | reconnect delivery, no change expected |
