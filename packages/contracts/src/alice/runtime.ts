import { z } from 'zod';
// Display contract for the bridge's validated audit feed. The owning audit JSON
// schema and semantic/hash checks run in services.runtime_feed before delivery.
const Id = z.string().min(1).max(128);
const Digest = z.string().regex(/^[0-9a-f]{64}$/);
const Time = z.iso.datetime({ offset: true }).nullable();
const Source = z.strictObject({
  source_id: Id.nullable(),
  source_event_id: Id.nullable(),
  observed_at: Time,
  confidence: z.enum(['TRUSTED', 'UNCERTAIN', 'UNAVAILABLE']),
  verification: z.enum(['VERIFIED', 'UNVERIFIED', 'UNKNOWN']),
  freshness: z.enum(['FRESH', 'STALE', 'UNKNOWN']),
  availability: z.enum(['AVAILABLE', 'UNAVAILABLE', 'UNKNOWN']),
});
const Artifact = z.strictObject({
  id: Id.nullable(),
  sha256: Digest.nullable(),
  missing_reason: z.enum(['MISSING', 'UNAVAILABLE', 'NOT_APPLICABLE', 'UNRECEIVED']).nullable(),
});
const Detail = z
  .object({
    outcome: z.string().optional(),
    reason_codes: z.array(z.string()).optional(),
    kind: z.string().optional(),
    status: z.string().optional(),
    result: z.string().optional(),
    contextual: z
      .object({
        model_id: Id.nullable(),
        model_fingerprint: Digest.nullable(),
        phase: z.enum(['PRE_ACTION', 'POST_ACTION']),
        context: z.array(z.strictObject({ key: z.string(), value: z.string() })),
        source_ids: z.array(Id),
      })
      .passthrough()
      .nullable()
      .optional(),
    source: Source.optional(),
    asset_id: Id.optional(),
    sensor_id: Id.optional(),
    origin: z.enum(['INDEPENDENT_SENSOR', 'ACTUATOR_FEEDBACK', 'SIMULATED']).optional(),
    property: Id.optional(),
    value: z.string().nullable().optional(),
    unit: z.string().optional(),
    quality: z.enum(['GOOD', 'DEGRADED', 'INVALID', 'UNAVAILABLE', 'UNKNOWN']).optional(),
  })
  .passthrough();
