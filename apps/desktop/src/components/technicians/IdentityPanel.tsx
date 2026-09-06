import { useEffect, useRef, useState } from 'react';
import { Modal, Badge, CommandButton, TransitionPanel } from '@alice/ui';
import { ScanFace, LogOut, UserRound } from 'lucide-react';
import { nativeCall, isNative } from '../../lib/native';
import { useConsole, type Technician } from '../../state/console';
import type { LiveBiometricSession } from '@alice/contracts';
import { CameraCapture } from '../biometrics/CameraCapture';
import { FaceIdMorph, useFaceIdMorph } from '../biometrics/FaceIdMorph';
export function IdentityPanel({ onClose }: { onClose: () => void }) {
  const { technician, setTechnician, biometricMode, log } = useConsole();
  const faceIdMorph = useFaceIdMorph();
  const [username, setUsername] = useState(''),
    [stage, setStage] = useState<'CLAIM' | 'VERIFY'>('CLAIM'),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [closing, setClosing] = useState(false);
  const operation = useRef(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    if (stage === 'CLAIM') setUsername(technician?.username ?? '');
  }, [technician, stage]);
  useEffect(() => {
    function hidden() {
      if (!document.hidden) return;
      clearTimeout(closeTimer.current);
      closeTimer.current = undefined;
      setClosing(false);
    }
    document.addEventListener('visibilitychange', hidden);
    return () => {
      clearTimeout(closeTimer.current);
      document.removeEventListener('visibilitychange', hidden);
    };
  }, []);
  function acknowledge() {
    if (closeTimer.current) return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      onClose();
      return;
    }
    setClosing(true);
    closeTimer.current = setTimeout(onClose, 120);
  }
  async function login(session: LiveBiometricSession) {
    log('TECHNICIAN_LOGIN_ATTEMPT', 'Identity claimed; local face verification requested');
    try {
      const t = session.technician;
      if (!t) throw new Error('Native login result is missing.');
      setTechnician(t);
      log('TECHNICIAN_LOGIN_SUCCESS', `Technician ${t.technician_id} authenticated`);
    } catch (e) {
      log('TECHNICIAN_LOGIN_FAILURE', 'Face login rejected');
      throw e;
    }
  }
  async function logout() {
    if (operation.current) return;
    operation.current = true;
    setBusy(true);
    setError('');
    clearTimeout(closeTimer.current);
    closeTimer.current = undefined;
    setClosing(false);
    // Unmount capture immediately, including any pending success acknowledgement.
    setStage('CLAIM');
    try {
      if (isNative) await nativeCall('logout');
      setTechnician(undefined);
      setStage('CLAIM');
    } catch (e) {
      setError(String(e));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }
  return (
    <Modal
      title={stage === 'VERIFY' ? 'Face ID' : 'Technician identity'}
      onClose={onClose}
      morphId="technician-identity"
      className={`identity-dialog ${stage === 'VERIFY' ? 'face-id-dialog' : ''} ${closing ? 'biometric-dialog-exit' : ''}`}
    >
      {stage === 'CLAIM' && (
        <div className="verification-intro identity-intro">
          <div className="identity-emblem" aria-hidden="true">
            <ScanFace size={26} strokeWidth={1.4} />
          </div>
          <Badge tone={biometricMode === 'mock' ? 'warning' : 'information'}>
            {biometricMode === 'mock' ? 'Demonstration session' : 'Local identity verification'}
          </Badge>
          <h3>{technician ? 'Your console session' : 'Claim your identity'}</h3>
          <p>
            {technician
              ? `Signed in as ${technician.display_name}. Sign out or change user to end this session.`
              : biometricMode === 'mock'
                ? 'Open a simulated identity session to explore the console.'
                : 'Enter your username. Face ID checks your saved face automatically; no head turns needed.'}
          </p>
        </div>
      )}
      {stage === 'VERIFY' && <FaceIdMorph source={faceIdMorph.source} />}
      {stage === 'VERIFY' && <p className="face-id-account">{username}</p>}
      <TransitionPanel
        stage={stage}
        className="identity-content"
        animateContent={false}
        animateSize={stage === 'VERIFY' && biometricMode !== 'mock'}
      >
        {technician && stage === 'CLAIM' ? (
          <CommandButton className="primary-button" disabled={busy} onClick={() => void logout()}>
            Change user
          </CommandButton>
        ) : biometricMode === 'mock' ? (
          <>
            <div className="identity-session">
              <UserRound size={18} aria-hidden="true" />
              <strong>{technician?.display_name ?? 'No active session'}</strong>
              <p>This mock session is isolated from real enrollment and protected systems.</p>
            </div>
            <CommandButton
              className="primary-button"
              disabled={busy}
              onClick={async () => {
                if (operation.current) return;
                operation.current = true;
                setBusy(true);
                setError('');
                try {
                  const t = isNative
                    ? await nativeCall<Technician>('demo_session')
                    : {
                        technician_id: 'TECH-DEMO',
                        username: 'alex.demo',
                        display_name: 'Alex Morgan',
                        role: 'Technician',
                        enabled: true,
                        enrolled: true,
                      };
                  setTechnician(t);
                  onClose();
                } catch (e) {
                  setError(String(e));
                } finally {
                  operation.current = false;
                  setBusy(false);
                }
              }}
            >
              {busy ? 'Signing in…' : 'Enter simulated console'}
            </CommandButton>
          </>
        ) : stage === 'CLAIM' ? (
          <form
            className="stack-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (busy || technician || !username.trim()) return;
              setUsername(username.trim());
              setError('');
              setStage('VERIFY');
            }}
          >
            <label>
              Technician username
              <input
                required
                maxLength={100}
                disabled={busy}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                placeholder="Enter your username"
                spellCheck={false}
                autoCapitalize="none"
              />
            </label>
            <CommandButton
              ref={faceIdMorph.trigger}
              className="primary-button"
              disabled={busy || !username.trim()}
            >
              <ScanFace size={17} aria-hidden="true" />
              Continue to facial login
            </CommandButton>
          </form>
        ) : (
          <CameraCapture
            intent={{ purpose: 'LOGIN', username }}
            onComplete={login}
            onAcknowledged={acknowledge}
            onCancel={() => {
              clearTimeout(closeTimer.current);
              closeTimer.current = undefined;
              setClosing(false);
              setStage('CLAIM');
            }}
          />
        )}
      </TransitionPanel>
      <p className="inline-error" role="alert">
        {error}
      </p>
      {technician && stage === 'CLAIM' && (
        <CommandButton
          className="text-button identity-signout"
          disabled={busy}
          onClick={() => void logout()}
        >
          <LogOut size={14} aria-hidden="true" />
          {busy ? 'Signing out…' : 'Sign out of console'}
        </CommandButton>
      )}
    </Modal>
  );
}
