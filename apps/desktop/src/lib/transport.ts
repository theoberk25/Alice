import {
  ActionReceiptSchema,
  ClarificationSchema,
  TechnicianActionSchema,
  type ActionReceipt,
  type ClarificationRequest,
  type TechnicianAction,
} from '@alice/contracts';
import type { AliceTransport } from '@alice/domain';
import {
  scenarioEvents,
  type ScenarioName,
  baseDecision,
  reassessedDecision,
  demoAgent,
} from '../../../../fixtures/scenarios';
import { nativeCall, isNative } from './native';
export class MockAliceTransport implements AliceTransport {
  readonly mode = 'mock' as const;
  private listener?: (event: unknown) => void;
  private timers: ReturnType<typeof setTimeout>[] = [];
  private reassessmentScheduled = false;
  readonly actions: TechnicianAction[] = [];
  constructor(public scenario: ScenarioName = '03_hold_high_anomaly') {}
  async connect(onEvent: (event: unknown) => void) {
    this.listener = onEvent;
    scenarioEvents(this.scenario).forEach(onEvent);
    return () => {
      this.timers.forEach(clearTimeout);
      this.listener = undefined;
    };
  }
  async requestClarification(input: ClarificationRequest) {
    const request = ClarificationSchema.parse(input);
    const reassess =
      this.scenario === '04_hold_context_rejustification' &&
      request.decision_id === 'DEC-20260905-000184' &&
      !this.reassessmentScheduled;
    if (reassess) {
      this.reassessmentScheduled = true;
      this.listener?.({
        ...demoAgent(),
        status: 'WAITING_FOR_CONTEXT',
        current_activity: {
          type: 'context_response',
          label: 'Responding to automatic context request',
        },
      });
    }
    this.timers.push(
      setTimeout(() => {
        this.listener?.({
          schema_version: '1.0',
          event_type: 'alice.agent_response',
          timestamp: new Date().toISOString(),
          decision_id: request.decision_id,
          request_id: request.request_id,
          challenge_id: request.challenge_id,
          agent_id: request.agent_id,
          response: baseDecision().context_challenge.agent_response,
        });
        if (reassess) {
          this.listener?.({
            ...demoAgent(),
            status: 'VERIFYING_EVIDENCE',
            current_activity: {
              type: 'reassessment',
              label: 'Context returned; awaiting ALICE reassessment',
            },
          });
          this.timers.push(
            setTimeout(() => {
              this.listener?.(reassessedDecision());
              this.listener?.({
                ...demoAgent(),
                current_activity: {
                  type: 'review',
                  label: 'Reassessed request awaiting technician review',
                },
              });
            }, 1200),
          );
        }
      }, 1200),
    );
  }
  async submitTechnicianAction(input: TechnicianAction): Promise<ActionReceipt> {
    const action = TechnicianActionSchema.parse(input);
    if (action.mode !== 'mock') throw new Error('Mock transport refuses remote actions.');
    // Native deployments recheck the cached upstream decision and biometric grant in Rust.
    const receipt = isNative
      ? await nativeCall<ActionReceipt>('submit_action', { action })
      : {
          action_id: action.action_id,
          status: 'ACCEPTED',
          execution_status: 'NOT_EXECUTED',
          message: 'Recorded by the simulated ALICE node. No protected action was executed.',
        };
    this.actions.push(action);
    return ActionReceiptSchema.parse(receipt);
  }
}
// ---------------------------------------------------------------------------
// Read-only ledger feed adapter (first-light integration, per AGENTS.md).
//
// The Pi runtime exposes GET /events, a read-only projection of its durable
// audit ledger. This transport polls it and translates each request's event
// chain into the console's alice.* contracts for DISPLAY ONLY. It grants no
// authority: clarification and technician actions remain fail-closed because
// the first-light slice has no approval path — permitted+normal auto-allows,
// everything else is denied by the Pi itself.
// ---------------------------------------------------------------------------
type LedgerEvent = {
  sequence: number;
  event_id: string;
  event_type: string;
  node_id: string;
  time: { recorded_at: string | null };
  correlation: Record<string, string | null>;
  attribution: Record<string, string | null>;
  authority: Record<string, string | null>;
  provenance: { policy: { id: string | null; sha256: string | null } };
  detail: Record<string, unknown>;
};

