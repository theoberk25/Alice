import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { createElement } from 'react';
import { WebAccessGate } from '../../apps/desktop/src/app/WebAccessGate';
import { useConsole } from '../../apps/desktop/src/state/console';
import { RemoteAliceTransport } from '../../apps/desktop/src/lib/remote-transport';
import { nativeCall, runtimeConfig } from '../../apps/desktop/src/lib/native';
vi.mock('../../apps/desktop/src/lib/native', () => ({
  isNative: true,
  nativeCall: vi.fn().mockResolvedValue({ status: 'UNCONFIGURED', model: '' }),
  runtimeConfig: vi.fn().mockResolvedValue({
    transport_mode: 'remote',
    biometric_mode: 'arcface',
    llm_model: '',
    ollama_url: '',
    biometric_url: '',
    admin_configured: true,
  }),
}));
const technician = {
  technician_id: 'TECH-1',
  username: 'tech',
  display_name: 'Technician',
  role: 'Technician',
  enabled: true,
  enrolled: true,
};
beforeEach(() => {
  useConsole.setState({ technician: undefined, mode: 'remote', ready: false });
  vi.clearAllMocks();
  vi.mocked(runtimeConfig).mockResolvedValue({
    transport_mode: 'remote',
    biometric_mode: 'arcface',
    llm_model: '',
    ollama_url: '',
    biometric_url: '',
    admin_configured: true,
  });
  vi.mocked(nativeCall).mockResolvedValue({ status: 'UNCONFIGURED', model: '' });
});
afterEach(() => {
  cleanup();
  useConsole.getState().setTechnician(undefined);
  vi.restoreAllMocks();
});
it('does not render a web logout action inside native ALICE', () => {
  render(createElement(WebAccessGate, {}, 'Native content'));
  expect(screen.getByText('Native content')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Log out' })).toBeNull();
});
it('does not start native event reads before login, and disconnects on logout', async () => {
  const stop = vi.fn();
  const connect = vi.spyOn(RemoteAliceTransport.prototype, 'connect').mockResolvedValue(stop);
  await useConsole.getState().start();
  expect(connect).not.toHaveBeenCalled();
  expect(nativeCall).not.toHaveBeenCalledWith('read_runtime_events', expect.anything());
  expect(useConsole.getState().ready).toBe(true);
  useConsole.getState().setTechnician(technician);
  await waitFor(() => expect(connect).toHaveBeenCalledTimes(1));
  useConsole.getState().setTechnician(undefined);
  expect(stop).toHaveBeenCalledTimes(1);
  expect(useConsole.getState().runtime.events).toEqual([]);
  expect(useConsole.getState().feed.state).toBe('unavailable');
});
it('expires renderer identity when native polling rejects the current technician', async () => {
  const stop = vi.fn();
  let fail!: (reason: string) => void;
  vi.spyOn(RemoteAliceTransport.prototype, 'connect').mockImplementation(async (_emit, error) => {
    fail = error;
    return stop;
  });
  useConsole.setState({ technician });
  await useConsole.getState().start();
  expect(fail).toBeTypeOf('function');
  fail('Runtime feed unavailable: Technician authentication required');
  expect(useConsole.getState().technician).toBeUndefined();
  expect(useConsole.getState().feed.state).toBe('unavailable');
  expect(stop).toHaveBeenCalledTimes(1);
});
