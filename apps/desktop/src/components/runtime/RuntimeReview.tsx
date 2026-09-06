import { useEffect, useRef, useState } from 'react';
import { Modal, Badge } from '@alice/ui';
import { matchesRuntimeRequest, runtimeReviewBinding } from '@alice/domain';
import type {
  RuntimeReview,
  RuntimeReviewAction,
  LiveBiometricSession,
  RuntimeReviewStatus,
} from '@alice/contracts';
import { runtimeReviewer } from '../../features/biometrics/runtime-review';
import { CameraCapture } from '../biometrics/CameraCapture';
import { useConsole } from '../../state/console';
import { useRuntimeReview } from '../../state/runtime-review';

const snapshotLifetimeMs = 55_000;
const reasons: Record<string, string> = {
  READY: 'Ready for a fresh facial verification.',
  CONSOLE_TRUST_NOT_CONFIGURED:
    'The Pi has no console review trust configured. A separate trust setup is required.',
  AUTHORITY_NOT_LOCAL:
    'Execution belongs to enterprise or local authority is unconfirmed. Local approval is unavailable.',
  REQUEST_DETAILS_UNAVAILABLE:
    'The Pi does not retain the exact signed request details for this historical record.',
  MACHINE_DECISION_NOT_REVIEWABLE:
    'The original machine decision does not permit technician review.',
  REVIEW_ALREADY_RESOLVED: 'The Pi has already recorded a technician response.',
  REVIEW_HISTORY_CONFLICT:
    'The Pi reports conflicting review history. Review remains blocked until the authoritative records are reconciled.',
  POLICY_OR_AUTHORITY_CHANGED:
    'Policy or execution authority changed since this decision. A new assessment is required.',
};
function explain(error: unknown): string {
  const text = String(error);
  if (/CONSOLE.*(CONFIGURED|KEY|PRIVATE)|REVIEW_KEY/.test(text))
    return `Native review setup is incomplete. Configure the local console key and the Pi's scoped trust before reviewing. ${text}`;
  return text;
}
type Attempt = {
  snapshot: RuntimeReview;
  action: RuntimeReviewAction;
  technicianId: string;
  expiresAt: number;
};

