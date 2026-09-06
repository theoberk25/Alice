import { it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { useConsole } from '../../apps/desktop/src/state/console';
import {
  EnvironmentPanel,
  AgentActivityFeed,
  HoldAnnouncement,
} from '../../apps/desktop/src/components/runtime/RuntimeTelemetry';
import { emptyRuntime } from '../../packages/domain/src/runtime-feed';
import { event, page } from './runtime-fixtures';

afterEach(cleanup);

type Json = Record<string, unknown>;

const source = {
  source_id: 'demo-sensor',
  source_event_id: null,
  observed_at: '2026-09-06T01:00:00Z',
  confidence: 'TRUSTED',
  verification: 'VERIFIED',
  freshness: 'FRESH',
  availability: 'AVAILABLE',
};

function reading(sequence: number, property: string, value: string, unit: string) {
  const raw = event(sequence, 'OBSERVED_STATE', 'request-1') as Json;
  raw.detail = {
    asset_id: 'DEMO-SERVER-01',
    sensor_id: 'demo-sensor',
    origin: 'INDEPENDENT_SENSOR',
    property,
    value,
    unit,
    quality: 'GOOD',
    source,
  };
  return raw;
}

function plantState(values: Record<string, number>) {
  return {
    event_type: 'alice.plant_state',
    schema_version: 'alice-plant-snapshot-v1',
    simulation: true,
    status: 'RUNNING',
    revision: 1,
    values,
  };
}

function seed(events: unknown[], feedState = 'live') {
  useConsole.setState({
    mode: 'remote',
    runtime: emptyRuntime(),
    plant: null,
    selectedRuntimeId: '',
    decisions: {},
    errors: [],
    feed: {
      state: feedState,
      last_success_at: 1,
      message: '',
    } as never,
  });
  useConsole.getState().ingest({ ...page(events), event_type: 'alice.runtime_feed' });
}

it('renders live plant readings with threshold colouring', () => {
  seed([reading(1, 'server_temperature', '100', 'F')]);
  useConsole.getState().ingest(
    plantState({
      temperature_f: 161,
      fan_actual_pct: 80,
      fan_target_pct: 90,
      power_w: 500,
      supply_w: 450,
      battery_pct: 18,
      battery_remaining_wh: 18,
      battery_draw_w: 50,
    }),
  );
  const { container } = render(<EnvironmentPanel />);
  expect(screen.getByText('161')).toBeVisible();
  expect(screen.getByText('80')).toBeVisible();
  expect(screen.getByText(/target 90%/)).toBeVisible();
  // Temperature over 150, draw over supply and battery under 25 are all danger.
  expect(container.querySelectorAll('.metric-tile.tone-danger')).toHaveLength(3);
  expect(container.querySelectorAll('.metric-tile.is-stale')).toHaveLength(0);
});

it('prefers the live plant value over the last audited reading', () => {
  seed([reading(1, 'server_temperature', '100', 'F')]);
  const { container, rerender } = render(<EnvironmentPanel />);
  // Audited only: the reading is shown but must not claim to be current.
  expect(screen.getByText('100')).toBeVisible();
  expect(container.querySelectorAll('.metric-tile.is-stale').length).toBeGreaterThan(0);
  useConsole.getState().ingest(plantState({ temperature_f: 207 }));
  rerender(<EnvironmentPanel />);
  expect(screen.getByText('207')).toBeVisible();
  expect(container.querySelectorAll('.metric-tile.is-stale')).toHaveLength(0);
});

it('falls back to the audited reading when the plant snapshot drops', () => {
  seed([reading(1, 'server_temperature', '100', 'F')]);
  useConsole.getState().ingest(plantState({ temperature_f: 207 }));
  const { rerender } = render(<EnvironmentPanel />);
  expect(screen.getByText('207')).toBeVisible();
  useConsole.getState().ingest({ event_type: 'alice.plant_state', unavailable: true });
  rerender(<EnvironmentPanel />);
  expect(screen.getByText('100')).toBeVisible();
});

it('marks every tile stale when the feed is not live', () => {
  seed([reading(1, 'server_temperature', '100', 'F')], 'stale');
  const { container } = render(<EnvironmentPanel />);
  expect(container.querySelectorAll('.metric-tile.is-stale').length).toBeGreaterThan(0);
});

it('reports no readings rather than showing zeroes', () => {
  seed([event(1, 'REQUEST')]);
  render(<EnvironmentPanel />);
  expect(screen.getByText(/No plant readings/)).toBeVisible();
});

it('renders the HOLD seam and selects the request when a card is clicked', () => {
  const held = event(2, 'DECISION', 'request-1') as Json;
  held.detail = { outcome: 'CHALLENGE', result: 'CHALLENGE', reason_codes: [] };
  seed([event(1, 'REQUEST'), held]);
  const { container } = render(<AgentActivityFeed />);
  const seam = container.querySelector('.thought-card.outcome-seam');
  expect(seam).not.toBeNull();
  fireEvent.click(seam!);
  expect(useConsole.getState().selectedRuntimeId).toBe('request-1');
});

it('announces a held request and routes the technician to review it', () => {
  const held = event(2, 'DECISION', 'request-1') as Json;
  held.detail = { outcome: 'CHALLENGE', result: 'CHALLENGE', reason_codes: [] };
  seed([event(1, 'REQUEST'), held]);
  const onReview = vi.fn();
  render(<HoldAnnouncement onReview={onReview} />);
  expect(screen.getByText(/ALICE is holding an agent action/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: /Review in decision history/ }));
  expect(onReview).toHaveBeenCalledOnce();
  expect(useConsole.getState().selectedRuntimeId).toBe('request-1');
});

it('never offers an approve or reject control in the announcement', () => {
  const held = event(2, 'DECISION', 'request-1') as Json;
  held.detail = { outcome: 'CHALLENGE', result: 'CHALLENGE', reason_codes: [] };
  seed([event(1, 'REQUEST'), held]);
  render(<HoldAnnouncement onReview={() => {}} />);
  const labels = screen.getAllByRole('button').map((b) => b.textContent ?? '');
  expect(labels.some((l) => /approve|reject/i.test(l))).toBe(false);
});

it('stays silent once the hold carries a technician action', () => {
  const held = event(2, 'DECISION', 'request-1') as Json;
  held.detail = { outcome: 'CHALLENGE', result: 'CHALLENGE', reason_codes: [] };
  const actioned = event(3, 'TECHNICIAN_ACTION', 'request-1') as Json;
  actioned.detail = { intent: 'REQUEST_DENIAL', reason_codes: [] };
  seed([event(1, 'REQUEST'), held, actioned]);
  const { container } = render(<HoldAnnouncement onReview={() => {}} />);
  expect(container.querySelector('.hold-announcement')).toBeNull();
});
