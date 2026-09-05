import { render, screen, cleanup, act, fireEvent, within } from '@testing-library/react';
import { it, expect, beforeEach, afterEach, vi } from 'vitest';
import { DecisionWorkspace } from '../../apps/desktop/src/components/decisions/DecisionWorkspace';
import { baseDecision, reassessedDecision } from '../../fixtures/scenarios';
import { useConsole } from '../../apps/desktop/src/state/console';
import { History } from '../../apps/desktop/src/components/audit/History';
import { ApprovalModal } from '../../apps/desktop/src/components/biometrics/ApprovalModal';
beforeEach(async () => {
  vi.useFakeTimers();
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
  };
  await useConsole.getState().start('04_hold_context_rejustification');
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
it('shows the original supplied HOLD, anomaly and execution status', () => {
  render(<DecisionWorkspace decision={baseDecision()} onResearch={() => {}} />);
  expect(screen.getByRole('heading', { name: 'HOLD' })).toBeInTheDocument();
  expect(screen.getByRole('img', { name: 'Behavioral risk 94 of 100, HIGH' })).toBeInTheDocument();
  expect(screen.getByText('NOT EXECUTED')).toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/DCAMR/);
});
it('shows pending reassessment followed by both immutable assessments and deterministic deltas', async () => {
  function Current() {
    const s = useConsole();
    return <DecisionWorkspace decision={s.decisions[s.selectedId]!} onResearch={() => {}} />;
  }
  render(<Current />);
  await act(() => vi.advanceTimersByTimeAsync(1200));
  expect(screen.getByRole('status')).toHaveTextContent('Reassessment pending');
  expect(screen.getByRole('img', { name: 'Behavioral risk 94 of 100, HIGH' })).toBeInTheDocument();
  await act(() => vi.advanceTimersByTimeAsync(1200));
  const lineage = screen.getByRole('list', { name: 'Decision reassessment history' });
  for (const label of [
    'Original decision',
    'Automatic context request',
    'Agent response',
    'Reassessment · Current decision',
  ])
    expect(within(lineage).getByText(label)).toBeInTheDocument();
  expect(screen.getByText('94 → 62')).toBeInTheDocument();
  expect(screen.getByText('1 → 2')).toBeInTheDocument();
  expect(screen.getByText('HOLD → HOLD')).toBeInTheDocument();
  expect(screen.getByText('CURRENT ASSESSMENT')).toBeInTheDocument();
  fireEvent.click(
    within(lineage).getByRole('button', { name: 'Inspect assessment DEC-20260905-000184' }),
  );
  expect(screen.getByText('ORIGINAL ASSESSMENT')).toBeInTheDocument();
  expect(screen.getByRole('img', { name: 'Behavioral risk 94 of 100, HIGH' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /View current assessment/ }));
  expect(
    screen.getByRole('img', { name: 'Behavioral risk 62 of 100, MEDIUM' }),
  ).toBeInTheDocument();
});
it('groups selectable original and current records in history', () => {
  useConsole.getState().ingest(reassessedDecision());
  render(<History expanded />);
  expect(screen.getByText('REASSESSMENT · CURRENT')).toBeInTheDocument();
  expect(
    screen.getByText(/Parent DEC-20260905-000184 · root DEC-20260905-000184/),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Inspect DEC-20260905-000184 HELD' }));
  expect(useConsole.getState().selectedId).toBe('DEC-20260905-000184');
  fireEvent.click(screen.getByRole('button', { name: 'Inspect DEC-20260905-000185 HELD' }));
  expect(useConsole.getState().selectedId).toBe('DEC-20260905-000185');
});
it('blocks an already open approval dialog when a successor arrives', () => {
  useConsole.getState().advance('APPROVE');
  useConsole.getState().advance('REQUIRE_BIOMETRIC');
  render(<ApprovalModal decisionId="DEC-20260905-000184" onClose={() => {}} />);
  act(() => useConsole.getState().ingest(reassessedDecision()));
  expect(screen.getByRole('alert')).toHaveTextContent('superseded');
  expect(screen.queryByRole('button', { name: 'Simulate pass' })).not.toBeInTheDocument();
  expect(Object.keys(useConsole.getState().actions)).toHaveLength(0);
});
