import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import {
  type BiometricIntent,
  LiveBiometricPreviewSchema,
  LiveBiometricSessionSchema,
  type LiveBiometricSession,
} from '@alice/contracts';
import { CameraCapture } from '../../apps/desktop/src/components/biometrics/CameraCapture';
import * as api from '../../apps/desktop/src/features/biometrics/verify';
vi.mock('../../apps/desktop/src/features/biometrics/verify', () => ({
  beginBiometricSession: vi.fn(),
  readBiometricSession: vi.fn(),
  readBiometricPreview: vi.fn(),
  cancelBiometricSession: vi.fn(),
  recoverBiometricEnrollment: vi.fn(),
}));
vi.mock('motion/react', async () => {
  const actual = await vi.importActual<typeof import('motion/react')>('motion/react');
  return { ...actual, useReducedMotion: () => true };
});
const id = '86b5ab92-7eb7-4a34-9e7c-72ea008a6f67';
function session(overrides: Partial<LiveBiometricSession> = {}): LiveBiometricSession {
  return {
    schema_version: '2.0',
    session_id: id,
    purpose: 'ENROLLMENT',
    state: 'CAPTURING',
    policy: 'alice.live-face.v3',
    prompt: 'CENTER',
    reason: '',
    coverage: {},
    accepted_samples: 0,
    controls: {},
    preview: null,
    technician: null,
    verification: null,
    ...overrides,
  };
}
beforeEach(() => {
  vi.mocked(api.beginBiometricSession).mockResolvedValue(session());
  vi.mocked(api.readBiometricSession).mockResolvedValue(session());
  vi.mocked(api.readBiometricPreview).mockResolvedValue(null);
  vi.mocked(api.cancelBiometricSession).mockResolvedValue();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  vi.useRealTimers();
});

it('starts with intent only and has no shutter or renderer frame input', async () => {
  const done = vi.fn();
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={done}
      onCancel={vi.fn()}
    />,
  );
  await waitFor(() =>
    expect(api.beginBiometricSession).toHaveBeenCalledWith({
      purpose: 'ENROLLMENT',
      technician_id: 'T1',
    }),
  );
  expect(screen.queryByRole('button', { name: /capture|photo|shutter/i })).not.toBeInTheDocument();
  expect(screen.getByText('0 / 7 angles complete · 0 accepted observations')).toBeInTheDocument();
  expect(document.querySelector('.biometric-scan')).toBeNull(); // reduced motion
  expect(done).not.toHaveBeenCalled();
});

it('coverage changes only from accepted native observations', async () => {
  vi.mocked(api.readBiometricSession).mockResolvedValue(
    session({ coverage: { CENTER: 2 }, accepted_samples: 2 }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  expect(
    await screen.findByText('1 / 7 angles complete · 2 accepted observations'),
  ).toBeInTheDocument();
});

it('navigation cancels the owned native session', async () => {
  const { unmount } = render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await waitFor(() => expect(api.beginBiometricSession).toHaveBeenCalled());
  await act(async () => {});
  unmount();
  expect(api.cancelBiometricSession).toHaveBeenCalledWith(id);
});

it('late creation after navigation is cancelled and never completes the UI', async () => {
  let resolve!: (s: LiveBiometricSession) => void;
  vi.mocked(api.beginBiometricSession).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const done = vi.fn();
  const { unmount } = render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={done}
      onCancel={vi.fn()}
    />,
  );
  await waitFor(() => expect(api.beginBiometricSession).toHaveBeenCalled());
  unmount();
  await act(async () => resolve(session({ state: 'SUCCEEDED' })));
  expect(api.cancelBiometricSession).toHaveBeenCalledWith(id);
  expect(done).not.toHaveBeenCalled();
});

it('a wrong-session result cancels the current session without UI success', async () => {
  vi.mocked(api.readBiometricSession).mockResolvedValue(
    session({ session_id: 'old', state: 'SUCCEEDED' }),
  );
  const done = vi.fn();
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={done}
      onCancel={vi.fn()}
    />,
  );
  expect(await screen.findByText(/Biometric session changed/)).toBeInTheDocument();
  expect(api.cancelBiometricSession).toHaveBeenCalledWith(id);
  expect(done).not.toHaveBeenCalled();
});

