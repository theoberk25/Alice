import { describe, expect, it } from 'vitest';
import {
  deriveAgentActivity,
  deriveEnvironment,
  emptyRuntime,
  latestObservations,
  mergeRuntimeFeed,
  pendingHolds,
  type RuntimeState,
} from '@alice/domain';
import { event, page } from './runtime-fixtures';

type Json = Record<string, unknown>;

/** Builds a valid hash-chained feed so the selectors read real merged state. */
function build(specs: Array<{ type: string; request?: string; detail?: Json }>): RuntimeState {
  const events = specs.map((spec, index) => {
    const raw = event(index + 1, spec.type, spec.request ?? 'request-1') as Json;
    if (spec.detail) raw.detail = { ...(raw.detail as Json), ...spec.detail };
    return raw;
  });
  return mergeRuntimeFeed(emptyRuntime(), page(events));
}

const source = {
  source_id: 'demo-sensor',
  source_event_id: null,
  observed_at: '2026-09-06T01:00:00Z',
  confidence: 'TRUSTED',
  verification: 'VERIFIED',
  freshness: 'FRESH',
  availability: 'AVAILABLE',
};

const observation = (property: string, value: string, unit: string, extra: Json = {}) => ({
  type: 'OBSERVED_STATE',
  detail: {
    asset_id: 'DEMO-SERVER-01',
    sensor_id: 'demo-sensor',
    origin: 'INDEPENDENT_SENSOR',
    property,
    value,
    unit,
    quality: 'GOOD',
    source,
    ...extra,
  },
});

describe('latestObservations', () => {
  it('keeps the newest reading per property', () => {
    const runtime = build([
      observation('server_temperature', '120', 'F'),
      observation('server_temperature', '155', 'F'),
      observation('power_consumption', '500', 'W'),
    ]);
    const latest = latestObservations(runtime);
    expect(latest.get('server_temperature')?.value).toBe(155);
    expect(latest.get('power_consumption')?.value).toBe(500);
    expect(latest.size).toBe(2);
  });

  it('reports an unparsable reading as unknown rather than zero', () => {
    const runtime = build([observation('server_temperature', 'n/a', 'F')]);
    const reading = latestObservations(runtime).get('server_temperature');
    expect(reading?.value).toBeNull();
    expect(reading?.raw).toBe('n/a');
  });

  it('carries quality through untouched', () => {
    const runtime = build([observation('server_temperature', '120', 'F', { quality: 'DEGRADED' })]);
    expect(latestObservations(runtime).get('server_temperature')?.quality).toBe('DEGRADED');
  });
});

describe('deriveEnvironment', () => {
  it('flags temperature at or above the danger threshold', () => {
    expect(deriveEnvironment(build([observation('server_temperature', '149', 'F')])).temperatureOver)
      .toBe(false);
    expect(deriveEnvironment(build([observation('server_temperature', '150', 'F')])).temperatureOver)
      .toBe(true);
  });

  it('flags power only once draw exceeds supply', () => {
    const under = deriveEnvironment(
      build([observation('power_consumption', '440', 'W'), observation('power_supply', '450', 'W')]),
    );
    const over = deriveEnvironment(
      build([observation('power_consumption', '460', 'W'), observation('power_supply', '450', 'W')]),
    );
    expect(under.powerOver).toBe(false);
    expect(over.powerOver).toBe(true);
  });

  it('separates battery warning from danger', () => {
    const danger = deriveEnvironment(build([observation('battery_reserve', '25', 'percent')]));
    const warning = deriveEnvironment(build([observation('battery_reserve', '50', 'percent')]));
    const healthy = deriveEnvironment(build([observation('battery_reserve', '51', 'percent')]));
    expect([danger.batteryDanger, danger.batteryWarning]).toEqual([true, false]);
    expect([warning.batteryDanger, warning.batteryWarning]).toEqual([false, true]);
    expect([healthy.batteryDanger, healthy.batteryWarning]).toEqual([false, false]);
  });

  it('never treats a missing reading as safe or as breached', () => {
    const env = deriveEnvironment(emptyRuntime());
    expect(env.observed).toBe(false);
    expect(env.temperatureOver).toBe(false);
    expect(env.powerOver).toBe(false);
    expect(env.temperatureF).toBeNull();
  });

  it('does not flag power when supply is unknown', () => {
    const env = deriveEnvironment(build([observation('power_consumption', '9999', 'W')]));
    expect(env.powerOver).toBe(false);
  });
});

describe('deriveAgentActivity', () => {
  it('maps decision results onto outcomes, newest first', () => {
    const runtime = build([
      { type: 'REQUEST' },
      { type: 'DECISION', detail: { result: 'ALLOW' } },
      { type: 'DECISION', request: 'request-2', detail: { result: 'CHALLENGE' } },
      { type: 'DECISION', request: 'request-3', detail: { result: 'DENY' } },
    ]);
    const items = deriveAgentActivity(runtime);
    expect(items[0]?.outcome).toBe('deny');
    expect(items[1]?.outcome).toBe('seam');
    expect(items[1]?.hold).toBe(true);
    expect(items[2]?.outcome).toBe('applied');
    expect(items.at(-1)?.kind).toBe('REQUEST');
  });

  it('ignores events with no request correlation and observations', () => {
    const runtime = build([{ type: 'REQUEST' }, observation('server_temperature', '120', 'F')]);
    expect(deriveAgentActivity(runtime)).toHaveLength(1);
  });
});

describe('pendingHolds', () => {
  it('lists held requests and drops those a technician has actioned', () => {
    const runtime = build([
      { type: 'DECISION', detail: { result: 'CHALLENGE' } },
      { type: 'DECISION', request: 'request-2', detail: { result: 'CHALLENGE' } },
      { type: 'TECHNICIAN_ACTION', request: 'request-2', detail: { intent: 'REQUEST_DENIAL' } },
      { type: 'DECISION', request: 'request-3', detail: { result: 'ALLOW' } },
    ]);
    expect(pendingHolds(runtime)).toEqual(['request-1']);
  });
});
