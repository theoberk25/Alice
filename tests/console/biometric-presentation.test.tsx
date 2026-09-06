import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { LiveBiometricSession } from '@alice/contracts';
import { BiometricScan } from '../../apps/desktop/src/components/biometrics/BiometricScan';
import { FaceIdScan } from '../../apps/desktop/src/components/biometrics/FaceIdScan';
import { CameraCapture } from '../../apps/desktop/src/components/biometrics/CameraCapture';
import * as biometricApi from '../../apps/desktop/src/features/biometrics/verify';

vi.mock('../../apps/desktop/src/features/biometrics/verify', () => ({
  beginBiometricSession: vi.fn(),
  readBiometricSession: vi.fn(),
  readBiometricPreview: vi.fn(),
  cancelBiometricSession: vi.fn(),
  recoverBiometricEnrollment: vi.fn(),
}));

const animation = vi.hoisted(() => ({
  reduced: false,
  animate: vi.fn(() => ({ stop: vi.fn() })),
}));
const illustration = vi.hoisted(() => ({
  animate: vi.fn(() => ({ cancel: vi.fn(), revert: vi.fn() })),
  stagger: vi.fn(() => 0),
  morphTo: vi.fn(() => ['source-path', 'target-path']),
}));
vi.mock('animejs', () => ({
  animate: illustration.animate,
  stagger: illustration.stagger,
  svg: { morphTo: illustration.morphTo },
}));
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: () => animation.reduced,
  animate: animation.animate,
}));
beforeEach(() => {
  animation.reduced = false;
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.useRealTimers();
});

it('never advances enrollment geometry or shows verification because time has elapsed', async () => {
  vi.useFakeTimers();
  const { container } = render(
    <BiometricScan
      enrollment
      coverage={{ CENTER: 2, LEFT: 1 }}
      centerReady
      complete={false}
      failed={false}
    />,
  );
  const left = container.querySelector('[data-region="LEFT"] .biometric-arc-progress');
  const right = container.querySelector('[data-region="RIGHT"] .biometric-arc-progress');
  expect(left).toHaveAttribute('stroke-dasharray', '50 100');
  expect(right).toHaveAttribute('stroke-dasharray', '0 100');
  await act(async () => vi.advanceTimersByTimeAsync(30000));
  expect(left).toHaveAttribute('stroke-dasharray', '50 100');
  expect(right).toHaveAttribute('stroke-dasharray', '0 100');
  expect(container.querySelector('.biometric-success-mark')).toBeNull();
});

it('retains the same guide and accepted coverage through failure, then resolves only confirmed success', () => {
  const props = { enrollment: true, coverage: { CENTER: 2, LEFT: 2 } as const, centerReady: true };
  const { container, rerender } = render(
    <BiometricScan {...props} complete={false} failed={false} />,
  );
  const guide = container.querySelector('svg');
  rerender(<BiometricScan {...props} complete={false} failed />);
  expect(container.querySelector('svg')).toBe(guide);
  expect(container.querySelector('[data-region="LEFT"]')).toHaveAttribute('data-accepted', '2');
  expect(container.querySelector('.biometric-success-mark')).toBeNull();
  rerender(<BiometricScan {...props} complete failed={false} />);
  expect(container.querySelector('svg')).toBe(guide);
  expect(container.querySelector('.biometric-success-mark')).toBeInTheDocument();
});

it('shows confirmed results without scheduling SVG animation when reduced motion is requested', () => {
  animation.reduced = true;
  const { container, rerender } = render(
    <BiometricScan enrollment coverage={{ LEFT: 2 }} centerReady complete={false} failed={false} />,
  );
  expect(container.querySelector('[data-region="LEFT"] .biometric-arc-progress')).toHaveAttribute(
    'stroke-dasharray',
    '100 100',
  );
  rerender(<BiometricScan enrollment={false} centerReady complete failed={false} />);
  expect(container.querySelector('.biometric-success-mark path')).toHaveAttribute(
    'stroke-dashoffset',
    '0',
  );
  expect(animation.animate).not.toHaveBeenCalled();
});