it('retry starts a new operation and missing required PAD model remains visible', async () => {
  vi.mocked(api.beginBiometricSession).mockResolvedValue(
    session({
      state: 'FAILED',
      reason: 'REQUIRED_MODELS_UNAVAILABLE',
      controls: {
        pad: {
          result: 'NOT_CONFIGURED',
          model: 'PAD_UNAVAILABLE',
          reason: 'unavailable',
          score: null,
        },
      },
    }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  expect(await screen.findByText('NOT CONFIGURED')).toBeInTheDocument();
  expect(document.querySelector('.biometric-success-mark')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Retry with new session' }));
  await waitFor(() => expect(api.beginBiometricSession).toHaveBeenCalledTimes(2));
});

it('contract rejects missing required controls, unknown fields and nonfinite results', () => {
  expect(LiveBiometricSessionSchema.safeParse(session({ state: 'SUCCEEDED' })).success).toBe(false);
  expect(LiveBiometricSessionSchema.safeParse({ ...session(), frames: ['injected'] }).success).toBe(
    false,
  );
  expect(
    LiveBiometricSessionSchema.safeParse(
      session({ controls: { pad: { result: 'PASS', model: 'x', reason: 'test', score: NaN } } }),
    ).success,
  ).toBe(false);
});

it('accepts five-control v3 live face evidence and rejects previous policies', () => {
  const controls = Object.fromEntries(
    ['identity', 'quality', 'capture_integrity', 'pose', 'pad'].map((key) => [
      key,
      { result: 'PASS', model: 'fixture', reason: 'TEST_ONLY', score: null },
    ]),
  );
  const result = { ...session({ state: 'SUCCEEDED' }), controls };
  expect(LiveBiometricSessionSchema.safeParse(result).success).toBe(true);
  for (const policy of ['alice.live-face.v1', 'alice.live-face.v2', 'alice.full-protected.v1'])
    expect(LiveBiometricSessionSchema.safeParse({ ...result, policy }).success).toBe(false);
  expect(
    LiveBiometricSessionSchema.safeParse({
      ...result,
      controls: {
        ...controls,
        challenge: { result: 'PASS', model: 'retired', reason: 'TEST_ONLY', score: null },
      },
    }).success,
  ).toBe(false);
  for (const key of Object.keys(controls)) {
    const missing = { ...controls };
    delete missing[key];
    expect(LiveBiometricSessionSchema.safeParse({ ...result, controls: missing }).success).toBe(
      false,
    );
  }
});

it('offers generation recovery only within enrollment and waits for native acknowledgement', async () => {
  vi.mocked(api.beginBiometricSession).mockRejectedValue(
    new Error('ENROLLMENT_ACTIVATION_RECOVERY_REQUIRED'),
  );
  vi.mocked(api.recoverBiometricEnrollment).mockResolvedValue();
  const recovered = vi.fn().mockResolvedValue(undefined);
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
      onRecovered={recovered}
    />,
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Recover pending enrollment' }));
  await waitFor(() => expect(recovered).toHaveBeenCalledTimes(1));
  expect(api.recoverBiometricEnrollment).toHaveBeenCalledWith('T1');
});

it('does not offer activation recovery for a pending removal', async () => {
  vi.mocked(api.beginBiometricSession).mockRejectedValue(
    new Error('ENROLLMENT_REMOVAL_RECOVERY_REQUIRED'),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
      onRecovered={vi.fn()}
    />,
  );
  expect(await screen.findByText(/ENROLLMENT_REMOVAL_RECOVERY_REQUIRED/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Recover pending enrollment' })).toBeNull();
  expect(api.recoverBiometricEnrollment).not.toHaveBeenCalled();
});

it('updates preview independently and ignores old or foreign display frames', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricPreview)
    .mockResolvedValueOnce({ session_id: id, sequence: 2, jpeg: 'dHdv' })
    .mockResolvedValueOnce({ session_id: id, sequence: 1, jpeg: 'b2xk' })
    .mockResolvedValueOnce({ session_id: 'foreign', sequence: 3, jpeg: 'bm8=' })
    .mockResolvedValue({ session_id: id, sequence: 4, jpeg: 'bmV3' });
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  const preview = screen.getByAltText('Mirrored live camera preview');
  expect(preview).toHaveAttribute('src', 'data:image/jpeg;base64,dHdv');
  await act(async () => vi.advanceTimersByTimeAsync(66));
  expect(preview).toHaveAttribute('src', 'data:image/jpeg;base64,dHdv');
  await act(async () => vi.advanceTimersByTimeAsync(33));
  expect(preview).toHaveAttribute('src', 'data:image/jpeg;base64,bmV3');
  expect(api.readBiometricSession).not.toHaveBeenCalled();
});

it('allows only one preview read in flight and discards a late frame after unmount', async () => {
  vi.useFakeTimers();
  let resolve!: (value: { session_id: string; sequence: number; jpeg: string }) => void;
  vi.mocked(api.readBiometricPreview).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const { unmount } = render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  const preview = screen.getByAltText('Mirrored live camera preview');
  expect(api.readBiometricPreview).toHaveBeenCalledTimes(1);
  expect(api.readBiometricSession).toHaveBeenCalled();
  unmount();
  await act(async () => resolve({ session_id: id, sequence: 1, jpeg: 'bGF0ZQ==' }));
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(preview).not.toHaveAttribute('src');
  expect(api.readBiometricPreview).toHaveBeenCalledTimes(1);
  expect(api.cancelBiometricSession).toHaveBeenCalledWith(id);
});

it('cancelling blocks an in-flight success callback and repeated cancel clicks', async () => {
  vi.useFakeTimers();
  let resolveStatus!: (value: LiveBiometricSession) => void;
  let resolveCancel!: () => void;
  vi.mocked(api.readBiometricSession).mockReturnValue(
    new Promise((r) => {
      resolveStatus = r;
    }),
  );
  vi.mocked(api.cancelBiometricSession).mockReturnValue(
    new Promise((r) => {
      resolveCancel = r;
    }),
  );
  const done = vi.fn(),
    cancel = vi.fn();
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={done}
      onCancel={cancel}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(200));
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  fireEvent.click(screen.getByRole('button', { name: 'Closing…' }));
  await act(async () => resolveStatus(session({ state: 'SUCCEEDED' })));
  expect(done).not.toHaveBeenCalled();
  expect(api.cancelBiometricSession).toHaveBeenCalledTimes(1);
  expect(cancel).not.toHaveBeenCalled();
  await act(async () => resolveCancel());
  expect(cancel).toHaveBeenCalledTimes(1);
});

it('stops preview and capture when hidden and requires an explicit retry', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricPreview).mockResolvedValue({
    session_id: id,
    sequence: 1,
    jpeg: 'bGl2ZQ==',
  });
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
  fireEvent(document, new Event('visibilitychange'));
  expect(api.cancelBiometricSession).toHaveBeenCalledWith(id);
  expect(screen.getByAltText('Mirrored live camera preview')).not.toHaveAttribute('src');
  hidden.mockReturnValue(false);
  fireEvent(document, new Event('visibilitychange'));
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(api.readBiometricPreview).toHaveBeenCalledTimes(1);
  expect(api.beginBiometricSession).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Retry with new session' })).toBeEnabled();
  hidden.mockRestore();
});

