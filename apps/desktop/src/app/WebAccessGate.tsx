import { type FormEvent, type PropsWithChildren, useEffect, useState } from 'react';
import { isNative } from '../lib/native';

export function WebAccessGate({ children }: PropsWithChildren) {
  const enabled = !isNative && import.meta.env.VITE_ALICE_WEB_LOGIN === 'enabled';
  const [authenticated, setAuthenticated] = useState<boolean | null>(enabled ? null : true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    fetch('/api/alice/session', { cache: 'no-store' })
      .then((response) => response.json())
      .then((body) => setAuthenticated(body.authenticated === true))
      .catch(() => setAuthenticated(false));
  }, [enabled]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const data = new FormData(event.currentTarget);
    try {
      const response = await fetch('/api/alice/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: data.get('username'), password: data.get('password') }),
      });
      if (!response.ok) throw new Error((await response.json()).error ?? 'Login failed');
      setAuthenticated(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      await fetch('/api/alice/logout', { method: 'POST' });
    } finally {
      setAuthenticated(false);
      setBusy(false);
    }
  }

  if (!enabled) return children;
  if (authenticated === null)
    return (
      <main className="web-login">
        <p>Checking technician dashboard access…</p>
      </main>
    );
  if (!authenticated)
    return (
      <main className="web-login">
        <form onSubmit={login}>
          <span className="eyebrow">ALICE LOCAL NETWORK</span>
          <h1>Technician dashboard</h1>
          <p>Sign in to view the Pi’s live, read-only decision stream.</p>
          <label>
            Username
            <input name="username" autoComplete="username" required />
          </label>
          <label>
            Password
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          {error && (
            <p role="alert" className="tone-danger">
              {error}
            </p>
          )}
          <button className="primary-button" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </main>
    );
  return (
    <>
      <button className="web-logout" onClick={logout} disabled={busy}>
        Log out
      </button>
      {children}
    </>
  );
}
