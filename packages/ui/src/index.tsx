import { useLayoutEffect, useRef, type ReactNode } from 'react';
import { animate, useReducedMotion } from 'motion/react';
import { CommandButton } from './motion';
import { motionTokens } from './motion-tokens';
export * from './motion';
import { X } from 'lucide-react';
export type Tone = 'healthy' | 'warning' | 'danger' | 'neutral' | 'information';
export function toneFor(status: string): Tone {
  if (/FAIL|DENY|DENIED|REJECT|NOT_FOUND|TERMINATED/.test(status)) return 'danger';
  if (/OFFLINE|UNAVAILABLE|UNKNOWN|DISCONNECTED|NOT_CONFIGURED/.test(status)) return 'neutral';
  if (/UNVERIFIED/.test(status)) return 'warning';
  if (/HOLD|HELD|PENDING|WAITING|REVIEW|DDIL|DISCREPANCY/.test(status)) return 'warning';
  if (/READY|HEALTHY|VERIFIED|ALLOW|CONNECTED|PASS|APPROVED/.test(status)) return 'healthy';
  if (/RUNNING|RESEARCH|PROCESSING/.test(status)) return 'information';
  return 'neutral';
}
export const human = (value: string) => value.replaceAll('_', ' ');
export function Badge({
  children,
  tone = 'neutral',
  dot = true,
}: {
  children: ReactNode;
  tone?: Tone;
  dot?: boolean;
}) {
  return (
    <span className={`badge tone-${tone}`}>
      {dot && <i />}
      {children}
    </span>
  );
}
export function Panel({
  title,
  meta,
  children,
  className = '',
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <h2>{title}</h2>
        {meta}
      </div>
      {children}
    </section>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
  closeDisabled = false,
  className = '',
  morphId,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  closeDisabled?: boolean;
  className?: string;
  morphId?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const reduce = useReducedMotion();
  // Capture initial presentation preferences without reopening an active native dialog.
  const opening = useRef({ morphId, reduce });
  useLayoutEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const trigger = opening.current.morphId
      ? Array.from(document.querySelectorAll<HTMLElement>('[data-morph-id]')).find(
          (element) => element.dataset.morphId === opening.current.morphId,
        )
      : undefined;
    const source = trigger?.getBoundingClientRect();
    dialog.showModal();
    const target = dialog.getBoundingClientRect();
    // Native dialog remains in the top layer. Geometry only supplies a visual origin;
    // no close, authentication or action callback is linked to animation completion.
    const canMorph =
      source && source.width > 0 && source.height > 0 && target.width > 0 && target.height > 0;
    const initialTransform = canMorph
      ? `translate(${source.left + source.width / 2 - target.left - target.width / 2}px, ${source.top + source.height / 2 - target.top - target.height / 2}px) scale(${source.width / target.width}, ${source.height / target.height})`
      : 'translate(0px, 8px) scale(0.985, 0.985)';
    const animation = opening.current.reduce
      ? undefined
      : animate(
          dialog,
          { opacity: [0.7, 1], transform: [initialTransform, 'translate(0px, 0px) scale(1, 1)'] },
          canMorph ? motionTokens.dialog : motionTokens.panel,
        );
    return () => {
      animation?.stop();
      dialog.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      data-morph-dialog={morphId}
      className={`modal ${wide ? 'modal-wide' : ''} ${className}`}
      onCancel={(event) => {
        event.preventDefault();
        if (!closeDisabled) onClose();
      }}
      onKeyDown={(event) => {
        if (
          event.key !== 'Tab' ||
          event.ctrlKey ||
          event.altKey ||
          event.metaKey ||
          event.defaultPrevented
        )
          return;
        const dialog = event.currentTarget;
        const controls = Array.from(
          dialog.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]',
          ),
        ).filter(
          (element) =>
            element.tabIndex >= 0 &&
            !element.matches(':disabled') &&
            !element.closest('[hidden], [inert]') &&
            element.getClientRects().length > 0 &&
            window.getComputedStyle(element).visibility !== 'hidden',
        );
        const first = controls[0];
        const last = controls[controls.length - 1];
        const active = document.activeElement;
        if (!first || !last) {
          event.preventDefault();
          dialog.focus();
        } else if (event.shiftKey && (active === first || active === dialog)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (active === last || active === dialog)) {
          event.preventDefault();
          first.focus();
        }
      }}
      aria-label={title}
    >
      <div className="modal-heading">
        <h2>{title}</h2>
        <CommandButton
          type="button"
          className="icon-button modal-close"
          aria-label="Close dialog"
          disabled={closeDisabled}
          onClick={onClose}
        >
          <X size={16} />
        </CommandButton>
      </div>
      {children}
    </dialog>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty-state">{children}</p>;
}
