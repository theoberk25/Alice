import { describe, it, expect } from 'vitest';
import {
  normalizeEvent,
  AliceEventSchema,
  AgentStatusSchema,
  IntentSchema,
  VerificationSchema,
} from '@alice/contracts';
import decision from '../fixtures/legacy/decision.json';
import status from '../fixtures/legacy/status.json';
import reconciliation from '../fixtures/legacy/reconciliation.json';
import {
  scenarioEvents,
  scenarioNames,
  demoAgent,
  baseDecision,
  reassessedDecision,
} from '../fixtures/scenarios';
describe('upstream contract compatibility', () => {
  it('accepts both original and explicitly linked reassessment decisions', () => {
    expect(AliceEventSchema.parse(baseDecision())).not.toHaveProperty('reassessment');
    expect(AliceEventSchema.parse(reassessedDecision())).toHaveProperty('reassessment.sequence', 1);
    const next = reassessedDecision();
    next.reassessment!.sequence = 0;
    expect(() => AliceEventSchema.parse(next)).toThrow();
  });
  it('accepts native Rust UTC offset timestamps on verification grants', () => {
    expect(
      VerificationSchema.safeParse({
        verification_id: 'V1',
        decision_id: 'D1',
        request_id: 'R1',
        technician_id: 'T1',
        timestamp: '2026-09-05T15:45:00+00:00',
        expires_at: '2026-09-05T15:46:00+00:00',
        result: 'PASS',
        provider: 'mock',
      }).success,
    ).toBe(true);
  });
  it('normalizes all three original payloads without modifying input', () => {
    const before = JSON.stringify(decision);
    for (const fixture of [decision, status, reconciliation])
      expect(normalizeEvent(fixture).event_type).toMatch(/^alice\./);
    expect(JSON.stringify(decision)).toBe(before);
    const result = normalizeEvent(decision);
    expect(JSON.stringify(result)).not.toMatch(/dcamr/i);
    if (result.event_type === 'alice.decision') {
      expect(result.system.node).toBe('ALICE-PI-01');
      expect(result.anomaly.risk_score).toBe(94);
      expect(result.decision.result).toBe('HOLD');
    }
  });
  it('fails closed on malformed and out-of-range external data', () => {
    expect(() =>
      normalizeEvent({ ...decision, decision: { ...decision.decision, confidence: 9 } }),
    ).toThrow();
    expect(() => normalizeEvent({ event_type: 'alice.agent_status', status: 'APPROVE' })).toThrow();
  });
  it('rejects reconciliation that rewrites history', () =>
    expect(() =>
      normalizeEvent({
        ...reconciliation,
        result: { ...reconciliation.result, original_decision_changed: true },
      }),
    ).toThrow());
  it.each(scenarioNames)('validates every event in %s', (name) => {
    for (const e of scenarioEvents(name)) expect(AliceEventSchema.safeParse(e).success).toBe(true);
  });
  it('preserves arbitrary agent model names and operational status', () => {
    const e = demoAgent();
    e.model = 'organization/custom-model:small';
    expect(AgentStatusSchema.parse(e).model).toBe(e.model);
  });
  it('cannot parse an LLM approval or hidden extra commands', () => {
    expect(() =>
      IntentSchema.parse({ intent: 'APPROVE', decision_id: 'D1', question: '' }),
    ).toThrow();
    expect(() =>
      IntentSchema.parse({
        intent: 'RESEARCH',
        decision_id: 'D1',
        question: '',
        execute: 'disable_edr',
      }),
    ).toThrow();
  });
});
