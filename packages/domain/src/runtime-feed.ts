import { RuntimeFeedSchema, type RuntimeEvent, type RuntimeFeed } from '@alice/contracts';
export interface RuntimeRequest {
  id: string;
  events: RuntimeEvent[];
  decision?: RuntimeEvent;
  assessment?: RuntimeEvent;
  receipt?: RuntimeEvent;
  execution?: RuntimeEvent;
  observation?: RuntimeEvent;
}
export interface RuntimeState {
  source?: RuntimeFeed['source'];
  events: RuntimeEvent[];
  requests: Record<string, RuntimeRequest>;
  cursor: number;
}
export const emptyRuntime = (): RuntimeState => ({ events: [], requests: {}, cursor: 0 });
// Object key order is not event identity. Preserve all fields for conflict checks.
function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object')
    return `{${Object.entries(value)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${JSON.stringify(k)}:${canonical(v)}`)
      .join(',')}}`;
  return JSON.stringify(value);
}
export function mergeRuntimeFeed(current: RuntimeState, input: unknown): RuntimeState {
  const page = RuntimeFeedSchema.parse(input);
  if (current.source && canonical(current.source) !== canonical(page.source))
    throw new Error('Runtime source changed; reconnect explicitly');
  const events = [...current.events];
  const ids = new Map(events.map((e) => [e.event_id, e]));
  const bindings = new Map(
    Object.values(current.requests).map((r) => [r.id, r.events[0]!.correlation.request_sha256]),
  );
  for (const event of [...page.events].sort((a, b) => a.sequence - b.sequence)) {
    const prior = events[event.sequence - 1];
    if (prior) {
      if (canonical(prior) !== canonical(event))
        throw new Error('Conflicting duplicate ledger event');
      continue;
    }
    const head = events.at(-1);
    if (
      ids.has(event.event_id) ||
      event.sequence !== events.length + 1 ||
      event.previous_hash !== (head?.event_hash ?? '0'.repeat(64)) ||
      (head && (head.ledger_id !== event.ledger_id || head.node_id !== event.node_id))
    )
      throw new Error('Ledger gap, identity change or hash-chain conflict');
    const rid = event.correlation.request_id;
    if (rid) {
      if (
        !event.correlation.request_sha256 ||
        (bindings.has(rid) && bindings.get(rid) !== event.correlation.request_sha256)
      )
        throw new Error('Conflicting request digest');
      bindings.set(rid, event.correlation.request_sha256);
    }
    ids.set(event.event_id, event);
    events.push(event);
  }
  const requests: Record<string, RuntimeRequest> = Object.create(null);
  for (const event of events) {
    const rid = event.correlation.request_id;
    if (!rid) continue;
    const request = (requests[rid] ??= { id: rid, events: [] });
    request.events.push(event);
    if (event.event_type === 'DECISION' || event.event_type === 'REJECTION')
      request.decision = event;
    if (event.event_type === 'ASSESSMENT') request.assessment = event;
    if (event.event_type === 'CONTROLLER_RECEIPT') request.receipt = event;
    if (event.event_type === 'EXECUTION_RESULT') request.execution = event;
    if (event.event_type === 'OBSERVED_STATE') request.observation = event;
  }
  return { source: page.source, events, requests, cursor: events.at(-1)?.sequence ?? 0 };
}
