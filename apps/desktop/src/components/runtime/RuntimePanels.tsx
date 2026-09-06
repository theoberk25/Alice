import { useState } from 'react';
import { Panel, Badge, Empty, toneFor } from '@alice/ui';
import { RuntimeReviewPanel } from './RuntimeReview';
import { useConsole } from '../../state/console';
import type { RuntimeEvent } from '@alice/contracts';
const when = (e?: RuntimeEvent) =>
  e?.time.recorded_at ? `${e.time.recorded_at} · ${e.time.confidence}` : 'Timestamp unavailable';
const outcome = (e?: RuntimeEvent) =>
  e?.detail.outcome === 'CHALLENGE' ? 'HOLD' : (e?.detail.outcome ?? 'UNAVAILABLE');
export function RuntimeHistory() {
  const { runtime, selectedRuntimeId, selectRuntime } = useConsole();
  const requests = Object.values(runtime.requests).reverse();
  return (
    <Panel
      title="Recent decisions"
      meta={<span className="count-label">{requests.length} REQUESTS</span>}
    >
      <div className="history-list">
        {requests.map((r) => (
          <button
            key={r.id}
            className={`history-item ${selectedRuntimeId === r.id ? 'selected' : ''}`}
            onClick={() => selectRuntime(r.id)}
          >
            <span className="history-info">
              <strong>{r.id}</strong>
              <small>{r.events[0]?.attribution.agent_id ?? 'Agent unavailable'}</small>
              <small>{r.events.length} correlated events</small>
            </span>
            <span className={`history-outcome tone-${toneFor(outcome(r.decision))}`}>
              {r.decision ? outcome(r.decision) : 'IN PROGRESS'}
            </span>
          </button>
        ))}
      </div>
      {!requests.length && <Empty>No runtime requests received</Empty>}
      <div className="panel-footnote">Immutable events · execution results arrive separately</div>
    </Panel>
  );
}
export function RuntimeWorkspace() {
  const { runtime, selectedRuntimeId } = useConsole();
  const r = runtime.requests[selectedRuntimeId];
  if (!r) return <Empty>Awaiting runtime history or a new request</Empty>;
  const assessment = r.assessment?.detail;
  const context = assessment?.contextual?.context ?? [];
  const fixture = context.some((c) => c.key === 'fixture_mode' && c.value === 'true');
  return (
    <>
      <section className="decision-hero">
        <div className="hero-topline">
          <span className="eyebrow">RUNTIME REQUEST / {r.id}</span>
          <span className="mono muted">{when(r.decision ?? r.events[0])}</span>
        </div>
        <div className="hero-main">
          <div className="hero-copy">
            <div className={`decision-title tone-${toneFor(outcome(r.decision))}`}>
              <h1>{r.decision ? outcome(r.decision) : 'IN PROGRESS'}</h1>
            </div>
            <p className="hero-subtitle">
              {r.decision?.event_type === 'REJECTION'
                ? 'Runtime rejection'
                : 'Outcome reported by the Pi runtime'}
            </p>
            <div className="action-code">
              {context.find((c) => c.key === 'action')?.value ?? 'Action unavailable'}
            </div>
            <p className="muted">
              {context.length
                ? 'Action/target context from the assessment; full signed request is not exposed by this feed.'
                : 'Request action, target and parameters are not exposed by this feed.'}
            </p>
          </div>
          <div>
            <p>Risk score: unavailable</p>
            <p>Confidence: unavailable</p>
            {fixture && <Badge tone="warning">FIXTURE ASSESSMENT</Badge>}
          </div>
        </div>
        <div className="hero-metrics">
          <div>
            <span>ASSESSMENT</span>
            <strong>
              {assessment ? `${assessment.result} · ${assessment.status}` : 'UNAVAILABLE'}
            </strong>
          </div>
          <div>
            <span>CONTROLLER RECEIPT</span>
            <strong>{outcome(r.receipt)}</strong>
          </div>
          <div>
            <span>EXECUTION RESULT</span>
            <strong>{outcome(r.execution)}</strong>
          </div>
        </div>
        <div className="panel-footnote">
          The original ALICE decision remains unchanged by technician review. Controller receipts,
          execution results and observed state are recorded separately.
        </div>
      </section>
      <div className="request-context">
        <div>
          <span className="eyebrow">REQUEST SHA256</span>
          <strong>{r.events[0]?.correlation.request_sha256 ?? 'Unavailable'}</strong>
        </div>
        <div>
          <span className="eyebrow">AGENT</span>
          <strong>{r.events[0]?.attribution.agent_id ?? 'Unavailable'}</strong>
        </div>
      </div>
      <RuntimeReviewPanel key={selectedRuntimeId} />
      <Panel title="Runtime event timeline">
        {r.events.map((e) => (
          <article className="reconciliation-row" key={e.event_id}>
            <div>
              <strong>
                #{e.sequence} {e.event_type}
              </strong>
              <p>
                {e.detail.outcome ??
                  e.detail.result ??
                  e.detail.property ??
                  (typeof e.detail.intent === 'string' ? e.detail.intent : 'Recorded event')}
              </p>
              <small>
                {when(e)}
                <br />
                {e.event_id}
                <br />
                Assessment: {e.correlation.assessment_id ?? 'unavailable'} · Execution:{' '}
                {e.correlation.execution_id ?? 'unavailable'}
              </small>
              {e.detail.reason_codes?.length ? <p>{e.detail.reason_codes.join(' · ')}</p> : null}
            </div>
          </article>
        ))}
      </Panel>
    </>
  );
}
export function RuntimeEvidence() {
  const { runtime, selectedRuntimeId } = useConsole();
  const r = runtime.requests[selectedRuntimeId];
  const observation = r?.observation;
  const detail = observation?.detail;
  return (
    <Panel title="Evidence & observed state">
      <p>
        {detail
          ? `${detail.asset_id} · ${detail.property}: ${detail.value ?? 'Unavailable'} ${detail.unit}`
          : 'Observed state unavailable'}
      </p>
      <p>
        {detail?.quality ?? 'UNAVAILABLE'} · {detail?.origin ?? 'Origin unavailable'}
      </p>
      <p>
        {runtime.source?.controller === 'mock'
          ? 'MOCK CONTROLLER'
          : 'Controller provenance unavailable'}
      </p>
      <small>
        {when(observation)}
        <br />
        Source freshness: {detail?.source?.freshness ?? 'UNKNOWN'} ·{' '}
        {detail?.source?.verification ?? 'UNKNOWN'}
      </small>
      <p className="muted">
        A controller receipt is separate from an observed state. Feed delivery does not verify the
        physical reading.
      </p>
      {r?.events.flatMap((e) =>
        e.provenance.evidence.map((ref) => (
          <div key={`${e.event_id}:${ref.ref}`} className="reconciliation-row">
            <div>
              <strong>{ref.ref}</strong>
              <p>
                {ref.source.source_id ?? 'Source unavailable'} · {ref.source.verification}
              </p>
              <small>{ref.sha256}</small>
            </div>
          </div>
        )),
      )}
    </Panel>
  );
}
export function RuntimeSystem() {
  const { runtime, feed } = useConsole();
  const head = runtime.events.at(-1);
  return (
    <Panel
      title="System integrity"
      meta={
        <Badge tone={feed.state === 'live' ? 'healthy' : 'warning'}>
          {feed.state.toUpperCase()}
        </Badge>
      }
    >
      <p role="status">{feed.message}</p>
      <p>Source: {runtime.source?.connection ?? 'Unavailable'}</p>
      <p>
        Coverage: collected ALICE requests and audit events. Network packet telemetry is not
        connected.
      </p>
      <p>
        Feed last received:{' '}
        {feed.last_success_at ? new Date(feed.last_success_at).toISOString() : 'Never'}
      </p>
      <p>
        Ledger: {head?.ledger_id ?? 'Unavailable'} · sequence {runtime.cursor}
      </p>
      <p>
        Recorded authority: {head?.authority.product_mode ?? 'UNAVAILABLE'} ·{' '}
        {head?.authority.execution_owner ?? 'UNKNOWN'}
      </p>
      <small>Authority is historical runtime metadata, not a current connectivity probe.</small>
      <p>Cloud / SIEM / EDR connectivity: unavailable</p>
      <p>Policy, anomaly and protected endpoint readiness: unavailable</p>
      <p>Policy reference: {head?.provenance.policy.id ?? 'Unavailable'}</p>
      <small>Signature verification status is not supplied by the feed.</small>
    </Panel>
  );
}
export function RuntimeAgents() {
  const { runtime } = useConsole();
  const agents = [...new Set(runtime.events.map((e) => e.attribution.agent_id).filter(Boolean))];
  return (
    <Panel
      title="Agent network"
      meta={<span className="count-label">{agents.length} OBSERVED IDENTITIES</span>}
    >
      <div className="agent-list">
        {agents.map((id) => (
          <article className="agent-card" key={id}>
            <strong>{id}</strong>
            <p>Observed in runtime audit events</p>
            <Badge tone="neutral">HEALTH UNAVAILABLE</Badge>
          </article>
        ))}
      </div>
      <div className="panel-footnote">
        An audit identity does not establish current agent connectivity.
      </div>
    </Panel>
  );
}
export function RuntimeAudit() {
  const { runtime } = useConsole();
  const [filter, setFilter] = useState('');
  const events = [...runtime.events]
    .reverse()
    .filter((e) => JSON.stringify(e).toLowerCase().includes(filter.toLowerCase()));
  return (
    <Panel title="Pi audit trail">
      <p>
        Collected request, decision, technician and execution events. This is not a record of every
        network packet.
      </p>
      <label>
        Filter collected traffic{' '}
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Request, agent, action or outcome"
        />
      </label>
      <p>
        {events.length} / {runtime.events.length} collected events
      </p>
      <div className="audit-table">
        {events.map((e) => (
          <article key={e.event_id}>
            <span>#{e.sequence}</span>
            <div>
              <strong>{e.event_type}</strong>
              <p>
                {e.correlation.request_id ?? 'Uncorrelated event'} · {e.event_id}
              </p>
              <small>{when(e)}</small>
              <details>
                <summary>Retained event and provenance</summary>
                <pre>{JSON.stringify(e, null, 2)}</pre>
              </details>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}
