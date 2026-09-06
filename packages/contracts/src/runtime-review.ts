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
      .discriminatedUnion('action', [
        z.strictObject({
          schema_version: z.literal('1.0'),
          request_id: RequestId,
          agent_id: RequestId,
          action: z.literal('set_light_state'),
          target: z.string().regex(/^ESP-LIGHT-0[1-8]$/),
          parameters: z.strictObject({ state: z.enum(['on', 'off']) }),
          issued_at: z.iso.datetime(),
        }),
        z.strictObject({
          schema_version: z.literal('1.0'),
          request_id: RequestId,
          agent_id: RequestId,
          action: z.literal('set_fan_speed'),
          target: z.literal('SERVER-ROOM-FANS'),
          parameters: z.strictObject({ value: z.number().int().min(0).max(100) }),
          issued_at: z.iso.datetime(),
        }),
      ])
      .nullable(),
    decision: z.enum(['ALLOW', 'DENY', 'CHALLENGE', 'REJECTED']),
    decision_reason_codes: z.array(Id).max(32).optional(),
    assessment: z
      .strictObject({
        status: z.literal('OK'),
        result: z.enum(['LOW', 'ELEVATED', 'HIGH']),
        score_ppm: z.number().int().min(0).max(1_000_000),
        raw_score_ppm: z.number().int(),
        model_id: Id,
        model_fingerprint: Hash,
        reason_codes: z.array(Id).max(32),
      })
      .nullable()
      .optional(),
    review_state: z.enum(['PENDING', 'APPROVED', 'REJECTED']),
    accepted_action_id: Id.nullable(),
    accepted_action: RuntimeReviewActionSchema.nullable(),
    eligible: z.boolean(),
    reason: z.string().max(200),
    execution_status: Execution,
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
