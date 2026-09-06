/**
 * Presentation primitives adapted from Motion Primitives concepts (MIT).
 * Source links, adaptation details and retained notice:
 * docs/guides/console/visual-sources.md
 * State and action handlers always remain with the caller.
 */
import {
  cloneElement,
  forwardRef,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactElement,
  type ReactNode,
} from 'react';
import { AnimatePresence, MotionConfig, motion, useAnimate, useReducedMotion } from 'motion/react';
import { motionTokens } from './motion-tokens';

export { motionTokens } from './motion-tokens';

export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={motionTokens.panel}>
      {children}
    </MotionConfig>
  );
}

/** A controlled, purely visual AnimatedBackground adaptation; never clones a control. */
export function AnimatedSelection({
  active,
  layoutId,
  className = '',
}: {
  active: boolean;
  layoutId: string;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return active ? (
    <motion.span
      aria-hidden="true"
      className={`animated-selection ${className}`}
      layoutId={reduce ? undefined : layoutId}
      initial={false}
      transition={reduce ? { duration: 0 } : motionTokens.selection}
      style={{
        position: 'absolute',
        inset: 0,
        borderRadius: 'inherit',
        pointerEvents: 'none',
        zIndex: -1,
      }}
    />
  ) : null;
}

/** Stage changes animate the existing subtree; camera and form identity stay intact. */
export function TransitionPanel({
  stage,
  children,
  className = '',
}: {
  stage: string | number;
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const [scope, animate] = useAnimate<HTMLDivElement>();
  const previous = useRef(stage);
  const panel = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | 'auto'>('auto');
  useLayoutEffect(() => {
    const content = scope.current;
    const container = panel.current;
    if (!content || !container || typeof ResizeObserver === 'undefined') return;
    const measure = (contentHeight: number) => {
      // Layout dimensions remain correct while a containing dialog is morphing.
      // Border-box surfaces must include their own padding and borders as well.
      const style = window.getComputedStyle(container);
      const chrome =
        style.boxSizing === 'border-box'
          ? [
              style.paddingTop,
              style.paddingBottom,
              style.borderTopWidth,
              style.borderBottomWidth,
            ].reduce((total, value) => total + (Number.parseFloat(value) || 0), 0)
          : 0;
      setHeight(Math.ceil(contentHeight + chrome));
    };
    // A child layout effect can run before its native dialog calls showModal().
    // Keep intrinsic height while hidden; the observer measures the visible layout.
    if (content.offsetHeight > 0) measure(content.offsetHeight);
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) measure(entry.borderBoxSize?.[0]?.blockSize ?? entry.contentRect.height);
    });
    observer.observe(content);
    return () => observer.disconnect();
  }, [scope]);
  useEffect(() => {
    if (!scope.current) return;
    if (reduce) {
      previous.current = stage;
      scope.current.style.opacity = '';
      scope.current.style.transform = '';
      return;
    }
    if (previous.current === stage) return;
    previous.current = stage;
    const animation = animate(scope.current, { opacity: [0.65, 1], y: [8, 0] }, motionTokens.panel);
    return () => animation.stop();
  }, [stage, reduce, animate, scope]);
  return (
    <motion.div
      ref={panel}
      initial={false}
      animate={{ height }}
      style={{ overflow: 'clip', overflowClipMargin: 4 }}
      className={`transition-panel ${className}`}
      transition={reduce ? { duration: 0 } : motionTokens.panel}
      data-visual-stage={stage}
    >
      <div ref={scope} style={{ display: 'flow-root' }}>
        {children}
      </div>
    </motion.div>
  );
}

