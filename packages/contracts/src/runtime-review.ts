import { z } from 'zod';
const Id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
const RequestId = Id.max(64);
const Hash = z.string().regex(/^[a-f0-9]{64}$/);
export const RuntimeReviewActionSchema = z.enum(['APPROVE_ONCE', 'REJECT']);
const Execution = z.enum(['NOT_EXECUTED', 'COMPLETED', 'FAILED', 'UNKNOWN']);
export const RuntimeReviewStatusSchema = z.strictObject({
  ready: z.boolean(),
  reason: z.string().max(2000),
});
const DemoFanRequest = z.strictObject({
  schema_version: z.literal('alice-demo-fan-v1'),
  request_id: Hash,
  client_request_id: z.string().regex(/^[A-Za-z0-9_-]{1,64}$/),
  agent_id: RequestId,
  run_id: z.string().regex(/^[a-f0-9]{32}$/),
  expected_revision: z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER),
  action: z.literal('set_demo_fan_pct'),
  target: z.literal('DEMO-SERVER-01'),
  parameters: z.strictObject({ fan_basis_points: z.number().int().min(0).max(10000) }),
});
const DirectFanRequest = z.strictObject({
  schema_version: z.literal('1.0'),
  request_id: RequestId,
  agent_id: RequestId,
  action: z.literal('set_fan_speed'),
  target: z.literal('SERVER-ROOM-FANS'),
  parameters: z.strictObject({ value: z.number().int().min(0).max(100) }),
  issued_at: z.iso.datetime(),
});
const AnomalyAssessment = z.strictObject({
  status: z.literal('OK'),
  result: z.enum(['LOW', 'ELEVATED', 'HIGH']),
  score_ppm: z.number().int().min(-1_000_000).max(1_000_000),
  raw_score_ppm: z.number().int().min(-1_000_000).max(1_000_000),
  model_id: Id,
  model_fingerprint: Hash,
  reason_codes: z.array(Id).max(32),
});
export const RuntimeReviewSchema = z
  .strictObject({
    schema_version: z.literal('alice-runtime-review-v1'),
    request_id: RequestId,
    request_sha256: Hash,
    decision_event_id: Id,
    decision_event_hash: Hash,
    release_sha256: Hash,
    authority_interval_ref: Id.nullable(),
    runtime_epoch: Id,
    review_nonce: Id,
    request: z
      .strictObject({
        schema_version: z.literal('1.0'),
        request_id: RequestId,
        agent_id: RequestId,
        action: z.literal('set_light_state'),
        target: z.string().regex(/^ESP-LIGHT-0[1-8]$/),
        parameters: z.strictObject({ state: z.enum(['on', 'off']) }),
        issued_at: z.iso.datetime(),
      })
      .or(DirectFanRequest)
      .or(DemoFanRequest)
      .nullable(),
    decision: z.enum(['ALLOW', 'DENY', 'CHALLENGE', 'REJECTED']),
    review_state: z.enum(['PENDING', 'APPROVED', 'REJECTED']),
    accepted_action_id: Id.nullable(),
    accepted_action: RuntimeReviewActionSchema.nullable(),
    eligible: z.boolean(),
    reason: z.string().max(200),
    execution_status: Execution,
    // Native serialization emits null for an absent optional field, matching
    // assessment below. The Pi omits both unless the action is a fan action.
    decision_reason_codes: z.array(Id).max(32).nullish(),
    assessment: AnomalyAssessment.nullable().optional(),
  })
  .superRefine((v, c) => {
    const fail = (message: string) => c.addIssue({ code: 'custom', message });
    if (v.request && v.request.request_id !== v.request_id) fail('Conflicting request identity');
    if (
      v.eligible &&
      (!v.request ||
        !v.authority_interval_ref ||
        v.decision !== 'CHALLENGE' ||
        v.review_state !== 'PENDING' ||
        v.execution_status !== 'NOT_EXECUTED')
    )
      fail('Invalid review eligibility');
    if (
      (v.accepted_action_id === null) !== (v.accepted_action === null) ||
      (v.review_state === 'PENDING') !== (v.accepted_action_id === null) ||
      (v.review_state === 'APPROVED' && v.accepted_action !== 'APPROVE_ONCE') ||
      (v.review_state === 'REJECTED' && v.accepted_action !== 'REJECT')
    )
      fail('Conflicting accepted action');
    if (v.review_state === 'REJECTED' && v.execution_status !== 'NOT_EXECUTED')
      fail('Rejected review cannot execute');
  });
export const RuntimeReviewReceiptSchema = z
  .strictObject({
    schema_version: z.literal('alice-review-receipt-v1'),
    action_id: Id,
    request_id: Id,
    status: z.literal('ACCEPTED'),
    review_state: z.enum(['APPROVED', 'REJECTED']),
    execution_status: Execution,
    idempotent_replay: z.boolean(),
  })
  .superRefine((v, c) => {
    if (v.review_state === 'REJECTED' && v.execution_status !== 'NOT_EXECUTED')
      c.addIssue({ code: 'custom', message: 'Rejected review cannot execute' });
  });
export const RuntimeSubmissionSchema = z
  .strictObject({
    schema_version: z.literal('alice-native-review-submission-v1'),
    request_id: Id,
    action_id: Id,
    action: RuntimeReviewActionSchema,
    state: z.enum(['PENDING', 'ACCEPTED', 'UNCERTAIN']),
    created_at: z.iso.datetime({ offset: true }),
    receipt: RuntimeReviewReceiptSchema.nullable(),
    error: z.string().max(2000).nullable(),
  })
  .superRefine((v, c) => {
    if (
      (v.state === 'ACCEPTED') !== (v.receipt !== null) ||
      (v.receipt &&
        (v.receipt.action_id !== v.action_id ||
          v.receipt.request_id !== v.request_id ||
          v.receipt.review_state !== (v.action === 'APPROVE_ONCE' ? 'APPROVED' : 'REJECTED')))
    )
      c.addIssue({ code: 'custom', message: 'Conflicting submission receipt' });
  });
export type RuntimeReview = z.infer<typeof RuntimeReviewSchema>;
export type RuntimeReviewReceipt = z.infer<typeof RuntimeReviewReceiptSchema>;
export type RuntimeReviewAction = z.infer<typeof RuntimeReviewActionSchema>;
export type RuntimeSubmission = z.infer<typeof RuntimeSubmissionSchema>;
export type RuntimeReviewStatus = z.infer<typeof RuntimeReviewStatusSchema>;
