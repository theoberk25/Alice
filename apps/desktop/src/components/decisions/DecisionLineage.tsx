import type { Decision } from '@alice/contracts';
import { Panel, Badge, toneFor, human, CommandButton } from '@alice/ui';
import { useConsole } from '../../state/console';

export function DecisionLineage({ decision }: { decision: Decision }) {
  const s = useConsole();
  const ids = s.requestDecisionHistory[decision.request.request_id] ?? [decision.decision_id];
  const root = s.decisions[ids[0]!] ?? decision;
  const current = s.decisions[ids.at(-1)!] ?? decision;
  const pending = ids.some((id) => s.flows[id] === 'REASSESSMENT_PENDING');
  if (ids.length < 2 && !pending) return null;
  return (
    <Panel
      className="lineage-panel"
      title="Assessment lineage"
      meta={<span className="count-label">{decision.request.request_id}</span>}
    >
      <ol className="decision-lineage" aria-label="Decision reassessment history">
        {ids.map((id, index) => {
          const d = s.decisions[id]!;
          const sent =
            !!s.responses[id] ||
            s.audit.some((e) => e.type === 'AUTO_CLARIFICATION_SENT' && e.decision_id === id);
          return (
            <li key={id}>
              <CommandButton
                className="lineage-assessment"
                onClick={() => s.select(id)}
                aria-label={`Inspect assessment ${id}`}
                aria-current={s.selectedId === id ? 'true' : undefined}
              >
                <span className="eyebrow">
                  {index === 0 ? 'Original decision' : 'Reassessment'}
                  {id === current.decision_id && index > 0 ? ' · Current decision' : ''}
                </span>
                <strong>{id}</strong>
                <span>
                  <Badge tone={toneFor(d.decision.result)}>{d.decision.result}</Badge> Risk{' '}
                  {d.anomaly.risk_score} · Evidence {d.evidence.verified}/{d.evidence.items.length}
                </span>
                <time>
                  {new Date(d.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC' })} UTC
                </time>
                {d.reassessment && (
                  <small>
                    Parent {d.reassessment.previous_decision_id} · sequence{' '}
                    {d.reassessment.sequence}
                  </small>
                )}
              </CommandButton>
              {d.context_challenge.required && (
                <div className="lineage-events">
                  <p>
                    <strong>Automatic context request</strong>
                    <span>{sent ? `Sent to ${d.request.agent_id}` : 'Waiting to send'}</span>
                  </p>
                  <p>
                    <strong>Agent response</strong>
                    <span>{s.responses[id] ? 'Received' : 'Waiting'}</span>
                  </p>
                  {s.flows[id] === 'REASSESSMENT_PENDING' && (
                    <p role="status">
                      <strong>Reassessment pending</strong>
                      <span>Waiting for a new ALICE decision</span>
                    </p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
      {ids.length > 1 && (
        <div className="lineage-deltas" aria-label="Assessment changes">
          <div>
            <span>Risk</span>
            <strong>
              {root.anomaly.risk_score} → {current.anomaly.risk_score}
            </strong>
          </div>
          <div>
            <span>Verified evidence</span>
            <strong>
              {root.evidence.verified} → {current.evidence.verified}
            </strong>
          </div>
          <div>
            <span>Decision</span>
            <strong>
              {root.decision.result} → {current.decision.result}
            </strong>
          </div>
        </div>
      )}
      <div className="panel-footnote">
        {pending
          ? 'Awaiting upstream reassessment'
          : `Current decision · ${human(current.decision.result)}`}{' '}
        · Original assessments preserved
      </div>
    </Panel>
  );
}

export function ClarificationTrack({ decision }: { decision: Decision }) {
  const s = useConsole();
  const contextDecision =
    decision.reassessment && !decision.context_challenge.required
      ? (s.decisions[decision.reassessment.previous_decision_id] ?? decision)
      : decision;
  const response = s.responses[contextDecision.decision_id];
  const flow = s.flows[decision.decision_id] ?? 'IDLE';
  const ids = s.requestDecisionHistory[decision.request.request_id] ?? [];
  const hasSuccessor = ids.some(
    (id) => s.decisions[id]?.reassessment?.previous_decision_id === contextDecision.decision_id,
  );
  const sent =
    !!response ||
    !!s.contextRequests[contextDecision.decision_id] ||
    s.audit.some(
      (e) => e.type === 'AUTO_CLARIFICATION_SENT' && e.decision_id === contextDecision.decision_id,
    );
  const noContext = !contextDecision.context_challenge.required;
  const manualPending =
    s.mode === 'mock' && import.meta.env.VITE_ALICE_MANUAL_CONTEXT_DEMO === 'true' && !sent;
  const currentFlow =
    s.flows[s.latestDecisionByRequest[decision.request.request_id] ?? decision.decision_id] ?? flow;
  const reviewComplete = ['APPROVAL_SUBMITTED', 'REJECTED', 'RESOLVED'].includes(currentFlow);
  const review = [
    'AWAITING_TECHNICIAN',
    'RESEARCHING',
    'HELD_BY_TECHNICIAN',
    'APPROVAL_REQUESTED',
    'BIOMETRIC_REQUIRED',
    'BIOMETRIC_VERIFYING',
    'BIOMETRIC_PASSED',
    'BIOMETRIC_FAILED',
  ].includes(currentFlow);
  const steps = [
    ['HOLD received', 'complete'],
    [
      'Context requested',
      noContext
        ? 'not required'
        : sent
          ? 'complete'
          : manualPending
            ? 'waiting'
            : flow === 'AUTO_CONTEXT_REQUEST'
              ? 'active'
              : 'failed',
    ],
    [
      'Agent responded',
      noContext ? 'not required' : response ? 'complete' : sent ? 'active' : 'waiting',
    ],
    [
      'Reassessment',
      noContext
        ? decision.reassessment
          ? 'complete'
          : 'not required'
        : hasSuccessor
          ? 'complete'
          : flow === 'REASSESSMENT_PENDING'
            ? 'active'
            : 'waiting',
    ],
    [
      'Technician review',
      reviewComplete
        ? 'complete'
        : currentFlow === 'BIOMETRIC_FAILED'
          ? 'failed'
          : review
            ? 'active'
            : 'waiting',
    ],
  ];
  return (
    <ol className="clarification-track" aria-label="Clarification progress">
      {steps.map(([label, status]) => (
        <li key={label} className={`clarification-step ${status?.replaceAll(' ', '-')}`}>
          <span className={`track-point ${status}`} />
          <span>
            {label}
            <small>{status}</small>
          </span>
        </li>
      ))}
    </ol>
  );
}
