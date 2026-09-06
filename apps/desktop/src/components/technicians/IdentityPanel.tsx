import { useEffect, useRef, useState } from 'react';
import { Modal, Badge } from '@alice/ui';
import { nativeCall, isNative } from '../../lib/native';
import { useConsole, type Technician } from '../../state/console';
import type { LiveBiometricSession } from '@alice/contracts';
import { CameraCapture } from '../biometrics/CameraCapture';
export function IdentityPanel({ onClose }: { onClose: () => void }) {
  const { technician, setTechnician, biometricMode, log } = useConsole();
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
      title="Technician identity"
      onClose={onClose}
      className={closing ? 'biometric-dialog-exit' : ''}
    >
      <div className="verification-intro">
        <Badge tone={biometricMode === 'mock' ? 'warning' : 'information'}>
          {biometricMode === 'mock' ? 'DEMONSTRATION SESSION' : 'LOCAL IDENTITY VERIFICATION'}
        </Badge>
        <h3>{technician ? 'Your console session' : 'Claim your identity'}</h3>
        <p>
          {technician
            ? `Signed in as ${technician.display_name}. Enter another username to switch accounts.`
            : biometricMode === 'mock'
              ? 'Open a simulated identity session to explore the console.'
              : 'Enter your username. Face ID checks your saved face automatically; no head turns needed.'}
        </p>
      </div>
      {biometricMode === 'mock' ? (
        <>
          <div className="identity-session">
            <strong>{technician?.display_name ?? 'No active session'}</strong>
            <p>This mock session is isolated from real enrollment and protected systems.</p>
          </div>
          <button
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
          </button>
        </>
      ) : stage === 'CLAIM' ? (
        <form
          className="stack-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (busy || !username.trim()) return;
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
            />
          </label>
          <button className="primary-button" disabled={busy || !username.trim()}>
            Continue to facial login
          </button>
        </form>
      ) : (
        <CameraCapture
          intent={{ purpose: 'LOGIN', username }}
          onComplete={login}
          onAcknowledged={acknowledge}
          onCancel={() => setStage('CLAIM')}
        />
      )}
      <p className="inline-error" role="alert">
        {error}
      </p>
      {technician && (
        <button className="text-button" disabled={busy} onClick={() => void logout()}>
          {busy ? 'Signing out…' : 'Sign out of console'}
        </button>
      )}
    </Modal>
  );
}