export const RuntimeEventSchema = z
  .strictObject({
    schema_version: z.literal('alice-audit-event-v1'),
    canonicalization_version: z.literal('alice-json-v1'),
    ledger_id: Id,
    node_id: Id,
    event_id: Id,
    sequence: z.number().int().positive(),
    event_type: z.enum([
      'REQUEST',
      'REJECTION',
      'ASSESSMENT',
      'DECISION',
      'CONTEXT_CHALLENGE',
      'CONTEXT_RESPONSE',
      'TECHNICIAN_ACTION',
      'EXECUTION_ATTEMPT',
      'CONTROLLER_RECEIPT',
      'EXECUTION_RESULT',
      'OBSERVED_STATE',
      'AUTHORITY_TRANSITION',
      'CACHE_ACTIVATION',
      'RECONCILIATION_FINDING',
      'RECORDER_FAILURE',
    ]),
    previous_hash: Digest,
    event_hash: Digest,
    outbox_id: Id,
    initial_state: z.literal('LOCAL'),
    time: z.strictObject({
      recorded_at: Time,
      confidence: z.enum(['TRUSTED', 'UNCERTAIN', 'UNAVAILABLE']),
      clock_source: Id,
      boot_id: Id,
      monotonic_ns: z.string().regex(/^\d+$/),
    }),
    correlation: z.strictObject({
      correlation_id: Id.nullable(),
      request_id: Id.nullable(),
      request_sha256: Digest.nullable(),
      assessment_id: Id.nullable(),
      action_id: Id.nullable(),
      execution_id: Id.nullable(),
      parent_event_id: Id.nullable(),
    }),
    attribution: z.strictObject({
      actor_kind: z.enum([
        'SYSTEM',
        'AGENT',
        'USER',
        'TECHNICIAN',
        'CONTROLLER',
        'SENSOR',
        'ENTERPRISE',
        'UNKNOWN',
      ]),
      actor_id: Id.nullable(),
      authenticated_requester_id: Id.nullable(),
      agent_id: Id.nullable(),
      responsible_user_id: Id.nullable(),
      delegator_id: Id.nullable(),
      technician_id: Id.nullable(),
      assignment_source_id: Id.nullable(),
      resolution: z.enum(['RESOLVED', 'UNRESOLVED', 'NOT_APPLICABLE']),
    }),
    authority: z.strictObject({
      product_mode: z.enum(['ONLINE', 'OFFLINE', 'UNRECEIVED']),
      connectivity: z.enum(['CONNECTED', 'DISCONNECTED', 'DEGRADED', 'UNKNOWN']),
      execution_owner: z.enum(['ENTERPRISE', 'ALICE', 'UNKNOWN']),
      authority_interval_ref: Id.nullable(),
      confirmation: z.enum(['CONFIRMED', 'UNCONFIRMED', 'UNKNOWN']),
    }),
    provenance: z.strictObject({
      policy: Artifact,
      baseline: Artifact,
      model: Artifact,
      calibration: Artifact,
      snapshot: Artifact,
      evidence: z.array(z.strictObject({ ref: Id, sha256: Digest, source: Source })),
    }),
    detail: Detail,
  })
  .superRefine((event, ctx) => {
    const fail = (message: string) => ctx.addIssue({ code: 'custom', message });
    if ((event.time.recorded_at === null) !== (event.time.confidence === 'UNAVAILABLE'))
      fail('Timestamp availability conflict');
    if (event.outbox_id !== event.event_id) fail('Event/outbox identity conflict');
    const outcomes: Record<string, string[]> = {
      REQUEST: ['RECEIVED', 'ADMITTED'],
      REJECTION: ['REJECTED'],
      DECISION: ['ALLOW', 'DENY', 'CHALLENGE', 'UNKNOWN'],
      EXECUTION_ATTEMPT: ['ATTEMPTED'],
      CONTROLLER_RECEIPT: ['ACCEPTED', 'REJECTED', 'UNKNOWN'],
      EXECUTION_RESULT: ['ACCEPTED', 'STARTED', 'COMPLETED', 'FAILED', 'UNKNOWN'],
    };
    if (
      outcomes[event.event_type] &&
      !outcomes[event.event_type]!.includes(event.detail.outcome ?? '')
    )
      fail('Invalid event outcome');
    if (
      event.event_type === 'ASSESSMENT' &&
      (!event.detail.status || !event.detail.result || !event.detail.kind)
    )
      fail('Missing assessment metadata');
    if (
      event.event_type === 'OBSERVED_STATE' &&
      (event.detail.value === undefined ||
        !event.detail.unit ||
        !event.detail.source ||
        !event.detail.quality ||
        !event.detail.asset_id)
    )
      fail('Missing observation metadata');
  });
export const RuntimeFeedSchema = z.strictObject({
  schema_version: z.literal('alice-runtime-feed-v1'),
  source: z.strictObject({
    connection: z.enum(['local-runtime', 'ssh-tunnel']),
    controller: z.enum(['mock', 'physical-serial', 'unavailable']),
  }),
  events: z.array(RuntimeEventSchema),
});
export const FeedStatusSchema = z.strictObject({
  event_type: z.literal('alice.feed_status'),
  state: z.enum(['connecting', 'live', 'disconnected', 'stale', 'unavailable']),
  last_success_at: z.number().nullable(),
  message: z.string(),
});
export type RuntimeEvent = z.infer<typeof RuntimeEventSchema>;
export type RuntimeFeed = z.infer<typeof RuntimeFeedSchema>;
export type FeedStatus = z.infer<typeof FeedStatusSchema>;
