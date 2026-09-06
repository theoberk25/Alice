import { useEffect, useRef, useState } from 'react';
import { Panel, Badge, Empty, MetricTile, AgentThoughtCard, CommandButton } from '@alice/ui';
import {
  deriveAgentActivity,
  deriveEnvironment,
  mergePlant,
  pendingHolds,
  type Observation,
} from '@alice/domain';
import { useConsole } from '../../state/console';

const round = (value: number, places = 0) =>
  value.toLocaleString(undefined, { maximumFractionDigits: places, minimumFractionDigits: 0 });

const show = (o: Observation | null, places = 0) =>
  o && o.value !== null ? round(o.value, places) : null;

/** A reading the feed has stopped refreshing must never read as current. */
function tileQuality(o: Observation | null): string {
  return o ? o.quality : 'UNAVAILABLE';
}

export function EnvironmentPanel() {
  const runtime = useConsole((s) => s.runtime);
  const feed = useConsole((s) => s.feed);
  const plant = useConsole((s) => s.plant);
  // Live plant values when the snapshot is available, the last audited reading
  // otherwise. A tile must never present an audited value as if it were now.
  const env = mergePlant(deriveEnvironment(runtime), plant);
  const stale = !env.live;
  const supply = show(env.supplyW);
  const draw = show(env.batteryDrawW);
  const wh = show(env.batteryWh);
  return (
    <Panel
      title="Environment"
      meta={
        <Badge tone={env.live ? 'healthy' : 'warning'}>
          {env.live ? 'LIVE' : feed.state === 'live' ? 'LAST RECORDED' : feed.state.toUpperCase()}
        </Badge>
      }
    >
      {!env.observed ? (
        <Empty>No plant readings have been observed on this feed yet.</Empty>
      ) : (
        <div className="metric-grid">
          <MetricTile
            label="Server temperature"
            accent="temperature"
            value={show(env.temperatureF)}
            unit="°F"
            tone={env.temperatureOver ? 'danger' : 'healthy'}
            stale={stale}
            quality={tileQuality(env.temperatureF)}
            sub={`room 72°F · setpoint ~${150}°F`}
          />
          <MetricTile
            label="Fan speed"
            accent="fan"
            value={show(env.fanActual)}
            unit="%"
            tone="information"
            stale={stale}
            quality={tileQuality(env.fanActual)}
            bar={env.fanActual?.value ?? null}
            ghost={env.fanTarget?.value ?? null}
            sub={`target ${show(env.fanTarget) ?? '--'}%`}
          />
          <MetricTile
            label="Power draw"
            accent="power"
            value={show(env.powerW)}
            unit="W"
            tone={env.powerOver ? 'danger' : 'healthy'}
            stale={stale}
            quality={tileQuality(env.powerW)}
            sub={`supply ${supply ?? '--'}W · over-supply draw ${draw ?? '--'}W`}
          />
          <MetricTile
            label="Battery reserve"
            accent="battery"
            value={show(env.batteryPct)}
            unit="%"
            tone={env.batteryDanger ? 'danger' : env.batteryWarning ? 'warning' : 'healthy'}
            stale={stale}
            quality={tileQuality(env.batteryPct)}
            bar={env.batteryPct?.value ?? null}
            sub={`${wh ?? '--'} Wh remaining`}
          />
        </div>
      )}
    </Panel>
  );
}

export function AgentActivityFeed() {
  const runtime = useConsole((s) => s.runtime);
  const selectedRuntimeId = useConsole((s) => s.selectedRuntimeId);
  const selectRuntime = useConsole((s) => s.selectRuntime);
  const items = deriveAgentActivity(runtime);
  return (
    <Panel title="Agent activity">
      {items.length === 0 ? (
        <Empty>No agent activity has reached this console yet.</Empty>
      ) : (
        <div className="thought-feed">
          {items.map((item) => (
            <AgentThoughtCard
              key={item.eventId}
              agentId={item.agentId}
              kind={item.kind}
              summary={item.summary}
              outcome={item.outcome}
              timestamp={item.recordedAt}
              selected={item.requestId === selectedRuntimeId}
              onSelect={() => selectRuntime(item.requestId)}
            />
          ))}
        </div>
      )}
    </Panel>
  );
}

/**
 * Announces a newly held request on the operations page.
 *
 * It selects the request and sends the technician to the review surface. It
 * never carries an approve or reject control: those require the signed,
 * face-bound proof that only the review panel can build.
 */
export function HoldAnnouncement({ onReview }: { onReview: () => void }) {
  const runtime = useConsole((s) => s.runtime);
  const selectRuntime = useConsole((s) => s.selectRuntime);
  const held = pendingHolds(runtime);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const seen = useRef<string[]>([]);
  const pending = held.filter((id) => !dismissed.includes(id));
  const current = pending.at(-1);

  useEffect(() => {
    // A hold that is resolved elsewhere should stop being announced, and one
    // that reappears after a reconnect should not be suppressed by a stale
    // dismissal, so forget ids the feed no longer reports as held.
    seen.current = held;
    setDismissed((prior) => prior.filter((id) => held.includes(id)));
  }, [held.join(',')]);

  if (!current) return null;
  return (
    <div className="hold-announcement" role="status">
      <div className="hold-announcement-body">
        <strong>ALICE is holding an agent action</strong>
        <span>
          {pending.length > 1 ? `${pending.length} requests await review. ` : ''}
          Request {current.slice(0, 12)} needs a technician decision.
        </span>
      </div>
      <div className="hold-announcement-actions">
        <CommandButton
          onClick={() => {
            selectRuntime(current);
            onReview();
          }}
        >
          Review in decision history
        </CommandButton>
        <CommandButton onClick={() => setDismissed((prior) => [...prior, current])}>
          Dismiss
        </CommandButton>
      </div>
    </div>
  );
}
