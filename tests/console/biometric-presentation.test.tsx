import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { BiometricScan } from '../../apps/desktop/src/components/biometrics/BiometricScan';

const animation = vi.hoisted(() => ({
  reduced: false,
  animate: vi.fn(() => ({ revert: vi.fn() })),
  timeline: { add: vi.fn().mockReturnThis(), revert: vi.fn() },
  createTimeline: vi.fn(),
}));
vi.mock('animejs', () => ({
  animate: animation.animate,
  createTimeline: animation.createTimeline,
}));
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: () => animation.reduced,
}));
beforeEach(() => {
  animation.reduced = false;
  animation.createTimeline.mockReturnValue(animation.timeline);
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
  expect(animation.createTimeline).not.toHaveBeenCalled();
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
  expect(animation.createTimeline).toHaveBeenCalledTimes(1);
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
  expect(animation.createTimeline).not.toHaveBeenCalled();
});