it('keeps authentication running after a display-only preview failure', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricPreview).mockRejectedValue(new Error('display unavailable'));
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(400));
  expect(api.readBiometricSession).toHaveBeenCalledTimes(2);
  expect(api.cancelBiometricSession).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: 'Retry with new session' })).toBeNull();
});

it('validates the bounded display-only preview contract', () => {
  const frame = { session_id: id, sequence: 1, jpeg: 'aGVsbG8=' };
  expect(LiveBiometricPreviewSchema.safeParse(frame).success).toBe(true);
  expect(LiveBiometricPreviewSchema.safeParse({ ...frame, sequence: 3000 }).success).toBe(true);
  for (const invalid of [
    { ...frame, sequence: 0 },
    { ...frame, sequence: 3001 },
    { ...frame, sequence: 1.5 },
    { ...frame, jpeg: 'injected URL:' },
    { ...frame, jpeg: 'A'.repeat(700001) },
    { ...frame, accepted_samples: 14 },
  ])
    expect(LiveBiometricPreviewSchema.safeParse(invalid).success).toBe(false);
});

it('waits for completion processing and offers a fresh session if native submission fails', async () => {
  vi.useFakeTimers();
  let reject!: (reason: Error) => void;
  const done = vi.fn().mockReturnValue(
    new Promise<void>((_resolve, fail) => {
      reject = fail;
    }),
  );
  vi.mocked(api.readBiometricSession).mockResolvedValue(session({ state: 'SUCCEEDED' }));
  render(
    <CameraCapture
      intent={{ purpose: 'APPROVAL', technician_id: 'T1', decision_id: 'D1', request_id: 'R1' }}
      onComplete={done}
      onCancel={vi.fn()}
    />,
  );
  // Native success at 200ms submits immediately; only visual dismissal may be delayed.
  await act(async () => vi.advanceTimersByTimeAsync(200));
  expect(screen.getByRole('button', { name: 'Finishing…' })).toBeDisabled();
  await act(async () => reject(new Error('Request submission failed')));
  expect(screen.getByRole('button', { name: 'Retry with new session' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled();
  expect(done).toHaveBeenCalledTimes(1);
});

it('removes an expired native preview without cancelling the active face check', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricPreview)
    .mockResolvedValueOnce({ session_id: id, sequence: 1, jpeg: 'bGl2ZQ==' })
    .mockResolvedValue(null);
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  const preview = screen.getByAltText('Mirrored live camera preview');
  expect(preview).toHaveAttribute('src');
  await act(async () => vi.advanceTimersByTimeAsync(33));
  expect(preview).not.toHaveAttribute('src');
  expect(preview).toHaveAttribute('hidden');
  expect(api.cancelBiometricSession).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: 'Retry with new session' })).toBeNull();
});

