import { ShieldAlert, ArrowRight, LockKeyhole, CircleCheck, Ban, ChevronRight } from 'lucide-react';
import type { Decision } from '@alice/contracts';
import {
  Badge,
  Panel,
  toneFor,
  human,
  AnimatedCounter,
  BorderTrail,
  CommandButton,
} from '@alice/ui';
import { useConsole } from '../../state/console';
import { DecisionLineage, ClarificationTrack } from './DecisionLineage';
function RiskDial({ score, severity }: { score: number; severity: string }) {
  const radius = 56,
    circumference = 2 * Math.PI * radius;
  return (
    <div
      className={`risk-dial tone-${toneFor(severity === 'HIGH' ? 'HOLD' : severity === 'LOW' ? 'ALLOW' : 'HOLD')}`}
    >
      <svg
        viewBox="0 0 150 150"
        role="img"
        aria-label={`Behavioral risk ${score} of 100, ${severity}`}
      >
        <circle className="dial-outer" cx="75" cy="75" r="69" />
        <circle className="dial-track" cx="75" cy="75" r={radius} />
        <circle
          className="dial-value"
          cx="75"
          cy="75"
          r={radius}
          strokeDasharray={`${(circumference * score) / 100} ${circumference}`}
          transform="rotate(-90 75 75)"
        />
        <text x="75" y="77" textAnchor="middle" className="dial-number">
          {score}
        </text>
        <text x="75" y="97" textAnchor="middle" className="dial-denominator">
          / 100
        </text>
      </svg>
      <span>{severity} BEHAVIORAL RISK</span>
    </div>
  );
}
export function DecisionWorkspace({
  decision: d,
  onResearch,
}: {
  decision: Decision;
  onResearch: () => void;
}) {
  const {
    flows,
    actions,
    receipts,
    responses,
    reconciliations,
    contextSummaries,
    latestDecisionByRequest,
    select,
  } = useConsole();
  const currentId = latestDecisionByRequest[d.request.request_id] ?? d.decision_id;
  const current = currentId === d.decision_id;
  const result = d.decision.result;
  const action = actions[d.decision_id];
  const response = responses[d.decision_id];
  const reconciliation = reconciliations[d.decision_id];
  const Icon = result === 'HOLD' ? ShieldAlert : result === 'ALLOW' ? CircleCheck : Ban;
  return (
    <>
      <section
        data-decision-id={d.decision_id}
        className={`decision-hero result-${result.toLowerCase()}`}
      >
        <div className="hero-topline">
          <span className="eyebrow">
            {current
              ? 'CURRENT ASSESSMENT'
              : d.reassessment
                ? 'HISTORICAL ASSESSMENT'
                : 'ORIGINAL ASSESSMENT'}{' '}
            <span className="muted">/ {d.decision_id.replace('DEC-20260905-', '')}</span>
          </span>
          <span className="mono muted">
            {new Date(d.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC' })} UTC
          </span>
        </div>
        <div className="hero-main">
          <div className="hero-copy">
            <div className={`decision-title tone-${toneFor(result)}`}>
              <Icon size={39} strokeWidth={1.3} />
              <h1>{result === 'ALLOW' ? 'ALLOWED' : result === 'DENY' ? 'DENIED' : 'HOLD'}</h1>
            </div>
            <p className="hero-subtitle">
              {result === 'HOLD'
                ? 'Technician review required'
                : result === 'ALLOW'
                  ? 'Request permitted by upstream ALICE'
                  : 'Blocked by deterministic policy'}
            </p>
            <div className="action-code">
              {d.request.action}
              <span>( )</span>
            </div>
            <div className="target-path">
              <span>{d.request.target}</span>
              <ArrowRight size={16} />
              <strong>
                {String(
                  d.request.parameters.destination ??
                    d.request.parameters.service ??
                    d.request.parameters.scope ??
                    'Mission-scoped resource',
                )}
              </strong>
              {d.request.parameters.port && (
                <span className="port">:{String(d.request.parameters.port)}</span>
              )}
            </div>
          </div>
          <RiskDial score={d.anomaly.risk_score} severity={d.anomaly.severity} />
        </div>
        <div className="hero-metrics">
          <div>
            <span>CONFIDENCE</span>
            <strong>
              <AnimatedCounter value={Math.round(d.decision.confidence * 100)} />
              <small>%</small>
            </strong>
          </div>
          <div>
            <span>POLICY RESULT</span>
            <strong className={`tone-${toneFor(d.policy.result)}`}>
              {d.policy.result === 'REVIEW' ? 'REVIEW REQUIRED' : d.policy.result}
            </strong>
          </div>
          <div>
            <span>EXECUTION</span>
            <strong>
              <LockKeyhole size={12} />
              {human(d.decision.execution_status)}
            </strong>
          </div>
        </div>
        {action && (
          <div
            className={`action-receipt tone-${toneFor(action.action === 'APPROVE_ONCE' ? 'APPROVED' : action.action)}`}
          >
            <strong>
              {action.action === 'APPROVE_ONCE'
                ? 'APPROVED ONCE'
                : action.action === 'REJECT'
                  ? 'REJECTED'
                  : action.action === 'HOLD'
                    ? 'HELD BY TECHNICIAN'
                    : 'RESEARCH OPENED'}
            </strong>
            <span>
              {receipts[d.decision_id]?.status} ·{' '}
              {action.action === 'APPROVE_ONCE'
                ? 'One exact request. Execution awaits upstream confirmation.'
                : 'Original upstream decision preserved.'}
            </span>
          </div>
        )}
      </section>
      {!current && (
        <div className="historical-notice">
          Historical assessment · actions require the latest decision.{' '}
          <CommandButton className="text-button" onClick={() => select(currentId)}>
            View current assessment
          </CommandButton>
        </div>
      )}
      <DecisionLineage decision={d} />
      <div className="request-context">
        <div>
          <span className="eyebrow">REQUEST</span>
          <strong>{d.request.request_id}</strong>
        </div>
        <div>
          <span className="eyebrow">MISSION</span>
          <strong>{d.request.mission_id}</strong>
        </div>
        <div>
          <span className="eyebrow">AGENT</span>
          <strong>{d.request.agent_id}</strong>
        </div>
        <div>
          <span className="eyebrow">SCOPE</span>
          <strong>{d.request.state_changing ? 'State changing' : 'Read only'}</strong>
        </div>
      </div>
      <Panel
        title={result === 'HOLD' ? 'Why this was held' : 'Decision rationale'}
        meta={<span className="count-label">{d.policy.rule_id}</span>}
        className="rationale-panel"
      >
        <p className="policy-description">{d.policy.rule_description}</p>
        <div className="factor-list">
          {d.anomaly.factors.map((factor, index) => (
            <div className="factor" key={factor.id}>
              <span className="factor-index">0{index + 1}</span>
              <div>
                <strong>{factor.label}</strong>
                <span>
                  {factor.source.replaceAll('_', ' ')} <i>·</i> Observed{' '}
                  <b>{String(factor.value)}</b> / baseline <b>{String(factor.baseline_value)}</b>
                </span>
              </div>
              <span className={`severity-mark severity-${factor.severity.toLowerCase()}`}>
                {factor.severity}
              </span>
            </div>
          ))}
        </div>
        <div className="reason-chips">
          {d.decision.reason_codes.map((code) => (
            <span key={code}>{human(code).toLowerCase()}</span>
          ))}
        </div>
        <CommandButton className="text-button" onClick={onResearch}>
          Inspect full decision record <ChevronRight size={14} />
        </CommandButton>
      </Panel>
      {result === 'HOLD' && (
        <Panel
          title="Agent clarification"
          meta={
            <Badge tone={response ? 'healthy' : 'information'}>
              {flows[d.decision_id] === 'REASSESSMENT_PENDING'
                ? 'REASSESSMENT PENDING'
                : !d.context_challenge.required
                  ? 'NO FURTHER CONTEXT REQUIRED'
                  : response
                    ? 'RESPONSE RECEIVED'
                    : 'AWAITING RESPONSE'}
            </Badge>
          }
          className="clarification-panel"
        >
          <BorderTrail active={flows[d.decision_id] === 'REASSESSMENT_PENDING'} />
          <ClarificationTrack decision={d} />
          <div className="agent-quote">
            <span className="quote-mark">“</span>
            <div>
              <p>
                {contextSummaries[d.decision_id] ??
                  response?.response.mission_justification ??
                  (!d.context_challenge.required
                    ? 'ALICE requires no further automatic context request for this assessment. Review the structured current decision.'
                    : 'Additional mission justification, expected effect, evidence references, and alternatives have been requested automatically.')}
              </p>
              {response && (
                <p className="muted">Claimed effect: {response.response.expected_effect}</p>
              )}
              <span className="quote-attribution">
                {d.request.agent_id} <i>·</i>{' '}
                {response
                  ? 'AGENT-SUPPLIED CLAIM'
                  : !d.context_challenge.required
                    ? 'ALICE ASSESSMENT'
                    : 'AUTOMATIC CONTEXT CHALLENGE'}
              </span>
            </div>
          </div>
          {response && d.request.action === 'allow_outbound' && (
            <div className="context-warning">
              <ShieldAlert size={14} />
              <span>
                Review intent: the request opens outbound access; the justification describes
                preventing communication.
              </span>
            </div>
          )}
          <div className="workflow-label">
            WORKFLOW <span>{human(flows[d.decision_id] ?? 'IDLE')}</span>
          </div>
        </Panel>
      )}
      {reconciliation && (
        <Panel
          title="Evidence reconciled"
          meta={<Badge tone="warning">{human(reconciliation.result.status)}</Badge>}
        >
          <p className="reconciliation-copy">
            Cloud evidence was checked after reconnection. Original {result} at{' '}
            {new Date(d.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC' })} UTC is
            unchanged. Cloud was {d.system.cloud_connected ? 'online' : 'offline'} at decision time.
          </p>
          {reconciliation.evidence_results.map((e) => (
            <div className="reconciliation-row" key={e.evidence_id}>
              <span>{e.evidence_id}</span>
              <Badge tone={toneFor(e.reconciled_status)}>{human(e.reconciled_status)}</Badge>
            </div>
          ))}
        </Panel>
      )}
    </>
  );
}
