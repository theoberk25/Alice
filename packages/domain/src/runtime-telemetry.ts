import type { RuntimeEvent } from '@alice/contracts';
import type { RuntimeState } from './runtime-feed';

/** Thresholds are the demo's, kept verbatim so the console and the plant agree. */
export const TEMPERATURE_DANGER_F = 150;
export const BATTERY_DANGER_PCT = 25;
export const BATTERY_WARNING_PCT = 50;

export type Quality = NonNullable<RuntimeEvent['detail']['quality']>;

export interface Observation {
  property: string;
  value: number | null;
  raw: string | null;
  unit: string;
  quality: Quality;
  origin?: RuntimeEvent['detail']['origin'];
  assetId?: string;
  recordedAt: string | null;
  sequence: number;
}

/**
 * Latest reading per property across the whole feed.
 *
 * Reads runtime.events rather than request.observation: a request now carries
 * one observation per property and that field keeps only the last of them.
 */
export function latestObservations(runtime: RuntimeState): Map<string, Observation> {
  const latest = new Map<string, Observation>();
  for (const event of runtime.events) {
    if (event.event_type !== 'OBSERVED_STATE') continue;
    const { property, value, unit, quality } = event.detail;
    if (!property) continue;
    const prior = latest.get(property);
    if (prior && prior.sequence >= event.sequence) continue;
    const parsed = value === null || value === undefined ? null : Number(value);
    latest.set(property, {
      property,
      value: parsed === null || Number.isNaN(parsed) ? null : parsed,
      raw: value ?? null,
      unit: unit ?? '',
      quality: quality ?? 'UNKNOWN',
      origin: event.detail.origin,
      assetId: event.detail.asset_id,
      recordedAt: event.time.recorded_at,
      sequence: event.sequence,
    });
  }
  return latest;
}

export interface EnvironmentTelemetry {
  temperatureF: Observation | null;
  fanActual: Observation | null;
  fanTarget: Observation | null;
  powerW: Observation | null;
  supplyW: Observation | null;
  batteryPct: Observation | null;
  batteryWh: Observation | null;
  batteryDrawW: Observation | null;
  temperatureOver: boolean;
  powerOver: boolean;
  batteryDanger: boolean;
  batteryWarning: boolean;
  /** True once any reading exists; the panel renders empty rather than zeroed. */
  observed: boolean;
}

export function deriveEnvironment(runtime: RuntimeState): EnvironmentTelemetry {
  const latest = latestObservations(runtime);
  const at = (property: string) => latest.get(property) ?? null;
  const temperatureF = at('server_temperature');
  const fanActual = at('simulated_fan_actual');
  const fanTarget = at('simulated_fan_target');
  const powerW = at('power_consumption');
  const supplyW = at('power_supply');
  const batteryPct = at('battery_reserve');
  const batteryWh = at('battery_remaining_wh');
  const batteryDrawW = at('battery_draw');
  // An unknown reading is never treated as safe, so a missing value cannot
  // clear a threshold that the plant may in fact have crossed.
  const num = (o: Observation | null) => (o && o.value !== null ? o.value : null);
  const temperature = num(temperatureF);
  const power = num(powerW);
  const supply = num(supplyW);
  const battery = num(batteryPct);
  return {
    temperatureF,
    fanActual,
    fanTarget,
    powerW,
    supplyW,
    batteryPct,
    batteryWh,
    batteryDrawW,
    temperatureOver: temperature !== null && temperature >= TEMPERATURE_DANGER_F,
    powerOver: power !== null && supply !== null && power > supply,
    batteryDanger: battery !== null && battery <= BATTERY_DANGER_PCT,
    batteryWarning: battery !== null && battery > BATTERY_DANGER_PCT && battery <= BATTERY_WARNING_PCT,
    observed: latest.size > 0,
  };
}

export type ActivityOutcome = 'applied' | 'seam' | 'deny' | 'pending' | 'failed';
export type ActivityKind = 'REQUEST' | 'ASSESSMENT' | 'DECISION' | 'EXECUTION_RESULT';

export interface AgentActivityItem {
  eventId: string;
  requestId: string;
  agentId: string;
  actorKind?: string;
  kind: ActivityKind;
  summary: string;
  outcome: ActivityOutcome;
  recordedAt: string | null;
  sequence: number;
  /** Present on DECISION events that a technician may still act on. */
  hold: boolean;
}

const ACTIVITY_KINDS: ActivityKind[] = ['REQUEST', 'ASSESSMENT', 'DECISION', 'EXECUTION_RESULT'];

function outcomeFor(event: RuntimeEvent): ActivityOutcome {
  const detail = event.detail;
  if (event.event_type === 'DECISION') {
    const result = detail.result ?? detail.outcome ?? '';
    if (result === 'ALLOW') return 'applied';
    if (result === 'DENY') return 'deny';
    if (result === 'CHALLENGE' || result === 'HOLD') return 'seam';
    return 'pending';
  }
  if (event.event_type === 'EXECUTION_RESULT')
    return detail.outcome === 'COMPLETED' ? 'applied' : 'failed';
  return 'pending';
}

