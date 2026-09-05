import { useEffect, useState } from 'react';
import { Modal, Badge } from '@alice/ui';
import { nativeCall, isNative } from '../../lib/native';
import { useConsole, type Technician } from '../../state/console';
import { CameraCapture } from '../biometrics/CameraCapture';
export function IdentityPanel({ onClose }: { onClose: () => void }) {
  const { technician, setTechnician, biometricMode, log } = useConsole();
  const [username, setUsername] = useState(''),
    [stage, setStage] = useState<'CLAIM' | 'VERIFY'>('CLAIM'),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    setUsername(technician?.username ?? '');
  }, [technician]);
  async function login(frames: string[]) {
    setBusy(true);
    log('TECHNICIAN_LOGIN_ATTEMPT', 'Identity claimed; local face verification requested');
    try {
      const t = await nativeCall<Technician>('technician_login', { username, frames });
      setTechnician(t);
      log('TECHNICIAN_LOGIN_SUCCESS', `Technician ${t.technician_id} authenticated`);
      onClose();
    } catch (e) {
      setError(String(e));
      log('TECHNICIAN_LOGIN_FAILURE', 'Face login rejected');
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    if (isNative) await nativeCall('logout');
    setTechnician(undefined);
    setStage('CLAIM');
  }
  return (
    <Modal title="Technician identity" onClose={onClose}>
      <div className="verification-intro">
        <Badge tone={biometricMode === 'mock' ? 'warning' : 'information'}>
          {biometricMode === 'mock' ? 'DEMONSTRATION SESSION' : 'LOCAL IDENTITY VERIFICATION'}
        </Badge>
        <h3>{technician ? 'Your console session' : 'Claim your identity'}</h3>
        <p>
          Select your username before opening the camera. ALICE verifies that specific identity.
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
            onClick={async () => {
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
            }}
          >
            Enter simulated console
          </button>
        </>
      ) : stage === 'CLAIM' ? (
        <form
          className="stack-form"
          onSubmit={(e) => {
            e.preventDefault();
            setStage('VERIFY');
          }}
        >
          <label>
            Technician username
            <input
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </label>
          <button className="primary-button">Continue to facial login</button>
        </form>
      ) : (
        <CameraCapture busy={busy} onCapture={login} />
      )}
      <p className="inline-error" role="alert">
        {error}
      </p>
      {technician && (
        <button className="text-button" onClick={() => void logout()}>
          Sign out of console
        </button>
      )}
    </Modal>
  );
}
