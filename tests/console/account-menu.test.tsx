import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Header } from '../../apps/desktop/src/components/layout/Header';
import { useConsole } from '../../apps/desktop/src/state/console';
import { nativeCall } from '../../apps/desktop/src/lib/native';
vi.mock('../../apps/desktop/src/lib/native', () => ({ isNative: true, nativeCall: vi.fn() }));
const technician = {
  technician_id: 'T1',
  username: 'tech',
  display_name: 'Test user',
  role: 'Technician',
  enabled: true,
  enrolled: true,
};
beforeEach(() => {
  useConsole.setState({ technician, biometricMode: 'arcface', errors: [] });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  useConsole.setState({ technician: undefined });
});

it('Change user waits for native sign-out and never opens a second login while authenticated', async () => {
  let finish!: () => void;
  vi.mocked(nativeCall).mockImplementation(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  const identity = vi.fn();
  render(<Header onIdentity={identity} onSettings={vi.fn()} />);
  fireEvent.click(screen.getByLabelText('Account: Test user'));
  expect(screen.queryByRole('button', { name: /Sign in/ })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Change user' }));
  expect(identity).not.toHaveBeenCalled();
  expect(useConsole.getState().technician).toEqual(technician);
  expect(screen.getByRole('button', { name: 'Change user' })).toBeDisabled();
  await act(async () => finish());
  expect(nativeCall).toHaveBeenCalledExactlyOnceWith('logout');
  expect(useConsole.getState().technician).toBeUndefined();
  expect(identity).toHaveBeenCalledTimes(1);
});

it('Sign out ends the session without opening the identity popup', async () => {
  vi.mocked(nativeCall).mockResolvedValue(undefined);
  const identity = vi.fn();
  render(<Header onIdentity={identity} onSettings={vi.fn()} />);
  fireEvent.click(screen.getByLabelText('Account: Test user'));
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Sign out' })));
  expect(useConsole.getState().technician).toBeUndefined();
  expect(identity).not.toHaveBeenCalled();
});

it('a failed sign-out retains the current user and does not open login', async () => {
  vi.mocked(nativeCall).mockRejectedValue(new Error('TEST_LOGOUT_FAILURE'));
  const identity = vi.fn();
  render(<Header onIdentity={identity} onSettings={vi.fn()} />);
  fireEvent.click(screen.getByLabelText('Account: Test user'));
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Change user' })));
  expect(useConsole.getState().technician).toEqual(technician);
  expect(identity).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Change user' })).toBeEnabled();
});
