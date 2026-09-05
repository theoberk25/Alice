import { Badge, Modal, human } from '@alice/ui';
import { useConsole } from '../../state/console';
export function ResearchModal({ onClose }: { onClose: () => void }) {
  const { decisions, selectedId, responses } = useConsole();
  const d = decisions[selectedId]!;
  return (
    <Modal title="Evidence & context workspace" onClose={onClose} wide>
      <div className="research-summary">
        <Badge tone="warning">{d.decision.result}</Badge>
        <strong>
          {d.request.action} → {d.request.target}
        </strong>
        <span>{d.request.mission_type.replaceAll('_', ' ')}</span>
      </div>
      <div className="research-grid">
        <section>
          <h3>Request parameters</h3>
          <dl>
            {Object.entries(d.request.parameters).map(([k, v]) => (
              <div key={k}>
                <dt>{human(k)}</dt>
                <dd>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd>
              </div>
            ))}
          </dl>
          <h3>Policy & baseline provenance</h3>
          <dl>
            <div>
              <dt>Rule</dt>
              <dd>{d.policy.rule_id}</dd>
            </div>
            <div>
              <dt>Policy package</dt>
              <dd>
                {d.source_packages.policy.package_id} / v{d.source_packages.policy.version}
              </dd>
            </div>
            <div>
              <dt>Signature</dt>
              <dd>{d.source_packages.policy.signature_status}</dd>
            </div>
            <div>
              <dt>Baseline</dt>
              <dd>
                {d.source_packages.operations_baseline.package_id} / v
                {d.source_packages.operations_baseline.version}
              </dd>
            </div>
            <div>
              <dt>Mission consistency</dt>
              <dd>{d.mission_consistency ?? 'Not supplied by upstream'}</dd>
            </div>
          </dl>
        </section>
        <section>
          <h3>Evidence at original decision</h3>
          {d.evidence.items.map((e) => (
            <div className="research-evidence" key={e.evidence_id}>
              <strong>{e.evidence_id}</strong>
              <span>{human(e.status)}</span>
              <small>
                {e.source} · {e.claimed_by_agent ? 'Agent-referenced' : 'Local observation'}
              </small>
            </div>
          ))}
          <h3>Agent’s latest justification</h3>
          <p>
            {responses[selectedId]?.response.mission_justification ??
              d.context_challenge.agent_response?.mission_justification ??
              'No response received.'}
          </p>
          <p>
            Expected effect:{' '}
            {responses[selectedId]?.response.expected_effect ??
              d.context_challenge.agent_response?.expected_effect ??
              'Not supplied'}
          </p>
          <p>
            Alternatives:{' '}
            {(
              responses[selectedId]?.response.alternatives_considered ??
              d.context_challenge.agent_response?.alternatives_considered ??
              []
            ).join(', ') || 'Not supplied'}
          </p>
        </section>
      </div>
      <details className="structured-record">
        <summary>Normalized ALICE decision JSON</summary>
        <pre>{JSON.stringify(d, null, 2)}</pre>
      </details>
    </Modal>
  );
}