it('includes IPC time in the preview cadence while keeping requests sequential', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricPreview).mockImplementation(
    () =>
      new Promise((resolve) => {
        setTimeout(() => resolve(null), 20);
      }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(99));
  // Reads start at 0, 33, 66 and 99ms despite each IPC requiring 20ms.
  expect(api.readBiometricPreview).toHaveBeenCalledTimes(4);
});

it('starts enrollment centered, then supports a continuous scan without ordered turn prompts', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricSession).mockResolvedValue(
    session({
      prompt: 'LOOK_AROUND',
      coverage: { CENTER: 2, LEFT: 2, UP: 1 },
      accepted_samples: 5,
    }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  expect(screen.getByRole('status')).toHaveTextContent('Look straight ahead to begin');
  await act(async () => vi.advanceTimersByTimeAsync(200));
  expect(screen.getByRole('status')).toHaveTextContent('Slowly move your head in a circle');
  expect(screen.getByRole('status')).not.toHaveTextContent(/turn.*left|turn.*right/i);
  expect(screen.getByText('Center captured')).toBeInTheDocument();
  expect(screen.getByRole('progressbar', { name: 'Face enrollment progress' })).toHaveAttribute(
    'aria-valuenow',
    '5',
  );
  expect(document.querySelector('[data-region="LEFT"] .biometric-arc-progress')).toHaveAttribute(
    'stroke-dasharray',
    '100 100',
  );
  expect(document.querySelector('[data-region="UP"] .biometric-arc-progress')).toHaveAttribute(
    'stroke-dasharray',
    '50 100',
  );
  expect(document.querySelector('[data-region="RIGHT"] .biometric-arc-progress')).toHaveAttribute(
    'stroke-dasharray',
    '0 100',
  );
  expect(document.querySelectorAll('.biometric-coverage-arc')).toHaveLength(6);
});

