import { useRef, useState } from 'react';
import { ShieldCheck, Plus, ScanFace } from 'lucide-react';
import { Panel, Badge, Modal, TransitionPanel } from '@alice/ui';
import { nativeCall, isNative } from '../../lib/native';
import { useConsole, type Technician } from '../../state/console';
import { CameraCapture } from '../biometrics/CameraCapture';
import { FaceIdMorph, useFaceIdMorph } from '../biometrics/FaceIdMorph';
export function AdminPanel() {
  const faceIdMorph = useFaceIdMorph();
  const [authorized, setAuthorized] = useState(false),
    [username, setUsername] = useState(''),
    [password, setPassword] = useState(''),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [busy, setBusy] = useState(false),
    [technicians, setTechnicians] = useState<Technician[]>([]),
    [enrolling, setEnrolling] = useState<Technician>(),
    [editingId, setEditingId] = useState<string>(),
    [draft, setDraft] = useState({
      technician_id: '',
      username: '',
      display_name: '',
      role: 'Technician',
    });
  const operation = useRef(false);
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
    if (operation.current) return;
    operation.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await work();
    } catch (e) {
      setError(String(e));
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }
  return (
    <Panel title="Identity administration" meta={<ShieldCheck size={17} />}>
      <div className="admin-content">
        {!authorized ? (
          <div className="admin-login">
            <Badge tone="information">ADMINISTRATOR ACCESS</Badge>
            <h2>Set up Face ID.</h2>
            <p>
              Sign in as an administrator to manage identities and enroll a face for each
              technician.
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
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    setEnrolling(undefined);
                    await nativeCall('admin_logout');
                    setAuthorized(false);
                  })
                }
              >
                Lock administration
              </button>
            </div>
            <p className="inline-notice" role="status">
              {notice}
            </p>
            <p className="inline-error" role="alert">
              {error}
            </p>
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
                    {t.enrollment_pending
                      ? 'PENDING ENROLLMENT'
                      : t.enrolled
                        ? (t.enrollment_version ?? 'ENROLLED')
                        : 'NO FACE'}
                  </Badge>
                  <div className="technician-actions">
                    <button
                      ref={faceIdMorph.trigger}
                      className="small-button"
                      disabled={busy || !!enrolling || !t.enabled}
                      onClick={() => {
                        setError('');
                        setEnrolling(t);
                      }}
                    >
                      <ScanFace size={14} />{' '}
                      {t.enrolled ? 'Begin re-enrollment' : 'Begin enrollment'}
                    </button>
                    <button
                      className="small-button"
                      disabled={busy || !!enrolling}
                      onClick={() => {
                        setError('');
                        setEditingId(t.technician_id);
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
                      disabled={busy || !!enrolling}
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
                    {(t.enrolled || t.enrollment_pending) && (
                      <button
                        className="danger-button"
                        disabled={busy}
                        onClick={() =>
                          void run(async () => {
                            await nativeCall('remove_enrollment', {
                              technicianId: t.technician_id,
                            });
                            if (enrolling?.technician_id === t.technician_id)
                              setEnrolling(undefined);
                            await refresh();
                            setNotice(
                              `${t.display_name}: ${t.enrolled ? 'Face removed' : 'Pending enrollment discarded'}. Identity details are retained.`,
                            );
                          })
                        }
                      >
                        {t.enrolled ? 'Remove face' : 'Discard pending enrollment'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {enrolling ? (
              <Modal
                title="Set up Face ID"
                className="face-id-dialog"
                onClose={() => setEnrolling(undefined)}
                closeDisabled={busy}
              >
                <FaceIdMorph source={faceIdMorph.source} />
                <p className="face-id-account">{enrolling.display_name}</p>
                <TransitionPanel stage="enrollment" animateContent={false} animateSize>
                  <CameraCapture
                    intent={{ purpose: 'ENROLLMENT', technician_id: enrolling.technician_id }}
                    onCancel={() => setEnrolling(undefined)}
                    onRecovered={async () => {
                      await refresh();
                      setEnrolling(undefined);
                    }}
                    onComplete={async () => {
                      setBusy(true);
                      try {
                        const session = useConsole.getState();
                        if (session.technician?.technician_id === enrolling.technician_id)
                          session.setTechnician(undefined);
                        await refresh();
                      } finally {
                        setBusy(false);
                      }
                    }}
                    onAcknowledged={() => {
                      setNotice(`${enrolling.display_name}: Face ID is ready.`);
                      setEnrolling(undefined);
                    }}
                  />
                </TransitionPanel>
              </Modal>
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
                    if (!editingId && t.enabled) setEnrolling(t);
                    setEditingId(undefined);
                    setDraft({
                      technician_id: '',
                      username: '',
                      display_name: '',
                      role: 'Technician',
                    });
                  });
                }}
              >
                <h3>
                  <Plus size={16} /> {editingId ? 'Edit technician' : 'Add technician'}
                </h3>
                <div className="form-grid">
                  {(['technician_id', 'username', 'display_name', 'role'] as const).map((key) => (
                    <label key={key}>
                      {key.replaceAll('_', ' ')}
                      <input
                        required
                        maxLength={100}
                        disabled={busy || (key === 'technician_id' && !!editingId)}
                        value={draft[key]}
                        onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                      />
                    </label>
                  ))}
                </div>
                <button className="primary-button" disabled={busy}>
                  {busy ? 'Saving…' : editingId ? 'Save identity' : 'Save identity & enroll face'}
                </button>
                {editingId && (
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy}
                    onClick={() => {
                      setEditingId(undefined);
                      setDraft({
                        technician_id: '',
                        username: '',
                        display_name: '',
                        role: 'Technician',
                      });
                    }}
                  >
                    Cancel editing
                  </button>
                )}
              </form>
            )}
          </>
        )}
        {!authorized && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </Panel>
  );
}
