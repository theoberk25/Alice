# Handoff — "Request more context" pipeline (Slice A + Slice B units)

Date: 2026-09-06. Branch: `feat/cloud-agent-enterprise-ingress`.
Plan: [request-more-context-pipeline](../plans/2026-09-06-request-more-context-pipeline.md).
Scope of this session: the human-decision beat (technician-initiated context
request) — Slice A complete end-to-end in mock mode, plus the verifiable,
self-contained Slice B backend units. Cross-runtime wiring (Rust command, Pi
HTTP intake, MCP delivery, runtime-feed mapping) is **not** wired here and is
listed under "Remaining".

## What changed

### Slice A — mock-mode demo (complete, verified)
- **Store action `requestContext(decisionId)`** —
  [`console.ts`](../../apps/desktop/src/state/console.ts). A deliberate technician
  control, separate from the automatic context request. It issues **Record 1**
  (`CONTEXT_REQUESTED` audit line via `log()` → `append_audit`), then calls
  `transport.requestClarification(deterministicClarification(d))`, reusing the
  challenge id already tracked for the assessment so the returned
  `alice.agent_response` binds. Guards: remote mode, historical/superseded
  assessment, non-`HOLD`/`DENY`, `context_challenge.required === false`, an
  existing response, and an in-flight request. New transient state
  `contextRequests` (reset in `start()`) marks the in-flight assessment; it does
  not persist.
- **Action-bar button "Request more context"** —
  [`App.tsx`](../../apps/desktop/src/app/App.tsx), styled `.context-button` in
  [`global.css`](../../apps/desktop/src/styles/global.css). Gated on
  `available && result === 'HOLD' && context_challenge.required && no response && not in-flight`.
- **Display**: unchanged. The returned response parks the flow at
  `REASSESSMENT_PENDING` (per [hold-workflow](../architecture/hold-workflow.md));
  the existing "Agent clarification" panel renders the blurb.

### Slice B — backend units (component-level, verified; not integrated)
- **Pi producer** — [`dcamr/challenge/challenge.py`](../../dcamr/challenge/challenge.py)
  (was a 0-byte placeholder). Pure builders + a pluggable `ContextChallengeProducer`
  that emits through an injected `append` (the runtime's `FirstLightRuntime._append`):
  - **Record 1 `CONTEXT_CHALLENGE`** — `detail {challenge_id, outcome:"ISSUED", reason_codes:["TECHNICIAN_REQUESTED_CONTEXT"]}`, attributed to the technician.
  - **Record 2 `CONTEXT_RESPONSE`** — `detail {challenge_id, outcome:"RECEIVED", reason_codes:[]}`, attributed to the agent.
  - **Design note (schema constraint):** each audit `detail` is
    `additionalProperties:false` in
    [`audit_event.json`](../../common/schemas/audit_event.json); the free-text
    **blurb cannot live in the ledger detail**. It rides a separate console
    projection, `agent_response_projection(...)`, which mirrors
    [`events.ts`](../../packages/contracts/src/alice/events.ts) `AgentResponseSchema`.
    This matches the plan ("the blurb text rides the console-facing projection").
- **Local-agent responder** —
  [`agent/challenge_responder.py`](../../agent/challenge_responder.py)
  (was a 0-byte placeholder). Deterministic 1–2 sentence blurb generator with an
  optional `generate(prompt)` (Ollama) path, a **deterministic fallback** derived
  from the held decision, and `safe_blurb` rejecting `<think>`/scratchpad/system-prompt
  leakage (mirrors `safeExplanation`). Only the justification may come from the
  model; expected effect, evidence references and alternatives stay grounded.

## Verification (commands run)
- `npx tsc --noEmit` — clean.
- `npx eslint` on changed TS — clean.
- `npx vitest run` — **146 passed / 16 files** (adds
  [`context-request.test.ts`](../../tests/console/context-request.test.ts) — 6,
  [`context-request-button.test.tsx`](../../tests/console/context-request-button.test.tsx) — 5).
- `.venv/bin/python -m pytest tests/test_challenge.py tests/test_challenge_responder.py` —
  **16 passed** (producer emits schema-valid `CONTEXT_CHALLENGE`/`CONTEXT_RESPONSE`
  validated against the v1 schema with an intact hash chain; responder ≤2 sentences +
  fallback + chain-of-thought guard covered).
- `.venv/bin/python -m pytest tests/test_audit_contract.py tests/test_audit_integrity.py` —
  unchanged, passing; full suite still collects (518 tests).

No device, Ollama, Tauri build, Pi runtime or live delivery was exercised.
Component success is not integrated acceptance.

## Remaining (integration; needs device/build to verify)
- **B1/B2 native path**: "Request more context" button in
  [`RuntimeReview.tsx`](../../apps/desktop/src/components/runtime/RuntimeReview.tsx)
  (recommend no biometric); un-stub `RemoteAliceTransport.requestClarification`
  → new Rust `submit_context_request` (mirror `submit_action`) → workstation
  bridge → new Pi endpoint.
- **B3 intake**: Pi handler that calls `ContextChallengeProducer(runtime._append).issue(...)`;
  expose pending challenges to the agent (MCP tool or ledger feed).
- **B4 delivery**: agent poll loop → `respond(decision, generate=ollama)` →
  `ContextChallengeProducer.respond(...)` for the audit record + publish
  `agent_response_projection(...)` via an MCP write tool (mirror `brief_mcp`).
- **B5 feed mapping**: `read_runtime_events` / `runtime_feed.py` map
  `CONTEXT_RESPONSE` (+ the projection blurb) → `alice.agent_response` for the
  console — no dashboard change.
- **B6 Wazuh**: both event types already in the enum; confirm create-only sync.
- **Open decisions** (plan §Open decisions) still stand for the native slice.

## Notes for the owner
- `current.md` is stale relative to this checkout (it names branch
  `codex/led-display`; git is on `feat/cloud-agent-enterprise-ingress`). Left
  untouched to avoid clobbering another objective's snapshot — please reconcile.
- The three filled placeholders (`dcamr/challenge/challenge.py`,
  `agent/challenge_responder.py`, `tests/test_challenge.py`) were tracked 0-byte
  files; filling them is the plan's B3/B4 intent.
