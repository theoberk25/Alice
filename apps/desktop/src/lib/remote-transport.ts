import type { AliceTransport } from '@alice/domain';
import { emptyRuntime, mergeRuntimeFeed } from '@alice/domain';
import type {
  ActionReceipt,
  ClarificationRequest,
  TechnicianAction,
  FeedStatus,
} from '@alice/contracts';
import { nativeCall, isNative } from './native';

interface Options {
  read?: (after: number, signal: AbortSignal) => Promise<unknown>;
  pollMs?: number;
  staleMs?: number;
  timeoutMs?: number;
}
async function readFeed(after: number, signal: AbortSignal): Promise<unknown> {
  if (isNative) return nativeCall('read_runtime_events', { after });
  const response = await fetch(`/api/alice/events?after=${after}`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error(`Feed HTTP ${response.status}`);
  return response.json();
}
export class RemoteAliceTransport implements AliceTransport {
  readonly mode = 'remote' as const;
  constructor(private options: Options = {}) {}
  async connect(
    onEvent: (event: unknown) => void,
    onError: (message: string) => void,
  ): Promise<() => void> {
    let active = true,
      recovering = false;
    let state = emptyRuntime();
    let lastSuccess: number | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    let lastStatus = '';
    const status = (value: FeedStatus['state'], message: string) => {
      if (!active || lastStatus === `${value}:${lastSuccess}`) return;
      lastStatus = `${value}:${lastSuccess}`;
      onEvent({
        event_type: 'alice.feed_status',
        state: value,
        last_success_at: lastSuccess,
        message,
      });
    };
    status('connecting', 'Connecting to the authenticated runtime bridge');
    const staleTimer = setInterval(
      () => {
        if (lastSuccess !== null && Date.now() - lastSuccess >= (this.options.staleMs ?? 10000))
          status(
            'stale',
            'Feed stale; retained events are historical, hardware freshness is unknown',
          );
      },
      Math.min(this.options.pollMs ?? 1500, 1000),
    );
    const poll = async () => {
      controller = new AbortController();
      let deadline: ReturnType<typeof setTimeout> | undefined;
      try {
        const after = recovering ? 0 : state.cursor;
        const payload = await Promise.race([
          (this.options.read ?? readFeed)(after, controller.signal),
          new Promise<never>((_, reject) => {
            deadline = setTimeout(() => {
              controller?.abort();
              reject(new Error('Feed timeout'));
            }, this.options.timeoutMs ?? 6000);
          }),
        ]);
        if (!active) return;
        const next = mergeRuntimeFeed(state, payload);
        // A new USB or rolled-back ledger cannot be silently mixed into
        // retained history. Recovery restarts at the beginning, and the feed
        // is paginated, so the first page of a long ledger legitimately does
        // not carry the acknowledged head; demanding it there wedges the
        // console after any interruption. Only a page that reaches that
        // sequence without containing it proves the ledger diverged.
        // mergeRuntimeFeed above still rejects an identity change, a
        // hash-chain break or a conflicting duplicate on every page.
        const page = payload as { events: { sequence: number }[] };
        const reached = page.events.at(-1)?.sequence ?? 0;
        if (
          state.cursor &&
          reached >= state.cursor &&
          !page.events.some((e) => e.sequence === state.cursor)
        )
          throw new Error('Acknowledged ledger head missing; explicit reconnect required');
        onEvent({ ...(payload as object), event_type: 'alice.runtime_feed' });
        state = next;
        recovering = false;
        lastSuccess = Date.now();
        status('live', 'Runtime feed connected; source and measurement provenance remain separate');
      } catch (error) {
        if (!active) return;
        recovering = true;
        onError(
          `Runtime feed unavailable: ${error instanceof Error ? error.message : String(error)}`,
        );
        status('disconnected', 'Connection failed; retaining received history without fallback');
      } finally {
        clearTimeout(deadline);
        if (active) timer = setTimeout(() => void poll(), this.options.pollMs ?? 1500);
      }
    };
    await poll();
    return () => {
      active = false;
      controller?.abort();
      clearTimeout(timer);
      clearInterval(staleTimer);
    };
  }
  async requestClarification(_request: ClarificationRequest): Promise<void> {
    void _request;
    throw new Error('Remote clarification is unavailable: runtime feed is read-only.');
  }
  async submitTechnicianAction(_action: TechnicianAction): Promise<ActionReceipt> {
    void _action;
    throw new Error(
      'Remote accept/deny delivery is unavailable; no approval or execution was submitted.',
    );
  }
}
