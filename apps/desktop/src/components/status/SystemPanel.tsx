import { Shield, Cpu, Database, CloudOff, Cable, Fingerprint, Activity } from 'lucide-react';
import { Panel, Badge, toneFor, human } from '@alice/ui';
import { useConsole } from '../../state/console';
export function SystemPanel() {
  const { status: s, services, llm, biometricMode, selectedId, flows } = useConsole();
  const items = [
    {
      label: 'Policy engine',
      state: s?.decision_engine.policy_engine ?? 'UNKNOWN',
      icon: Shield,
      detail: s
        ? `Signed package v${s.packages.policy.version} · ${s.packages.policy.signature}`
        : 'Awaiting status',
    },
    {
      label: 'Operations baseline',
      state: s?.packages.operations_baseline.loaded ? 'READY' : 'UNAVAILABLE',
      icon: Database,
      detail: s
        ? `Baseline v${s.packages.operations_baseline.version} · ${s.packages.operations_baseline.signature}`
        : 'Awaiting status',
    },
    {
      label: 'Anomaly engine',
      state: s?.decision_engine.anomaly_engine ?? 'UNKNOWN',
      icon: Cpu,
      detail: 'Local behavioral evaluation',
    },
    {
      label: 'Protected endpoint',
      state: s?.connections.protected_system ? 'CONNECTED' : 'OFFLINE',
      icon: Cable,
      detail: 'Enforcement boundary',
    },
  ];
  return (
    <>
      <Panel
        className="integrity-panel"
        title="System integrity"
        meta={<span className="count-label">LOCAL NODE</span>}
      >
        <div className="system-rows">
          {items.map(({ label, state, icon: Icon, detail }) => (
            <div className="system-row" key={label}>
              <Icon size={15} />
              <div>
                <strong>{label}</strong>
                <small>{detail}</small>
              </div>
              <span className={`small-status tone-${toneFor(state)}`}>{state}</span>
            </div>
          ))}
        </div>
        <div className="connectivity-strip">
          <CloudOff size={15} />
          <span>
            Cloud <b>{s?.connections.cloud ? 'ONLINE' : 'OFFLINE'}</b>
          </span>
          <span>
            SIEM <b>{s?.connections.siem ? 'ONLINE' : 'OFFLINE'}</b>
          </span>
          <span>
            EDR <b>{s?.connections.edr ? 'ONLINE' : 'OFFLINE'}</b>
          </span>
        </div>
      </Panel>
      <Panel className="activity-panel" title="Internal activity" meta={<Activity size={14} />}>
        <div className="service-list">
          {Object.values(services).map((service) => (
            <div className="service-row" key={service.service_id}>
              <span>
                {service.label}
                <small>{service.detail}</small>
              </span>
              <Badge tone={toneFor(service.status)}>{service.status}</Badge>
            </div>
          ))}
          <div className="service-row">
            <span>
              Context investigation<small>{human(flows[selectedId] ?? 'IDLE')}</small>
            </span>
            <Badge
              tone={flows[selectedId] === 'AWAITING_AGENT_RESPONSE' ? 'information' : 'neutral'}
            >
              {flows[selectedId] === 'AWAITING_AGENT_RESPONSE' ? 'RUNNING' : 'IDLE'}
            </Badge>
          </div>
          <div className="service-row">
            <span>
              Local language gateway<small>{llm.model || 'Model not configured'}</small>
            </span>
            <Badge tone={toneFor(llm.status)}>{llm.status}</Badge>
          </div>
          <div className="service-row">
            <span>
              <Fingerprint size={12} /> Face identity
              <small>
                {biometricMode === 'mock' ? 'Simulated verification' : 'Local camera verification'}
              </small>
            </span>
            <Badge tone="neutral">{biometricMode === 'mock' ? 'SIMULATED' : 'ON DEMAND'}</Badge>
          </div>
        </div>
      </Panel>
    </>
  );
}
