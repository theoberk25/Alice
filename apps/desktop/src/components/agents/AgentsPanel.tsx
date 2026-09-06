import { Bot, Network, Search, ArrowUpRight } from 'lucide-react';
import { Panel, Badge, toneFor, human, AnimatedCounter } from '@alice/ui';
import { useConsole } from '../../state/console';
export function AgentsPanel() {
  const agents = Object.values(useConsole((s) => s.agents));
  const d = useConsole((s) => s.decisions[s.selectedId]);
  return (
    <Panel
      className="agents-panel"
      title="Agent network"
      meta={
        <span className="count-label">
          <AnimatedCounter value={agents.length.toString().padStart(2, '0')} /> nodes
        </span>
      }
    >
      <div className="agent-list">
        {agents.map((a) => (
          <article
            className={`agent-card ${d?.request.agent_id === a.agent_id ? 'agent-selected' : ''}`}
            key={a.agent_id}
          >
            <div className="agent-title">
              <span className="agent-icon">
                {a.agent_type === 'research' ? (
                  <Search size={17} />
                ) : a.agent_type === 'network' ? (
                  <Network size={17} />
                ) : (
                  <Bot size={17} />
                )}
              </span>
              <span>
                <strong>{a.agent_id}</strong>
                <small>{a.agent_type} agent</small>
              </span>
              {d?.request.agent_id === a.agent_id && <ArrowUpRight size={13} />}
            </div>
            <div className="agent-model">{a.model}</div>
            <Badge tone={toneFor(a.status)}>{human(a.status)}</Badge>
            <p className="agent-activity">{a.current_activity.label}</p>
            <div className="agent-foot">
              <span>{a.mission_id}</span>
              <span className={`tone-${toneFor(a.health)}`}>{a.health}</span>
            </div>
          </article>
        ))}
      </div>
      <div className="panel-footnote">
        <span className="mini-pulse" /> Agent state reported by ALICE
      </div>
    </Panel>
  );
}
