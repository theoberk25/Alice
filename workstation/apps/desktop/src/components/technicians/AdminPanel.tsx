import { useState } from 'react';
import { ShieldCheck, Plus, ScanFace } from 'lucide-react';
import { Panel, Badge } from '@alice/ui';
import { nativeCall, isNative } from '../../lib/native';
import { useConsole, type Technician } from '../../state/console';
import { CameraCapture } from '../biometrics/CameraCapture';
export function AdminPanel() {
  const [authorized, setAuthorized] = useState(false),
    [username, setUsername] = useState(''),
    [password, setPassword] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [technicians, setTechnicians] = useState<Technician[]>([]),
    [enrolling, setEnrolling] = useState<Technician>(),
    [draft, setDraft] = useState({
      technician_id: '',
      username: '',
      display_name: '',
      role: 'Technician',
    });
  async function refresh() {
    const identities = await nativeCall<Technician[]>('list_technicians');
    setTechnicians(identities);
    const session = useConsole.getState();
    if (session.biometricMode === 'arcface' && session.technician) {
      const current = identities.find((t) => t.technician_id === session.technician?.technician_id);
      if (!current?.enabled || !current.enrolled) session.setTechnician(undefined);
    }
  }
  async function run(work: () => Promise<void>) {
    setBusy(true);
    setError('');
    try {
      await work();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel title="Identity administration" meta={<ShieldCheck size={17} />}>
      <div className="admin-content">
        {!authorized ? (
          <div className="admin-login">
            <Badge tone="information">ADMINISTRATOR ACCESS</Badge>
            <h2>Enroll the human at the boundary.</h2>
            <p>
              Local administration manages technician identities and face enrollments. Your
              bootstrap account is configured through the native environment.
            </p>
            <form
              className="stack-form"
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await nativeCall('admin_login', { username, password });
                  setPassword('');
                  await refresh();
                  setAuthorized(true);
                });
              }}
            >
              <label>
                Admin username
                <input
                  required
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>
              <label>
                Password
                <input
                  required
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button className="primary-button" disabled={busy || !isNative}>
                {busy ? 'Authenticating…' : 'Authenticate administrator'}
              </button>
            </form>
            {!isNative && (
              <p className="inline-notice">
                Admin authentication and enrollment require the native ALICE.app. Browser preview
                does not store credentials.
              </p>
            )}
          </div>
        ) : (
          <>
            <div className="admin-title">
              <h3>Enrolled technicians</h3>
              <button
                className="small-button"
                onClick={() =>
                  void run(async () => {
                    await nativeCall('admin_logout');
                    setAuthorized(false);
                  })
                }
              >
                Lock administration
              </button>
            </div>
            <div className="technician-list">
              {technicians.map((t) => (
                <div className="technician-row" key={t.technician_id}>
                  <div>
                    <strong>{t.display_name}</strong>
                    <small>
                      {t.username} · {t.role} · {t.technician_id}
                    </small>
                  </div>
                  <Badge tone={t.enabled ? 'healthy' : 'neutral'}>
                    {t.enabled ? 'ENABLED' : 'DISABLED'}
                  </Badge>
                  <Badge tone={t.enrolled ? 'healthy' : 'warning'}>
                    {t.enrolled ? 'ENROLLED' : 'NO FACE'}
                  </Badge>
                  <button className="small-button" onClick={() => setEnrolling(t)}>
                    <ScanFace size={14} /> {t.enrolled ? 'Re-enroll' : 'Enroll face'}
                  </button>
                  <button
                    className="small-button"
                    onClick={() => {
                      setDraft({
                        technician_id: t.technician_id,
                        username: t.username,
                        display_name: t.display_name,
                        role: t.role,
                      });
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="small-button"
                    onClick={() =>
                      void run(async () => {
                        await nativeCall('set_technician_enabled', {
                          technicianId: t.technician_id,
                          enabled: !t.enabled,
                        });
                        await refresh();
                      })
                    }
                  >
                    {t.enabled ? 'Disable' : 'Enable'}
                  </button>
                  {t.enrolled && (
                    <button
                      className="danger-button"
                      onClick={() =>
                        void run(async () => {
                          await nativeCall('remove_enrollment', { technicianId: t.technician_id });
                          await refresh();
                        })
                      }
                    >
                      Remove face
                    </button>
                  )}
                </div>
              ))}
            </div>
            {enrolling ? (
              <section className="enrollment-capture">
                <h3>Enroll {enrolling.display_name}</h3>
                <p>
                  Five live camera frames will be checked for a single, sufficiently clear face. Raw
                  images are not stored.
                </p>
                <CameraCapture
                  busy={busy}
                  count={5}
                  onCapture={(frames) =>
                    run(async () => {
                      await nativeCall('enroll_technician', {
                        technicianId: enrolling.technician_id,
                        frames,
                      });
                      const session = useConsole.getState();
                      if (session.technician?.technician_id === enrolling.technician_id)
                        session.setTechnician(undefined);
                      await refresh();
                      setEnrolling(undefined);
                    })
                  }
                />
                <button className="text-button" onClick={() => setEnrolling(undefined)}>
                  Cancel enrollment
                </button>
              </section>
            ) : (
              <form
                className="admin-create stack-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    const t = await nativeCall<Technician>('save_technician', {
                      technician: { ...draft, enabled: true, enrolled: false },
                    });
                    await refresh();
                    setEnrolling(t);
                  });
                }}
              >
                <h3>
                  <Plus size={16} /> Add or update technician
                </h3>
                <div className="form-grid">
                  {(['technician_id', 'username', 'display_name', 'role'] as const).map((key) => (
                    <label key={key}>
                      {key.replaceAll('_', ' ')}
                      <input
                        required
                        value={draft[key]}
                        onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                      />
                    </label>
                  ))}
                </div>
                <button className="primary-button" disabled={busy}>
                  Save identity & enroll face
                </button>
              </form>
            )}
          </>
        )}
        <p className="inline-error" role="alert">
          {error}
        </p>
      </div>
    </Panel>
  );
}
