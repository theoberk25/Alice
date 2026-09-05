import { z } from 'zod';

export const Timestamp = z.iso.datetime({ offset: true });
const Id = z.string().min(1).max(200);
const Meta = { schema_version: z.literal('1.0'), timestamp: Timestamp };
const Severity = z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'NONE']);
const Package = z.object({
  package_id: Id,
  version: z.string(),
  signature_status: z.string(),
  source: z.string(),
});
export const DecisionSchema = z.object({
  ...Meta,
  event_type: z.literal('alice.decision'),
  decision_id: Id,
  reassessment: z
    .strictObject({
      previous_decision_id: Id,
      root_decision_id: Id,
      trigger: z.enum([
        'AGENT_CONTEXT_RESPONSE',
        'EVIDENCE_UPDATE',
        'TECHNICIAN_RESEARCH',
        'OTHER',
      ]),
      sequence: z.number().int().positive(),
    })
    .optional(),
  system: z.object({
    node: Id,
    mode: z.enum(['DDIL', 'CONNECTED', 'DEGRADED']),
    cloud_connected: z.boolean(),
    siem_connected: z.boolean(),
    edr_cloud_connected: z.boolean(),
    local_dashboard_connected: z.boolean(),
  }),
  request: z.object({
    request_id: Id,
    agent_id: Id,
    agent_known: z.boolean(),
    mission_id: Id,
    mission_type: z.string(),
    action: Id,
    target: Id,
    parameters: z.record(z.string(), z.json()),
    state_changing: z.boolean(),
  }),
  source_packages: z.object({ policy: Package, operations_baseline: Package }),
  policy: z.object({
    result: z.enum(['ALLOW', 'REVIEW', 'DENY']),
    rule_id: Id,
    rule_description: z.string(),
    policy_package: Id,
    policy_version: z.string(),
  }),
  anomaly: z.object({
    model: z.string(),
    model_version: z.string(),
    raw_score: z.number(),
    baseline_percentile: z.number().min(0).max(100),
    risk_score: z.number().min(0).max(100),
    severity: Severity,
    factors: z.array(
      z.object({
        id: Id,
        label: z.string(),
        severity: Severity,
        value: z.json(),
        baseline_value: z.json(),
        source: z.string(),
      }),
    ),
  }),
  evidence: z.object({
    verified: z.number().int().nonnegative(),
    unverified: z.number().int().nonnegative(),
    pending_external_verification: z.number().int().nonnegative(),
    items: z.array(
      z.object({
        evidence_id: Id,
        claimed_by_agent: z.boolean(),
        status: z.enum([
          'VERIFIED_LOCAL',
          'VERIFIED',
          'UNVERIFIED',
          'PENDING_EXTERNAL_VERIFICATION',
          'NOT_FOUND',
          'UNAVAILABLE',
        ]),
        source: z.string(),
      }),
    ),
  }),
  context_challenge: z.object({
    required: z.boolean(),
    challenge_id: Id.nullable(),
    attempt: z.number().int().nonnegative(),
    status: z.enum(['NOT_REQUIRED', 'PENDING', 'REQUESTED', 'RECEIVED', 'FAILED']),
    requested_fields: z.array(z.string()),
    agent_response: z
      .object({
        mission_justification: z.string(),
        expected_effect: z.string(),
        evidence_references: z.array(Id),
        alternatives_considered: z.array(z.string()),
      })
      .nullable(),
  }),
  decision: z.object({
    result: z.enum(['ALLOW', 'HOLD', 'DENY']),
    confidence: z.number().min(0).max(1),
    reason_codes: z.array(z.string()),
    execution_status: z.enum(['NOT_EXECUTED', 'EXECUTED', 'BLOCKED', 'PENDING', 'FAILED']),
    technician_required: z.boolean(),
    biometric_required_for_approval: z.boolean(),
  }),
  technician_actions: z.object({
    available: z.array(z.enum(['APPROVE', 'HOLD', 'RESEARCH', 'REJECT'])),
  }),
  mission_consistency: z.string().optional(),
});
export const StatusSchema = z.object({
  ...Meta,
  event_type: z.literal('alice.status'),
  node: Id,
  mode: z.enum(['DDIL', 'CONNECTED', 'DEGRADED']),
  connections: z.object({
    cloud: z.boolean(),
    siem: z.boolean(),
    edr: z.boolean(),
    technician_workstation: z.boolean(),
    protected_system: z.boolean(),
  }),
  packages: z.object({
    policy: z.object({ loaded: z.boolean(), version: z.string(), signature: z.string() }),
    operations_baseline: z.object({
      loaded: z.boolean(),
      version: z.string(),
      signature: z.string(),
    }),
  }),
  decision_engine: z.object({
    policy_engine: z.string(),
    anomaly_engine: z.string(),
    enforcement_gateway: z.string(),
  }),
});
export const ReconciliationSchema = z.object({
  ...Meta,
  event_type: z.literal('alice.reconciliation'),
  original_decision_id: Id,
  cloud_restored: z.boolean(),
  evidence_results: z.array(
    z.object({
      evidence_id: Id,
      original_status: z.string(),
      reconciled_status: z.enum(['VERIFIED', 'NOT_FOUND', 'UNAVAILABLE']),
    }),
  ),
  result: z.object({
    status: z.enum(['DISCREPANCY_FOUND', 'VERIFIED', 'PARTIAL']),
    original_decision_changed: z.literal(false),
    technician_review_recommended: z.boolean(),
  }),
});
export const AgentStatusSchema = z.object({
  ...Meta,
  event_type: z.literal('alice.agent_status'),
  agent_id: Id,
  agent_type: z.string(),
  model: z.string(),
  status: z.enum([
    'STARTING',
    'IDLE',
    'RUNNING',
    'WAITING_FOR_CONTEXT',
    'VERIFYING_EVIDENCE',
    'AWAITING_REVIEW',
    'COMPLETED',
    'FAILED',
    'TERMINATED',
    'OFFLINE',
  ]),
  mission_id: Id,
  current_activity: z.object({ type: z.string(), label: z.string() }),
  health: z.enum(['HEALTHY', 'DEGRADED', 'FAILED', 'UNKNOWN']),
});
export const ServiceStatusSchema = z.object({
  ...Meta,
  event_type: z.literal('alice.service_status'),
  service_id: Id,
  label: z.string(),
  status: z.enum(['READY', 'RUNNING', 'WAITING', 'IDLE', 'OFFLINE', 'FAILED', 'UNAVAILABLE']),
  detail: z.string().optional(),
});
export const AgentResponseSchema = z.object({
  ...Meta,
  event_type: z.literal('alice.agent_response'),
  decision_id: Id,
  request_id: Id,
  challenge_id: Id,
  agent_id: Id,
  response: z.object({
    mission_justification: z.string(),
    expected_effect: z.string(),
    evidence_references: z.array(Id),
    alternatives_considered: z.array(z.string()),
  }),
});
export const AliceEventSchema = z.discriminatedUnion('event_type', [
  DecisionSchema,
  StatusSchema,
  ReconciliationSchema,
  AgentStatusSchema,
  ServiceStatusSchema,
  AgentResponseSchema,
]);
export type Decision = z.infer<typeof DecisionSchema>;
export type Infrastructure = z.infer<typeof StatusSchema>;
export type AgentStatus = z.infer<typeof AgentStatusSchema>;
export type ServiceStatus = z.infer<typeof ServiceStatusSchema>;
export type Reconciliation = z.infer<typeof ReconciliationSchema>;
export type AgentResponse = z.infer<typeof AgentResponseSchema>;
export type AliceEvent = z.infer<typeof AliceEventSchema>;
