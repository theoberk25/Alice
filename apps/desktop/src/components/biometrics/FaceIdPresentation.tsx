import { forwardRef } from 'react';
import { AnimatePresence, motion, useIsPresent, useReducedMotion } from 'motion/react';
import { AnimatedCounter, TransitionPanel } from '@alice/ui';
import type { LiveBiometricSession } from '@alice/contracts';

const poseLabels = {
  CENTER: 'Center',
  LEFT: 'Left',
  RIGHT: 'Right',
  UP: 'Up',
  DOWN: 'Down',
  UP_LEFT: 'Upper left',
  UP_RIGHT: 'Upper right',
};

const StateText = forwardRef<HTMLElement, { text: string; reduce: boolean }>(function StateText(
  { text, reduce },
  ref,
) {
  const present = useIsPresent();
  return (
    <motion.strong
      ref={ref}
      aria-hidden={!present || undefined}
      initial={reduce ? false : { opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduce ? undefined : { opacity: 0, y: -3, transition: { duration: 0.055, delay: 0 } }}
      transition={{ duration: reduce ? 0 : 0.12, delay: reduce ? 0 : 0.055, ease: 'easeOut' }}
    >
      {text}
    </motion.strong>
  );
});

/** Transition Panel pattern applies only to copy; the camera is never keyed or retained. */
export function FaceIdStatus({ text }: { text: string }) {
  const reduce = useReducedMotion();
  return (
    <TransitionPanel stage={text} className="face-id-state-panel">
      <AnimatePresence initial={false} mode="popLayout">
        <StateText key={text} text={text} reduce={!!reduce} />
      </AnimatePresence>
    </TransitionPanel>
  );
}

/** Counts and completed indicators are direct projections of accepted native evidence. */
export function FaceIdEnrollmentProgress({
  coverage,
  observations,
  activeRegion,
  complete,
}: {
  coverage?: LiveBiometricSession['coverage'];
  observations: number;
  activeRegion?: string;
  complete: boolean;
}) {
  const reduce = useReducedMotion();
  const angles = Object.values(coverage ?? {}).filter((count) => count === 2).length;
  const samples = Object.values(coverage ?? {}).reduce((total, count) => total + (count ?? 0), 0);
  return (
    <motion.div
      layout={reduce ? false : 'position'}
      className="biometric-enrollment-feedback face-id-evidence"
      data-verified={complete}
    >
      <div className="biometric-coverage face-id-poses" aria-label="Accepted facial angle coverage">
        {Object.entries(poseLabels).map(([region, label]) => {
          const count = coverage?.[region as keyof typeof poseLabels] ?? 0;
          return (
            <div
              key={region}
              data-accepted={count}
              data-active={activeRegion === region}
              aria-label={`${label}: ${count} of 2 samples accepted`}
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <circle cx="10" cy="10" r="7" className="face-id-pose-track" />
                <motion.circle
                  cx="10"
                  cy="10"
                  r="7"
                  pathLength="1"
                  className="face-id-pose-fill"
                  initial={false}
                  animate={{ pathLength: count / 2 }}
                  transition={{ duration: reduce ? 0 : 0.22, ease: 'easeOut' }}
                />
                {count === 2 && <path d="m7 10 2 2 4-4" className="face-id-pose-check" />}
              </svg>
              <span>{label}</span>
            </div>
          );
        })}
      </div>
      <div className="face-id-metrics">
        <p
          className="biometric-progress-label"
          aria-label={`${angles} / 7 angles complete · ${observations} accepted observations`}
        >
          <span>
            <AnimatedCounter value={angles} />
            <span className="face-id-metric-denominator">/7</span> angles
          </span>
          <span>
            <AnimatedCounter value={observations} /> accepted observations
          </span>
        </p>
        <div className="biometric-sample-progress">
          <div
            className="biometric-progress"
            role="progressbar"
            aria-label="Face enrollment progress"
            aria-valuemin={0}
            aria-valuemax={14}
            aria-valuenow={samples}
            aria-valuetext={`${samples} of 14 angle samples accepted; ${angles} of 7 facial angles complete`}
          >
            <motion.span
              initial={false}
              animate={{ width: `${(samples / 14) * 100}%` }}
              transition={{ duration: reduce ? 0 : 0.22 }}
            />
          </div>
          <span>
            <AnimatedCounter value={samples} />
            /14 samples
          </span>
        </div>
      </div>
    </motion.div>
  );
}
