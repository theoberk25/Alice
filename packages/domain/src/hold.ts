import {
  TechnicianActionSchema,
  type Decision,
  type TechnicianAction,
  type Verification,
} from '@alice/contracts';
export type HoldState =
  | 'IDLE'
  | 'DECISION_RECEIVED'
  | 'HOLD_RECEIVED'
  | 'AUTO_CONTEXT_REQUEST'
  | 'AWAITING_AGENT_RESPONSE'
  | 'AGENT_RESPONSE_RECEIVED'
  | 'REASSESSMENT_PENDING'
  | 'SUPERSEDED'
  | 'AWAITING_TECHNICIAN'
  | 'RESEARCHING'
  | 'HELD_BY_TECHNICIAN'
  | 'APPROVAL_REQUESTED'
  | 'BIOMETRIC_REQUIRED'
  | 'BIOMETRIC_VERIFYING'
  | 'BIOMETRIC_PASSED'
  | 'BIOMETRIC_FAILED'
  | 'APPROVAL_SUBMITTED'
  | 'REJECTED'
  | 'RESOLVED';
export type HoldEvent =
  | 'RECEIVE_HOLD'
  | 'REQUEST_CONTEXT'
  | 'CONTEXT_SENT'
  | 'CONTEXT_RECEIVED'
  | 'REASSESS'
  | 'REASSESSMENT_RECEIVED'
  | 'REVIEW'
  | 'RESEARCH'
  | 'HOLD'
  | 'REJECT'
  | 'APPROVE'
  | 'REQUIRE_BIOMETRIC'
  | 'VERIFY'
  | 'PASS'
  | 'FAIL'
  | 'SUBMIT'
  | 'CANCEL'
  | 'RESOLVE';
const review: Partial<Record<HoldEvent, HoldState>> = {
  RESEARCH: 'RESEARCHING',
  HOLD: 'HELD_BY_TECHNICIAN',
  REJECT: 'REJECTED',
  APPROVE: 'APPROVAL_REQUESTED',
};
const transitions: Partial<Record<HoldState, Partial<Record<HoldEvent, HoldState>>>> = {
  IDLE: { RECEIVE_HOLD: 'HOLD_RECEIVED' },
  HOLD_RECEIVED: { REQUEST_CONTEXT: 'AUTO_CONTEXT_REQUEST' },
  AUTO_CONTEXT_REQUEST: { CONTEXT_SENT: 'AWAITING_AGENT_RESPONSE', REVIEW: 'AWAITING_TECHNICIAN' },
  AWAITING_AGENT_RESPONSE: {
    CONTEXT_RECEIVED: 'AGENT_RESPONSE_RECEIVED',
    REVIEW: 'AWAITING_TECHNICIAN',
    ...review,
  },
  AGENT_RESPONSE_RECEIVED: { REASSESS: 'REASSESSMENT_PENDING' },
  REASSESSMENT_PENDING: { ...review, REASSESSMENT_RECEIVED: 'SUPERSEDED' },
  AWAITING_TECHNICIAN: review,
  RESEARCHING: { ...review, REVIEW: 'AWAITING_TECHNICIAN' },
  HELD_BY_TECHNICIAN: review,
  APPROVAL_REQUESTED: {
    REQUIRE_BIOMETRIC: 'BIOMETRIC_REQUIRED',
    SUBMIT: 'APPROVAL_SUBMITTED',
    CANCEL: 'AWAITING_TECHNICIAN',
  },
  BIOMETRIC_REQUIRED: { VERIFY: 'BIOMETRIC_VERIFYING', CANCEL: 'AWAITING_TECHNICIAN' },
  BIOMETRIC_VERIFYING: {
    PASS: 'BIOMETRIC_PASSED',
    FAIL: 'BIOMETRIC_FAILED',
    CANCEL: 'AWAITING_TECHNICIAN',
  },
  BIOMETRIC_PASSED: { SUBMIT: 'APPROVAL_SUBMITTED', CANCEL: 'AWAITING_TECHNICIAN' },
  BIOMETRIC_FAILED: {
    VERIFY: 'BIOMETRIC_VERIFYING',
    CANCEL: 'AWAITING_TECHNICIAN',
    HOLD: 'HELD_BY_TECHNICIAN',
  },
  APPROVAL_SUBMITTED: { RESOLVE: 'RESOLVED' },
  REJECTED: { RESOLVE: 'RESOLVED' },
};
export function transition(state: HoldState, event: HoldEvent): HoldState {
  // An upstream successor can arrive while a technician is reviewing or verifying.
  // Superseding an assessment never changes its immutable decision payload.
  if (event === 'REASSESSMENT_RECEIVED' && state !== 'IDLE' && state !== 'SUPERSEDED')
    return 'SUPERSEDED';
  const next = transitions[state]?.[event];
  if (!next) throw new Error(`Invalid HOLD transition: ${state} → ${event}`);
  return next;
}
export function canReview(state: HoldState) {
  return [
    'AWAITING_AGENT_RESPONSE',
    'REASSESSMENT_PENDING',
    'AWAITING_TECHNICIAN',
    'RESEARCHING',
    'HELD_BY_TECHNICIAN',
  ].includes(state);
}
export function validateApproval(
  decision: Decision,
  technicianId: string,
  verification: Verification | undefined,
  now = Date.now(),
  mode: 'mock' | 'remote' = 'mock',
) {
  if (decision.decision.result !== 'HOLD' || decision.policy.result === 'DENY')
    throw new Error('Only an upstream HOLD can receive technician approval.');
  if (!decision.technician_actions.available.includes('APPROVE'))
    throw new Error('Approval is not available for this decision.');
  if (!technicianId) throw new Error('Technician authentication required.');
  if (decision.decision.biometric_required_for_approval) {
    if (!verification || verification.result !== 'PASS')
      throw new Error('Fresh face verification required.');
    if (
      verification.decision_id !== decision.decision_id ||
      verification.request_id !== decision.request.request_id ||
      verification.technician_id !== technicianId
    )
      throw new Error('Face verification belongs to a different request or technician.');
    if (
      Date.parse(verification.timestamp) > now ||
      Date.parse(verification.expires_at) <= now ||
      now - Date.parse(verification.timestamp) > 60_000
    )
      throw new Error('Face verification expired.');
    if (mode === 'remote' && verification.provider !== 'arcface')
      throw new Error('Mock face verification is invalid for remote actions.');
  }
}
export function makeAction(
  decision: Decision,
  technicianId: string,
  action: TechnicianAction['action'],
  mode: TechnicianAction['mode'],
  verification?: Verification,
): TechnicianAction {
  if (decision.decision.result !== 'HOLD' || decision.policy.result === 'DENY')
    throw new Error('This upstream result cannot be overridden.');
  const available = action === 'APPROVE_ONCE' ? 'APPROVE' : action;
  if (!decision.technician_actions.available.includes(available))
    throw new Error('Action unavailable.');
  if (action === 'APPROVE_ONCE')
    validateApproval(decision, technicianId, verification, Date.now(), mode);
  return TechnicianActionSchema.parse({
    schema_version: '1.0',
    event_type: 'alice.technician_action',
    action_id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    decision_id: decision.decision_id,
    request_id: decision.request.request_id,
    technician_id: technicianId,
    action,
    biometric_verification_id: verification?.verification_id ?? null,
    note: '',
    mode,
  });
}
