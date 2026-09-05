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
export class RemoteAliceTransport implements AliceTransport {
  readonly mode = 'remote' as const;
  async connect(
    _onEvent: (event: unknown) => void,
    onError: (message: string) => void,
  ): Promise<() => void> {
    void _onEvent;
    onError('ALICE edge transport is not configured. No remote event stream is connected.');
    return () => {};
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
