import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from '../../apps/desktop/src/app/App';
import { useConsole } from '../../apps/desktop/src/state/console';
import { baseDecision } from '../../fixtures/scenarios';

const technician = {
  technician_id: 'TECH-DEMO',
  username: 'alex.demo',
  display_name: 'Alex Morgan',
  role: 'Technician',
  enabled: true,
  enrolled: true,
};

function seed(overrides: Partial<ReturnType<typeof useConsole.getState>> = {}) {
  const d = baseDecision();
  useConsole.setState({
    ready: true,
    mode: 'mock',
    biometricMode: 'mock',
    technician,
    decisions: { [d.decision_id]: d },
    order: [d.decision_id],
    selectedId: d.decision_id,
    latestDecisionByRequest: { [d.request.request_id]: d.decision_id },
    flows: { [d.decision_id]: 'AWAITING_TECHNICIAN' },
    responses: {},
    contextRequests: {},
    ...overrides,
  });
  return d;
}

beforeEach(() => {
  vi.spyOn(useConsole.getState(), 'start').mockResolvedValue();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it('offers an enabled Request more context control on a HOLD that requires it', () => {
  seed();
  render(<App />);
  const button = screen.getByRole('button', { name: /Request more context/i });
  expect(button).toBeEnabled();
});

it('invokes the store action for the selected decision when clicked', () => {
  const d = seed();
  const request = vi.spyOn(useConsole.getState(), 'requestContext').mockResolvedValue();
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /Request more context/i }));
  expect(request).toHaveBeenCalledWith(d.decision_id);
});

it('disables the control once the agent context has been received', () => {
  const d = seed();
  render(<App />);
  act(() => {
    useConsole.setState({
      responses: {
        [d.decision_id]: {
          schema_version: '1.0',
          event_type: 'alice.agent_response',
          timestamp: d.timestamp,
          decision_id: d.decision_id,
          request_id: d.request.request_id,
          agent_id: d.request.agent_id,
          challenge_id: d.context_challenge.challenge_id ?? 'CTX-441',
          response: d.context_challenge.agent_response!,
        },
      },
    });
  });
  expect(screen.getByRole('button', { name: /Request more context/i })).toBeDisabled();
});

it('disables the control while a request is already in flight', () => {
  const d = seed({ contextRequests: { [baseDecision().decision_id]: 'CTX-441' } });
  render(<App />);
  expect(useConsole.getState().contextRequests[d.decision_id]).toBe('CTX-441');
  expect(screen.getByRole('button', { name: /Request more context/i })).toBeDisabled();
});

it('disables the control for a HOLD that requires no further context', () => {
  const d = baseDecision();
  d.context_challenge.required = false;
  seed({ decisions: { [d.decision_id]: d } });
  render(<App />);
  expect(screen.getByRole('button', { name: /Request more context/i })).toBeDisabled();
});