const EDGE_URL = (import.meta.env.VITE_ALICE_EDGE_URL as string | undefined)?.replace(/\/$/, '');

function ledgerDecision(chain: LedgerEvent[]): unknown {
  const by: Record<string, LedgerEvent> = {};
  for (const e of chain) by[e.event_type] = e;
  const head = chain[0]!;
  const decision = by.DECISION?.detail as { outcome: string; reason_codes: string[] } | undefined;
  const rejection = by.REJECTION?.detail as { reason_codes: string[] } | undefined;
  const assessment = by.ASSESSMENT?.detail as
    | { status: string; result: string; contextual: { model_id: string | null } | null }
    | undefined;
  const executionResult = (by.EXECUTION_RESULT?.detail as { outcome: string } | undefined)?.outcome;
  const result = decision?.outcome === 'ALLOW' ? 'ALLOW' : 'DENY';
  const reasons = decision?.reason_codes ?? rejection?.reason_codes ?? [];
  const policy = head.provenance.policy;
  const pkg = {
    package_id: policy.id ?? 'unknown-release',
    version: (policy.sha256 ?? '').slice(0, 12) || 'unknown',
    signature_status: 'VERIFIED',
    source: 'signed USB release',
  };
  const grantRule = reasons.find((r) => r.startsWith('GRANT_'));
  const severity = { LOW: 'LOW', ELEVATED: 'MEDIUM', HIGH: 'HIGH' }[assessment?.result ?? ''] ?? 'NONE';
  const risk = { LOW: 8, ELEVATED: 60, HIGH: 90 }[assessment?.result ?? ''] ?? 0;
  const timestamp = (by.DECISION ?? by.REJECTION ?? head).time.recorded_at ?? new Date().toISOString();
  return {
    schema_version: '1.0',
    event_type: 'alice.decision',
    timestamp,
    decision_id: `DEC-${head.correlation.request_id}`,
    system: {
      node: head.node_id,
      mode: 'DDIL',
      cloud_connected: false,
      siem_connected: false,
      edr_cloud_connected: false,
      local_dashboard_connected: true,
    },
    request: {
      request_id: head.correlation.request_id,
      agent_id: head.attribution.agent_id ?? 'unknown-agent',
      agent_known: head.attribution.resolution === 'RESOLVED',
      mission_id: 'FIRST-LIGHT',
      // The ledger's strict REQUEST detail carries no action/target fields;
      // the first-light contract pins them, so this is display-only echo.
      mission_type: 'first_light_test',
      action: 'set_light_state',
      target: 'ESP-LIGHT-01',
      parameters: {},
      state_changing: true,
    },
    source_packages: { policy: pkg, operations_baseline: pkg },
    policy: {
      result: result === 'ALLOW' ? 'ALLOW' : 'DENY',
      rule_id: grantRule ?? reasons[0] ?? 'DEFAULT_DENY',
      rule_description:
        result === 'ALLOW'
          ? 'Exact PERMIT grant match; no approval required.'
          : 'No covering grant; default effect is deny.',
      policy_package: pkg.package_id,
      policy_version: pkg.version,
    },
    anomaly: {
      model: assessment?.contextual?.model_id ?? 'fixture',
      model_version: 'first-light-fixture',
      raw_score: 0,
      baseline_percentile: risk,
      risk_score: risk,
      severity,
      factors: [],
    },
    evidence: {
      verified: assessment ? 1 : 0,
      unverified: 0,
      pending_external_verification: 0,
      items: assessment
        ? [
            {
              evidence_id: `${head.correlation.request_id}-assessment`,
              claimed_by_agent: false,
              status: 'VERIFIED_LOCAL',
              source: 'pi-ledger evidence store',
            },
          ]
        : [],
    },
    context_challenge: {
      required: false,
      challenge_id: null,
      attempt: 0,
      status: 'NOT_REQUIRED',
      requested_fields: [],
      agent_response: null,
    },
    decision: {
      result,
      confidence: 1,
      reason_codes: reasons,
      execution_status:
        executionResult === 'COMPLETED'
          ? 'EXECUTED'
          : executionResult === 'FAILED'
            ? 'FAILED'
            : result === 'DENY'
              ? 'BLOCKED'
              : 'PENDING',
      technician_required: false,
      biometric_required_for_approval: false,
    },
    technician_actions: { available: [] },
  };
}

