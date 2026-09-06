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
  MessageSquareText,
} from 'lucide-react';
import {
  Badge,
  Empty,
  AnimatedSelection,
  AnimatedCounter,
  CommandButton,
  Tooltip,
  motionTokens,
} from '@alice/ui';
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from 'motion/react';
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
  const reducedMotion = useReducedMotion();
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
  const canRequestContext =
    available &&
    !!d &&
    d.context_challenge.required &&
    !s.responses[d.decision_id] &&
    !s.contextRequests[d.decision_id];
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
  async function requestContext() {
    if (!d) return;
    setBusy(true);
    try {
      await s.requestContext(d.decision_id);
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
        <LayoutGroup id="console-navigation">
          <div className="nav-tabs">
            {(
              [
                { id: 'overview', label: 'Operations', icon: LayoutDashboard },
                { id: 'history', label: 'Decision history', icon: ListFilter },
                { id: 'audit', label: 'Audit trail', icon: FileClock },
                { id: 'admin', label: 'Administration', icon: UsersRound },
              ] as const
            ).map(({ id, label, icon: Icon }) => (
              <CommandButton
                key={id}
                className={view === id ? 'active' : ''}
                aria-label={label}
                aria-current={view === id ? 'page' : undefined}
                onClick={() => setView(id)}
                disabled={locked && id !== 'admin'}
              >
                <AnimatedSelection
                  active={view === id}
                  layoutId="nav-active"
                  className="nav-active-surface"
                />
                <Icon size={15} />
                <span className="nav-label">{label}</span>
                {id === 'history' && !locked && (
                  <span className="nav-count">
                    <AnimatedCounter value={remote ? runtimeRequests.length : s.order.length} />
                  </span>
                )}
              </CommandButton>
            ))}
          </div>
        </LayoutGroup>
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
            <Tooltip content="Development scenarios">
              <CommandButton
                className="icon-button"
                aria-label="Development scenarios"
                onClick={() => setDeveloper(!developer)}
              >
                <SlidersHorizontal size={15} />
              </CommandButton>
            </Tooltip>
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
          <CommandButton
            className="small-button"
            onClick={() => void s.start(s.scenario).catch((err) => s.error(String(err)))}
          >
            Reset scenario
          </CommandButton>
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
          <CommandButton
            className="icon-button"
            aria-label="Dismiss errors"
            onClick={s.dismissError}
          >
            <X size={16} />
          </CommandButton>
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
          <CommandButton
            className="primary-button"
            data-morph-id="technician-identity"
            onClick={() => setOverlay('identity')}
          >
            Technician sign in
          </CommandButton>
        </div>
      )}
      <AnimatePresence initial={false}>
        <motion.div key={view} className="page-surface" initial={false}>
          {(!locked || view === 'admin') &&
            (view === 'overview' ? (
              <main className="dashboard">
                <aside className="left-column">
                  <div className="section-kicker">
                    <span>Operations network</span>
                  </div>
                  {remote ? <RuntimeAgents /> : <AgentsPanel />}
                  {remote ? <RuntimeHistory /> : <History />}
                  <div className="mission-card">
                    <span className="eyebrow">Current mission</span>
                    <h3>
                      {remote
                        ? 'Mission unavailable'
                        : (d?.request.mission_id ?? 'No active mission')}
                    </h3>
                    <p>
                      {remote
                        ? 'Mission metadata is not supplied by the runtime feed'
                        : (d?.request.mission_type.replaceAll('_', ' ') ??
                          'Awaiting an ALICE event')}
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
                      <span>Decision workspace</span>
                    </div>
                    <div className="decision-counts">
                      <span className="tone-healthy">
                        <AnimatedCounter value={allowCount} /> <span>Allowed</span>
                      </span>
                      <i />
                      <span className="tone-warning">
                        <AnimatedCounter value={holdCount} /> <span>Held</span>
                      </span>
                      <i />
                      <span className="tone-danger">
                        <AnimatedCounter value={denyCount} /> <span>Denied</span>
                      </span>
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
                    <span>Trust & verification</span>
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
              <main className={`secondary-view view-${view}`}>
                {view === 'history' ? (
                  <>
                    {remote ? <RuntimeHistory /> : <History expanded />}
                    {remote ? (
                      <RuntimeWorkspace />
                    ) : (
                      d && (
                        <DecisionWorkspace decision={d} onResearch={() => setOverlay('research')} />
                      )
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
        </motion.div>
      </AnimatePresence>
      {!locked && (
        <motion.footer
          className="action-bar"
          initial={reducedMotion ? false : { opacity: 0.85, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={motionTokens.panel}
        >
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
            <CommandButton
              className="reject-button"
              disabled={!available || busy || !d?.technician_actions.available.includes('REJECT')}
              onClick={() => void act('REJECT')}
            >
              <X size={16} /> Reject
            </CommandButton>
            <CommandButton
              disabled={!available || busy || !d?.technician_actions.available.includes('RESEARCH')}
              onClick={() => void act('RESEARCH')}
            >
              <Search size={16} /> Research
            </CommandButton>
            <CommandButton
              className="context-button"
              disabled={!canRequestContext || busy}
              onClick={() => void requestContext()}
            >
              <MessageSquareText size={16} /> Request more context
            </CommandButton>
            <CommandButton
              disabled={!available || busy || !d?.technician_actions.available.includes('HOLD')}
              onClick={() => void act('HOLD')}
            >
              <Pause size={15} /> Hold
            </CommandButton>
            <CommandButton
              className="approve-button"
              data-morph-id="approval"
              disabled={!available || busy || !d?.technician_actions.available.includes('APPROVE')}
              onClick={approve}
            >
              <Fingerprint size={18} /> Approve once <ChevronDown size={13} />
            </CommandButton>
          </div>
        </motion.footer>
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