it('acknowledges only changed accepted sections, without repeating on status polls', () => {
  const props = { enrollment: true, centerReady: true, complete: false, failed: false };
  const { container, rerender } = render(<BiometricScan {...props} coverage={{ LEFT: 0 }} />);
  expect(animation.animate).not.toHaveBeenCalled();
  rerender(<BiometricScan {...props} coverage={{ LEFT: 1 }} />);
  expect(animation.animate).toHaveBeenCalledTimes(1);
  const [path, frames, transition] = animation.animate.mock.calls[0] as unknown as [
    Element,
    unknown,
    unknown,
  ];
  expect(path).toBe(container.querySelector('[data-region="LEFT"] .biometric-arc-progress'));
  expect(frames).toEqual({ strokeDasharray: ['0 100', '50 100'], strokeOpacity: [0.55, 1] });
  expect(transition).toEqual({ duration: 0.22, ease: 'easeOut' });
  rerender(<BiometricScan {...props} coverage={{ LEFT: 1 }} />);
  expect(animation.animate).toHaveBeenCalledTimes(1);
  rerender(<BiometricScan {...props} coverage={{ LEFT: 2 }} />);
  expect(animation.animate).toHaveBeenCalledTimes(2);
  expect(container.querySelector('[data-region="LEFT"] .biometric-arc-progress')).toHaveAttribute(
    'stroke-dasharray',
    '100 100',
  );
});

it('stops finite stroke acknowledgments immediately on failure', () => {
  const props = {
    enrollment: true,
    centerReady: true,
    complete: false,
    coverage: { LEFT: 1 } as const,
  };
  const { container, rerender } = render(<BiometricScan {...props} failed={false} />);
  const path = container.querySelector<SVGPathElement>(
    '[data-region="LEFT"] .biometric-arc-progress',
  )!;
  path.style.strokeDasharray = '12 100';
  path.style.strokeOpacity = '0.7';
  const motion = animation.animate.mock.results[0]!.value;
  rerender(<BiometricScan {...props} failed />);
  expect(motion.stop).toHaveBeenCalledTimes(1);
  expect(path.style.strokeDasharray).toBe('');
  expect(path.style.strokeOpacity).toBe('');
  expect(path).toHaveAttribute('stroke-dasharray', '50 100');
  expect(container.querySelector('.biometric-success-mark')).toBeNull();
});

it('maps Face ID enrollment evidence exactly and highlights only the supplied pose', async () => {
  vi.useFakeTimers();
  const props = {
    enrollment: true,
    coverage: { CENTER: 2, LEFT: 1, RIGHT: 0 },
    complete: false,
    failed: false,
    evaluating: false,
    faceDetected: true,
    activeRegion: 'LEFT',
  };
  const { container, rerender } = render(<FaceIdScan {...props} />);
  const guide = container.querySelector('.face-id-scan');
  const left = container.querySelector('[data-region="LEFT"]');
  const progress = container.querySelector('.face-id-scan-progress');
  expect(guide).toHaveAttribute('data-evidence-progress', '3');
  expect(left).toHaveAttribute('data-accepted', '1');
  expect(left).toHaveAttribute('data-completed', 'false');
  expect(left).toHaveAttribute('data-active', 'true');
  expect(left?.querySelector('.face-id-pose-progress')).toHaveAttribute(
    'stroke-dasharray',
    '50 100',
  );
  expect(container.querySelectorAll('[data-active="true"]')).toHaveLength(1);
  expect(container.querySelector('[data-region="CENTER"]')).toHaveAttribute(
    'data-completed',
    'true',
  );
  expect(container.querySelector('[data-region="RIGHT"] .face-id-pose-progress')).toHaveAttribute(
    'stroke-dasharray',
    '0 100',
  );
  expect(Number(progress?.getAttribute('stroke-dasharray')?.split(' ')[0])).toBeCloseTo(
    (3 / 14) * 100,
  );
  const evidence = progress?.getAttribute('stroke-dasharray');
  await act(async () => vi.advanceTimersByTimeAsync(30000));
  expect(progress).toHaveAttribute('stroke-dasharray', evidence!);
  expect(guide).toHaveAttribute('data-complete', 'false');
  rerender(<FaceIdScan {...props} coverage={{ ...props.coverage, LEFT: 2 }} activeRegion="UP" />);
  expect(container.querySelector('.face-id-scan')).toBe(guide);
  expect(left).toHaveAttribute('data-completed', 'true');
  expect(left).toHaveAttribute('data-active', 'false');
  expect(container.querySelector('[data-region="UP"]')).toHaveAttribute('data-active', 'true');
  expect(guide).toHaveAttribute('data-complete', 'false');
});