/** Fixed-size digit cells avoid measurement dependencies and only animate changed digits. */
export function AnimatedCounter({
  value,
  className = '',
}: {
  value: string | number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const text = String(value);
  return (
    <span
      className={`animated-counter ${className}`}
      style={{ display: 'inline-flex', fontVariantNumeric: 'tabular-nums' }}
    >
      <span
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: 'hidden',
          clipPath: 'inset(50%)',
          whiteSpace: 'nowrap',
          border: 0,
        }}
      >
        {text}
      </span>
      <span aria-hidden="true" style={{ display: 'inline-flex' }}>
        {Array.from(text).map((character, index) => (
          <span
            key={text.length - index}
            style={{
              position: 'relative',
              display: 'inline-block',
              width: /\d/.test(character) ? '1ch' : undefined,
              height: '1.2em',
              lineHeight: '1.2em',
              overflow: 'hidden',
            }}
          >
            <AnimatePresence initial={false} mode="popLayout">
              <motion.span
                key={character}
                style={{ display: 'inline-block' }}
                initial={reduce ? false : { y: '55%', opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={reduce ? undefined : { y: '-55%', opacity: 0 }}
                transition={reduce ? { duration: 0 } : motionTokens.selection}
              >
                {character}
              </motion.span>
            </AnimatePresence>
          </span>
        ))}
      </span>
    </span>
  );
}

/** An indeterminate edge accent is mounted only while caller-owned work is active. */
export function BorderTrail({ active, className = '' }: { active: boolean; className?: string }) {
  const reduce = useReducedMotion();
  if (!active || reduce) return null;
  return (
    <span
      aria-hidden="true"
      className={`border-trail ${className}`}
      style={{
        position: 'absolute',
        inset: 0,
        borderRadius: 'inherit',
        border: '1px solid transparent',
        pointerEvents: 'none',
        overflow: 'hidden',
        maskImage: 'linear-gradient(#000, #000), linear-gradient(#000, #000)',
        maskClip: 'padding-box, border-box',
        maskComposite: 'exclude',
        WebkitMaskComposite: 'xor',
      }}
    >
      <motion.span
        style={{
          position: 'absolute',
          width: 36,
          height: 36,
          background: 'var(--alice-cyan)',
          opacity: 0.45,
          offsetPath: 'rect(0 auto auto 0 round 10px)',
        }}
        animate={{ offsetDistance: ['0%', '100%'] }}
        transition={{ duration: 3.6, ease: 'linear', repeat: Infinity }}
      />
    </span>
  );
}

/** Native button action props pass through unchanged; animation callbacks are not exposed. */
type CommandButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'onAnimationStart' | 'onDrag' | 'onDragStart' | 'onDragEnd'
>;
export const CommandButton = forwardRef<HTMLButtonElement, CommandButtonProps>(
  function CommandButton({ children, disabled, ...props }, ref) {
    const reduce = useReducedMotion();
    return (
      <motion.button
        {...props}
        ref={ref}
        disabled={disabled}
        whileHover={disabled ? undefined : { filter: 'brightness(1.08)' }}
        whileTap={disabled || reduce ? undefined : { scale: 0.988 }}
        transition={reduce ? { duration: 0 } : motionTokens.press}
      >
        {children}
      </motion.button>
    );
  },
);

/** Original tooltip implementation; no Skiper Premium code. Child handlers are untouched. */
export function Tooltip({
  content,
  children,
  className = '',
  side = 'bottom',
  align = 'center',
}: {
  content: string;
  children: ReactElement<HTMLAttributes<HTMLElement>>;
  className?: string;
  side?: 'top' | 'bottom';
  align?: 'start' | 'center' | 'end';
}) {
  const id = useId();
  const reduce = useReducedMotion();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const visible = (hovered || focused) && !dismissed;
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(leaveTimer.current), []);
  useEffect(() => {
    if (!visible) return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDismissed(true);
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [visible]);
  const describedBy =
    [children.props['aria-describedby'], visible ? id : undefined].filter(Boolean).join(' ') ||
    undefined;
  return (
    <span
      className={`tooltip-anchor ${className}`}
      style={{ position: 'relative', display: 'inline-flex' }}
      onPointerEnter={(event) => {
        if (event.pointerType !== 'touch') {
          clearTimeout(leaveTimer.current);
          setHovered(true);
          setDismissed(false);
        }
      }}
      onPointerLeave={() => {
        leaveTimer.current = setTimeout(() => setHovered(false), 100);
      }}
      onFocus={() => {
        setFocused(true);
        setDismissed(false);
      }}
      onBlur={() => setFocused(false)}
      onKeyDown={(event) => {
        if (event.key === 'Escape') setDismissed(true);
      }}
    >
      {cloneElement(children, { 'aria-describedby': describedBy })}
      <AnimatePresence>
        {visible && (
          <motion.span
            id={id}
            role="tooltip"
            className="console-tooltip"
            initial={reduce ? false : { opacity: 0, y: side === 'bottom' ? -3 : 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={reduce ? { duration: 0 } : motionTokens.hover}
            style={{
              position: 'absolute',
              zIndex: 100,
              ...(align === 'end'
                ? { right: 0 }
                : align === 'start'
                  ? { left: 0 }
                  : { left: '50%', x: '-50%' }),
              ...(side === 'bottom' ? { top: 'calc(100% + 8px)' } : { bottom: 'calc(100% + 8px)' }),
              width: 'max-content',
              maxWidth: 'min(280px, calc(100vw - 24px))',
              padding: '7px 10px',
              borderRadius: 6,
              background: 'var(--alice-bg-floating, #20262e)',
              border: '1px solid var(--alice-border)',
              boxShadow: '0 5px 16px #0005',
              color: 'var(--alice-text-primary)',
              fontFamily: 'var(--alice-font-body)',
              fontSize: 12,
              fontWeight: 450,
              lineHeight: 1.4,
              letterSpacing: 0,
              textTransform: 'none',
              pointerEvents: 'auto',
            }}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
