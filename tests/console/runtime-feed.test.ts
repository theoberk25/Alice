import { describe, it, expect, vi, afterEach } from 'vitest';
import { mergeRuntimeFeed, emptyRuntime } from '../../packages/domain/src/runtime-feed';
import { RemoteAliceTransport } from '../../apps/desktop/src/lib/transport';

import { event, page } from './runtime-fixtures';

describe('runtime ledger mapping', () => {
  it('loads sorted history and later execution without mutating the original decision', () => {
    const initial = mergeRuntimeFeed(emptyRuntime(), page([event(2, 'DECISION'), event()]));
    expect(initial.requests['request-1']!.events.map((e) => e.sequence)).toEqual([1, 2]);
    const next = mergeRuntimeFeed(
      initial,
      page([event(2, 'DECISION'), event(3, 'EXECUTION_RESULT')]),
    );
    expect(next.requests['request-1']!.decision?.detail.outcome).toBe('ALLOW');
    expect(next.requests['request-1']!.execution?.detail.outcome).toBe('COMPLETED');
    expect(initial.requests['request-1']!.execution).toBeUndefined();
    expect(next.requests['request-1']!.decision).toEqual(initial.requests['request-1']!.decision);
  });
  it('ignores exact duplicates and rejects conflicts, gaps, malformed and mismatched request hashes atomically', () => {
    const initial = mergeRuntimeFeed(emptyRuntime(), page([event()]));
    expect(mergeRuntimeFeed(initial, page([event()])).events).toEqual(initial.events);
    for (const broken of [
      { ...event(), detail: { outcome: 'DENIED' } },
      event(3),
      { sequence: 2 },
      { ...event(2), correlation: { ...event(2).correlation, request_sha256: 'c'.repeat(64) } },
      { ...event(2), node_id: 'different-node' },
    ])
      expect(() => mergeRuntimeFeed(initial, page([broken]))).toThrow();
    expect(initial.events).toHaveLength(1);
  });
  it('retains null timestamp, unavailable readings, raw units and provenance without synthesized decision fields', () => {
    const raw = {
      ...event(),
      time: { ...event().time, recorded_at: null, confidence: 'UNAVAILABLE' },
      correlation: { ...event().correlation, request_id: null, request_sha256: null },
    };
    const state = mergeRuntimeFeed(emptyRuntime(), page([raw]));
    expect(state.events[0]!.time.recorded_at).toBeNull();
    expect(Object.keys(state.requests)).toHaveLength(0);
    expect(JSON.stringify(state)).not.toMatch(/risk_score|VERIFIED_LOCAL|cloud_connected/);
  });
});

afterEach(() => vi.useRealTimers());
it('polls initial history and increments automatically, recovers after disconnect and cancels cleanly', async () => {
  vi.useFakeTimers();
  const read = vi
    .fn()
    .mockResolvedValueOnce(page([event()]))
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue(page([event(), event(2, 'DECISION')]));
  const emit = vi.fn(),
    errors = vi.fn();
  const remote = new RemoteAliceTransport({ read, pollMs: 100, staleMs: 200, timeoutMs: 150 });
  const stop = await remote.connect(emit, errors);
  await vi.advanceTimersByTimeAsync(350);
  expect(read.mock.calls.map((c) => c[0])).toEqual([0, 1, 0, 2]);
  expect(
    emit.mock.calls.some(
      (c) => c[0].event_type === 'alice.runtime_feed' && c[0].events.length === 2,
    ),
  ).toBe(true);
  expect(errors).toHaveBeenCalled();
  expect(emit.mock.calls.some((c) => c[0].state === 'disconnected')).toBe(true);
  stop();
  const calls = read.mock.calls.length;
  await vi.advanceTimersByTimeAsync(1000);
  expect(read).toHaveBeenCalledTimes(calls);
});
it('never acknowledges malformed input or invents success for remote actions', async () => {
  vi.useFakeTimers();
  const remote = new RemoteAliceTransport({
    read: async () => page([{ sequence: 1 }]),
    pollMs: 100,
  });
  const emit = vi.fn(),
    errors = vi.fn();
  const stop = await remote.connect(emit, errors);
  expect(errors).toHaveBeenCalled();
  expect(emit.mock.calls.filter((c) => c[0].event_type === 'alice.runtime_feed')).toHaveLength(0);
  await expect(remote.requestClarification({} as never)).rejects.toThrow();
  await expect(remote.submitTechnicianAction({} as never)).rejects.toThrow();
  stop();
});
it('marks retained data stale during a hung request and ignores late data after cleanup', async () => {
  vi.useFakeTimers();
  let resolveLate: (input: unknown) => void = () => {};
  const read = vi
    .fn()
    .mockResolvedValueOnce(page([event()]))
    .mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLate = resolve;
        }),
    );
  const emit = vi.fn();
  const remote = new RemoteAliceTransport({ read, pollMs: 100, staleMs: 200, timeoutMs: 1000 });
  const stop = await remote.connect(emit, () => {});
  await vi.advanceTimersByTimeAsync(300);
  expect(emit.mock.calls.some((c) => c[0].state === 'stale')).toBe(true);
  stop();
  const count = emit.mock.calls.length;
  resolveLate(page([event(), event(2, 'DECISION')]));
  await vi.advanceTimersByTimeAsync(1200);
  expect(emit).toHaveBeenCalledTimes(count);
});
it('supports contract-valid request IDs that match object prototype names', () => {
  const state = mergeRuntimeFeed(
    emptyRuntime(),
    page([event(1, 'REQUEST', 'constructor'), event(2, 'DECISION', 'constructor')]),
  );
  expect(Object.values(state.requests).find((r) => r.id === 'constructor')?.events).toHaveLength(2);
});
