import { useEffect, useRef, type ReactNode } from 'react';
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
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  closeDisabled?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? 'modal-wide' : ''} ${className}`}
      onCancel={(event) => {
        event.preventDefault();
        if (!closeDisabled) onClose();
      }}
      aria-label={title}
    >
      <div className="modal-heading">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          disabled={closeDisabled}
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty-state">{children}</p>;
}
