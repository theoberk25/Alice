import { useEffect, useRef } from 'react';
import { animate, motion, useReducedMotion } from 'motion/react';
import type { LiveBiometricSession } from '@alice/contracts';

const evidenceTransition = { duration: 0.22, ease: 'easeOut' } as const;

// Positions follow the mirrored preview: the person's left is the left side of the guide.
const coverageArcs = [
  { region: 'UP', start: 250, end: 290 },
  { region: 'UP_RIGHT', start: 295, end: 335 },
  { region: 'RIGHT', start: 340, end: 380 },
  { region: 'DOWN', start: 25, end: 155 },
  { region: 'LEFT', start: 160, end: 200 },
  { region: 'UP_LEFT', start: 205, end: 245 },
] as const;
function arcPath(start: number, end: number) {
  const point = (angle: number) => {
    const radians = (angle * Math.PI) / 180;
    return `${120 + 108 * Math.cos(radians)} ${120 + 108 * Math.sin(radians)}`;
  };
  return `M ${point(start)} A 108 108 0 0 1 ${point(end)}`;
}

/** Display only: all geometry is bounded by accepted evidence and confirmed completion.
 * No animation callback can publish a biometric result or initiate a business action.
 */
export function BiometricScan({
  enrollment,
  coverage,
  centerReady,
  complete,
  failed,
}: {
  enrollment: boolean;
  coverage?: LiveBiometricSession['coverage'];
  centerReady: boolean;
  complete: boolean;
  failed: boolean;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const reducedMotion = useReducedMotion();
  const previousCoverage = useRef<LiveBiometricSession['coverage']>({});
  // A status poll may replace its object without changing accepted evidence.
  const coverageKey = JSON.stringify(coverage ?? {});
  useEffect(() => {
    const next = JSON.parse(coverageKey) as LiveBiometricSession['coverage'];
    const previous = previousCoverage.current;
    previousCoverage.current = next;
    if (!ref.current || reducedMotion || complete || failed) return;
    const animations = coverageArcs.flatMap(({ region }) => {
      const from = previous[region] ?? 0;
      const to = next[region] ?? 0;
      const path = ref.current?.querySelector<SVGPathElement>(
        `[data-region="${region}"] .biometric-arc-progress`,
      );
      if (!path || from === to) return [];
      const animation = animate(
        path,
        {
          strokeDasharray: [`${from * 50} 100`, `${to * 50} 100`],
          strokeOpacity: [0.55, 1],
        },
        evidenceTransition,
      );
      return [{ animation, path }];
    });
    return () =>
      animations.forEach(({ animation, path }) => {
        animation.stop();
        // The SVG attribute always holds exact accepted evidence. Remove the temporary
        // presentation styles when stopping so reduced/terminal states cannot freeze it.
        path.style.removeProperty('stroke-dasharray');
        path.style.removeProperty('stroke-opacity');
      });
  }, [coverageKey, reducedMotion, complete, failed]);

  return (
    <svg
      ref={ref}
      className="biometric-face-guide"
      viewBox="0 0 240 240"
      aria-hidden="true"
      data-complete={complete}
      data-failed={failed}
    >
      <g className="biometric-scan-perimeter">
        {enrollment ? (
          <>
            {coverageArcs.map(({ region, start, end }) => {
              const count = coverage?.[region] ?? 0;
              const path = arcPath(start, end);
              return (
                <g
                  key={region}
                  className="biometric-coverage-arc"
                  data-region={region}
                  data-accepted={count}
                >
                  <path className="biometric-guide-track" d={path} />
                  <path
                    className="biometric-arc-progress"
                    d={path}
                    pathLength="100"
                    strokeDasharray={`${(count / 2) * 100} 100`}
                  />
                </g>
              );
            })}
            {!centerReady && <circle className="biometric-center-guide" cx="120" cy="120" r="98" />}
          </>
        ) : (
          <>
            <circle className="biometric-guide-track" cx="120" cy="120" r="108" />
            <circle
              className="biometric-guide-progress"
              cx="120"
              cy="120"
              r="108"
              pathLength="100"
              strokeDasharray={`${complete ? 100 : 0} 100`}
            />
          </>
        )}
      </g>
      {complete && (
        <g
          className="biometric-success-mark"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="120" cy="120" r="56" />
          <motion.path
            initial={reducedMotion ? false : { strokeDashoffset: 100 }}
            animate={{ strokeDashoffset: 0 }}
            transition={reducedMotion ? { duration: 0 } : evidenceTransition}
            d="M94 120l17 17 35-37"
            pathLength="100"
            strokeDasharray="100"
            strokeDashoffset="0"
          />
        </g>
      )}
    </svg>
  );
}
