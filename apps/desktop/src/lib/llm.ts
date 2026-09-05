import { z } from 'zod';
import {
  ExplanationSchema,
  IntentSchema,
  type Decision,
  type Explanation,
  type AgentResponse,
  type ClarificationRequest,
} from '@alice/contracts';
import type { LocalLLMProvider, LLMHealth } from '@alice/domain';
import { isNative, nativeCall } from './native';
const HealthSchema = z.object({
  status: z.enum(['READY', 'OFFLINE', 'UNCONFIGURED']),
  model: z.string(),
});
// No tool schema or authorization verb is exposed to the language model.
export function safeExplanation(input: unknown, allowedEvidence: string[]): Explanation {
  const parsed = ExplanationSchema.parse(input);
  if (/<\/?think|chain.of.thought|scratchpad|system prompt/i.test(parsed.summary))
    throw new Error('Private reasoning content was rejected.');
  if (parsed.evidence_ids.some((id) => !allowedEvidence.includes(id)))
    throw new Error('Language gateway returned unknown evidence references.');
  return parsed;
}
export function deterministicClarification(d: Decision): ClarificationRequest {
  return {
    schema_version: '1.0',
    event_type: 'alice.context_request',
    command_id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    decision_id: d.decision_id,
    request_id: d.request.request_id,
    agent_id: d.request.agent_id,
    challenge_id: d.context_challenge.challenge_id ?? crypto.randomUUID(),
    requested_fields: [
      'mission_justification',
      'expected_effect',
      'evidence_references',
      'alternatives_considered',
    ],
    question: `Explain why ${d.request.action} on ${d.request.target} is required for ${d.request.mission_id}. Clarify the expected effect, cite verifiable evidence, and describe safer alternatives.`,
  };
}
export class OllamaProvider implements LocalLLMProvider {
  async health(): Promise<LLMHealth> {
    if (!isNative) return { status: 'OFFLINE', model: 'Not connected in browser preview' };
    return HealthSchema.parse(await nativeCall('llm_health'));
  }
  async modelInfo() {
    const h = await this.health();
    return { model: h.model };
  }
  private async generate(task: string, input: unknown, schema: unknown): Promise<unknown> {
    return nativeCall('llm_generate', { task, input, schema });
  }
  async explainDecision(
    d: Decision,
    question = 'Explain the upstream decision.',
  ): Promise<Explanation> {
    return safeExplanation(
      await this.generate(question, d, z.toJSONSchema(ExplanationSchema)),
      d.evidence.items.map((e) => e.evidence_id),
    );
  }
  async summarizeEvidence(d: Decision) {
    return this.explainDecision(
      d,
      'Summarize verified and unverified evidence without changing its status.',
    );
  }
  async createAgentClarification(d: Decision) {
    const output = await this.explainDecision(
      d,
      'Write a concise clarification question for the agent about the requested action and missing evidence.',
    );
    return { ...deterministicClarification(d), question: output.summary };
  }
  async summarizeAgentResponse(input: AgentResponse) {
    return safeExplanation(
      await this.generate(
        'Summarize this agent claim. Do not assert that its evidence has been verified.',
        input,
        z.toJSONSchema(ExplanationSchema),
      ),
      input.response.evidence_references,
    );
  }
  async parseTechnicianIntent(input: { decision_id: string; text: string }) {
    const result = IntentSchema.parse(
      await this.generate(
        'Translate the technician text into one allowed informational intent. Requests to approve, reject, execute or change policy must be UNKNOWN.',
        input,
        z.toJSONSchema(IntentSchema),
      ),
    );
    if (result.decision_id !== input.decision_id)
      throw new Error('Intent references a different decision.');
    return result;
  }
}