it('keeps login acquisition and evaluation distinct from a confirmed result', () => {
  const props = { enrollment: false, complete: false, failed: false };
  const { container, rerender } = render(
    <FaceIdScan {...props} evaluating={false} faceDetected={false} />,
  );
  const guide = container.querySelector('.face-id-scan');
  const progress = container.querySelector('.face-id-scan-progress');
  const pendingPath = progress?.getAttribute('d');
  expect(guide).toHaveAttribute('data-complete', 'false');
  expect(container.querySelector('.face-id-scan-highlight')).toBeNull();
  rerender(<FaceIdScan {...props} evaluating={false} faceDetected />);
  expect(guide).toHaveAttribute('data-face-detected', 'true');
  expect(guide).toHaveAttribute('data-complete', 'false');
  expect(progress).toHaveAttribute('d', pendingPath!);
  rerender(<FaceIdScan {...props} evaluating faceDetected />);
  expect(guide).toHaveAttribute('data-evaluating', 'true');
  expect(guide).toHaveAttribute('data-complete', 'false');
  expect(container.querySelector('.face-id-scan-highlight')).toBeInTheDocument();
  expect(progress).toHaveAttribute('d', pendingPath!);
  expect(illustration.morphTo).not.toHaveBeenCalled();
  expect(container.querySelector('[data-region]')).toBeNull();
  expect(guide).toHaveAttribute('aria-hidden', 'true');
  expect(container.querySelector('.face-id-landmarks')).toHaveAttribute('data-decorative', 'true');
});

it.each([false, true])(
  'stops Face ID active decoration on failure and preserves coverage (enrollment=%s)',
  (enrollment) => {
    const props = {
      enrollment,
      coverage: { CENTER: 2, LEFT: 1 },
      complete: false,
      failed: false,
      evaluating: true,
      faceDetected: true,
      activeRegion: 'LEFT',
    };
    const { container, rerender, unmount } = render(<FaceIdScan {...props} />);
    const guide = container.querySelector('.face-id-scan');
    const running = illustration.animate.mock.results.map((result) => result.value);
    expect(running.length).toBeGreaterThan(0);
    rerender(<FaceIdScan {...props} failed />);
    for (const action of running) expect(action.cancel).toHaveBeenCalledTimes(1);
    expect(container.querySelector('.face-id-scan')).toBe(guide);
    expect(guide).toHaveAttribute('data-complete', 'false');
    expect(guide).toHaveAttribute('data-failed', 'true');
    expect(guide).toHaveAttribute('data-evaluating', 'false');
    expect(container.querySelector('.face-id-scan-highlight')).toBeNull();
    expect(container.querySelector('[data-active="true"]')).toBeNull();
    if (enrollment)
      expect(container.querySelector('[data-region="LEFT"]')).toHaveAttribute('data-accepted', '1');
    const terminalAnimation = illustration.animate.mock.results.at(-1)!.value;
    unmount();
    expect(terminalAnimation.cancel).toHaveBeenCalledTimes(1);
  },
);

it('does not replay Face ID illustration animations on unchanged native status polls', () => {
  const props = {
    enrollment: true,
    complete: false,
    failed: false,
    evaluating: false,
    faceDetected: true,
  };
  const { rerender } = render(<FaceIdScan {...props} coverage={{ CENTER: 2, LEFT: 1 }} />);
  const calls = illustration.animate.mock.calls.length;
  rerender(<FaceIdScan {...props} coverage={{ CENTER: 2, LEFT: 1 }} />);
  expect(illustration.animate).toHaveBeenCalledTimes(calls);
});

