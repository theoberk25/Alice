import { Check, Clock3, ArrowUpRight, ShieldCheck } from 'lucide-react';
import type { Decision } from '@alice/contracts';
import { Panel, Badge, toneFor, human, AnimatedCounter, CommandButton } from '@alice/ui';
import { useConsole } from '../../state/console';
export function EvidencePanel({
  decision: d,
  onResearch,
}: {
  decision: Decision;
  onResearch: () => void;
}) {
  const reconciled = useConsole((s) => s.reconciliations[d.decision_id]);
  return (
    <Panel className="evidence-panel" title="Evidence ledger" meta={<ShieldCheck size={14} />}>
      <div className="evidence-score">
        <strong>
          <AnimatedCounter value={d.evidence.verified} />
          <span>
            {' '}
            / <AnimatedCounter value={d.evidence.items.length} />
          </span>
        </strong>
        <div>
          References verified<small>At this assessment</small>
        </div>
      </div>
      <div className="evidence-meter">
        {d.evidence.items.map((e) => (
          <i
            key={e.evidence_id}
            className={e.status.startsWith('VERIFIED') ? 'verified' : 'pending'}
          />
        ))}
      </div>
      <div className="evidence-stats">
        <span>
          <i className="healthy-dot" />
          {d.evidence.verified} verified
        </span>
        <span>
          <i className="warning-dot" />
          {d.evidence.pending_external_verification} pending
        </span>
      </div>
      <div className="evidence-items">
        {d.evidence.items.map((e) => (
          <article key={e.evidence_id}>
            <div className={`evidence-icon tone-${toneFor(e.status)}`}>
              {e.status.startsWith('VERIFIED') ? <Check size={16} /> : <Clock3 size={16} />}
            </div>
            <div>
              <strong>{e.evidence_id}</strong>
              <span>{human(e.source)}</span>
              <small className={`tone-${toneFor(e.status)}`}>
                {human(
                  e.status === 'PENDING_EXTERNAL_VERIFICATION' ? 'PENDING_EXTERNAL' : e.status,
                )}
              </small>
              {reconciled && (
                <small>
                  Reconciled:{' '}
                  {reconciled.evidence_results.find((r) => r.evidence_id === e.evidence_id)
                    ?.reconciled_status ?? 'Unchanged'}
                </small>
              )}
            </div>
          </article>
        ))}
      </div>
      {d.evidence.pending_external_verification > 0 && (
        <div className="evidence-note">
          <span className="note-bracket">[ ! ]</span>
          <p>External references await cloud verification. Local enforcement remains active.</p>
        </div>
      )}
      <CommandButton className="full-text-button" onClick={onResearch}>
        Open evidence workspace <ArrowUpRight size={15} />
      </CommandButton>
      <div className="evidence-footer">
        <Badge tone="neutral">CLAIMS ≠ VERIFIED EVIDENCE</Badge>
      </div>
    </Panel>
  );
}
