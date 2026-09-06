import { useEffect, useState } from 'react';
import { ShieldCheck, Radio, WifiOff, UserRound, Settings2 } from 'lucide-react';
import { Badge } from '@alice/ui';
import { useConsole } from '../../state/console';
export function Header({
  onIdentity,
  onSettings,
}: {
  onIdentity: () => void;
  onSettings: () => void;
}) {
  const { status, mode, biometricMode, technician, llm, runtime, feed } = useConsole();
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-symbol">
          <ShieldCheck size={29} strokeWidth={1.25} />
        </div>
        <div>
          <div className="brand-name">
            ALICE
            <span className="brand-divider" /> <span>TECHNICIAN CONSOLE</span>
          </div>
          <p>AUTHENTICATED LOCAL IDENTITY & CYBER ENFORCEMENT</p>
          {mode === 'mock' && <span className="mobile-simulation">SIMULATION</span>}
        </div>
      </div>
      <div className="topbar-node">
        <span className="eyebrow">ENFORCEMENT NODE</span>
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
      <div className="clock">
        <strong>{now.toLocaleTimeString('en-GB', { timeZone: 'UTC' })}</strong>
        <span>
          UTC /{' '}
          {now
            .toLocaleDateString('en-US', { month: 'short', day: '2-digit', timeZone: 'UTC' })
            .toUpperCase()}
        </span>
      </div>
      <button className="identity-button" onClick={onIdentity}>
        <span className="avatar">
          <UserRound size={17} />
        </span>
        <span>
          <strong>{technician?.display_name ?? 'Sign in'}</strong>
          <small>
            {mode === 'remote' && biometricMode === 'mock'
              ? 'READ-ONLY PREVIEW'
              : biometricMode === 'mock'
                ? 'SIMULATED SESSION'
                : (technician?.role ?? 'IDENTITY REQUIRED')}
          </small>
        </span>
      </button>
      <button
        className="icon-button"
        title={`Local gateway: ${llm.status}`}
        aria-label="Connection settings"
        onClick={onSettings}
      >
        <Settings2 size={18} />
      </button>
    </header>
  );
}
