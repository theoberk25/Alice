import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../apps/desktop/src/app/App';
import { useConsole } from '../apps/desktop/src/state/console';
import { baseDecision } from '../fixtures/scenarios';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it('hides cached decisions and technician actions until a real identity logs in', () => {
  const d = baseDecision();
  useConsole.setState({
    ready: true,
    biometricMode: 'arcface',
    technician: undefined,
    decisions: { [d.decision_id]: d },
    order: [d.decision_id],
    selectedId: d.decision_id,
  });
  vi.spyOn(useConsole.getState(), 'start').mockResolvedValue();
  render(<App />);
  expect(screen.getByRole('heading', { name: 'Technician identity required' })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'HOLD' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Approve once' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Decision history' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Administration' }));
  expect(screen.getByLabelText('Admin username')).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'HOLD' })).not.toBeInTheDocument();
});
