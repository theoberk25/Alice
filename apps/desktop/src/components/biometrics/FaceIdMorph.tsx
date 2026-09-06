/**
 * Chrome-only adaptation of Motion Primitives' MorphingDialog pattern (MIT).
 * Source and retained notice: docs/guides/console/visual-sources.md.
 * The caller owns the native dialog, focus, camera lifetime and every action.
 */
import { useCallback, useLayoutEffect, useRef, type RefObject } from 'react';
import { animate, useReducedMotion } from 'motion/react';
import './face-id-morph.css';

type SurfaceBox = { left: number; top: number; width: number; height: number; radius: number };
type MorphSource = {
  element?: HTMLButtonElement;
  box?: SurfaceBox;
  disposed: boolean;
  cleanup: Set<() => void>;
};

function surfaceBox(element: HTMLElement): SurfaceBox | undefined {
  const { left, top, width, height } = element.getBoundingClientRect();
  if (
    !element.isConnected ||
    width <= 0 ||
    height <= 0 ||
    left + width <= 0 ||
    top + height <= 0 ||
    left >= window.innerWidth ||
    top >= window.innerHeight
  )
    return;
  const style = window.getComputedStyle(element);
  if (style.visibility === 'hidden' || style.display === 'none') return;
  return { left, top, width, height, radius: Number.parseFloat(style.borderRadius) || 8 };
}

// TransitionPanel can be growing its visible box while its persistent child already
// has its final layout. Native scrollHeight sees that content without scaling it.
function dialogSurfaceBox(dialog: HTMLDialogElement): SurfaceBox | undefined {
  const box = surfaceBox(dialog);
  if (!box) return;
  const style = window.getComputedStyle(dialog);
  const borders =
    (Number.parseFloat(style.borderTopWidth) || 0) +
    (Number.parseFloat(style.borderBottomWidth) || 0);
  const maxHeight = Number.parseFloat(style.maxHeight) || window.innerHeight - 40;
  const height = Math.min(maxHeight, Math.max(box.height, dialog.scrollHeight + borders));
  return { ...box, height, top: box.top - (height - box.height) / 2 };
}

/** Attach the same ref to eligible initiating controls; native listeners only record geometry. */
export function useFaceIdMorph() {
  const source = useRef<MorphSource>({ disposed: false, cleanup: new Set() });
  useLayoutEffect(() => {
    const state = source.current;
    state.disposed = false;
    return () => {
      state.disposed = true;
      state.cleanup.forEach((cleanup) => cleanup());
      state.cleanup.clear();
    };
  }, []);
  const trigger = useCallback((element: HTMLButtonElement | null) => {
    if (!element) return;
    const record = () => {
      const box = surfaceBox(element);
      if (box) {
        source.current.element = element;
        source.current.box = box;
      }
    };
    if (!source.current.element?.isConnected) {
      source.current.element = element;
      record();
    }
    const form = element.form;
    const submitted = (event: SubmitEvent) => {
      if (event.submitter === element) record();
    };
    // These listeners do not prevent events, replace handlers, or initiate work.
    element.addEventListener('pointerdown', record, { passive: true });
    element.addEventListener('focus', record, { passive: true });
    element.addEventListener('click', record, { passive: true });
    form?.addEventListener('submit', submitted, { passive: true });
    return () => {
      if (source.current.element === element) record();
      element.removeEventListener('pointerdown', record);
      element.removeEventListener('focus', record);
      element.removeEventListener('click', record);
      form?.removeEventListener('submit', submitted);
    };
  }, []);
  return { source, trigger };
}

