import { useEffect, useId, useRef } from 'react';
import { animate, stagger, svg } from 'animejs';
import { motion, useReducedMotion } from 'motion/react';
import type { LiveBiometricSession } from '@alice/contracts';
import './face-id-scan.css';

const circlePath = 'M120 22 A98 98 0 1 1 119.999 22';
const checkPath = 'M93 120 L112 139 L150 100';
const poseArcs = [
  { region: 'UP', start: 250, end: 290 },
  { region: 'UP_RIGHT', start: 295, end: 327 },
  { region: 'RIGHT', start: 334, end: 386 },
  { region: 'DOWN', start: 63, end: 117 },
  { region: 'LEFT', start: 154, end: 206 },
  { region: 'UP_LEFT', start: 213, end: 245 },
] as const;

function arcPath(start: number, end: number) {
  const point = (angle: number) => {
    const radians = (angle * Math.PI) / 180;
    return `${120 + 110 * Math.cos(radians)} ${120 + 110 * Math.sin(radians)}`;
  };
  return `M ${point(start)} A110 110 0 0 1 ${point(end)}`;
}

/** An illustration of a usable face, never measured landmark positions. The native
 * contract provides a quality result, not camera-space landmarks. This entire
 * display is decorative and cannot report success or initiate a business action.
 */
const contourPoints = [
  [91, 109],
  [149, 109],
  [120, 127],
  [106, 148],
  [134, 148],
  [82, 127],
  [158, 127],
  [120, 172],
] as const;

