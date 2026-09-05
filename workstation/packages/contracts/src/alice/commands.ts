import { z } from 'zod';
import { Timestamp } from './events';
const Id = z.string().min(1).max(200);
export const IntentSchema = z.strictObject({
  intent: z.enum([
    'EXPLAIN_DECISION',
    'SUMMARIZE_EVIDENCE',
    'SUMMARIZE_CONTEXT',
    'REQUEST_CLARIFICATION',
    'RESEARCH',
    'UNKNOWN',
  ]),
  decision_id: Id,
  question: z.string().max(2000),
});
export const ExplanationSchema = z.strictObject({
  summary: z.string().min(1).max(3000),
  evidence_ids: z.array(Id),
});
export const ClarificationSchema = z.strictObject({
  schema_version: z.literal('1.0'),
  event_type: z.literal('alice.context_request'),
  command_id: Id,
  timestamp: Timestamp,
  decision_id: Id,
  request_id: Id,
  agent_id: Id,
  challenge_id: Id,
  requested_fields: z.array(
    z.enum([
      'mission_justification',
      'expected_effect',
      'evidence_references',
      'alternatives_considered',
    ]),
  ),
  question: z.string().min(1).max(2000),
});
export const VerificationSchema = z.strictObject({
  verification_id: Id,
  decision_id: Id,
  request_id: Id,
  technician_id: Id,
  timestamp: Timestamp,
  expires_at: Timestamp,
  result: z.enum(['PASS', 'FAIL']),
  provider: z.enum(['mock', 'arcface']),
  similarity: z.number().min(-1).max(1).optional(),
  threshold: z.number().min(0).max(1).optional(),
});
export const TechnicianActionSchema = z.strictObject({
  schema_version: z.literal('1.0'),
  event_type: z.literal('alice.technician_action'),
  action_id: Id,
  timestamp: Timestamp,
  decision_id: Id,
  request_id: Id,
  technician_id: Id,
  action: z.enum(['APPROVE_ONCE', 'HOLD', 'RESEARCH', 'REJECT']),
  biometric_verification_id: Id.nullable(),
  note: z.string().max(2000),
  mode: z.enum(['mock', 'remote']),
});
export const ActionReceiptSchema = z.strictObject({
  action_id: Id,
  status: z.enum(['ACCEPTED', 'PENDING', 'REJECTED']),
  execution_status: z.literal('NOT_EXECUTED'),
  message: z.string(),
});
export type StructuredIntent = z.infer<typeof IntentSchema>;
export type Explanation = z.infer<typeof ExplanationSchema>;
export type ClarificationRequest = z.infer<typeof ClarificationSchema>;
export type Verification = z.infer<typeof VerificationSchema>;
export type TechnicianAction = z.infer<typeof TechnicianActionSchema>;
export type ActionReceipt = z.infer<typeof ActionReceiptSchema>;
