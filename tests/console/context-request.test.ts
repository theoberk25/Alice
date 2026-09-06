import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { useConsole } from '../../apps/desktop/src/state/console';
import { baseDecision, reassessedDecision } from '../../fixtures/scenarios';

// Slice A of the "request more context" pipeline: a technician-initiated control,
// separate from the automatic context request, that issues Record 1
// (CONTEXT_REQUESTED) and surfaces the agent's returned blurb. See
// docs/plans/2026-09-06-request-more-context-pipeline.md and
// docs/architecture/hold-workflow.md.
describe('technician request more context (mock mode)', () => {
  const held = 'DEC-20260905-000184';
  beforeEach(async () => {
    vi.useRealTimers();
    await useConsole.getState().start('03_hold_high_anomaly');
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('issues Record 1 and surfaces the returned blurb', async () => {
    vi.useFakeTimers();
    await useConsole.getState().requestContext(held);
    let s = useConsole.getState();
    // Record 1: the audited fact that the technician asked for more context.
    expect(s.audit.some((e) => e.type === 'CONTEXT_REQUESTED' && e.decision_id === held)).toBe(true);
    expect(s.contextRequests[held]).toBeTruthy();
    expect(s.responses[held]).toBeUndefined();
    // Record 2: the agent's returned claim binds to this assessment and parks the
    // flow at REASSESSMENT_PENDING (only a fresh upstream decision changes it).
    await vi.advanceTimersByTimeAsync(1200);
    s = useConsole.getState();
    expect(s.responses[held]?.response.mission_justification).toBeTruthy();
    expect(s.responses[held]?.challenge_id).toBe(s.contextRequests[held]);
    expect(s.flows[held]).toBe('REASSESSMENT_PENDING');
  });

  it('refuses a second request while one is in flight', async () => {
    vi.useFakeTimers();
    await useConsole.getState().requestContext(held);
    await expect(useConsole.getState().requestContext(held)).rejects.toThrow(/in flight/i);
  });

  it('refuses another request once the agent has responded', async () => {
    vi.useFakeTimers();
    await useConsole.getState().requestContext(held);
    await vi.advanceTimersByTimeAsync(1200);
    expect(useConsole.getState().responses[held]).toBeDefined();
    await expect(useConsole.getState().requestContext(held)).rejects.toThrow(/already returned/i);
  });

  it('is unavailable for a HOLD that does not require context', async () => {
    const d = baseDecision();
    d.decision_id = 'NO-CONTEXT';
    d.request.request_id = 'NO-CONTEXT-REQUEST';
    d.context_challenge.required = false;
    useConsole.getState().ingest(d);
    expect(useConsole.getState().flows['NO-CONTEXT']).toBe('AWAITING_TECHNICIAN');
    await expect(useConsole.getState().requestContext('NO-CONTEXT')).rejects.toThrow(
      /only available for a HOLD/i,
    );
  });

  it('is unavailable for a superseded historical assessment', async () => {
    useConsole.getState().ingest(reassessedDecision());
    expect(useConsole.getState().latestDecisionByRequest['REQ-88291']).toBe('DEC-20260905-000185');
    await expect(useConsole.getState().requestContext(held)).rejects.toThrow(/Historical/i);
  });

  it('is refused in remote mode where the feed is read-only', async () => {
    useConsole.setState({ mode: 'remote' });
    await expect(useConsole.getState().requestContext(held)).rejects.toThrow(/read-only/i);
  });
});
