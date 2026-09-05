import { describe, it, expect } from 'vitest';
import { transition, validateApproval, makeAction, type HoldState } from '@alice/domain';
import type { Verification } from '@alice/contracts';
import { baseDecision, reassessedDecision } from '../../fixtures/scenarios';
import { safeExplanation } from '../../apps/desktop/src/lib/llm';
const proof = (): Verification => ({
  verification_id: 'V1',
  decision_id: 'DEC-20260905-000184',
  request_id: 'REQ-88291',
  technician_id: 'T1',
  timestamp: new Date().toISOString(),
  expires_at: new Date(Date.now() + 60_000).toISOString(),
  result: 'PASS',
  provider: 'mock',
});
describe('deterministic HOLD workflow', () => {
  it('follows automatic context through successful fresh approval', () => {
    let s: HoldState = 'IDLE';
    for (const e of [
      'RECEIVE_HOLD',
      'REQUEST_CONTEXT',
      'CONTEXT_SENT',
      'CONTEXT_RECEIVED',
      'REASSESS',
    ] as const)
      s = transition(s, e);
    expect(s).toBe('REASSESSMENT_PENDING');
    expect(() => transition(s, 'REVIEW')).toThrow();
    expect(transition(s, 'REASSESSMENT_RECEIVED')).toBe('SUPERSEDED');
    s = 'AWAITING_TECHNICIAN';
    for (const e of ['APPROVE', 'REQUIRE_BIOMETRIC', 'VERIFY', 'PASS', 'SUBMIT'] as const)
      s = transition(s, e);
    expect(s).toBe('APPROVAL_SUBMITTED');
  });
  it('cannot submit failed verification or bypass required state transitions', () => {
    expect(() => transition('BIOMETRIC_FAILED', 'SUBMIT')).toThrow();
    expect(() => transition('HOLD_RECEIVED', 'PASS')).toThrow();
  });
  it('allows controlled retry and cancellation', () => {
    expect(transition('BIOMETRIC_FAILED', 'VERIFY')).toBe('BIOMETRIC_VERIFYING');
    expect(transition('BIOMETRIC_REQUIRED', 'CANCEL')).toBe('AWAITING_TECHNICIAN');
  });
  it('requires a separate bound proof despite technician login', () =>
    expect(() => validateApproval(baseDecision(), 'T1', undefined)).toThrow());
  it('rejects an original decision grant for a reassessment of the same request', () => {
    const originalGrant = proof();
    expect(() => validateApproval(baseDecision(), 'T1', originalGrant)).not.toThrow();
    expect(() =>
      makeAction(reassessedDecision(), 'T1', 'APPROVE_ONCE', 'mock', originalGrant),
    ).toThrow(/different request/);
    const freshGrant = { ...proof(), decision_id: reassessedDecision().decision_id };
    expect(
      makeAction(reassessedDecision(), 'T1', 'APPROVE_ONCE', 'mock', freshGrant).decision_id,
    ).toBe('DEC-20260905-000185');
    expect(() => transition('SUPERSEDED', 'APPROVE')).toThrow();
  });
  it('rejects cross-request, cross-user, stale, future, failed and mock-to-remote proofs', () => {
    for (const change of [
      { request_id: 'OTHER' },
      { decision_id: 'OTHER' },
      { technician_id: 'OTHER' },
      { timestamp: new Date(Date.now() - 65_000).toISOString() },
      { timestamp: new Date(Date.now() + 65_000).toISOString() },
      { result: 'FAIL' as const },
    ])
      expect(() => validateApproval(baseDecision(), 'T1', { ...proof(), ...change })).toThrow();
    expect(() => validateApproval(baseDecision(), 'T1', proof(), Date.now(), 'remote')).toThrow();
  });
  it('does not override policy DENY even with a valid biometric', () => {
    const d = baseDecision();
    d.policy.result = 'DENY';
    expect(() => makeAction(d, 'T1', 'APPROVE_ONCE', 'mock', proof())).toThrow();
  });
  it('emits a single-request command without changing the upstream record', () => {
    const d = baseDecision(),
      before = structuredClone(d);
    const action = makeAction(d, 'T1', 'APPROVE_ONCE', 'mock', proof());
    expect(action.request_id).toBe(d.request.request_id);
    expect(action.action).toBe('APPROVE_ONCE');
    expect(d).toEqual(before);
  });
  it('rejects unavailable capabilities', () => {
    const d = baseDecision();
    d.technician_actions.available = [];
    expect(() => makeAction(d, 'T1', 'REJECT', 'mock')).toThrow();
  });
  it('rejects private reasoning and fabricated evidence references', () => {
    expect(() =>
      safeExplanation({ summary: '<think>private</think>', evidence_ids: [] }, []),
    ).toThrow();
    expect(() =>
      safeExplanation({ summary: 'Verified', evidence_ids: ['fake'] }, ['real']),
    ).toThrow();
  });
  it('still enforces output lengths after Ollama sampling constraints are relaxed', () => {
    expect(() => safeExplanation({ summary: 'x'.repeat(3001), evidence_ids: [] }, [])).toThrow();
    expect(() => safeExplanation({ summary: '', evidence_ids: [] }, [])).toThrow();
  });
});
