import { useEffect, useRef } from 'react';
import { animate, createTimeline } from 'animejs';
import { useReducedMotion } from 'motion/react';
import { motionTokens } from '@alice/ui';
import type { LiveBiometricSession } from '@alice/contracts';

const scanMotion = {
  evidence: Number(motionTokens.panel.duration) * 1000,
  retract: 160,
  resolve: 300,
  checkDelay: 100,
  ease: 'outCubic',
};

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
      const path = ref.current?.querySelector(`[data-region="${region}"] .biometric-arc-progress`);
      if (!path || from === to) return [];
      return [
        animate(path, {
          strokeDasharray: [`${from * 50} 100`, `${to * 50} 100`],
          duration: scanMotion.evidence,
          ease: scanMotion.ease,
        }),
      ];
    });
    return () => animations.forEach((animation) => animation.revert());
  }, [coverageKey, reducedMotion, complete, failed]);

  useEffect(() => {
    const scan = ref.current;
    if (!scan || reducedMotion) return;
    const perimeter = scan.querySelector('.biometric-scan-perimeter');
    if (!perimeter) return;
    if (complete) {
      const check = scan.querySelector('.biometric-success-mark path');
      const circle = scan.querySelector('.biometric-success-mark circle');
      if (!check || !circle) return;
      const timeline = createTimeline({ defaults: { ease: scanMotion.ease } })
        .add(perimeter, { opacity: [1, 0], duration: scanMotion.retract }, 0)
        .add(circle, { r: [108, 56], opacity: [0.2, 0.6], duration: scanMotion.resolve }, 0)
        .add(
          check,
          { strokeDashoffset: [100, 0], opacity: [0, 1], duration: scanMotion.evidence },
          scanMotion.checkDelay,
        );
      return () => {
        timeline.revert();
      };
    }
    if (failed) {
      const animation = animate(perimeter, {
        opacity: [0.65, 0.12],
        duration: scanMotion.evidence,
        ease: scanMotion.ease,
      });
      return () => {
        animation.revert();
      };
    }
  }, [complete, failed, reducedMotion]);

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
            <path
              className="biometric-landmark-guide"
              d="M85 102h12 M143 102h12 M120 113v16 M103 148q17 8 34 0"
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
          <path
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