it('pauses enrollment guidance for quality without resetting coverage or requiring a retry', async () => {
  vi.useFakeTimers();
  vi.mocked(api.beginBiometricSession).mockResolvedValue(
    session({
      prompt: 'LOOK_AROUND',
      coverage: { CENTER: 2, RIGHT: 1 },
      accepted_samples: 3,
      controls: {
        quality: {
          result: 'INCONCLUSIVE',
          model: 'fixture',
          reason: 'LOW_QUALITY_BLUR',
          score: null,
        },
      },
    }),
  );
  vi.mocked(api.readBiometricSession).mockResolvedValue(
    session({
      prompt: 'LOOK_AROUND',
      coverage: { CENTER: 2, RIGHT: 2, DOWN: 1 },
      accepted_samples: 5,
    }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  expect(screen.getByRole('status')).toHaveTextContent('Pause briefly for a clear view');
  expect(screen.getByRole('status')).toHaveTextContent('Your progress is kept');
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3');
  expect(screen.queryByRole('button', { name: 'Retry with new session' })).toBeNull();
  await act(async () => vi.advanceTimersByTimeAsync(200));
  expect(screen.getByRole('status')).toHaveTextContent('Slowly move your head in a circle');
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '5');
  expect(api.beginBiometricSession).toHaveBeenCalledTimes(1);
  expect(api.cancelBiometricSession).not.toHaveBeenCalled();
});

it('keeps enrollment coverage unchanged when the service rejects a candidate sample', async () => {
  vi.useFakeTimers();
  vi.mocked(api.beginBiometricSession).mockResolvedValue(
    session({
      prompt: 'LOOK_AROUND',
      coverage: { CENTER: 2, LEFT: 2 },
      accepted_samples: 4,
      controls: {
        quality: {
          result: 'INCONCLUSIVE',
          model: 'fixture',
          reason: 'ENROLLMENT_SAMPLE_NOT_ACCEPTED',
          score: null,
        },
        identity: {
          result: 'FAIL',
          model: 'fixture',
          reason: 'ENROLLMENT_IDENTITY_NOT_MATCHED',
          score: null,
        },
      },
    }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  expect(screen.getByRole('status')).toHaveTextContent('Face the camera for a moment');
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '4');
  expect(document.querySelector('[data-region="RIGHT"]')).toHaveAttribute('data-accepted', '0');
  expect(screen.queryByRole('button', { name: 'Retry with new session' })).toBeNull();
  expect(api.cancelBiometricSession).not.toHaveBeenCalled();
});

it('uses the decoded camera aspect ratio instead of cropping a differently shaped native frame', async () => {
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  const preview = screen.getByAltText('Mirrored live camera preview');
  Object.defineProperty(preview, 'naturalWidth', { configurable: true, value: 1280 });
  Object.defineProperty(preview, 'naturalHeight', { configurable: true, value: 720 });
  fireEvent.load(preview);
  expect(preview.parentElement).toHaveStyle({ aspectRatio: '1280 / 720' });
  Object.defineProperty(preview, 'naturalWidth', { configurable: true, value: 640 });
  Object.defineProperty(preview, 'naturalHeight', { configurable: true, value: 480 });
  fireEvent.load(preview);
  expect(preview.parentElement).toHaveStyle({ aspectRatio: '640 / 480' });
  expect(screen.getByText(/The ring shows scan progress/)).toBeInTheDocument();
});

it('shows camera disconnection prominently with its exact native reason, without opening details', async () => {
  vi.mocked(api.beginBiometricSession).mockResolvedValue(
    session({
      state: 'FAILED',
      reason: 'CAMERA_DISCONNECTED',
      coverage: { CENTER: 2, RIGHT: 2, UP_RIGHT: 1 },
      accepted_samples: 5,
    }),
  );
  render(
    <CameraCapture
      intent={{ purpose: 'ENROLLMENT', technician_id: 'T1' }}
      onComplete={vi.fn()}
      onCancel={vi.fn()}
    />,
  );
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('Camera disconnected');
  expect(alert).toHaveTextContent('The camera stopped delivering images');
  expect(alert).toHaveTextContent('Reason: CAMERA_DISCONNECTED');
  expect(screen.queryByText('Technical details')).toBeNull();
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '5');
  expect(screen.getByRole('button', { name: 'Retry with new session' })).toBeEnabled();
});

it.each([
  ['MULTIPLE_FACES_DETECTED', 'Pause while the camera finds a clear view of your face'],
  ['PAD_INVALID_BOUNDS', 'Move slightly away so your whole face is visible'],
])(
  'keeps login active through an acquisition pause (%s) and resumes native guidance',
  async (reason, guidance) => {
    vi.useFakeTimers();
    vi.mocked(api.beginBiometricSession).mockResolvedValue(
      session({
        purpose: 'LOGIN',
        controls: { quality: { result: 'INCONCLUSIVE', model: 'fixture', reason, score: null } },
      }),
    );
    vi.mocked(api.readBiometricSession).mockResolvedValue(
      session({
        purpose: 'LOGIN',
        prompt: 'LEFT',
        controls: {
          quality: { result: 'PASS', model: 'fixture', reason: 'OBSERVED', score: null },
        },
      }),
    );
    const complete = vi.fn(),
      cancel = vi.fn();
    render(
      <CameraCapture
        intent={{ purpose: 'LOGIN', username: 'tech' }}
        onComplete={complete}
        onCancel={cancel}
      />,
    );
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(screen.getByRole('status')).toHaveTextContent(guidance);
    expect(screen.getByRole('status')).toHaveTextContent('Verification continues automatically');
    expect(screen.queryByRole('button', { name: 'Retry with new session' })).toBeNull();
    expect(complete).not.toHaveBeenCalled();
    expect(cancel).not.toHaveBeenCalled();
    expect(api.cancelBiometricSession).not.toHaveBeenCalled();
    await act(async () => vi.advanceTimersByTimeAsync(200));
    expect(screen.getByRole('status')).toHaveTextContent('Recognizing your face…');
    expect(screen.getByRole('status')).toHaveTextContent('No head turns needed');
    expect(screen.queryByRole('button', { name: 'Retry with new session' })).toBeNull();
    expect(api.beginBiometricSession).toHaveBeenCalledTimes(1);
    expect(complete).not.toHaveBeenCalled();
    expect(cancel).not.toHaveBeenCalled();
    expect(api.cancelBiometricSession).not.toHaveBeenCalled();
  },
);

it.each<BiometricIntent>([
  { purpose: 'LOGIN', username: 'tech' },
  { purpose: 'APPROVAL', technician_id: 'T1', decision_id: 'D1', request_id: 'R1' },
])(
  'recognizes automatically for $purpose and completes only from native success',
  async (intent) => {
    vi.useFakeTimers();
    const controls = Object.fromEntries(
      ['identity', 'quality', 'capture_integrity', 'pose', 'pad'].map((key) => [
        key,
        { result: 'PASS' as const, model: 'fixture', reason: 'OBSERVED', score: null },
      ]),
    );
    const pending = session({
      purpose: intent.purpose,
      prompt: 'LEFT',
      controls,
      accepted_samples: 1,
    });
    const nativeSuccess = session({
      purpose: intent.purpose,
      state: 'SUCCEEDED',
      prompt: 'UP',
      controls,
      accepted_samples: 3,
      technician:
        intent.purpose === 'LOGIN'
          ? {
              technician_id: 'T1',
              username: 'tech',
              display_name: 'Technician',
              role: 'Technician',
              enabled: true,
              enrolled: true,
            }
          : null,
      verification:
        intent.purpose === 'APPROVAL'
          ? {
              technician_id: 'T1',
              decision_id: 'D1',
              request_id: 'R1',
              verification_id: id,
              timestamp: new Date().toISOString(),
              expires_at: new Date(Date.now() + 60000).toISOString(),
              result: 'PASS',
              provider: 'arcface',
            }
          : null,
    });
    expect(LiveBiometricSessionSchema.safeParse(nativeSuccess).success).toBe(true);
    vi.mocked(api.beginBiometricSession).mockResolvedValue(pending);
    vi.mocked(api.readBiometricSession)
      .mockResolvedValueOnce({ ...pending, prompt: 'RIGHT', accepted_samples: 2 })
      .mockResolvedValue(nativeSuccess);
    const complete = vi.fn().mockResolvedValue(undefined);
    render(<CameraCapture intent={intent} onComplete={complete} onCancel={vi.fn()} />);
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(screen.getByRole('status')).toHaveTextContent('Recognizing your face…');
    expect(screen.getByRole('status')).toHaveTextContent('No head turns needed');
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(complete).not.toHaveBeenCalled();
    await act(async () => vi.advanceTimersByTimeAsync(200));
    expect(screen.getByRole('status')).toHaveTextContent('Recognizing your face…');
    expect(screen.getByRole('status')).not.toHaveTextContent(/left|right|upward|downward|circle/i);
    expect(complete).not.toHaveBeenCalled();
    await act(async () => vi.advanceTimersByTimeAsync(200));
    expect(screen.getByRole('status')).toHaveTextContent('Face ID verified');
    expect(complete).toHaveBeenCalledExactlyOnceWith(nativeSuccess);
    expect(api.beginBiometricSession).toHaveBeenCalledExactlyOnceWith(intent);
  },
);

it('acknowledges native success after clearing preview and stops reading camera frames immediately', async () => {
  vi.useFakeTimers();
  vi.mocked(api.readBiometricPreview).mockResolvedValue({
    session_id: id,
    sequence: 1,
    jpeg: 'bGl2ZQ==',
  });
  vi.mocked(api.readBiometricSession).mockResolvedValue(
    session({ purpose: 'LOGIN', state: 'SUCCEEDED' }),
  );
  const complete = vi.fn().mockResolvedValue(undefined);
  const acknowledged = vi.fn();
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={complete}
      onAcknowledged={acknowledged}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(0));
  const preview = screen.getByAltText('Mirrored live camera preview');
  expect(preview).toHaveAttribute('src');
  await act(async () => vi.advanceTimersByTimeAsync(200));
  expect(preview).not.toHaveAttribute('src');
  expect(document.querySelector('.biometric-success-mark')).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('Face ID verified');
  expect(complete).toHaveBeenCalledTimes(1);
  const reads = vi.mocked(api.readBiometricPreview).mock.calls.length;
  await act(async () => vi.advanceTimersByTimeAsync(449));
  expect(acknowledged).not.toHaveBeenCalled();
  expect(api.readBiometricPreview).toHaveBeenCalledTimes(reads);
  await act(async () => vi.advanceTimersByTimeAsync(1));
  expect(acknowledged).toHaveBeenCalledTimes(1);
  expect(complete).toHaveBeenCalledTimes(1);
});

