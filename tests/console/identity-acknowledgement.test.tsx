import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { LiveBiometricSession } from '@alice/contracts';
import { IdentityPanel } from '../../apps/desktop/src/components/technicians/IdentityPanel';
import { useConsole } from '../../apps/desktop/src/state/console';
import { emptyRuntime } from '../../packages/domain/src/runtime-feed';
import { event, page } from './runtime-fixtures';
import * as api from '../../apps/desktop/src/features/biometrics/verify';
vi.mock('../../apps/desktop/src/features/biometrics/verify', () => ({
  beginBiometricSession: vi.fn(),
  readBiometricSession: vi.fn(),
  readBiometricPreview: vi.fn(),
  cancelBiometricSession: vi.fn(),
  recoverBiometricEnrollment: vi.fn(),
}));
const technician = {
  technician_id: 'T1',
  username: 'tech',
  display_name: 'Technician',
  role: 'Technician',
  enabled: true,
  enrolled: true,
};
const success: LiveBiometricSession = {
  schema_version: '2.0',
  session_id: '86b5ab92-7eb7-4a34-9e7c-72ea008a6f67',
  purpose: 'LOGIN',
  state: 'SUCCEEDED',
  policy: 'alice.live-face.v3',
  prompt: '',
  reason: '',
  coverage: {},
  accepted_samples: 3,
  preview: null,
  technician,
  verification: null,
  controls: Object.fromEntries(
    ['identity', 'quality', 'capture_integrity', 'pose', 'pad'].map((key) => [
      key,
      { result: 'PASS', model: 'fixture', reason: 'OBSERVED', score: null },
    ]),
  ),
};
beforeEach(() => {
  vi.useFakeTimers();
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
  };
  useConsole.setState({ biometricMode: 'arcface', technician: undefined });
  vi.mocked(api.beginBiometricSession).mockResolvedValue(success);
  vi.mocked(api.cancelBiometricSession).mockResolvedValue();
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.useRealTimers();
});
async function signIn(onClose: () => void) {
  render(<IdentityPanel onClose={onClose} />);
  // A normalized native username must not restart the retained success presentation.
  fireEvent.change(screen.getByLabelText('Technician username'), { target: { value: 'TECH' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue to facial login' }));
  await act(async () => vi.advanceTimersByTimeAsync(0));
}
it('applies native login immediately then fades out after acknowledgement without restarting capture', async () => {
  const close = vi.fn();
  await signIn(close);
  expect(useConsole.getState().technician).toEqual(technician);
  expect(screen.getByRole('status')).toHaveTextContent('Identity verified');
  expect(close).not.toHaveBeenCalled();
  await act(async () => vi.advanceTimersByTimeAsync(450));
  expect(screen.getByRole('dialog')).toHaveClass('biometric-dialog-exit');
  expect(close).not.toHaveBeenCalled();
  await act(async () => vi.advanceTimersByTimeAsync(120));
  expect(close).toHaveBeenCalledTimes(1);
  expect(api.beginBiometricSession).toHaveBeenCalledTimes(1);
});
it.each([200, 480])(
  'logout at %dms invalidates presentation timers and cannot restore the signed-out identity',
  async (elapsed) => {
    const close = vi.fn();
    await signIn(close);
    await act(async () => vi.advanceTimersByTimeAsync(elapsed));
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Cancel' })));
    fireEvent.click(screen.getByRole('button', { name: 'Sign out of console' }));
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(useConsole.getState().technician).toBeUndefined();
    expect(close).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Continue to facial login' })).toBeInTheDocument();
    expect(api.beginBiometricSession).toHaveBeenCalledTimes(1);
  },
);

// Main's live Pi feed is a separate read-only authority boundary. Login must
// preserve its state, and failed biometric attempts must not unlock it.
it.each(['SUCCEEDED', 'FAILED', 'CANCELLED'] as const)(
  'preserves the latest remote feed and read-only action boundary after %s login',
  async (state) => {
    useConsole.setState({
      mode: 'remote',
      runtime: emptyRuntime(),
      selectedRuntimeId: '',
      decisions: {},
    });
    useConsole
      .getState()
      .ingest({ ...page([event(), event(2, 'DECISION')]), event_type: 'alice.runtime_feed' });
    const before = useConsole.getState().runtime;
    vi.mocked(api.beginBiometricSession).mockResolvedValue({
      ...success,
      state,
      technician: state === 'SUCCEEDED' ? technician : null,
      reason: state === 'SUCCEEDED' ? '' : 'OPERATOR_OR_NATIVE_REJECTED',
    });
    await signIn(vi.fn());
    expect(useConsole.getState().technician).toEqual(
      state === 'SUCCEEDED' ? technician : undefined,
    );
    expect(useConsole.getState().runtime).toEqual(before);
    expect(useConsole.getState().decisions).toEqual({});
    await expect(useConsole.getState().act('APPROVE_ONCE')).rejects.toThrow(
      'Remote technician actions are unavailable',
    );
    expect(useConsole.getState().runtime).toEqual(before);
  },
);

it('shows only session actions while already signed in, and Change user clears the old identity first', async () => {
  useConsole.setState({ technician });
  render(<IdentityPanel onClose={vi.fn()} />);
  expect(screen.queryByLabelText('Technician username')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Continue to facial login' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Sign out of console' })).toBeEnabled();
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Change user' })));
  expect(useConsole.getState().technician).toBeUndefined();
  expect(screen.getByLabelText('Technician username')).toHaveValue('');
  expect(api.beginBiometricSession).not.toHaveBeenCalled();
});
