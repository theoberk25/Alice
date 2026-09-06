import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AdminPanel } from '../../apps/desktop/src/components/technicians/AdminPanel';
import { nativeCall } from '../../apps/desktop/src/lib/native';

vi.mock('../../apps/desktop/src/lib/native', () => ({ isNative: true, nativeCall: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it('lets an administrator retry a lost removal acknowledgment before first enrollment exists', async () => {
  let removals = 0;
  vi.mocked(nativeCall).mockImplementation(async (command) => {
    if (command === 'list_technicians')
      return [
        {
          technician_id: 'T1',
          username: 'tech',
          display_name: 'Technician',
          role: 'Technician',
          enabled: true,
          enrolled: false,
        },
      ];
    if (command === 'remove_enrollment' && ++removals === 1)
      throw new Error('ENROLLMENT_REMOVAL_RECOVERY_REQUIRED');
    return undefined;
  });
  render(<AdminPanel />);
  expect(screen.queryByRole('button', { name: 'Discard pending enrollment' })).toBeNull();
  fireEvent.change(screen.getByLabelText('Admin username'), { target: { value: 'admin' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Authenticate administrator' }));
  const discard = await screen.findByRole('button', { name: 'Discard pending enrollment' });
  fireEvent.click(discard);
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'ENROLLMENT_REMOVAL_RECOVERY_REQUIRED',
  );
  await waitFor(() => expect(discard).toBeEnabled());
  fireEvent.click(discard);
  await waitFor(() => expect(removals).toBe(2));
  await waitFor(() => expect(screen.getByRole('alert')).toBeEmptyDOMElement());
  expect(nativeCall).toHaveBeenCalledWith('remove_enrollment', { technicianId: 'T1' });
  expect(screen.getByText('NO FACE')).toBeInTheDocument();
});

it('edits identity metadata without opening another enrollment and locks the identity ID', async () => {
  const technician = {
    technician_id: 'T1',
    username: 'tech',
    display_name: 'Technician',
    role: 'Technician',
    enabled: true,
    enrolled: true,
  };
  vi.mocked(nativeCall).mockImplementation(async (command) => {
    if (command === 'list_technicians') return [technician];
    if (command === 'save_technician') return technician;
    return undefined;
  });
  render(<AdminPanel />);
  fireEvent.change(screen.getByLabelText('Admin username'), { target: { value: 'admin' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Authenticate administrator' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
  expect(screen.getByLabelText('technician id')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('display name'), { target: { value: 'Updated name' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save identity' }));
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'Add technician' })).toBeInTheDocument(),
  );
  expect(nativeCall).toHaveBeenCalledWith('save_technician', {
    technician: { ...technician, display_name: 'Updated name', enrolled: false },
  });
  expect(
    vi.mocked(nativeCall).mock.calls.some(([command]) => command === 'begin_biometric_session'),
  ).toBe(false);
});

it('serializes administration mutations and does not enroll disabled identities', async () => {
  let finish!: () => void;
  const technician = {
    technician_id: 'T1',
    username: 'tech',
    display_name: 'Technician',
    role: 'Technician',
    enabled: false,
    enrolled: false,
  };
  vi.mocked(nativeCall).mockImplementation(async (command) => {
    if (command === 'list_technicians') return [technician];
    if (command === 'set_technician_enabled')
      return new Promise<void>((resolve) => {
        finish = resolve;
      });
    return undefined;
  });
  render(<AdminPanel />);
  fireEvent.change(screen.getByLabelText('Admin username'), { target: { value: 'admin' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Authenticate administrator' }));
  const enable = await screen.findByRole('button', { name: 'Enable' });
  expect(screen.getByRole('button', { name: 'Begin enrollment' })).toBeDisabled();
  fireEvent.click(enable);
  fireEvent.click(enable);
  expect(screen.getByRole('button', { name: 'Edit' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Lock administration' })).toBeDisabled();
  expect(
    vi.mocked(nativeCall).mock.calls.filter(([command]) => command === 'set_technician_enabled'),
  ).toHaveLength(1);
  finish();
  await waitFor(() => expect(enable).toBeEnabled());
});