/** A blank top-layer surface. It never contains a frame, user text, controls, or a dialog. */
function morphSurface(source: MorphSource, from: SurfaceBox, to: SurfaceBox, reverse = false) {
  const surface = document.createElement('div');
  surface.className = 'face-id-morph-surface';
  surface.dataset.direction = reverse ? 'close' : 'open';
  surface.setAttribute('aria-hidden', 'true');
  surface.setAttribute('popover', 'manual');
  Object.assign(surface.style, {
    left: `${from.left}px`,
    top: `${from.top}px`,
    width: `${from.width}px`,
    height: `${from.height}px`,
    borderRadius: `${from.radius}px`,
  });
  document.body.appendChild(surface);
  // A noninteractive manual popover puts only this blank chrome above the native
  // modal's top layer. Unsupported engines omit the decoration, not the flow.
  try {
    if (typeof surface.showPopover !== 'function') {
      surface.remove();
      return () => {};
    }
    surface.showPopover();
  } catch {
    surface.remove();
    return () => {};
  }
  const duration = reverse ? 0.2 : 0.38;
  const geometry = animate(
    surface,
    {
      left: to.left,
      top: to.top,
      width: to.width,
      height: to.height,
      borderRadius: to.radius,
    },
    { duration, ease: [0.22, 1, 0.36, 1] },
  );
  const fade = animate(
    surface,
    { opacity: reverse ? [0.45, 0] : [0.96, 0.96, 0] },
    {
      duration: reverse ? duration : 0.3,
      times: reverse ? [0, 1] : [0, 0.2, 1],
      ease: 'linear',
    },
  );
  let removed = false;
  const cleanup = () => {
    if (removed) return;
    removed = true;
    geometry.stop();
    fade.stop();
    surface.remove();
    window.removeEventListener('resize', cleanup);
    window.removeEventListener('scroll', cleanup, true);
    document.removeEventListener('visibilitychange', cleanup);
    source.cleanup.delete(cleanup);
  };
  source.cleanup.add(cleanup);
  window.addEventListener('resize', cleanup, { passive: true });
  window.addEventListener('scroll', cleanup, { passive: true, capture: true });
  document.addEventListener('visibilitychange', cleanup);
  // Completion removes only disposable decoration; it cannot affect application state.
  void fade.then(cleanup);
  return cleanup;
}

/** Mount beside capture inside its existing native dialog; camera is never wrapped or retained. */
export function FaceIdMorph({ source }: { source: RefObject<MorphSource> }) {
  const anchor = useRef<HTMLSpanElement>(null);
  const reducedMotion = useReducedMotion();
  useLayoutEffect(() => {
    const dialog = anchor.current?.closest('dialog');
    const state = source.current;
    if (!dialog || reducedMotion || document.hidden) return;
    let destination: SurfaceBox | undefined;
    let cancelSurface: (() => void) | undefined;
    let reveal: ReturnType<typeof animate> | undefined;
    const originalOpacity = dialog.style.opacity;
    // Hide only the surface paint until its blank chrome begins growing; the
    // native dialog is already open and its focus/actions/camera remain live.
    dialog.setAttribute('data-face-id-morph-opening', 'true');
    // A child layout effect precedes native showModal(). Measure once it is visible.
    const openingFrame = requestAnimationFrame(() => {
      dialog.removeAttribute('data-face-id-morph-opening');
      if (state.disposed || !dialog.open || document.hidden) return;
      destination = dialogSurfaceBox(dialog);
      if (state.box && destination) {
        cancelSurface = morphSurface(state, state.box, destination);
        reveal = animate(
          dialog,
          { opacity: [0, 1] },
          { duration: 0.22, delay: 0.06, ease: 'easeOut' },
        );
        void reveal.then(() => {
          dialog.style.opacity = originalOpacity;
        });
      }
    });
    return () => {
      cancelAnimationFrame(openingFrame);
      reveal?.stop();
      dialog.removeAttribute('data-face-id-morph-opening');
      dialog.style.opacity = originalOpacity;
      cancelSurface?.();
      const from = surfaceBox(dialog) ?? destination;
      if (
        !from ||
        state.disposed ||
        document.hidden ||
        window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      )
        return;
      // The caller has already unmounted capture. Wait one frame only to locate
      // a restored CLAIM button or the still-visible enrollment control.
      const closingFrame = requestAnimationFrame(() => {
        state.cleanup.delete(cancelClosing);
        if (
          state.disposed ||
          document.hidden ||
          !state.element ||
          window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
        )
          return;
        const to = surfaceBox(state.element);
        if (to) morphSurface(state, from, to, true);
      });
      const cancelClosing = () => cancelAnimationFrame(closingFrame);
      state.cleanup.add(cancelClosing);
    };
  }, [source, reducedMotion]);
  return <span ref={anchor} className="face-id-morph-anchor" aria-hidden="true" />;
}