function summarize(event: RuntimeEvent): string {
  const detail = event.detail;
  const codes = detail.reason_codes?.length ? ` (${detail.reason_codes.join(', ')})` : '';
  switch (event.event_type) {
    case 'REQUEST':
      return `Requested ${detail.outcome ?? 'action'}${codes}`;
    case 'ASSESSMENT':
      return `Assessed ${detail.result ?? detail.status ?? 'behaviour'}${codes}`;
    case 'DECISION':
      return `ALICE returned ${detail.result ?? detail.outcome ?? 'a decision'}${codes}`;
    default:
      return `Execution ${detail.outcome ?? 'reported'}${codes}`;
  }
}

/** Newest first. Purely observational; acting on a request stays with review. */
export function deriveAgentActivity(runtime: RuntimeState, limit = 40): AgentActivityItem[] {
  const items: AgentActivityItem[] = [];
  for (const event of runtime.events) {
    if (!ACTIVITY_KINDS.includes(event.event_type as ActivityKind)) continue;
    const requestId = event.correlation.request_id;
    if (!requestId) continue;
    const outcome = outcomeFor(event);
    items.push({
      eventId: event.event_id,
      requestId,
      agentId: event.attribution.agent_id ?? event.attribution.actor_id ?? 'unknown',
      actorKind: event.attribution.actor_kind,
      kind: event.event_type as ActivityKind,
      summary: summarize(event),
      outcome,
      recordedAt: event.time.recorded_at,
      sequence: event.sequence,
      hold: event.event_type === 'DECISION' && outcome === 'seam',
    });
  }
  return items.sort((a, b) => b.sequence - a.sequence).slice(0, limit);
}

/**
 * Requests ALICE held that carry no technician action yet.
 *
 * The console announces these; the review panel remains the only place an
 * action can be signed, so this reports nothing about eligibility.
 */
export function pendingHolds(runtime: RuntimeState): string[] {
  const held: string[] = [];
  for (const request of Object.values(runtime.requests)) {
    const result = request.decision?.detail.result ?? request.decision?.detail.outcome;
    if (result !== 'CHALLENGE' && result !== 'HOLD') continue;
    if (request.events.some((e) => e.event_type === 'TECHNICIAN_ACTION')) continue;
    held.push(request.id);
  }
  return held;
}

/**
 * Environment values preferring live plant telemetry over the last audited
 * reading.
 *
 * The ledger records a reading only when a request executes, so audited values
 * go stale while the plant keeps moving. Live values are shown when present
 * and fall back to the audited observation otherwise, with `live` saying which
 * a tile is displaying so the console can label provenance honestly.
 */
export function mergePlant(
  audited: EnvironmentTelemetry,
  plant: { values: Record<string, number> } | null,
): EnvironmentTelemetry & { live: boolean } {
  if (!plant) return { ...audited, live: false };
  const at = (key: string, property: string): Observation | null => {
    const value = plant.values[key];
    const prior = priorFor(audited, property);
    if (typeof value !== 'number' || Number.isNaN(value)) return prior;
    return {
      property,
      value,
      raw: String(value),
      unit: prior?.unit ?? '',
      quality: 'GOOD',
      origin: 'SIMULATED',
      assetId: prior?.assetId,
      recordedAt: null,
      sequence: prior?.sequence ?? 0,
    };
  };
  const temperatureF = at('temperature_f', 'server_temperature');
  const fanActual = at('fan_actual_pct', 'simulated_fan_actual');
  const fanTarget = at('fan_target_pct', 'simulated_fan_target');
  const powerW = at('power_w', 'power_consumption');
  const supplyW = at('supply_w', 'power_supply');
  const batteryPct = at('battery_pct', 'battery_reserve');
  const batteryWh = at('battery_remaining_wh', 'battery_remaining_wh');
  const batteryDrawW = at('battery_draw_w', 'battery_draw');
  const num = (o: Observation | null) => (o && o.value !== null ? o.value : null);
  const temperature = num(temperatureF);
  const power = num(powerW);
  const supply = num(supplyW);
  const battery = num(batteryPct);
  return {
    temperatureF,
    fanActual,
    fanTarget,
    powerW,
    supplyW,
    batteryPct,
    batteryWh,
    batteryDrawW,
    temperatureOver: temperature !== null && temperature >= TEMPERATURE_DANGER_F,
    powerOver: power !== null && supply !== null && power > supply,
    batteryDanger: battery !== null && battery <= BATTERY_DANGER_PCT,
    batteryWarning:
      battery !== null && battery > BATTERY_DANGER_PCT && battery <= BATTERY_WARNING_PCT,
    observed: true,
    live: true,
  };
}

type ObservationField =
  | 'temperatureF'
  | 'fanActual'
  | 'fanTarget'
  | 'powerW'
  | 'supplyW'
  | 'batteryPct'
  | 'batteryWh'
  | 'batteryDrawW';

const FIELD_BY_PROPERTY: Record<string, ObservationField> = {
  server_temperature: 'temperatureF',
  simulated_fan_actual: 'fanActual',
  simulated_fan_target: 'fanTarget',
  power_consumption: 'powerW',
  power_supply: 'supplyW',
  battery_reserve: 'batteryPct',
  battery_remaining_wh: 'batteryWh',
  battery_draw: 'batteryDrawW',
};

function priorFor(audited: EnvironmentTelemetry, property: string): Observation | null {
  const field = FIELD_BY_PROPERTY[property];
  return field ? audited[field] : null;
}
