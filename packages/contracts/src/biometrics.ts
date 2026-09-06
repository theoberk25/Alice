import { z } from 'zod';
import { VerificationSchema } from './alice/commands';
export const BiometricOutcomeSchema = z.enum([
  'PASS',
  'FAIL',
  'INCONCLUSIVE',
  'UNAVAILABLE',
  'NOT_CONFIGURED',
]);
export const PoseRegionSchema = z.enum([
  'CENTER',
  'LEFT',
  'RIGHT',
  'UP',
  'DOWN',
  'UP_LEFT',
  'UP_RIGHT',
]);
/** Display-only frames; authentication samples remain owned by the native session. */
export const LiveBiometricPreviewSchema = z
  .object({
    session_id: z.uuid(),
    sequence: z.number().int().min(1).max(3000),
    jpeg: z
      .string()
      .min(1)
      .max(700_000)
      .regex(/^[A-Za-z0-9+/]*={0,2}$/),
  })
  .strict();
export type LiveBiometricPreview = z.infer<typeof LiveBiometricPreviewSchema>;
export const LiveBiometricSessionSchema = z
  .object({
    schema_version: z.literal('2.0'),
    session_id: z.uuid(),
    purpose: z.enum(['ENROLLMENT', 'LOGIN', 'APPROVAL']),
    state: z.enum([
      'CREATED',
      'CAPTURING',
      'EVALUATING',
      'SUCCEEDED',
      'FAILED',
      'CANCELLED',
      'EXPIRED',
    ]),
    policy: z.literal('alice.live-face.v3'),
    prompt: z.string().max(100),
    reason: z.string().max(500),
    coverage: z.partialRecord(PoseRegionSchema, z.number().int().min(0).max(2)),
    accepted_samples: z.number().int().min(0).max(360),
    controls: z.partialRecord(
      z.enum(['identity', 'quality', 'capture_integrity', 'pose', 'pad']),
      z
        .object({
          result: BiometricOutcomeSchema,
          model: z.string().min(1).max(200),
          reason: z.string().max(200),
          score: z.number().min(-1).max(1).nullable(),
        })
        .strict(),
    ),
    preview: z
      .string()
      .max(700_000)
      .regex(/^[A-Za-z0-9+/]*={0,2}$/)
      .nullable(),
    technician: z
      .object({
        technician_id: z.string(),
        username: z.string(),
        display_name: z.string(),
        role: z.string(),
        enabled: z.boolean(),
        enrolled: z.boolean(),
        enrollment_pending: z.boolean().optional(),
        enrollment_version: z.enum(['IDENTITY_ONLY_V1', 'MULTI_POSE_V2']).optional(),
      })
      .strict()
      .nullable(),
    verification: VerificationSchema.nullable(),
  })
  .strict()
  .superRefine((v, c) => {
    if (v.state !== 'SUCCEEDED') return;
    const required = ['identity', 'quality', 'capture_integrity', 'pose', 'pad'] as const;
    if (
      required.some((key) => v.controls[key]?.result !== 'PASS') ||
      (v.purpose === 'LOGIN' && !v.technician) ||
      (v.purpose === 'APPROVAL' && !v.verification) ||
      v.preview !== null
    )
      c.addIssue({ code: 'custom', message: 'Incomplete native success evidence' });
  });
export type LiveBiometricSession = z.infer<typeof LiveBiometricSessionSchema>;
export type BiometricIntent =
  | { purpose: 'ENROLLMENT'; technician_id: string }
  | { purpose: 'LOGIN'; username: string }
  | {
      purpose: 'APPROVAL';
      technician_id: string;
      decision_id: string;
      request_id: string;
      runtime_action?: 'APPROVE_ONCE' | 'REJECT';
    };
