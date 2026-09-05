import type {
  Decision,
  StructuredIntent,
  Explanation,
  ClarificationRequest,
  AgentResponse,
} from '@alice/contracts';
export interface LLMHealth {
  status: 'READY' | 'OFFLINE' | 'UNCONFIGURED';
  model: string;
}
export interface LocalLLMProvider {
  health(): Promise<LLMHealth>;
  modelInfo(): Promise<{ model: string }>;
  explainDecision(input: Decision, question?: string): Promise<Explanation>;
  summarizeEvidence(input: Decision): Promise<Explanation>;
  createAgentClarification(input: Decision): Promise<ClarificationRequest>;
  summarizeAgentResponse(input: AgentResponse): Promise<Explanation>;
  parseTechnicianIntent(input: { decision_id: string; text: string }): Promise<StructuredIntent>;
}
