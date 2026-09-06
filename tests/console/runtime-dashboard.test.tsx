import { it, expect, afterEach } from 'vitest';
import { render, screen, act, cleanup } from '@testing-library/react';
import { useConsole } from '../../apps/desktop/src/state/console';
import {
  RuntimeWorkspace,
  RuntimeHistory,
  RuntimeSystem,
  RuntimeEvidence,
} from '../../apps/desktop/src/components/runtime/RuntimePanels';
import { emptyRuntime } from '../../packages/domain/src/runtime-feed';
import { event, page } from './runtime-fixtures';
import { baseDecision } from '../../fixtures/scenarios';
afterEach(cleanup);
it('updates the existing store and runtime workspace when execution arrives after the decision', () => {
  useConsole.setState({
    mode: 'remote',
    runtime: emptyRuntime(),
    selectedRuntimeId: '',
    decisions: {},
    errors: [],
  });
  useConsole
    .getState()
    .ingest({ ...page([event(), event(2, 'DECISION')]), event_type: 'alice.runtime_feed' });
  render(
    <>
      <RuntimeWorkspace />
      <RuntimeHistory />
      <RuntimeSystem />
      <RuntimeEvidence />
    </>,
  );
  expect(screen.getByRole('heading', { name: 'ALLOW' })).toBeInTheDocument();
  expect(screen.getByText('Risk score: unavailable')).toBeInTheDocument();
  expect(screen.queryByRole('img', { name: /Behavioral risk/ })).not.toBeInTheDocument();
  expect(screen.getByText('MOCK CONTROLLER')).toBeInTheDocument();
  act(() =>
    useConsole
      .getState()
      .ingest({
        ...page([event(2, 'DECISION'), event(3, 'EXECUTION_RESULT')]),
        event_type: 'alice.runtime_feed',
      }),
  );
  expect(screen.getAllByText('COMPLETED').length).toBeGreaterThan(0);
  expect(useConsole.getState().runtime.events).toHaveLength(3);
  expect(useConsole.getState().decisions).toEqual({});
  act(() => useConsole.getState().ingest(baseDecision()));
  expect(useConsole.getState().decisions).toEqual({});
});
it('clears only transient feed errors after recovery', () => {
  useConsole.setState({
    mode: 'remote',
    errors: ['Runtime feed unavailable: Feed HTTP 502', 'Keep this validation error'],
  });
  useConsole
    .getState()
    .ingest({
      event_type: 'alice.feed_status',
      state: 'live',
      last_success_at: 10,
      message: 'Recovered',
    });
  expect(useConsole.getState().errors).toEqual(['Keep this validation error']);
});