it.each([false, true])(
  'shows a static confirmed Face ID result under reduced motion (enrollment=%s)',
  (enrollment) => {
    animation.reduced = true;
    const props = {
      enrollment,
      coverage: { CENTER: 2, LEFT: 2 },
      failed: false,
      evaluating: true,
      faceDetected: true,
    };
    const { container, rerender } = render(<FaceIdScan {...props} complete={false} />);
    const guide = container.querySelector('.face-id-scan');
    const pendingPath = container.querySelector('.face-id-scan-progress')?.getAttribute('d');
    expect(guide).toHaveAttribute('data-complete', 'false');
    rerender(<FaceIdScan {...props} complete />);
    expect(container.querySelector('.face-id-scan')).toBe(guide);
    expect(guide).toHaveAttribute('data-complete', 'true');
    expect(guide).toHaveAttribute('data-evaluating', 'false');
    expect(container.querySelector('.face-id-scan-highlight')).toBeNull();
    expect(container.querySelector('.face-id-scan-progress')).not.toHaveAttribute(
      'd',
      pendingPath!,
    );
    expect(container.querySelector('.face-id-landmarks')).toHaveStyle({ opacity: 0 });
    expect(illustration.animate).not.toHaveBeenCalled();
    expect(illustration.morphTo).not.toHaveBeenCalled();
  },
);

it('schedules Face ID illustration work without authentication or animation lifecycle callbacks', () => {
  const props = { enrollment: false, failed: false, evaluating: false, faceDetected: true };
  const { rerender } = render(<FaceIdScan {...props} complete={false} />);
  rerender(<FaceIdScan {...props} complete />);
  for (const call of illustration.animate.mock.calls) {
    const options = (call as unknown as [unknown, Record<string, unknown>])[1];
    expect(Object.keys(options).filter((key) => /^on[A-Z]/.test(key))).toEqual([]);
  }
  expect(biometricApi.beginBiometricSession).not.toHaveBeenCalled();
  expect(biometricApi.readBiometricSession).not.toHaveBeenCalled();
  expect(biometricApi.cancelBiometricSession).not.toHaveBeenCalled();
});

it.each(['LOGIN', 'ENROLLMENT'] as const)(
  'keeps %s completion under native authority even after full coverage and elapsed presentation time',
  async (purpose) => {
    vi.useFakeTimers();
    const coverage = { CENTER: 2, LEFT: 2, RIGHT: 2, UP: 2, DOWN: 2, UP_LEFT: 2, UP_RIGHT: 2 };
    const nativeSession: LiveBiometricSession = {
      schema_version: '2.0',
      session_id: '86b5ab92-7eb7-4a34-9e7c-72ea008a6f67',
      purpose,
      state: 'CAPTURING',
      policy: 'alice.live-face.v3',
      prompt: 'CENTER',
      reason: '',
      coverage,
      accepted_samples: 14,
      controls: {},
      preview: null,
      technician: null,
      verification: null,
    };
    vi.mocked(biometricApi.beginBiometricSession).mockResolvedValue(nativeSession);
    vi.mocked(biometricApi.readBiometricSession).mockResolvedValue({
      ...nativeSession,
      state: 'EVALUATING',
    });
    vi.mocked(biometricApi.readBiometricPreview).mockResolvedValue(null);
    vi.mocked(biometricApi.cancelBiometricSession).mockResolvedValue();
    const complete = vi.fn(async () => {});
    const { container } = render(
      <CameraCapture
        intent={
          purpose === 'LOGIN'
            ? { purpose, username: 'synthetic-user' }
            : { purpose, technician_id: 'TECH-SYNTHETIC' }
        }
        onComplete={complete}
        onCancel={vi.fn()}
      />,
    );
    await act(async () => vi.advanceTimersByTimeAsync(30000));
    expect(complete).not.toHaveBeenCalled();
    expect(biometricApi.beginBiometricSession).toHaveBeenCalledTimes(1);
    expect(biometricApi.cancelBiometricSession).not.toHaveBeenCalled();
    expect(container.querySelector('[data-complete="true"]')).toBeNull();
    vi.mocked(biometricApi.readBiometricSession).mockResolvedValue({
      ...nativeSession,
      state: 'SUCCEEDED',
    });
    await act(async () => vi.advanceTimersByTimeAsync(200));
    expect(complete).toHaveBeenCalledTimes(1);
    expect(complete).toHaveBeenCalledWith({ ...nativeSession, state: 'SUCCEEDED' });
    expect(container.querySelector('[data-complete="true"]')).toBeInTheDocument();
    expect(biometricApi.beginBiometricSession).toHaveBeenCalledTimes(1);
  },
);
