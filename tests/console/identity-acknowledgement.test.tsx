import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { LiveBiometricSession } from '@alice/contracts';
import { IdentityPanel } from '../../apps/desktop/src/components/technicians/IdentityPanel';
import { useConsole } from '../../apps/desktop/src/state/console';
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
  expect(screen.getByRole('status')).toHaveTextContent('Face ID verified');
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
    fireEvent.click(screen.getByRole('button', { name: 'Sign out of console' }));
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(useConsole.getState().technician).toBeUndefined();
    expect(close).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Continue to facial login' })).toBeInTheDocument();
    expect(api.beginBiometricSession).toHaveBeenCalledTimes(1);
  },
);
