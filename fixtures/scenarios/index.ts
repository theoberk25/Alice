import rawDecision from '../legacy/decision.json';
import rawStatus from '../legacy/status.json';
import rawReconciliation from '../legacy/reconciliation.json';
import { normalizeEvent, type AliceEvent, type Decision, type AgentStatus } from '@alice/contracts';
export const scenarioNames = [
  '01_normal_allow',
  '02_hard_policy_deny',
  '03_hold_high_anomaly',
  '04_hold_context_rejustification',
  '05_hold_face_approval_pass',
  '06_hold_face_approval_fail',
  '07_ddil_cloud_offline',
  '08_reconnect_reconciliation',
  '09_agent_failure',
  '10_llm_offline',
] as const;
export type ScenarioName = (typeof scenarioNames)[number];
export function baseDecision(): Decision {
  return normalizeEvent(structuredClone(rawDecision)) as Decision;
}
// Predetermined mock-core output, never calculated by the console or the LLM.
export function reassessedDecision(): Decision {
  const next = baseDecision();
  next.decision_id = 'DEC-20260905-000185';
  next.timestamp = '2026-09-05T15:42:21.000Z';
  next.reassessment = {
    previous_decision_id: 'DEC-20260905-000184',
    root_decision_id: 'DEC-20260905-000184',
    trigger: 'AGENT_CONTEXT_RESPONSE',
    sequence: 1,
  };
  next.anomaly = {
    ...next.anomaly,
    risk_score: 62,
    severity: 'MEDIUM',
    raw_score: -0.32,
    baseline_percentile: 62,
  };
  next.evidence = {
    ...next.evidence,
    verified: 2,
    unverified: 1,
    pending_external_verification: 1,
    items: next.evidence.items.map((item) =>
      item.evidence_id === 'EDR-9921' ? { ...item, status: 'VERIFIED' } : item,
    ),
  };
  next.context_challenge = { ...next.context_challenge, required: false, status: 'RECEIVED' };
  next.decision = {
    ...next.decision,
    result: 'HOLD',
    reason_codes: ['TECHNICIAN_REVIEW_REQUIRED', 'PARTIAL_EVIDENCE_VERIFICATION'],
    technician_required: true,
    biometric_required_for_approval: true,
  };
  return next;
}
export const demoAgent = (suffix = '04'): AgentStatus => ({
  schema_version: '1.0',
  event_type: 'alice.agent_status',
  timestamp: '2026-09-05T15:44:04Z',
  agent_id: `diagnostic-agent-${suffix}`,
  agent_type: 'diagnostic',
  model: 'llama3.3:70b',
  status: 'AWAITING_REVIEW',
  mission_id: 'MISSION-291',
  current_activity: { type: 'review', label: 'Awaiting technician review' },
  health: 'HEALTHY',
});
export function scenarioEvents(name: ScenarioName): AliceEvent[] {
  const held = baseDecision();
  const allowed: Decision = structuredClone(held);
  allowed.decision_id = 'DEC-20260905-000182';
  allowed.timestamp = '2026-09-05T15:39:21.000Z';
  allowed.request.request_id = 'REQ-88289';
  allowed.request.action = 'query_network';
  allowed.request.parameters = { scope: 'active_connections' };
  allowed.request.state_changing = false;
  allowed.policy = {
    ...allowed.policy,
    result: 'ALLOW',
    rule_id: 'NET-READ-01',
    rule_description: 'Read-only diagnostics are permitted within the assigned mission.',
  };
  allowed.anomaly = {
    ...allowed.anomaly,
    risk_score: 12,
    severity: 'LOW',
    baseline_percentile: 12,
    factors: [],
  };
  allowed.decision = {
    ...allowed.decision,
    result: 'ALLOW',
    confidence: 0.98,
    reason_codes: ['MISSION_SCOPED_READ'],
    execution_status: 'EXECUTED',
    technician_required: false,
    biometric_required_for_approval: false,
  };
  allowed.technician_actions.available = [];
  allowed.context_challenge = {
    required: false,
    challenge_id: null,
    attempt: 0,
    status: 'NOT_REQUIRED',
    requested_fields: [],
    agent_response: null,
  };
  allowed.evidence = {
    verified: 1,
    unverified: 0,
    pending_external_verification: 0,
    items: [held.evidence.items[0]!],
  };
  const denied: Decision = structuredClone(held);
  denied.decision_id = 'DEC-20260905-000183';
  denied.timestamp = '2026-09-05T15:40:52.000Z';
  denied.request.request_id = 'REQ-88290';
  denied.request.action = 'disable_edr';
  denied.request.parameters = { service: 'endpoint-protection' };
  denied.policy = {
    ...denied.policy,
    result: 'DENY',
    rule_id: 'SEC-EDR-01',
    rule_description: 'Disabling endpoint protection is prohibited for diagnostic agents.',
  };
  denied.decision = {
    ...denied.decision,
    result: 'DENY',
    reason_codes: ['PROHIBITED_ACTION'],
    technician_required: false,
  };
  denied.technician_actions.available = [];
  denied.context_challenge = allowed.context_challenge;
  const status = normalizeEvent(rawStatus);
  const agent = demoAgent();
  const research: AgentStatus = {
    ...agent,
    agent_id: 'research-agent-02',
    agent_type: 'research',
    model: 'qwen2.5:7b',
    status: 'IDLE',
    current_activity: { type: 'standby', label: 'Available for evidence research' },
  };
  const network: AgentStatus = {
    ...agent,
    agent_id: 'network-agent-01',
    agent_type: 'network',
    model: 'llama3.2:3b',
    status: 'RUNNING',
    current_activity: { type: 'telemetry', label: 'Observing local network telemetry' },
  };
  if (name === '09_agent_failure') {
    network.status = 'FAILED';
    network.health = 'FAILED';
    network.current_activity = {
      type: 'error',
      label: 'Telemetry process exited; reconnect required',
    };
  }
  const services: AliceEvent[] = [
    {
      schema_version: '1.0',
      event_type: 'alice.service_status',
      timestamp: held.timestamp,
      service_id: 'evidence',
      label: 'Evidence service',
      status: 'WAITING',
      detail: '2 external references pending',
    },
    {
      schema_version: '1.0',
      event_type: 'alice.service_status',
      timestamp: held.timestamp,
      service_id: 'gateway',
      label: 'Enforcement gateway',
      status: 'READY',
      detail: 'Local boundary active',
    },
  ];
  let decisions = [allowed, denied, held];
  if (name === '01_normal_allow') decisions = [denied, held, allowed];
  if (name === '02_hard_policy_deny') decisions = [allowed, held, denied];
  const events: AliceEvent[] = [status, agent, research, network, ...services, ...decisions];
  if (name === '08_reconnect_reconciliation') {
    if (status.event_type === 'alice.status')
      events.push({
        ...status,
        timestamp: '2026-09-05T18:47:11Z',
        mode: 'CONNECTED',
        connections: { ...status.connections, cloud: true, siem: true, edr: true },
      });
    events.push(normalizeEvent(rawReconciliation));
  }
  return events;
}
