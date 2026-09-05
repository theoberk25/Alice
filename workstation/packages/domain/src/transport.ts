import type { ActionReceipt, ClarificationRequest, TechnicianAction } from '@alice/contracts';
export interface AliceTransport {
  readonly mode: 'mock' | 'remote';
  connect(
    onEvent: (event: unknown) => void,
    onError: (message: string) => void,
  ): Promise<() => void>;
  requestClarification(request: ClarificationRequest): Promise<void>;
  submitTechnicianAction(action: TechnicianAction): Promise<ActionReceipt>;
}
