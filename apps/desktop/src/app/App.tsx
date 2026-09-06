import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  ListFilter,
  FileClock,
  UsersRound,
  SlidersHorizontal,
  ShieldCheck,
  Search,
  Pause,
  X,
  Fingerprint,
  AlertTriangle,
  ChevronDown,
} from 'lucide-react';
import { Badge, Empty } from '@alice/ui';
import { canReview } from '@alice/domain';
import { useConsole } from '../state/console';
import { Header } from '../components/layout/Header';
import { AgentsPanel } from '../components/agents/AgentsPanel';
import { SystemPanel } from '../components/status/SystemPanel';
import { DecisionWorkspace } from '../components/decisions/DecisionWorkspace';
import { EvidencePanel } from '../components/evidence/EvidencePanel';
import { History, AuditLog } from '../components/audit/History';
import { CommandPanel } from '../components/command/CommandPanel';
import { ApprovalModal } from '../components/biometrics/ApprovalModal';
import { ResearchModal } from '../components/decisions/ResearchModal';
import { IdentityPanel } from '../components/technicians/IdentityPanel';
import { AdminPanel } from '../components/technicians/AdminPanel';
import { SettingsModal } from '../components/layout/SettingsModal';
import {
  RuntimeWorkspace,
  RuntimeEvidence,
  RuntimeSystem,
  RuntimeAgents,
  RuntimeHistory,
  RuntimeAudit,
} from '../components/runtime/RuntimePanels';
import { scenarioNames, type ScenarioName } from '../../../../fixtures/scenarios';
import { isNative } from '../lib/native';
type View = 'overview' | 'history' | 'audit' | 'admin';
type Overlay = 'approval' | 'research' | 'identity' | 'settings' | undefined;
export default function App() {
  const s = useConsole();
  const [view, setView] = useState<View>('overview'),
    [approvalId, setApprovalId] = useState<string>(),
    [overlay, setOverlay] = useState<Overlay>(),
    [developer, setDeveloper] = useState(false),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    void useConsole
      .getState()
      .start()
      .catch((e) => useConsole.getState().error(`Console startup failed: ${String(e)}`));
  }, []);
  const d = s.decisions[s.selectedId];
  const remote = s.mode === 'remote';
  const runtimeRequests = Object.values(s.runtime.requests);
  const locked = !s.technician && (s.biometricMode === 'arcface' || !s.ready);
  const available =
    !remote &&
    !!d &&
    !!s.technician &&
    s.latestDecisionByRequest[d.request.request_id] === d.decision_id &&
    canReview(s.flows[s.selectedId] ?? 'IDLE') &&
    d.decision.result === 'HOLD' &&
    d.policy.result !== 'DENY';
  const allowCount = remote
      ? runtimeRequests.filter((r) => r.decision?.detail.outcome === 'ALLOW').length
      : s.order.filter((id) => s.decisions[id]?.decision.result === 'ALLOW').length,
    holdCount = remote
      ? runtimeRequests.filter((r) => r.decision?.detail.outcome === 'CHALLENGE').length
      : s.order.filter((id) => s.decisions[id]?.decision.result === 'HOLD').length,
    denyCount = remote
      ? runtimeRequests.filter((r) =>
          ['DENY', 'REJECTED'].includes(r.decision?.detail.outcome ?? ''),
        ).length
      : s.order.filter((id) => s.decisions[id]?.decision.result === 'DENY').length;
  async function act(action: 'HOLD' | 'RESEARCH' | 'REJECT') {
    setBusy(true);
    try {
      await s.act(action);
      if (action === 'RESEARCH') setOverlay('research');
    } catch (e) {
      s.error(String(e));
    } finally {
      setBusy(false);
    }
  }
  function approve() {
    if (!d) return;
    setApprovalId(d.decision_id);
    s.advance('APPROVE');
    if (d.decision.biometric_required_for_approval) s.advance('REQUIRE_BIOMETRIC');
    setOverlay('approval');
  }
  return (
    <div className="alice-app">
      <Header onIdentity={() => setOverlay('identity')} onSettings={() => setOverlay('settings')} />
      <nav className="main-nav" aria-label="Console navigation">
        <div className="nav-tabs">
          {(
            [
              { id: 'overview', label: 'Operations', icon: LayoutDashboard },
              { id: 'history', label: 'Decision history', icon: ListFilter },
              { id: 'audit', label: 'Audit trail', icon: FileClock },
              { id: 'admin', label: 'Administration', icon: UsersRound },
            ] as const
          ).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={view === id ? 'active' : ''}
              onClick={() => setView(id)}
              disabled={locked && id !== 'admin'}
            >
              <Icon size={15} />
              {label}
              {id === 'history' && !locked && (
                <span>{remote ? runtimeRequests.length : s.order.length}</span>
              )}
            </button>
          ))}
        </div>
        <div className="nav-status">
          {s.mode === 'mock' && (
            <Badge tone="warning" dot={false}>
              SIMULATION
            </Badge>
          )}
          <span>
            <span className="mini-pulse" />
            {remote
              ? `FEED ${s.feed.state.toUpperCase()}`
              : s.ready
                ? 'CONSOLE ACTIVE'
                : 'INITIALIZING'}
          </span>
          {import.meta.env.DEV && (
            <button
              className="icon-button"
              aria-label="Development scenarios"
              onClick={() => setDeveloper(!developer)}
            >
              <SlidersHorizontal size={15} />
            </button>
          )}
        </div>
      </nav>
      {developer && !remote && !locked && import.meta.env.DEV && (
        <div className="dev-panel">
          <label>
            DEVELOPMENT SCENARIO{' '}
            <select
              value={s.scenario}
              onChange={(e) =>
                void s.start(e.target.value as ScenarioName).catch((err) => s.error(String(err)))
              }
            >
              {scenarioNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="small-button"
            onClick={() => void s.start(s.scenario).catch((err) => s.error(String(err)))}
          >
            Reset scenario
          </button>
          <span>Deterministic fixtures · no protected system execution</span>
        </div>
      )}
      {s.errors.length > 0 && (
        <div className="error-banner" role="alert">
          <AlertTriangle size={16} />
          <div>
            {s.errors.map((error, i) => (
              <p key={i}>{error}</p>
            ))}
          </div>
          <button className="icon-button" aria-label="Dismiss errors" onClick={s.dismissError}>
            <X size={16} />
          </button>
        </div>
      )}
      {locked && view !== 'admin' && (
        <div className="login-gate">
          <ShieldCheck size={42} />
          <h1>Technician identity required</h1>
          <p>
            Sign in with your username and local facial verification, or open Administration to
            enroll.
          </p>
          <button className="primary-button" onClick={() => setOverlay('identity')}>
            Technician sign in
          </button>
        </div>
      )}
      {(!locked || view === 'admin') &&
        (view === 'overview' ? (
          <main className="dashboard">
            <aside className="left-column">
              <div className="section-kicker">
                01 <span>OPERATIONS NETWORK</span>
              </div>
              {remote ? <RuntimeAgents /> : <AgentsPanel />}
              {remote ? <RuntimeHistory /> : <History />}
              <div className="mission-card">
                <span className="eyebrow">CURRENT MISSION</span>
                <h3>
                  {remote ? 'Mission unavailable' : (d?.request.mission_id ?? 'No active mission')}
                </h3>
                <p>
                  {remote
                    ? 'Mission metadata is not supplied by the runtime feed'
                    : (d?.request.mission_type.replaceAll('_', ' ') ?? 'Awaiting an ALICE event')}
                </p>
                <div>
                  <ShieldCheck size={14} />{' '}
                  {remote ? 'Target unavailable' : (d?.request.target ?? 'No target')}{' '}
                  <span>PROTECTED ASSET</span>
                </div>
              </div>
            </aside>
            <section className="center-column">
              <div className="workspace-title">
                <div className="section-kicker">
                  02 <span>DECISION WORKSPACE</span>
                </div>
                <div className="decision-counts">
                  <span className="tone-healthy">{allowCount} ALLOWED</span>
                  <i />
                  <span className="tone-warning">{holdCount} HELD</span>
                  <i />
                  <span className="tone-danger">{denyCount} DENIED</span>
                </div>
              </div>
              {remote ? (
                <RuntimeWorkspace />
              ) : d ? (
                <DecisionWorkspace decision={d} onResearch={() => setOverlay('research')} />
              ) : (
                <Empty>
                  {s.mode === 'remote'
                    ? 'Awaiting an authenticated connection to the ALICE edge node.'
                    : 'Loading decision fixtures…'}
                </Empty>
              )}
              {!remote && <CommandPanel />}
            </section>
            <aside className="right-column">
              <div className="section-kicker">
                03 <span>TRUST & VERIFICATION</span>
              </div>
              {remote ? <RuntimeSystem /> : <SystemPanel />}
              {remote ? (
                <RuntimeEvidence />
              ) : (
                d && <EvidencePanel decision={d} onResearch={() => setOverlay('research')} />
              )}
            </aside>
          </main>
        ) : (
          <main className="secondary-view">
            {view === 'history' ? (
              <>
                {remote ? <RuntimeHistory /> : <History expanded />}
                {remote ? (
                  <RuntimeWorkspace />
                ) : (
                  d && <DecisionWorkspace decision={d} onResearch={() => setOverlay('research')} />
                )}
              </>
            ) : view === 'audit' ? (
              remote ? (
                <RuntimeAudit />
              ) : (
                <AuditLog />
              )
            ) : (
              <AdminPanel />
            )}
          </main>
        ))}
      {!locked && (
        <footer className="action-bar">
          <div className="action-bar-status">
            <span
              className={`bar-status-icon ${d?.decision.result === 'HOLD' ? 'tone-warning' : 'tone-healthy'}`}
            >
              <ShieldCheck size={21} />
            </span>
            <div>
              <strong>
                {remote
                  ? isNative
                    ? 'Live runtime · review eligible HOLDs in the decision workspace'
                    : 'Read-only runtime feed · native review required'
                  : s.actions[s.selectedId]?.action === 'APPROVE_ONCE'
                    ? 'Approval submitted · awaiting upstream'
                    : d?.decision.result === 'HOLD'
                      ? 'Action secured at the local boundary'
                      : d
                        ? `Upstream result: ${d.decision.result}`
                        : 'Awaiting ALICE node'}
              </strong>
              <span>
                {d?.decision.biometric_required_for_approval
                  ? 'Fresh identity verification required for approval'
                  : 'Technician actions scoped to the selected request'}
              </span>
            </div>
          </div>
          <div className="action-buttons">
            <button
              className="reject-button"
              disabled={!available || busy || !d?.technician_actions.available.includes('REJECT')}
              onClick={() => void act('REJECT')}
            >
              <X size={16} /> Reject
            </button>
            <button
              disabled={!available || busy || !d?.technician_actions.available.includes('RESEARCH')}
              onClick={() => void act('RESEARCH')}
            >
              <Search size={16} /> Research
            </button>
            <button
              disabled={!available || busy || !d?.technician_actions.available.includes('HOLD')}
              onClick={() => void act('HOLD')}
            >
              <Pause size={15} /> Hold
            </button>
            <button
              className="approve-button"
              disabled={!available || busy || !d?.technician_actions.available.includes('APPROVE')}
              onClick={approve}
            >
              <Fingerprint size={18} /> Approve once <ChevronDown size={13} />
            </button>
          </div>
        </footer>
      )}
      {!locked && overlay === 'approval' && approvalId && (
        <ApprovalModal
          key={approvalId}
          decisionId={approvalId}
          onClose={() => setOverlay(undefined)}
        />
      )}{' '}
      {!locked && overlay === 'research' && d && (
        <ResearchModal onClose={() => setOverlay(undefined)} />
      )}{' '}
      {overlay === 'identity' && <IdentityPanel onClose={() => setOverlay(undefined)} />}{' '}
      {overlay === 'settings' && <SettingsModal onClose={() => setOverlay(undefined)} />}
    </div>
  );
}
