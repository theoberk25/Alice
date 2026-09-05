import { ArrowUpRight, Check, Pause, X } from 'lucide-react';
import { Panel, Badge, toneFor } from '@alice/ui';
import { useConsole } from '../../state/console';
export function History({ expanded = false }: { expanded?: boolean }) {
  const {
    order,
    decisions,
    selectedId,
    select,
    actions,
    reconciliations,
    requestDecisionHistory,
    latestDecisionByRequest,
  } = useConsole();
  const requests = [...new Set(order.map((id) => decisions[id]!.request.request_id))];
  return (
    <Panel
      title={expanded ? 'Decision history' : 'Recent decisions'}
      meta={<span className="count-label">{order.length.toString().padStart(2, '0')} RECORDS</span>}
    >
      <div className={`history-list ${expanded ? 'history-expanded' : ''}`}>
        {requests.map((request) => (
          <div className="history-request" key={request}>
            <div className="history-request-label">{request}</div>
            {(
              requestDecisionHistory[request] ??
              order.filter((id) => decisions[id]?.request.request_id === request)
            ).map((id) => {
              const d = decisions[id]!;
              const action = actions[id];
              const outcome =
                action?.action === 'REJECT'
                  ? 'REJECTED'
                  : action?.action === 'APPROVE_ONCE'
                    ? 'APPROVED ONCE'
                    : d.decision.result === 'ALLOW'
                      ? 'ALLOWED'
                      : d.decision.result === 'DENY'
                        ? 'DENIED'
                        : 'HELD';
              return (
                <button
                  onClick={() => select(id)}
                  key={id}
                  aria-label={expanded ? `Inspect ${id} ${outcome}` : undefined}
                  className={`history-item ${selectedId === id ? 'selected' : ''}`}
                >
                  <span className={`history-icon tone-${toneFor(outcome)}`}>
                    {outcome === 'ALLOWED' || outcome === 'APPROVED ONCE' ? (
                      <Check size={14} />
                    ) : outcome === 'HELD' ? (
                      <Pause size={12} />
                    ) : (
                      <X size={14} />
                    )}
                  </span>
                  <span className="history-info">
                    <strong>{d.request.action}</strong>
                    <small>
                      {d.reassessment ? 'REASSESSMENT' : 'ORIGINAL'}
                      {latestDecisionByRequest[d.request.request_id] === id ? ' · CURRENT' : ''}
                    </small>
                    {d.reassessment && (
                      <small>
                        Parent {d.reassessment.previous_decision_id} · root{' '}
                        {d.reassessment.root_decision_id}
                      </small>
                    )}
                    <small>
                      {new Date(d.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC' })} ·{' '}
                      {d.request.target}
                    </small>
                    {expanded && (
                      <small>
                        {d.decision_id} · {d.request.agent_id}
                      </small>
                    )}
                  </span>
                  <span className={`history-outcome tone-${toneFor(outcome)}`}>
                    {outcome}
                    {reconciliations[id] && <small>RECONCILED</small>}
                  </span>
                </button>
              );
            })}
          </div>
        ))}
      </div>
      {!expanded && (
        <div className="panel-footnote">
          <ArrowUpRight size={12} /> Immutable upstream decisions
        </div>
      )}
    </Panel>
  );
}
export function AuditLog() {
  const audit = useConsole((s) => s.audit);
  function download() {
    const blob = new Blob([JSON.stringify(audit, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'alice-console-audit.json';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <Panel
      title="Local console audit"
      meta={
        <button className="small-button" onClick={download}>
          Export JSON
        </button>
      }
    >
      <div className="audit-table">
        {audit.map((e) => (
          <article key={e.id}>
            <time>{new Date(e.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC' })}</time>
            <div>
              <Badge tone={toneFor(e.type)} dot={false}>
                {e.type.replaceAll('_', ' ')}
              </Badge>
              <p>{e.detail}</p>
              <small>{e.decision_id}</small>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}
