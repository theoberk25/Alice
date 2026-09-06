import type { ReactNode } from 'react';
import type { Tone } from './index';

/**
 * A single plant reading. Presentational only: it renders the value it is
 * given and the honesty state around it, and never reaches for the store.
 */
export function MetricTile({
  label,
  value,
  unit,
  sub,
  tone = 'neutral',
  stale = false,
  quality = 'GOOD',
  bar,
  ghost,
}: {
  label: string;
  value: string | null;
  unit?: string;
  sub?: ReactNode;
  tone?: Tone;
  stale?: boolean;
  quality?: string;
  /** 0-100 fill, for fan and battery. */
  bar?: number | null;
  /** 0-100 marker for the value the plant is chasing. */
  ghost?: number | null;
}) {
  const trusted = quality === 'GOOD';
  const unknown = value === null;
  const classes = [
    'metric-tile',
    `tone-${tone}`,
    stale ? 'is-stale' : '',
    trusted ? '' : 'is-untrusted',
    unknown ? 'is-unknown' : '',
  ]
    .filter(Boolean)
    .join(' ');
  const clamp = (n: number) => Math.max(0, Math.min(100, n));
  return (
    <article className={classes}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {unknown ? '--' : value}
        {unit && !unknown && <i className="metric-unit">{unit}</i>}
      </span>
      {bar !== undefined && bar !== null && (
        <span className="metric-bar" role="presentation">
          <i className="metric-bar-fill" style={{ width: `${clamp(bar)}%` }} />
          {ghost !== undefined && ghost !== null && (
            <i className="metric-bar-ghost" style={{ left: `${clamp(ghost)}%` }} />
          )}
        </span>
      )}
      {sub && <span className="metric-sub">{sub}</span>}
      {(stale || !trusted) && (
        <span className="metric-ribbon">{stale ? 'stale' : quality.toLowerCase()}</span>
      )}
    </article>
  );
}

/**
 * One line of agent reasoning from the audit feed. Selecting a card is the
 * caller's business; no technician action is ever bound inside this card.
 */
export function AgentThoughtCard({
  agentId,
  kind,
  summary,
  outcome,
  timestamp,
  selected = false,
  onSelect,
}: {
  agentId: string;
  kind: string;
  summary: string;
  outcome: string;
  timestamp?: string | null;
  selected?: boolean;
  onSelect?: () => void;
}) {
  const classes = [
    'thought-card',
    `outcome-${outcome}`,
    selected ? 'is-selected' : '',
    onSelect ? 'is-actionable' : '',
  ]
    .filter(Boolean)
    .join(' ');
  const body = (
    <>
      <span className="thought-head">
        <span className={`thought-agent agent-${agentId.split('-')[0]}`}>{agentId}</span>
        <span className="thought-kind">{kind.replaceAll('_', ' ')}</span>
        {timestamp && <time className="thought-time">{timestamp.slice(11, 19)}</time>}
      </span>
      <span className="thought-summary">{summary}</span>
      <span className={`thought-outcome outcome-${outcome}`}>{outcome}</span>
    </>
  );
  if (!onSelect) return <article className={classes}>{body}</article>;
  return (
    <button type="button" className={classes} onClick={onSelect}>
      {body}
    </button>
  );
}