it.each(['cancel', 'hidden', 'unmount'] as const)(
  'invalidates a pending success acknowledgement on %s',
  async (reason) => {
    vi.useFakeTimers();
    vi.mocked(api.beginBiometricSession).mockResolvedValue(
      session({ purpose: 'LOGIN', state: 'SUCCEEDED' }),
    );
    const complete = vi.fn(),
      cancelled = vi.fn(),
      acknowledged = vi.fn();
    const { unmount } = render(
      <CameraCapture
        intent={{ purpose: 'LOGIN', username: 'tech' }}
        onComplete={complete}
        onAcknowledged={acknowledged}
        onCancel={cancelled}
      />,
    );
    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(screen.getByRole('status')).toHaveTextContent('Face ID verified');
    const hidden =
      reason === 'hidden' ? vi.spyOn(document, 'hidden', 'get').mockReturnValue(true) : undefined;
    if (reason === 'cancel') fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    else if (reason === 'hidden') fireEvent(document, new Event('visibilitychange'));
    else unmount();
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(complete).toHaveBeenCalledTimes(1);
    expect(acknowledged).not.toHaveBeenCalled();
    expect(api.cancelBiometricSession).toHaveBeenCalledWith(id);
    if (reason === 'cancel') expect(cancelled).toHaveBeenCalledTimes(1);
    hidden?.mockRestore();
  },
);

it('uses a brief static acknowledgement for reduced motion', async () => {
  vi.useFakeTimers();
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }));
  vi.mocked(api.beginBiometricSession).mockResolvedValue(
    session({ purpose: 'LOGIN', state: 'SUCCEEDED' }),
  );
  const complete = vi.fn().mockResolvedValue(undefined);
  const acknowledged = vi.fn();
  render(
    <CameraCapture
      intent={{ purpose: 'LOGIN', username: 'tech' }}
      onComplete={complete}
      onAcknowledged={acknowledged}
      onCancel={vi.fn()}
    />,
  );
  await act(async () => vi.advanceTimersByTimeAsync(59));
  expect(complete).toHaveBeenCalledTimes(1);
  expect(acknowledged).not.toHaveBeenCalled();
  await act(async () => vi.advanceTimersByTimeAsync(1));
  expect(acknowledged).toHaveBeenCalledTimes(1);
});
