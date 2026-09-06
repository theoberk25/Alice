import { useRef, useState } from 'react';
import type { Verification } from '@alice/contracts';
import { Fingerprint, ShieldCheck, ShieldX, ScanFace, LockKeyhole, Check, X } from 'lucide-react';
import { Modal, Badge, BorderTrail, CommandButton, TransitionPanel } from '@alice/ui';
import { useConsole } from '../../state/console';
import { verifyFace } from '../../features/biometrics/verify';
import { CameraCapture } from './CameraCapture';
export function ApprovalModal({
  onClose,
  decisionId: selectedId,
}: {
  onClose: () => void;
  decisionId: string;
}) {
  const { decisions, technician, biometricMode, act, log, scenario, latestDecisionByRequest } =
    useConsole();
  const advance = (event: Parameters<ReturnType<typeof useConsole.getState>['advance']>[0]) =>
    useConsole.getState().advance(event, selectedId);
  const d = decisions[selectedId]!;
  const [state, setState] = useState<'WAITING' | 'VERIFYING' | 'FAILED' | 'SUBMITTED'>('WAITING'),
    [error, setError] = useState('');
  const required = d.decision.biometric_required_for_approval;
  const superseded = latestDecisionByRequest[d.request.request_id] !== selectedId;
  const [score, setScore] = useState<{ similarity: number; threshold: number }>();
  const submitting = useRef(false);
  const [submissionPending, setSubmissionPending] = useState(false);
  function close() {
    if (submitting.current) return;
    if (state !== 'SUBMITTED' && !superseded) advance('CANCEL');
    onClose();
  }
  async function verify(frames: string[], result?: 'PASS' | 'FAIL', supplied?: Verification) {
    if (submitting.current) return;
    submitting.current = true;
    setSubmissionPending(true);
    setState('VERIFYING');
    setError('');
    try {
      if (useConsole.getState().flows[selectedId] !== 'BIOMETRIC_VERIFYING') advance('VERIFY');
      log('STEP_UP_STARTED', 'Fresh verification for this exact held request', selectedId);
      const proof =
        supplied ??
        (await verifyFace(
          {
            technician_id: technician!.technician_id,
            decision_id: d.decision_id,
            request_id: d.request.request_id,
          },
          frames,
          result,
        ));
      if (useConsole.getState().latestDecisionByRequest[d.request.request_id] !== selectedId)
        throw new Error('This assessment was superseded. Close and review the current assessment.');
      if (proof.similarity !== undefined && proof.threshold !== undefined)
        setScore({ similarity: proof.similarity, threshold: proof.threshold });
      if (proof.result !== 'PASS') {
        advance('FAIL');
        log('STEP_UP_FAILED', 'Identity did not match; approval blocked', selectedId);
        setState('FAILED');
        return;
      }
      advance('PASS');
      log('STEP_UP_PASSED', 'Identity verified for this exact request', selectedId);
      await act('APPROVE_ONCE', proof, selectedId);
      setState('SUBMITTED');
    } catch (e) {
      const flow = useConsole.getState().flows[selectedId];
      if (flow === 'BIOMETRIC_VERIFYING') advance('FAIL');
      else if (flow === 'BIOMETRIC_PASSED') {
        advance('CANCEL');
        advance('APPROVE');
        advance('REQUIRE_BIOMETRIC');
      }
      setState('FAILED');
      setError(String(e));
      log(
        'STEP_UP_FAILED',
        'Verification or submission failed; no execution authorization confirmed',
        selectedId,
      );
      // A consumed/failed native proof requires CameraCapture to offer a fresh session.
      if (supplied) throw e;
    } finally {
      submitting.current = false;
      setSubmissionPending(false);
    }
  }
  async function confirm() {
    if (submitting.current) return;
    submitting.current = true;
    setSubmissionPending(true);
    setState('VERIFYING');
    setError('');
    try {
      await act('APPROVE_ONCE', undefined, selectedId);
      setState('SUBMITTED');
    } catch (e) {
      setError(String(e));
      setState('FAILED');
    } finally {
      submitting.current = false;
      setSubmissionPending(false);
    }
  }
  return (
    <Modal
      title={state === 'SUBMITTED' ? 'Approval submitted' : 'Verify to approve once'}
      onClose={close}
      closeDisabled={submissionPending}
      morphId="approval"
      className="approval-dialog"
    >
      <TransitionPanel stage={state} className="approval-content">
        <div className="verification-intro">
          <Badge tone={biometricMode === 'mock' ? 'warning' : 'information'}>
            {biometricMode === 'mock' ? 'Simulated identity verification' : 'Local face identity'}
          </Badge>
          <h3>
            {state === 'SUBMITTED'
              ? 'One request. One approval.'
              : state === 'FAILED'
                ? 'Approval blocked'
                : required
                  ? 'Confirm it’s you.'
                  : 'Confirm this exact request.'}
          </h3>
          <p>
            {state === 'SUBMITTED'
              ? 'The structured approval request has been recorded. The console does not execute protected actions.'
              : state === 'FAILED'
                ? 'The request remains held. A fresh successful verification is required.'
                : required
                  ? biometricMode === 'mock'
                    ? 'Use the simulated controls to test this approval.'
                    : 'The camera checks your saved face automatically for this action. No head turns needed.'
                  : 'Upstream ALICE does not require facial step-up for this request.'}
          </p>
        </div>
        <div className="verification-binding">
          <div>
            <span>Technician</span>
            <strong>{technician?.display_name}</strong>
          </div>
          <div>
            <span>Decision / request</span>
            <strong>
              {d.decision_id} / {d.request.request_id}
            </strong>
          </div>
          <div>
            <span>Exact action</span>
            <strong>
              {d.request.action} → {d.request.target}
            </strong>
          </div>
        </div>
        {superseded ? (
          <p className="inline-error" role="alert">
            This assessment was superseded. Close this dialog and review the current assessment; a
            new verification is required.
          </p>
        ) : state === 'SUBMITTED' ? (
          <div className="verification-result tone-healthy">
            <ShieldCheck size={55} strokeWidth={1} />
            <strong>APPROVED ONCE</strong>
            <span>Upstream decision: HOLD · Execution: not confirmed</span>
            {score && (
              <span>
                Identity cosine similarity {score.similarity.toFixed(2)} · threshold{' '}
                {score.threshold.toFixed(2)}
              </span>
            )}
            <CommandButton className="primary-button" onClick={onClose}>
              Return to console
            </CommandButton>
          </div>
        ) : (
          <>
            {required && biometricMode === 'mock' ? (
              <div className={`simulated-face ${state === 'FAILED' ? 'face-failed' : ''}`}>
                <div className="scan-corners">
                  {state === 'FAILED' ? (
                    <ShieldX size={48} strokeWidth={1} />
                  ) : (
                    <ScanFace size={52} strokeWidth={1} />
                  )}
                  <BorderTrail active={state === 'VERIFYING'} />
                </div>
                <span>
                  {state === 'VERIFYING'
                    ? 'VERIFYING IDENTITY'
                    : state === 'FAILED'
                      ? 'IDENTITY NOT VERIFIED'
                      : 'MOCK CAPTURE · NO CAMERA USED'}
                </span>
                <div className="mock-biometric-buttons">
                  <CommandButton
                    className="danger-button"
                    disabled={state === 'VERIFYING'}
                    onClick={() => void verify([], 'FAIL')}
                  >
                    <X size={15} /> Simulate fail
                  </CommandButton>
                  <CommandButton
                    className="primary-button"
                    disabled={state === 'VERIFYING'}
                    onClick={() =>
                      void verify([], scenario === '06_hold_face_approval_fail' ? 'FAIL' : 'PASS')
                    }
                  >
                    <Check size={15} />
                    {scenario === '06_hold_face_approval_fail'
                      ? 'Run failure scenario'
                      : 'Simulate pass'}
                  </CommandButton>
                </div>
              </div>
            ) : required ? (
              <CameraCapture
                intent={{
                  purpose: 'APPROVAL',
                  technician_id: technician!.technician_id,
                  decision_id: d.decision_id,
                  request_id: d.request.request_id,
                }}
                onStarted={() => {
                  setState('VERIFYING');
                  if (useConsole.getState().flows[selectedId] !== 'BIOMETRIC_VERIFYING')
                    advance('VERIFY');
                }}
                onComplete={async (session) => {
                  if (!session.verification) throw new Error('Native approval grant is missing.');
                  await verify([], undefined, session.verification);
                }}
                onCancel={close}
              />
            ) : (
              <CommandButton
                className="primary-button"
                disabled={state === 'VERIFYING'}
                onClick={() => void confirm()}
              >
                Confirm approve once
              </CommandButton>
            )}
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            {score && (
              <p className="capture-guidance">
                Identity cosine similarity {score.similarity.toFixed(2)} · threshold{' '}
                {score.threshold.toFixed(2)}. This is not a liveness score.
              </p>
            )}
            <div className="identity-boundary">
              <Fingerprint size={16} />
              <span>
                {biometricMode === 'mock'
                  ? 'Simulated identity only. No live controls run.'
                  : 'A fresh Face ID check is required for this exact request.'}
              </span>
              <LockKeyhole size={14} />
            </div>
          </>
        )}
      </TransitionPanel>
    </Modal>
  );
}