export class RemoteAliceTransport implements AliceTransport {
  readonly mode = 'remote' as const;
  private timer?: ReturnType<typeof setTimeout>;
  private after = 0;
  private chains = new Map<string, LedgerEvent[]>();
  private announced = new Set<string>();
  async connect(
    onEvent: (event: unknown) => void,
    onError: (message: string) => void,
  ): Promise<() => void> {
    if (!EDGE_URL) {
      onError('ALICE edge transport is not configured. No remote event stream is connected.');
      return () => {};
    }
    let statusSent = false;
    const poll = async () => {
      try {
        const response = await fetch(`${EDGE_URL}/events?after=${this.after}`, {
          cache: 'no-store',
        });
        const { events } = (await response.json()) as { events: LedgerEvent[] };
        const touched = new Set<string>();
        for (const e of events) {
          this.after = Math.max(this.after, e.sequence);
          if (!statusSent) {
            statusSent = true;
            onEvent({
              schema_version: '1.0',
              event_type: 'alice.status',
              timestamp: e.time.recorded_at ?? new Date().toISOString(),
              node: e.node_id,
              mode: 'DDIL',
              connections: {
                cloud: false,
                siem: false,
                edr: false,
                technician_workstation: true,
                protected_system: true,
              },
              packages: {
                policy: {
                  loaded: true,
                  version: e.provenance.policy.id ?? 'unknown',
                  signature: 'VERIFIED',
                },
                operations_baseline: { loaded: false, version: 'n/a', signature: 'FIXTURE' },
              },
              decision_engine: {
                policy_engine: 'READY',
                anomaly_engine: 'FIXTURE',
                enforcement_gateway: 'READY',
              },
            });
          }
          const rid = e.correlation.request_id;
          if (!rid) continue;
          if (!this.chains.has(rid)) this.chains.set(rid, []);
          this.chains.get(rid)!.push(e);
          touched.add(rid);
          const agent = e.attribution.agent_id;
          if (agent && !this.announced.has(agent)) {
            this.announced.add(agent);
            onEvent({
              schema_version: '1.0',
              event_type: 'alice.agent_status',
              timestamp: e.time.recorded_at ?? new Date().toISOString(),
              agent_id: agent,
              agent_type: 'terminal',
              model: 'signed-envelope client',
              status: 'RUNNING',
              mission_id: 'FIRST-LIGHT',
              current_activity: { type: 'request', label: 'Submitting signed action requests' },
              health: 'HEALTHY',
            });
          }
        }
        for (const rid of touched) {
          const chain = this.chains.get(rid)!;
          if (chain.some((e) => e.event_type === 'DECISION' || e.event_type === 'REJECTION'))
            onEvent(ledgerDecision(chain));
        }
      } catch (err) {
        onError(`ALICE edge feed unreachable: ${String(err)}`);
      }
      this.timer = setTimeout(poll, 1500);
    };
    await poll();
    return () => clearTimeout(this.timer);
  }
  async requestClarification(_request: ClarificationRequest): Promise<void> {
    void _request;
    throw new Error('Remote context endpoint has not been integrated.');
  }
  async submitTechnicianAction(_action: TechnicianAction): Promise<ActionReceipt> {
    void _action;
    throw new Error('Remote action endpoint has not been integrated. Approval was not sent.');
  }
}
