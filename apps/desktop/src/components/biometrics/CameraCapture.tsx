import { useEffect, useRef, useState } from 'react';
import { Check, ScanFace, VideoOff } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { BorderTrail, CommandButton, TransitionPanel, motionTokens } from '@alice/ui';
import { BiometricScan } from './BiometricScan';
import type { BiometricIntent, LiveBiometricSession } from '@alice/contracts';
import {
  beginBiometricSession,
  readBiometricSession,
  readBiometricPreview,
  cancelBiometricSession,
  recoverBiometricEnrollment,
} from '../../features/biometrics/verify';
import './biometrics.css';
const angleLabels = {
  CENTER: 'Center',
  LEFT: 'Left',
  RIGHT: 'Right',
  UP: 'Up',
  DOWN: 'Down',
  UP_LEFT: 'Upper left',
  UP_RIGHT: 'Upper right',
};
const terminal = new Set(['SUCCEEDED', 'FAILED', 'CANCELLED', 'EXPIRED']);
const successAcknowledgementMs = 450;
const qualityGuidance: Record<string, string> = {
  LOW_QUALITY_FACE_TOO_SMALL: 'Move a little closer',
  LOW_QUALITY_LIGHTING: 'Find even light across your face',
  LOW_QUALITY_BLUR: 'Pause briefly for a clear view',
  NO_FACE_DETECTED: 'Bring your face into the camera view',
  MULTIPLE_FACES_DETECTED: 'Pause while the camera finds a clear view of your face',
  FACE_FEATURES_NOT_VISIBLE: 'Keep your whole face in the camera view',
  FACE_POSE_INCONCLUSIVE: 'Keep your face clearly visible',
  PAD_INVALID_BOUNDS: 'Move slightly away so your whole face is visible',
  PAD_EMPTY_CROP: 'Move slightly away so your whole face is visible',
  INVALID_POSE_MATRIX: 'Face the camera for a moment',
  NONFINITE_POSE: 'Face the camera for a moment',
  ENROLLMENT_SAMPLE_NOT_ACCEPTED: 'Face the camera for a moment',
};
const controlLabels: Record<string, string> = {
  identity: 'Face match',
  quality: 'Clear image',
  capture_integrity: 'Camera session',
  pose: 'Face position',
  pad: 'Presentation check',
};
function explainError(error: string) {
  if (/CAMERA_DISCONNECTED/.test(error))
    return 'The camera stopped delivering images before Face ID finished. Start a new session to reconnect it.';
  if (/CAMERA.*PERMISSION|PERMISSION.*CAMERA/i.test(error))
    return 'Allow ALICE camera access in macOS Privacy & Security, then try again.';
  if (/ACTIVATION[_ ]RECOVERY[_ ]REQUIRED/.test(error))
    return 'Your face was captured, but saving was interrupted. Recover the pending enrollment below.';
  if (/REMOVAL[_ ]RECOVERY[_ ]REQUIRED/.test(error))
    return 'An earlier removal needs to finish. Return to administration and choose Discard pending enrollment or Remove face.';
  if (/MODEL|NOT_CONFIGURED/.test(error))
    return 'Face ID is not ready. Ask your administrator to check the local face service.';
  if (/EXPIRED|DEADLINE/.test(error))
    return 'This attempt timed out. Start again when you are ready.';
  if (/ENROLLMENT|NOT_ENROLLED/.test(error))
    return 'This identity needs a new face enrollment. Open Administration to set it up.';
  if (/IDENTITY|MATCH/.test(error))
    return 'Your face could not be verified. Check your username and try again.';
  if (/hidden/.test(error)) return 'Keep ALICE in the foreground, then start a new camera session.';
  return 'The camera session could not finish. The reason is shown below. Try again when you are ready.';
}
function errorTitle(error: string) {
  if (/CAMERA.*PERMISSION|PERMISSION.*CAMERA/i.test(error)) return 'Camera permission needed';
  const code = error.match(/\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/)?.[0];
  if (!code) return 'Face scan stopped';
  const words = code.toLowerCase().replaceAll('_', ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
/** Preview/progress only. No renderer camera API, frame selection or success authority. */
export function CameraCapture({
  intent,
  onComplete,
  onCancel,
  onStarted,
  onRecovered,
  onAcknowledged,
}: {
  intent: BiometricIntent;
  onComplete: (session: LiveBiometricSession) => Promise<void>;
  onCancel: () => void;
  onStarted?: () => void;
  onRecovered?: () => Promise<void>;
  /** Optional visual dismissal only; authoritative completion is never delayed. */
  onAcknowledged?: () => void;
}) {
  const [session, setSession] = useState<LiveBiometricSession>();
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [successPresented, setSuccessPresented] = useState(false);
  const [action, setAction] = useState<'CANCELLING' | 'RECOVERING' | 'COMPLETING'>();
  const busy = useRef(false);
  const preview = useRef<HTMLImageElement>(null);
  const previewRatio = useRef('');
  const stopCapture = useRef<() => Promise<void>>(async () => {});
  const callbacks = useRef({ onComplete, onCancel, onStarted, onAcknowledged });
  callbacks.current = { onComplete, onCancel, onStarted, onAcknowledged };
  const intentKey = JSON.stringify(intent);
  useEffect(() => {
    let disposed = false;
    let finished = false;
    let statusTimer: ReturnType<typeof setTimeout> | undefined;
    let previewTimer: ReturnType<typeof setTimeout> | undefined;
    let successTimer: ReturnType<typeof setTimeout> | undefined;
    let resolveAcknowledgement: ((proceed: boolean) => void) | undefined;
    let acknowledging = false;
    let owned: string | undefined;
    let lastPreviewSequence = 0;
    let cancellation: Promise<void> | undefined;
    busy.current = false;
    setAction(undefined);
    setError('');
    setSession(undefined);
    setSuccessPresented(false);
    function clearPreview() {
      if (preview.current) {
        preview.current.removeAttribute('src');
        preview.current.hidden = true;
      }
    }
    clearPreview();
    function stopTimers() {
      clearTimeout(statusTimer);
      clearTimeout(previewTimer);
      clearTimeout(successTimer);
      resolveAcknowledgement?.(false);
      resolveAcknowledgement = undefined;
      clearPreview();
    }
    function cancelNative() {
      if (!owned) return Promise.resolve();
      cancellation ??= cancelBiometricSession(owned).catch(() => undefined);
      return cancellation;
    }
    function stop() {
      disposed = true;
      stopTimers();
      return cancelNative();
    }
    stopCapture.current = stop;
    // The independent preview never drives progress or completion. Only one read is in flight.
    async function pollPreview() {
      if (disposed || finished || !owned) return;
      const started = performance.now();
      let delay = 33;
      try {
        const frame = await readBiometricPreview(owned);
        if (disposed || finished) return;
        if (frame === null) clearPreview();
        else if (frame.session_id === owned && frame.sequence > lastPreviewSequence) {
          lastPreviewSequence = frame.sequence;
          if (preview.current) {
            preview.current.src = `data:image/jpeg;base64,${frame.jpeg}`;
            preview.current.hidden = false;
          }
        }
      } catch {
        // Status remains authoritative; a display-only IPC interruption must not stop capture.
        if (!disposed && !finished) clearPreview();
        delay = 200;
      }
      if (!disposed && !finished)
        previewTimer = setTimeout(
          () => void pollPreview(),
          Math.max(0, delay - (performance.now() - started)),
        );
    }
    async function update(next: LiveBiometricSession) {
      if (disposed) return;
      if (next.session_id !== owned)
        throw new Error('Biometric session changed. Retry with a new session.');
      setSession(next);
      if (terminal.has(next.state)) {
        finished = true;
        stopTimers();
        if (next.state === 'SUCCEEDED') {
          busy.current = true;
          setAction('COMPLETING');
          try {
            await callbacks.current.onComplete(next);
          } finally {
            if (!disposed) {
              busy.current = false;
              setAction(undefined);
            }
          }
          if (disposed) return;
          setSuccessPresented(true);
          if (!callbacks.current.onAcknowledged) return;
          // Authority has already been reflected in the parent. Delay only visual dismissal;
          // this callback can never publish authentication or submit an approval.
          acknowledging = true;
          const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
          const proceed = await new Promise<boolean>((resolve) => {
            resolveAcknowledgement = resolve;
            successTimer = setTimeout(
              () => {
                resolveAcknowledgement = undefined;
                resolve(true);
              },
              reduced ? 60 : successAcknowledgementMs,
            );
          });
          acknowledging = false;
          if (!proceed || disposed || document.hidden) return;
          callbacks.current.onAcknowledged?.();
        } else setError(next.reason || next.state);
      } else {
        // Supports recorded native-status fixtures; live frames use the independent preview path.
        if (next.preview && !lastPreviewSequence && preview.current) {
          preview.current.src = `data:image/jpeg;base64,${next.preview}`;
          preview.current.hidden = false;
        }
        statusTimer = setTimeout(() => void pollStatus(), 200);
      }
    }
    async function fail(e: unknown) {
      if (disposed) return;
      finished = true;
      stopTimers();
      await cancelNative();
      if (!disposed) setError(String(e));
    }
    async function pollStatus() {
      try {
        if (!disposed && owned) await update(await readBiometricSession(owned));
      } catch (e) {
        await fail(e);
      }
    }
    async function begin() {
      try {
        callbacks.current.onStarted?.();
        const next = await beginBiometricSession(JSON.parse(intentKey) as BiometricIntent);
        owned = next.session_id;
        if (disposed) {
          await cancelNative();
          return;
        }
        await update(next);
        if (!finished && !disposed) void pollPreview();
      } catch (e) {
        await fail(e);
      }
    }
    function hidden() {
      if (!document.hidden || disposed || (finished && !acknowledging)) return;
      void stop();
      // Authentication already completed; hiding cancels only its visual dismissal.
      if (finished) return;
      setSession(undefined);
      setError(
        'Session cancelled when the application became hidden. Keep ALICE open and retry when ready.',
      );
    }
    document.addEventListener('visibilitychange', hidden);
    queueMicrotask(() => {
      if (!disposed) void begin();
    });
    return () => {
      document.removeEventListener('visibilitychange', hidden);
      void stop();
    };
  }, [intentKey, attempt]);
  const reducedMotion = useReducedMotion();
  const enrollment = intent.purpose === 'ENROLLMENT';
  const covered = Object.values(session?.coverage ?? {}).filter((n) => n === 2).length;
  const accepted = Object.values(session?.coverage ?? {}).reduce((sum, n) => sum + (n ?? 0), 0);
  const complete = session?.state === 'SUCCEEDED' && successPresented && !error;
  const running = !!session && !terminal.has(session.state) && !error;
  const centerReady = (session?.coverage.CENTER ?? 0) === 2;
  const quality = qualityGuidance[session?.controls.quality?.reason ?? ''];
  const guidance = !session
    ? 'Starting your camera…'
    : session.state === 'EVALUATING'
      ? enrollment
        ? 'Saving your face…'
        : 'Recognizing your face…'
      : (quality ??
        (enrollment
          ? centerReady
            ? 'Slowly move your head in a circle'
            : 'Look straight ahead to begin'
          : 'Recognizing your face…'));
  const detail = quality
    ? enrollment
      ? 'Your progress is kept. Continue when your face is clear and visible.'
      : 'Keep your face visible. Verification continues automatically when the view is clear. No head turns needed.'
    : session?.controls.pose?.reason === 'FACE_POSE_INCONCLUSIVE'
      ? enrollment
        ? 'Use a smaller turn and keep your whole face visible in the camera view.'
        : 'Keep your whole face visible in the camera view. No head turns needed.'
      : enrollment
        ? centerReady
          ? 'Look gently up, down and to each side. Filled sections are already captured.'
          : 'Keep your head comfortably centered for a moment. Then you can look around in any order.'
        : 'Keep your face visible. No head turns needed.';
  return (
    <motion.section
      layout={!reducedMotion}
      transition={reducedMotion ? { duration: 0 } : motionTokens.panel}
      className={`biometric-session ${complete ? 'biometric-session-complete' : ''}`}
      aria-label="Automatic facial verification"
      aria-busy={!!action}
    >
      <motion.div
        layout={!reducedMotion}
        transition={reducedMotion ? { duration: 0 } : motionTokens.panel}
        className={`biometric-preview ${complete ? 'biometric-complete' : ''} ${error ? 'biometric-paused' : ''}`}
      >
        <div className="biometric-placeholder" aria-hidden="true">
          {!complete &&
            (error ? (
              <VideoOff size={36} strokeWidth={1.25} />
            ) : (
              <ScanFace size={52} strokeWidth={1} />
            ))}
        </div>
        <img
          ref={preview}
          hidden
          alt="Mirrored live camera preview"
          decoding="async"
          onLoad={(event) => {
            const image = event.currentTarget;
            if (!image.naturalWidth || !image.naturalHeight) return;
            const ratio = `${image.naturalWidth} / ${image.naturalHeight}`;
            if (previewRatio.current !== ratio) {
              previewRatio.current = ratio;
              image.parentElement?.style.setProperty('aspect-ratio', ratio);
            }
          }}
        />
        <BiometricScan
          enrollment={enrollment}
          coverage={session?.coverage}
          centerReady={centerReady}
          complete={complete}
          failed={!!error}
        />
        <BorderTrail
          active={
            !error &&
            !complete &&
            (!session || session.state === 'EVALUATING' || action === 'COMPLETING')
          }
        />
        {enrollment && !error && (
          <span className={`biometric-center-status ${centerReady ? 'center-ready' : ''}`}>
            {centerReady && <Check size={12} />}
            {centerReady ? 'Center captured' : 'Center your face'}
          </span>
        )}
        <span className="biometric-preview-badge">
          {complete
            ? 'Complete'
            : error
              ? errorTitle(error)
              : running
                ? enrollment
                  ? 'Continuous face scan'
                  : 'Live Face ID'
                : 'Connecting'}
        </span>
      </motion.div>
      {!error && (
        <p className="biometric-frame-guidance">
          Keep your whole head visible in the camera view.
          {enrollment && ' The ring shows scan progress.'}
        </p>
      )}
      <TransitionPanel
        stage={
          error ? 'FAILED' : complete ? 'COMPLETE' : `${session?.state ?? 'CREATED'}:${guidance}`
        }
        className="biometric-stage"
      >
        <div
          className="biometric-guidance"
          role={error ? 'alert' : 'status'}
          aria-live={error ? 'assertive' : 'polite'}
          aria-atomic="true"
        >
          <strong>
            {action === 'CANCELLING'
              ? 'Closing camera…'
              : error
                ? errorTitle(error)
                : complete
                  ? enrollment
                    ? 'Face saved'
                    : 'Face ID verified'
                  : guidance}
          </strong>
          <p>
            {error
              ? explainError(error)
              : complete
                ? enrollment
                  ? 'Your face is ready to use.'
                  : intent.purpose === 'LOGIN'
                    ? 'Opening your dashboard…'
                    : 'Continuing to your approval…'
                : detail}
          </p>
          {error && (
            <p className="biometric-error-reason">
              Reason: <code>{error}</code>
            </p>
          )}
        </div>
      </TransitionPanel>
      {enrollment && (
        <>
          <div
            className="biometric-progress"
            role="progressbar"
            aria-label="Face enrollment progress"
            aria-valuemin={0}
            aria-valuemax={14}
            aria-valuenow={accepted}
            aria-valuetext={`${covered} of 7 facial angles complete`}
          >
            <span style={{ width: `${(accepted / 14) * 100}%` }} />
          </div>
          <div className="biometric-coverage" aria-label="Accepted facial angle coverage">
            {Object.entries(angleLabels).map(([region, label]) => {
              const count = session?.coverage[region as keyof typeof angleLabels] ?? 0;
              return (
                <div
                  key={region}
                  className={count === 2 ? 'angle-complete' : count === 1 ? 'angle-partial' : ''}
                  aria-label={`${label}: ${count} of 2 samples accepted`}
                >
                  {count === 2 ? <Check size={14} /> : <span className="biometric-angle-dot" />}
                  <span>{label}</span>
                </div>
              );
            })}
          </div>
          <p className="biometric-progress-label">
            {covered} / 7 angles complete · {session?.accepted_samples ?? 0} accepted observations
          </p>
          <p className="biometric-direction-note">
            Left and right mean your own left and right. You can look around in either direction.
          </p>
        </>
      )}
      {!!session && Object.keys(session.controls).length > 0 && (
        <details className="biometric-check-details">
          <summary>Face ID checks</summary>
          <ul className="biometric-controls">
            {Object.entries(session.controls).map(([name, control]) => (
              <li key={name}>
                <span>{controlLabels[name] ?? name.replaceAll('_', ' ')}</span>
                <strong>{control!.result.replaceAll('_', ' ')}</strong>
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="biometric-policy">
        Keep ALICE in the foreground. Camera images stay on this device.
      </p>
      <div className="biometric-actions">
        {enrollment && /ACTIVATION[_ ]RECOVERY[_ ]REQUIRED/.test(error) && onRecovered && (
          <CommandButton
            type="button"
            className="primary-button"
            disabled={!!action}
            onClick={async () => {
              if (busy.current || intent.purpose !== 'ENROLLMENT') return;
              busy.current = true;
              setAction('RECOVERING');
              try {
                await recoverBiometricEnrollment(intent.technician_id);
                await onRecovered();
              } catch (e) {
                setError(String(e));
              } finally {
                busy.current = false;
                setAction(undefined);
              }
            }}
          >
            {action === 'RECOVERING' ? 'Recovering enrollment…' : 'Recover pending enrollment'}
          </CommandButton>
        )}
        {error && (
          <CommandButton
            type="button"
            className="primary-button"
            disabled={!!action}
            onClick={() => {
              if (busy.current) return;
              busy.current = true;
              setError('');
              setAttempt((v) => v + 1);
            }}
          >
            Retry with new session
          </CommandButton>
        )}
        <CommandButton
          type="button"
          className="text-button"
          disabled={!!action}
          onClick={async () => {
            if (busy.current) return;
            busy.current = true;
            setAction('CANCELLING');
            await stopCapture.current();
            callbacks.current.onCancel();
          }}
        >
          {action === 'CANCELLING' ? 'Closing…' : action === 'COMPLETING' ? 'Finishing…' : 'Cancel'}
        </CommandButton>
      </div>
    </motion.section>
  );
}
