import { useEffect } from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import {
  AnimatedCounter,
  AnimatedSelection,
  BorderTrail,
  CommandButton,
  Modal,
  Tooltip,
  TransitionPanel,
} from '@alice/ui';

const preference = vi.hoisted(() => ({ reduced: false }));
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: () => preference.reduced,
}));

beforeEach(() => {
  preference.reduced = false;
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
  };
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it('preserves the existing button action and disabled enablement rule', () => {
  const action = vi.fn();
  const { rerender } = render(<CommandButton onClick={action}>Approve once</CommandButton>);
  fireEvent.click(screen.getByRole('button', { name: 'Approve once' }));
  expect(action).toHaveBeenCalledTimes(1);
  rerender(
    <CommandButton onClick={action} disabled>
      Approve once
    </CommandButton>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Approve once' }));
  expect(action).toHaveBeenCalledTimes(1);
});

it('preserves tooltip child handlers and existing descriptions, and dismisses with Escape', async () => {
  const action = vi.fn();
  const focus = vi.fn();
  render(
    <>
      <p id="existing-description">Local system settings</p>
      <Tooltip content="Settings" align="end">
        <button
          aria-label="Open settings"
          aria-describedby="existing-description"
          onClick={action}
          onFocus={focus}
        >
          Settings icon
        </button>
      </Tooltip>
    </>,
  );
  const control = screen.getByRole('button', { name: 'Open settings' });
  fireEvent.focus(control);
  expect(focus).toHaveBeenCalledTimes(1);
  const tooltip = screen.getByRole('tooltip');
  expect(control.getAttribute('aria-describedby')).toBe(`existing-description ${tooltip.id}`);
  expect(tooltip).toHaveStyle({ right: '0px' });
  fireEvent.click(control);
  expect(action).toHaveBeenCalledTimes(1);
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(control).toHaveAttribute('aria-describedby', 'existing-description');
  await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());
});

it('keeps the child capture surface mounted and preserves form input across stage changes', () => {
  const mount = vi.fn();
  const unmount = vi.fn();
  function CaptureSurface() {
    useEffect(() => {
      mount();
      return unmount;
    }, []);
    return <input aria-label="Capture surface state" defaultValue="" />;
  }
  const { rerender } = render(
    <TransitionPanel stage="preparation">
      <CaptureSurface />
    </TransitionPanel>,
  );
  const input = screen.getByRole('textbox');
  fireEvent.change(input, { target: { value: 'preserved' } });
  rerender(
    <TransitionPanel stage="challenge">
      <CaptureSurface />
    </TransitionPanel>,
  );
  expect(screen.getByRole('textbox')).toBe(input);
  expect(input).toHaveValue('preserved');
  expect(mount).toHaveBeenCalledTimes(1);
  expect(unmount).not.toHaveBeenCalled();
});

it('omits the moving edge with reduced motion and keeps values and selection available', () => {
  preference.reduced = true;
  const { container, rerender } = render(
    <>
      <BorderTrail active />
      <AnimatedCounter value="12:34" />
      <AnimatedSelection active layoutId="selected" />
    </>,
  );
  expect(container.querySelector('.border-trail')).not.toBeInTheDocument();
  expect(screen.getByText('12:34')).toBeInTheDocument();
  expect(container.querySelector('.animated-selection')).toBeInTheDocument();
  rerender(
    <>
      <BorderTrail active />
      <AnimatedCounter value="12:35" />
      <AnimatedSelection active layoutId="selected" />
    </>,
  );
  expect(screen.getByText('12:35')).toBeInTheDocument();
  expect(container.querySelector('.border-trail')).not.toBeInTheDocument();
});

it('only shows an indeterminate edge while existing async work is active', () => {
  const { container, rerender } = render(<BorderTrail active={false} />);
  expect(container.querySelector('.border-trail')).not.toBeInTheDocument();
  rerender(<BorderTrail active />);
  expect(container.querySelector('.border-trail')).toBeInTheDocument();
  rerender(<BorderTrail active={false} />);
  expect(container.querySelector('.border-trail')).not.toBeInTheDocument();
});

it('honors native dialog cancellation immediately and preserves disabled close behavior', () => {
  const close = vi.fn();
  const { rerender, unmount } = render(
    <Modal title="Verify identity" onClose={close} closeDisabled>
      <p>Current stage</p>
    </Modal>,
  );
  const dialog = screen.getByRole('dialog');
  fireEvent(dialog, new Event('cancel', { cancelable: true }));
  fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }));
  expect(close).not.toHaveBeenCalled();
  rerender(
    <Modal title="Verify identity" onClose={close}>
      <p>Current stage</p>
    </Modal>,
  );
  fireEvent(dialog, new Event('cancel', { cancelable: true }));
  expect(close).toHaveBeenCalledTimes(1);
  unmount();
  expect(dialog).not.toHaveAttribute('open');
});