export function RuntimeReviewPanel() {
  const { selectedRuntimeId, runtime, feed, technician } = useConsole();
  const submission = useRuntimeReview((s) => s.submissions[selectedRuntimeId]);
  const sending = useRuntimeReview((s) => !!s.sending[selectedRuntimeId]);
  const [snapshot, setSnapshot] = useState<RuntimeReview>();
  const [setup, setSetup] = useState<RuntimeReviewStatus>();
  const [expiresAt, setExpiresAt] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [attempt, setAttempt] = useState<Attempt>();
  const [acknowledged, setAcknowledged] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [now, setNow] = useState(Date.now());
  const mounted = useRef(false);
  const selected = runtime.requests[selectedRuntimeId];
  const lastEvent = selected?.events.at(-1)?.event_id;
  const authority = runtime.events.at(-1)?.authority;
  const authorityBinding = JSON.stringify(authority);
  const resolved = selected?.events.some((e) => e.event_type === 'TECHNICIAN_ACTION');
  useEffect(() => {
    mounted.current = true;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    let cancelled = false;
    if (!runtimeReviewer.available || !technician || !selectedRuntimeId || feed.state !== 'live') {
      setLoading(false);
      return;
    }
    setLoading(true);
    // Refreshes can race technician-action events and HTTP acknowledgment. They never
    // reset an attempt/submission; native and local records retain its exact action ID.
    void Promise.all([
      runtimeReviewer.read(selectedRuntimeId),
      runtimeReviewer.readSubmission(selectedRuntimeId),
      runtimeReviewer.status(),
    ])
      .then(([value, saved, status]) => {
        if (cancelled) return;
        setSnapshot(value);
        setSetup(status);
        setExpiresAt(Date.now() + snapshotLifetimeMs);
        setError('');
        useRuntimeReview.getState().remember(saved, selectedRuntimeId);
      })
      .catch((e) => {
        if (!cancelled) {
          setExpiresAt(0);
          setError(explain(e));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [
    selectedRuntimeId,
    lastEvent,
    technician?.technician_id,
    feed.state,
    authorityBinding,
    revision,
  ]);

  const eligible =
    !!snapshot?.eligible &&
    !!setup?.ready &&
    !resolved &&
    feed.state === 'live' &&
    !!technician?.enabled &&
    matchesRuntimeRequest(snapshot, selected) &&
    now < expiresAt &&
    authority?.product_mode === 'OFFLINE' &&
    authority.execution_owner === 'ALICE' &&
    authority.confirmation === 'CONFIRMED' &&
    authority.authority_interval_ref === snapshot.authority_interval_ref;
  const attemptCurrent =
    !!attempt &&
    eligible &&
    technician?.technician_id === attempt.technicianId &&
    Date.now() < attempt.expiresAt &&
    !!snapshot &&
    runtimeReviewBinding(snapshot) === runtimeReviewBinding(attempt.snapshot);
  // Read from this ref in camera completion so a queued success can never use an
  // earlier render after logout, changed authority, cancellation or feed loss.
  const latest = useRef({ attempt, attemptCurrent });
  latest.current = { attempt, attemptCurrent };
  function cancel() {
    latest.current = { attempt: undefined, attemptCurrent: false };
    setAttempt(undefined);
    setAcknowledged(false);
  }
  async function complete(session: LiveBiometricSession, expectedAttempt: Attempt) {
    const current = latest.current;
    const consoleState = useConsole.getState();
    const latestAuthority = consoleState.runtime.events.at(-1)?.authority;
    const verification = session.verification;
    if (
      !mounted.current ||
      !current.attemptCurrent ||
      !current.attempt ||
      current.attempt !== expectedAttempt ||
      !verification ||
      Date.now() >= current.attempt.expiresAt ||
      consoleState.feed.state !== 'live' ||
      consoleState.technician?.technician_id !== current.attempt.technicianId ||
      !consoleState.technician.enabled ||
      consoleState.selectedRuntimeId !== current.attempt.snapshot.request_id ||
      !matchesRuntimeRequest(
        current.attempt.snapshot,
        consoleState.runtime.requests[consoleState.selectedRuntimeId],
      ) ||
      latestAuthority?.product_mode !== 'OFFLINE' ||
      latestAuthority.execution_owner !== 'ALICE' ||
      latestAuthority.confirmation !== 'CONFIRMED' ||
      latestAuthority.authority_interval_ref !== current.attempt.snapshot.authority_interval_ref ||
      session.purpose !== 'APPROVAL' ||
      session.state !== 'SUCCEEDED' ||
      verification.result !== 'PASS' ||
      verification.provider !== 'arcface' ||
      verification.technician_id !== current.attempt.technicianId ||
      verification.request_id !== current.attempt.snapshot.request_id ||
      verification.decision_id !== current.attempt.snapshot.decision_event_id ||
      Date.parse(verification.expires_at) <= Date.now() ||
      document.hidden
    )
      throw new Error('Fresh face verification no longer matches this current request.');
    try {
      await useRuntimeReview
        .getState()
        .submit(
          current.attempt.snapshot.request_id,
          current.attempt.action,
          verification.verification_id,
        );
    } catch (e) {
      if (mounted.current) setError(explain(e));
      // The submission panel owns uncertainty. Unmount the camera rather than offer
      // an automatic new biometric attempt against an unresolved transmission.
      if (mounted.current) cancel();
    }
  }
  async function reconcile() {
    if (reconciling || sending) return;
    setReconciling(true);
    try {
      const saved = await runtimeReviewer.reconcile(selectedRuntimeId);
      useRuntimeReview.getState().remember(saved, selectedRuntimeId);
      if (mounted.current) {
        setError('');
        setRevision((v) => v + 1);
      }
    } catch (e) {
      if (mounted.current) setError(explain(e));
    } finally {
      if (mounted.current) setReconciling(false);
    }
  }
  if (!runtimeReviewer.available)
    return (
      <p className="panel-footnote">
        Read-only browser · open native ALICE to review eligible HOLDs.
      </p>
    );
  return (
    <section className="panel runtime-review-panel">
      <div className="section-kicker">REQUEST DETAILS & TECHNICIAN REVIEW</div>
      {loading && <p role="status">Loading current request…</p>}
      {snapshot?.request && (
        <dl className="request-context">
          <div>
            <dt>AGENT</dt>
            <dd>{snapshot.request.agent_id}</dd>
          </div>
          <div>
            <dt>ACTION / TARGET</dt>
            <dd>
              {snapshot.request.action} · {snapshot.request.target}
            </dd>
          </div>
          <div>
            <dt>EXACT PARAMETERS</dt>
            <dd>{JSON.stringify(snapshot.request.parameters)}</dd>
          </div>
          <div>
            <dt>ISSUED</dt>
            <dd>{snapshot.request.issued_at}</dd>
          </div>
        </dl>
      )}
      {snapshot && (
        <p>
          Pi review: {snapshot.review_state} · Execution: {snapshot.execution_status}
        </p>
      )}
      {snapshot?.assessment && (
        <p>
          Anomaly: {snapshot.assessment.result} · normal-tail rank{' '}
          {(snapshot.assessment.score_ppm / 10_000).toFixed(1)}% · model{' '}
          {snapshot.assessment.model_id}
        </p>
      )}
      {snapshot && <p className="muted">{reasons[snapshot.reason] ?? snapshot.reason}</p>}
      {setup && !setup.ready && <p role="alert">{explain(setup.reason)}</p>}
      {error && <p role="alert">{error}</p>}
      {snapshot && now >= expiresAt && !loading && (
        <p role="status">Request details are stale. Refresh before reviewing.</p>
      )}
      {feed.state !== 'live' && (
        <p>Review paused while the feed is {feed.state}. Retained events remain historical.</p>
      )}
      {submission && (
        <div role="status" className="runtime-submission">
          <h3>
            {submission.state === 'ACCEPTED'
              ? submission.action === 'APPROVE_ONCE'
                ? 'Approval accepted by Pi'
                : 'Rejection accepted by Pi'
              : sending
                ? 'Sending technician response…'
                : 'Delivery outcome is uncertain'}
          </h3>
          <p>Action ID: {submission.action_id}</p>
          {submission.receipt ? (
            <p>
              Execution: {submission.receipt.execution_status}. Controller receipt and observed
              state appear separately in the feed.
            </p>
          ) : (
            <p>
              The response may have reached the Pi. Check the recorded outcome; do not submit
              another action.
            </p>
          )}
          {submission.error && <p>{submission.error}</p>}
          {submission.state !== 'ACCEPTED' && (
            <button
              disabled={sending || reconciling || feed.state !== 'live'}
              onClick={() => void reconcile()}
            >
              {reconciling ? 'Checking recorded outcome…' : 'Check recorded outcome'}
            </button>
          )}
        </div>
      )}
      <div className="action-buttons">
        <button
          disabled={loading || !!attempt || sending || reconciling || feed.state !== 'live'}
          onClick={() => setRevision((v) => v + 1)}
        >
          Refresh request
        </button>
        {(['REJECT', 'APPROVE_ONCE'] as const).map((action) => (
          <button
            key={action}
            className={action === 'REJECT' ? 'reject-button' : 'approve-button'}
            disabled={!eligible || loading || !!attempt || !!submission || sending}
            onClick={() => {
              if (snapshot && technician)
                setAttempt({ snapshot, action, technicianId: technician.technician_id, expiresAt });
            }}
          >
            {action === 'REJECT' ? 'Verify to reject' : 'Verify to approve once'}
          </button>
        ))}
      </div>
      <p className="panel-footnote">
        Either response requires fresh facial verification for this exact request. The Pi checks
        current permission and execution authority. An acknowledgment does not confirm execution.
      </p>
      {attempt && (
        <Modal
          title={
            attempt.action === 'APPROVE_ONCE'
              ? 'Verify to approve this request'
              : 'Verify to reject this request'
          }
          onClose={cancel}
          closeDisabled={sending}
        >
          <Badge tone="information">FRESH REQUEST VERIFICATION</Badge>
          <h3>
            {attempt.snapshot.request?.action} · {attempt.snapshot.request?.target}
          </h3>
          <p>
            {JSON.stringify(attempt.snapshot.request?.parameters)} · {attempt.snapshot.request_id}
          </p>
          {submission?.state === 'ACCEPTED' && acknowledged ? (
            <div role="status">
              <p>The Pi accepted your response. Execution and observed state remain separate.</p>
              <button onClick={cancel}>Done</button>
            </div>
          ) : (attemptCurrent && !submission) ||
            sending ||
            (submission?.state === 'ACCEPTED' && !acknowledged) ? (
            <CameraCapture
              key={`${attempt.snapshot.request_id}:${attempt.action}`}
              intent={{
                purpose: 'APPROVAL',
                technician_id: attempt.technicianId,
                decision_id: attempt.snapshot.decision_event_id,
                request_id: attempt.snapshot.request_id,
                runtime_action: attempt.action,
              }}
              onCancel={cancel}
              onComplete={(session) => complete(session, attempt)}
              onAcknowledged={() => setAcknowledged(true)}
            />
          ) : (
            <p role="alert">
              The request, identity or connection changed. Close this window and refresh before
              starting a new verification.
            </p>
          )}
        </Modal>
      )}
    </section>
  );
}