export function FaceIdScan({
  enrollment,
  coverage,
  complete,
  failed,
  evaluating,
  faceDetected,
  activeRegion,
}: {
  enrollment: boolean;
  coverage?: LiveBiometricSession['coverage'];
  complete: boolean;
  failed: boolean;
  evaluating: boolean;
  faceDetected: boolean;
  activeRegion?: string;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const reducedMotion = useReducedMotion();
  const gradientId = useId();
  const accepted = Object.values(coverage ?? {}).reduce((total, count) => total + (count ?? 0), 0);
  // Login stages are discrete presentation states, never a confidence score.
  const stateProgress = complete ? 100 : evaluating ? 72 : faceDetected ? 36 : 0;
  const evidenceProgress = enrollment ? (accepted / 14) * 100 : stateProgress;
  const progress = complete ? 100 : evidenceProgress;
  const active = !failed && !complete;
  const transition = reducedMotion ? { duration: 0 } : { duration: 0.22, ease: 'easeOut' as const };

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const points = element.querySelectorAll('.face-id-contour-point');
    const contours = element.querySelectorAll('.face-id-contour-line');
    const illustration = element.querySelector<SVGGElement>('.face-id-landmarks');
    if (!illustration) return;
    // Keep this layer's opacity under Anime.js alone: a React opacity update before
    // the effect would snap a lost face away before its exit could be drawn.
    // No completion callback is involved. Native completion owns all timing and actions.
    if (reducedMotion) {
      illustration.style.opacity = faceDetected && !failed && !complete ? '1' : '0';
      illustration.style.transform = 'none';
      points.forEach((point) => (point as SVGCircleElement).style.removeProperty('opacity'));
      contours.forEach((contour) => {
        (contour as SVGPathElement).style.removeProperty('opacity');
        (contour as SVGPathElement).style.removeProperty('stroke-dashoffset');
      });
      return;
    }
    const animations = complete
      ? [
          animate(illustration, {
            opacity: 0,
            scale: 0.94,
            delay: 100,
            duration: 80,
            ease: 'inOutQuad',
          }),
        ]
      : faceDetected && !failed
        ? [
            animate(illustration, {
              opacity: 1,
              scale: 1,
              duration: 160,
              ease: 'outQuad',
            }),
            animate(points, {
              opacity: [0, 0.58],
              delay: stagger(18),
              duration: 160,
              ease: 'outQuad',
            }),
            animate(contours, {
              strokeDashoffset: [1, 0],
              opacity: [0, 0.3],
              duration: 260,
              ease: 'outQuad',
            }),
          ]
        : [animate(illustration, { opacity: 0, duration: 110, ease: 'outQuad' })];
    // Preserve the current displayed opacity for an interrupted reveal/retraction.
    // cancel() stops every animator without rewinding the next state's starting point.
    return () => animations.forEach((animation) => animation.cancel());
  }, [faceDetected, failed, complete, reducedMotion]);

  useEffect(() => {
    const ring = ref.current?.querySelector<SVGPathElement>('.face-id-scan-progress');
    const target = ref.current?.querySelector<SVGPathElement>('.face-id-check-target');
    if (!ring || !target) return;
    ring.setAttribute('d', complete && reducedMotion ? checkPath : circlePath);
    if (!complete || reducedMotion) return;
    // First finish the evidence ring, then collapse it into the check. The complete
    // 400ms sequence fits inside the existing 450ms success acknowledgement.
    // Geometry-less DOM renderers use the authoritative static result directly.
    if (typeof ring.getTotalLength !== 'function') {
      ring.setAttribute('d', checkPath);
      return () => ring.setAttribute('d', circlePath);
    }
    const animation = animate(ring, {
      d: svg.morphTo(target, 0.18),
      delay: 180,
      duration: 220,
      ease: 'inOutQuad',
    });
    return () => animation.revert();
  }, [complete, reducedMotion]);

  return (
    <svg
      ref={ref}
      className="face-id-scan"
      viewBox="0 0 240 240"
      aria-hidden="true"
      data-enrollment={enrollment}
      data-complete={complete}
      data-failed={failed}
      data-evaluating={evaluating && active}
      data-face-detected={faceDetected && active}
      data-state-progress={enrollment ? undefined : stateProgress}
      data-evidence-progress={enrollment ? accepted : undefined}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="currentColor" stopOpacity="0" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0.85" />
        </linearGradient>
      </defs>
      <path
        className="face-id-scan-vignette"
        d="M-600 -400 H840 V640 H-600 Z M120 25 A95 95 0 1 0 120 215 A95 95 0 1 0 120 25 Z"
        fillRule="evenodd"
      />
      <motion.circle
        className="face-id-base-ring"
        cx="120"
        cy="120"
        r="102"
        animate={{ opacity: complete ? 0 : failed ? 0.2 : 0.65 }}
        transition={transition}
      />
      <motion.circle
        className="face-id-inner-ring"
        cx="120"
        cy="120"
        r="94"
        animate={{ opacity: complete ? 0 : 1 }}
        transition={transition}
      />
      <motion.path
        className="face-id-scan-progress"
        d={complete && reducedMotion ? checkPath : circlePath}
        pathLength="100"
        strokeDasharray={`${progress} 100`}
        initial={false}
        animate={{
          strokeDasharray: `${failed ? 0 : progress} 100`,
          opacity: failed ? 0 : 1,
          strokeWidth: complete ? 2.3 : 1.4,
        }}
        transition={complete && !reducedMotion ? { duration: 0.1 } : transition}
      />
      <path className="face-id-check-target" d={checkPath} />
      <motion.g
        className="face-id-pose-regions"
        initial={false}
        animate={{ opacity: complete ? 0 : failed ? 0.3 : 1 }}
        transition={transition}
      >
        {enrollment && (
          <>
            {poseArcs.map(({ region, start, end }) => {
              const count = coverage?.[region] ?? 0;
              const path = arcPath(start, end);
              return (
                <g
                  key={region}
                  className="face-id-pose-arc"
                  data-region={region}
                  data-accepted={count}
                  data-active={active && activeRegion === region}
                  data-completed={count === 2}
                >
                  <path className="face-id-pose-emphasis" d={path} />
                  <path className="face-id-region-track" d={path} />
                  <motion.path
                    className="face-id-pose-progress"
                    d={path}
                    pathLength="100"
                    strokeDasharray={`${count * 50} 100`}
                    initial={false}
                    animate={{ strokeDasharray: `${count * 50} 100` }}
                    transition={transition}
                  />
                </g>
              );
            })}
            <g
              className="face-id-pose-arc face-id-center-region"
              data-region="CENTER"
              data-accepted={coverage?.CENTER ?? 0}
              data-active={active && activeRegion === 'CENTER'}
              data-completed={coverage?.CENTER === 2}
            >
              <circle className="face-id-pose-emphasis" cx="120" cy="120" r="87" />
              <circle className="face-id-center-track" cx="120" cy="120" r="87" />
              <motion.circle
                className="face-id-center-progress"
                cx="120"
                cy="120"
                r="87"
                pathLength="100"
                strokeDasharray={`${(coverage?.CENTER ?? 0) * 50} 100`}
                initial={false}
                animate={{ strokeDasharray: `${(coverage?.CENTER ?? 0) * 50} 100` }}
                transition={transition}
              />
            </g>
          </>
        )}
      </motion.g>
      {evaluating && active && (
        <motion.g
          className="face-id-scan-highlight"
          initial={false}
          animate={{ rotate: reducedMotion ? 0 : 360 }}
          transition={
            reducedMotion ? { duration: 0 } : { duration: 2.8, repeat: Infinity, ease: 'linear' }
          }
        >
          <path d="M120 22 A98 98 0 0 1 209 79" stroke={`url(#${gradientId})`} />
        </motion.g>
      )}
      <g className="face-id-landmarks" data-decorative="true" style={{ opacity: 0 }}>
        <path
          className="face-id-contour-line"
          d="M80 127 C83 151 97 173 120 178 C143 173 157 151 160 127"
          pathLength="1"
          strokeDasharray="1"
        />
        <path
          className="face-id-contour-line"
          d="M89 103 Q97 98 105 103 M135 103 Q143 98 151 103 M109 149 Q120 155 131 149"
          pathLength="1"
          strokeDasharray="1"
        />
        {contourPoints.map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} className="face-id-contour-point" cx={cx} cy={cy} r="1.4" />
        ))}
      </g>
    </svg>
  );
}
