import { useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { nativeCall, isNative } from '../../lib/native';
import {
  ShieldCheck,
  Radio,
  WifiOff,
  UserRound,
  Settings2,
  LogOut,
  UsersRound,
  ChevronDown,
} from 'lucide-react';
import { Badge, CommandButton, Tooltip } from '@alice/ui';
import { useConsole } from '../../state/console';
import { useDashboardClock } from './dashboard-clock';
export function Header({
  onIdentity,
  onSettings,
}: {
  onIdentity: () => void;
  onSettings: () => void;
}) {
  const { status, mode, biometricMode, technician, llm, runtime, feed } = useConsole();
  const clock = useDashboardClock();
  const [signingOut, setSigningOut] = useState(false);
  const operation = useRef(false);
  const accountMenu = useRef<HTMLDetailsElement>(null);
  const signInButton = useRef<HTMLButtonElement>(null);
  async function endSession(changeUser: boolean) {
    if (operation.current) return;
    operation.current = true;
    setSigningOut(true);
    try {
      if (isNative) await nativeCall('logout');
      // Commit the replacement trigger before opening its native dialog so Escape
      // restores focus to Sign in after the old account menu unmounts.
      flushSync(() => useConsole.getState().setTechnician(undefined));
      signInButton.current?.focus();
      if (accountMenu.current) accountMenu.current.open = false;
      if (changeUser) onIdentity();
    } catch (error) {
      useConsole.getState().error(`Unable to sign out: ${String(error)}`);
    } finally {
      operation.current = false;
      setSigningOut(false);
    }
  }
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-symbol">
          <ShieldCheck size={29} strokeWidth={1.25} />
        </div>
        <div>
          <div className="brand-name">
            ALICE
            <span className="brand-divider" /> <span>Technician console</span>
          </div>
          <p>Authenticated local identity & cyber enforcement</p>
          {mode === 'mock' && <span className="mobile-simulation">SIMULATION</span>}
        </div>
      </div>
      <div className="topbar-node">
        <span className="eyebrow">Enforcement node</span>
        <strong>
          <Radio size={12} />
          {mode === 'remote'
            ? (runtime.events.at(-1)?.node_id ?? 'AWAITING NODE')
            : (status?.node ?? 'AWAITING NODE')}
        </strong>
      </div>
      <div className="topbar-network">
        <Badge tone={!status ? 'neutral' : status.mode === 'DDIL' ? 'warning' : 'healthy'}>
          {mode === 'remote' ? `FEED ${feed.state.toUpperCase()}` : (status?.mode ?? 'UNKNOWN')}
        </Badge>
        <span className="topbar-cloud">
          {status?.connections.cloud ? <Radio size={12} /> : <WifiOff size={12} />} CLOUD{' '}
          {!status ? 'UNKNOWN' : status.connections.cloud ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>
      <div
        className="clock"
        role="timer"
        aria-label={`Device time: ${clock.time}, ${clock.date}, ${clock.zoneLabel} (${clock.timeZone})`}
        title={`Device time zone: ${clock.timeZone}`}
      >
        <strong>{clock.time}</strong>
        <span>
          {clock.zoneLabel} / {clock.date}
        </span>
      </div>
      {technician ? (
        <details
          className="account-menu"
          ref={accountMenu}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.currentTarget.open = false;
              event.currentTarget.querySelector('summary')?.focus();
            }
          }}
        >
          <summary className="identity-button" aria-label={`Account: ${technician.display_name}`}>
            <span className="avatar">
              <UserRound size={17} />
            </span>
            <span>
              <strong>{technician.display_name}</strong>
              <small>{technician.role}</small>
            </span>
            <ChevronDown size={13} aria-hidden="true" />
          </summary>
          <div className="account-menu-actions">
            <button type="button" disabled={signingOut} onClick={() => void endSession(true)}>
              <UsersRound size={15} aria-hidden="true" /> Change user
            </button>
            <button type="button" disabled={signingOut} onClick={() => void endSession(false)}>
              <LogOut size={15} aria-hidden="true" /> {signingOut ? 'Signing out…' : 'Sign out'}
            </button>
          </div>
        </details>
      ) : (
        <CommandButton
          ref={signInButton}
          data-morph-id="technician-identity"
          className="identity-button"
          onClick={onIdentity}
        >
          <span className="avatar">
            <UserRound size={17} />
          </span>
          <span>
            <strong>Sign in</strong>
            <small>
              {mode === 'remote' && biometricMode === 'mock'
                ? 'READ-ONLY PREVIEW'
                : biometricMode === 'mock'
                  ? 'SIMULATED SESSION'
                  : 'IDENTITY REQUIRED'}
            </small>
          </span>
        </CommandButton>
      )}
      <Tooltip align="end" content={`Connection settings · Local gateway: ${llm.status}`}>
        <CommandButton
          className="icon-button"
          aria-label="Connection settings"
          onClick={onSettings}
        >
          <Settings2 size={18} />
        </CommandButton>
      </Tooltip>
    </header>
  );
}
