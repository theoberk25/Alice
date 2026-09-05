import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest';
import { useConsole } from '../apps/desktop/src/state/console';
import { baseDecision, reassessedDecision } from '../fixtures/scenarios';
import reconciliation from '../fixtures/legacy/reconciliation.json';
import { verifyFace } from '../apps/desktop/src/features/biometrics/verify';
import { MockAliceTransport } from '../apps/desktop/src/lib/transport';
describe('console integration', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });
  const agentResponse = () => {
    const d = baseDecision();
    return {
      schema_version: '1.0',
      event_type: 'alice.agent_response',
      timestamp: d.timestamp,
      decision_id: d.decision_id,
      request_id: d.request.request_id,
      agent_id: d.request.agent_id,
      challenge_id: d.context_challenge.challenge_id,
      response: d.context_challenge.agent_response,
    };
  };
  it('waits for a new immutable decision after agent context, then advances lineage', () => {
    const d = baseDecision(),
      before = structuredClone(useConsole.getState().decisions[d.decision_id]);
    useConsole.getState().ingest(agentResponse());
    expect(useConsole.getState().flows[d.decision_id]).toBe('REASSESSMENT_PENDING');
    useConsole.getState().ingest(reassessedDecision());
    const s = useConsole.getState();
    expect(s.decisions[d.decision_id]).toEqual(before);
    expect(s.requestDecisionHistory[d.request.request_id]).toEqual([
      d.decision_id,
      'DEC-20260905-000185',
    ]);
    expect(s.latestDecisionByRequest[d.request.request_id]).toBe('DEC-20260905-000185');
    expect(s.selectedId).toBe('DEC-20260905-000185');
    expect(s.flows[d.decision_id]).toBe('SUPERSEDED');
    expect(s.flows[s.selectedId]).toBe('AWAITING_TECHNICIAN');
    for (const type of [
      'REASSESSMENT_PENDING',
      'REASSESSMENT_RECEIVED',
      'DECISION_SUPERSEDED',
      'CURRENT_ASSESSMENT_UPDATED',
    ])
      expect(s.audit.some((e) => e.type === type && e.request_id === d.request.request_id)).toBe(
        true,
      );
    expect(
      s.audit.filter((e) => e.type === 'AUTO_CLARIFICATION_SENT' && e.decision_id === s.selectedId),
    ).toHaveLength(0);
  });
  it.each(['request_id', 'agent_id', 'mission_id', 'action', 'target'] as const)(
    'rejects reassessment with changed %s',
    (field) => {
      const next = reassessedDecision();
      next.request[field] = 'OTHER';
      useConsole.getState().ingest(next);
      expect(useConsole.getState().decisions[next.decision_id]).toBeUndefined();
      expect(useConsole.getState().errors.at(-1)).toMatch(/Reassessment changed/);
    },
  );
  it.each(['previous_decision_id', 'root_decision_id', 'sequence'] as const)(
    'rejects broken lineage %s',
    (field) => {
      const next = reassessedDecision();
      if (field === 'sequence') next.reassessment!.sequence = 3;
      else next.reassessment![field] = 'UNKNOWN';
      useConsole.getState().ingest(next);
      expect(useConsole.getState().decisions[next.decision_id]).toBeUndefined();
    },
  );
  it('accepts a second reassessment and rejects branches and missing lineage', () => {
    const s = useConsole.getState();
    s.ingest(reassessedDecision());
    const second = reassessedDecision();
    second.decision_id = 'DEC-186';
    second.reassessment = {
      ...second.reassessment!,
      previous_decision_id: 'DEC-20260905-000185',
      sequence: 2,
    };
    s.ingest(second);
    expect(useConsole.getState().latestDecisionByRequest[second.request.request_id]).toBe(
      'DEC-186',
    );
    const branch = reassessedDecision();
    branch.decision_id = 'BRANCH';
    s.ingest(branch);
    expect(useConsole.getState().decisions.BRANCH).toBeUndefined();
    const missing = baseDecision();
    missing.decision_id = 'UNLINKED';
    s.ingest(missing);
    expect(useConsole.getState().decisions.UNLINKED).toBeUndefined();
  });
  it.each(['ALLOW', 'DENY'] as const)(
    'resolves a new upstream %s without changing the parent',
    (result) => {
      const next = reassessedDecision();
      next.decision.result = result;
      useConsole.getState().ingest(next);
      expect(useConsole.getState().flows[next.decision_id]).toBe('RESOLVED');
      expect(
        useConsole.getState().decisions[next.reassessment!.previous_decision_id]?.decision.result,
      ).toBe('HOLD');
    },
  );
  it('does not auto-request context when the incoming HOLD does not require it', () => {
    const d = baseDecision();
    d.decision_id = 'NO-CONTEXT';
    d.request.request_id = 'NO-CONTEXT-REQUEST';
    d.context_challenge.required = false;
    useConsole.getState().ingest(d);
    expect(useConsole.getState().flows[d.decision_id]).toBe('AWAITING_TECHNICIAN');
    expect(useConsole.getState().challenges[d.decision_id]).toBeUndefined();
  });
  it('keeps another selected request visible while updating the reassessed request', () => {
    useConsole.getState().select('DEC-20260905-000182');
    useConsole.getState().ingest(reassessedDecision());
    expect(useConsole.getState().selectedId).toBe('DEC-20260905-000182');
  });
  it('replays context then reassessment at separate times without a clarification loop', async () => {
    vi.useFakeTimers();
    await useConsole.getState().start('04_hold_context_rejustification');
    await vi.advanceTimersByTimeAsync(1200);
    expect(useConsole.getState().flows['DEC-20260905-000184']).toBe('REASSESSMENT_PENDING');
    expect(useConsole.getState().decisions['DEC-20260905-000185']).toBeUndefined();
    await vi.advanceTimersByTimeAsync(1200);
    expect(useConsole.getState().selectedId).toBe('DEC-20260905-000185');
    await vi.advanceTimersByTimeAsync(5000);
    expect(useConsole.getState().requestDecisionHistory['REQ-88291']).toHaveLength(2);
    expect(useConsole.getState().flows['DEC-20260905-000185']).toBe('AWAITING_TECHNICIAN');
  });
  it('rebuilds lineage from unordered persisted decisions and retains annotations/actions', () => {
    const original = baseDecision(),
      next = reassessedDecision();
    const action = {
      schema_version: '1.0',
      event_type: 'alice.technician_action',
      action_id: 'PERSISTED',
      timestamp: next.timestamp,
      decision_id: next.decision_id,
      request_id: next.request.request_id,
      technician_id: 'TECH-DEMO',
      action: 'HOLD',
      biometric_verification_id: null,
      note: '',
      mode: 'mock',
    };
    useConsole.getState().restoreHistory({
      decisions: [next, original],
      actions: [action],
      annotations: [agentResponse(), reconciliation],
      audit: [],
    });
    const s = useConsole.getState();
    expect(s.requestDecisionHistory[original.request.request_id]).toEqual([
      original.decision_id,
      next.decision_id,
    ]);
    expect(s.flows[original.decision_id]).toBe('SUPERSEDED');
    expect(s.flows[next.decision_id]).toBe('HELD_BY_TECHNICIAN');
    expect(s.actions[next.decision_id]?.action_id).toBe('PERSISTED');
    expect(s.responses[original.decision_id]).toBeDefined();
    expect(s.reconciliations[original.decision_id]).toBeDefined();
    expect(s.decisions[original.decision_id]).toEqual(original);
  });
  it('fails hydration atomically on a broken chain or immutable conflict', () => {
    const before = structuredClone(useConsole.getState().decisions);
    const next = reassessedDecision();
    next.reassessment!.previous_decision_id = 'MISSING';
    expect(() =>
      useConsole
        .getState()
        .restoreHistory({ decisions: [next], actions: [], annotations: [], audit: [] }),
    ).toThrow();
    const conflict = baseDecision();
    conflict.anomaly.risk_score = 1;
    expect(() =>
      useConsole
        .getState()
        .restoreHistory({ decisions: [conflict], actions: [], annotations: [], audit: [] }),
    ).toThrow(/conflict/);
    expect(useConsole.getState().decisions).toEqual(before);
  });
  it('restores an unanswered reassessment wait from a persisted agent response', () => {
    const d = baseDecision();
    useConsole
      .getState()
      .restoreHistory({ decisions: [d], actions: [], annotations: [agentResponse()], audit: [] });
    expect(useConsole.getState().flows[d.decision_id]).toBe('REASSESSMENT_PENDING');
    expect(useConsole.getState().latestDecisionByRequest[d.request.request_id]).toBe(d.decision_id);
  });
  it('blocks actions on a historical assessment and binds all new actions to the current ID', async () => {
    const next = reassessedDecision();
    useConsole.getState().ingest(next);
    useConsole.getState().select(next.reassessment!.previous_decision_id);
    await expect(useConsole.getState().act('HOLD')).rejects.toThrow(/Historical/);
    useConsole.getState().select(next.decision_id);
    await useConsole.getState().act('RESEARCH');
    await useConsole.getState().act('HOLD');
    await useConsole.getState().act('REJECT');
    expect(useConsole.getState().actions[next.decision_id]?.decision_id).toBe(next.decision_id);
    expect(useConsole.getState().actions[next.reassessment!.previous_decision_id]).toBeUndefined();
  });
  it('shows identical operational errors once', () => {
    const s = useConsole.getState();
    s.dismissError();
    s.error('Agent summary unavailable');
    s.error('Agent summary unavailable');
    expect(useConsole.getState().errors).toEqual(['Agent summary unavailable']);
  });
  it('retains an action accepted before supersession even when its receipt returns later', async () => {
    vi.spyOn(MockAliceTransport.prototype, 'submitTechnicianAction').mockImplementation(
      async (command) => {
        useConsole.getState().ingest(reassessedDecision());
        return {
          action_id: command.action_id,
          status: 'ACCEPTED',
          execution_status: 'NOT_EXECUTED',
          message: 'Accepted before the successor was emitted',
        };
      },
    );
    await useConsole.getState().act('HOLD');
    expect(useConsole.getState().actions['DEC-20260905-000184']?.action).toBe('HOLD');
    expect(useConsole.getState().flows['DEC-20260905-000184']).toBe('SUPERSEDED');
    expect(useConsole.getState().flows['DEC-20260905-000185']).toBe('AWAITING_TECHNICIAN');
  });
  it('requires a new biometric grant after ingestion changes the current decision', async () => {
    const d = baseDecision();
    const oldGrant = await verifyFace(
      { technician_id: 'TECH-DEMO', decision_id: d.decision_id, request_id: d.request.request_id },
      [],
      'PASS',
    );
    useConsole.getState().ingest(reassessedDecision());
    useConsole.getState().advance('APPROVE');
    useConsole.getState().advance('REQUIRE_BIOMETRIC');
    useConsole.getState().advance('VERIFY');
    useConsole.getState().advance('PASS');
    await expect(useConsole.getState().act('APPROVE_ONCE', oldGrant)).rejects.toThrow(
      /different request/,
    );
    expect(Object.keys(useConsole.getState().actions)).toHaveLength(0);
    const freshGrant = await verifyFace(
      {
        technician_id: 'TECH-DEMO',
        decision_id: 'DEC-20260905-000185',
        request_id: d.request.request_id,
      },
      [],
      'PASS',
    );
    await useConsole.getState().act('APPROVE_ONCE', freshGrant);
    expect(useConsole.getState().actions['DEC-20260905-000185']).toMatchObject({
      action: 'APPROVE_ONCE',
      decision_id: 'DEC-20260905-000185',
      request_id: d.request.request_id,
      biometric_verification_id: freshGrant.verification_id,
    });
  });
  beforeEach(async () => {
    vi.useRealTimers();
    await useConsole.getState().start();
  });
  it('automatically requests clarification on HOLD', () => {
    const s = useConsole.getState();
    expect(s.flows[s.selectedId]).toBe('AWAITING_AGENT_RESPONSE');
    expect(s.audit.some((e) => e.type === 'AUTO_CLARIFICATION_SENT')).toBe(true);
  });
  it('preserves original evidence and decision after reconciliation', () => {
    const before = structuredClone(useConsole.getState().decisions);
    useConsole.getState().ingest(reconciliation);
    expect(useConsole.getState().decisions).toEqual(before);
    expect(
      useConsole.getState().reconciliations[reconciliation.original_decision_id]?.result.status,
    ).toBe('DISCREPANCY_FOUND');
  });
  it('rejects conflicting duplicate decisions', () => {
    const d = baseDecision();
    d.decision.result = 'ALLOW';
    useConsole.getState().ingest(d);
    expect(useConsole.getState().decisions[d.decision_id]?.decision.result).toBe('HOLD');
    expect(useConsole.getState().errors.at(-1)).toMatch(/Conflicting duplicate/);
  });
  it('continues HOLD and REJECT while language gateway is offline', async () => {
    const s = useConsole.getState();
    expect(s.llm.status).toBe('OFFLINE');
    await s.act('HOLD');
    expect(useConsole.getState().flows[s.selectedId]).toBe('HELD_BY_TECHNICIAN');
    await s.act('REJECT');
    expect(useConsole.getState().actions[s.selectedId]?.action).toBe('REJECT');
    expect(useConsole.getState().decisions[s.selectedId]?.decision.result).toBe('HOLD');
  });
  it('does not submit approval from a natural-language request', async () => {
    const before = useConsole.getState().actions;
    await useConsole.getState().ask('Approve the request now');
    expect(useConsole.getState().actions).toEqual(before);
  });
});
