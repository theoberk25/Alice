import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type {
  BiometricIntent,
  LiveBiometricSession,
  RuntimeReview,
  RuntimeReviewReceipt,
  RuntimeSubmission,
} from '@alice/contracts';
import {
  RuntimeReviewSchema,
  RuntimeReviewReceiptSchema,
  RuntimeSubmissionSchema,
} from '@alice/contracts';
import { emptyRuntime, mergeRuntimeFeed, matchesRuntimeRequest } from '@alice/domain';
import { RuntimeReviewPanel } from '../../apps/desktop/src/components/runtime/RuntimeReview';
import { runtimeReviewer } from '../../apps/desktop/src/features/biometrics/runtime-review';
import { useConsole } from '../../apps/desktop/src/state/console';
import { useRuntimeReview } from '../../apps/desktop/src/state/runtime-review';
import { event, page } from './runtime-fixtures';

vi.mock('../../apps/desktop/src/features/biometrics/runtime-review', () => ({
  runtimeReviewer: {
    available: true,
    read: vi.fn(),
    readSubmission: vi.fn(),
    submit: vi.fn(),
    reconcile: vi.fn(),
    status: vi.fn(),
  },
}));
const camera = vi.hoisted(() => ({
  complete: undefined as ((session: LiveBiometricSession) => Promise<void>) | undefined,
  intent: undefined as BiometricIntent | undefined,
  unmount: vi.fn(),
}));
vi.mock('../../apps/desktop/src/components/biometrics/CameraCapture', async () => {
  const React = await import('react');
  return {
    CameraCapture: (props: {
      intent: BiometricIntent;
      onComplete: (s: LiveBiometricSession) => Promise<void>;
    }) => {
      camera.complete = props.onComplete;
      camera.intent = props.intent;
      React.useEffect(() => () => camera.unmount(), []);
      return React.createElement('p', { 'data-testid': 'scan' }, 'Automatic native face scan');
    },
  };
});

const technician = {
  technician_id: 'TECH-1',
  username: 'tech',
  display_name: 'Technician',
  role: 'Technician',
  enabled: true,
  enrolled: true,
};
const actionId = 'a779e93e-8925-49f5-b0c0-5f2b463c22c9';
function review(overrides: Partial<RuntimeReview> = {}): RuntimeReview {
  return {
    schema_version: 'alice-runtime-review-v1',
    request_id: 'request-1',
    request_sha256: 'a'.repeat(64),
    decision_event_id: 'event-2',
    decision_event_hash: '2'.padStart(64, '0'),
    release_sha256: 'b'.repeat(64),
    authority_interval_ref: 'interval-1',
    runtime_epoch: 'boot-1',
    review_nonce: 'nonce-1',
    request: {
      schema_version: '1.0',
      request_id: 'request-1',
      agent_id: 'agent-1',
      action: 'set_light_state',
      target: 'ESP-LIGHT-01',
      parameters: { state: 'on' },
      issued_at: '2026-09-06T01:00:00Z',
    },
    decision: 'CHALLENGE',
    review_state: 'PENDING',
    eligible: true,
    reason: 'READY',
    execution_status: 'NOT_EXECUTED',
    accepted_action_id: null,
    accepted_action: null,
    ...overrides,
  };
}
function receipt(action: 'APPROVE_ONCE' | 'REJECT' = 'APPROVE_ONCE'): RuntimeReviewReceipt {
  return {
    schema_version: 'alice-review-receipt-v1',
    request_id: 'request-1',
    action_id: actionId,
    status: 'ACCEPTED',
    review_state: action === 'REJECT' ? 'REJECTED' : 'APPROVED',
    execution_status: action === 'REJECT' ? 'NOT_EXECUTED' : 'UNKNOWN',
    idempotent_replay: false,
  };
}
function saved(state: RuntimeSubmission['state'] = 'UNCERTAIN'): RuntimeSubmission {
  return {
    schema_version: 'alice-native-review-submission-v1',
    request_id: 'request-1',
    action_id: actionId,
    action: 'APPROVE_ONCE',
    state,
    created_at: new Date().toISOString(),
    receipt: state === 'ACCEPTED' ? receipt() : null,
    error: state === 'UNCERTAIN' ? 'HTTP acknowledgment lost' : null,
  };
}
function success(): LiveBiometricSession {
  return {
    schema_version: '2.0',
    session_id: '0e9f45e2-0641-45d9-b33b-29091a8a1dbb',
    purpose: 'APPROVAL',
    state: 'SUCCEEDED',
    policy: 'alice.live-face.v3',
    prompt: '',
    reason: '',
    coverage: {},
    accepted_samples: 3,
    controls: {},
    preview: null,
    technician: null,
    verification: {
      technician_id: technician.technician_id,
      decision_id: 'event-2',
      request_id: 'request-1',
      verification_id: actionId,
      timestamp: new Date().toISOString(),
      expires_at: new Date(Date.now() + 60000).toISOString(),
      result: 'PASS',
      provider: 'arcface',
    },
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
  };
  Object.defineProperty(runtimeReviewer, 'available', { value: true, configurable: true });
  vi.mocked(runtimeReviewer.read).mockResolvedValue(review());
  vi.mocked(runtimeReviewer.readSubmission).mockResolvedValue(null);
  vi.mocked(runtimeReviewer.submit).mockResolvedValue(receipt());
  vi.mocked(runtimeReviewer.status).mockResolvedValue({ ready: true, reason: 'READY' });
  vi.mocked(runtimeReviewer.reconcile).mockResolvedValue(saved('ACCEPTED'));
  const decision = event(2, 'DECISION');
  decision.detail.outcome = 'CHALLENGE';
  useConsole.setState({
    mode: 'remote',
    biometricMode: 'arcface',
    technician,
    runtime: mergeRuntimeFeed(emptyRuntime(), page([event(), decision])),
    selectedRuntimeId: 'request-1',
    feed: {
      event_type: 'alice.feed_status',
      state: 'live',
      last_success_at: Date.now(),
      message: 'Live',
    },
    errors: [],
  });
  useRuntimeReview.setState({ submissions: {}, sending: {} });
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
async function open(action = 'Verify to approve once') {
  render(<RuntimeReviewPanel />);
  const button = await screen.findByRole('button', { name: action });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  expect(screen.getByTestId('scan')).toBeVisible();
}

it('keeps browsers read-only without invoking native review APIs', () => {
  Object.defineProperty(runtimeReviewer, 'available', { value: false });
  render(<RuntimeReviewPanel />);
  expect(screen.getByText(/Read-only browser/)).toBeVisible();
  expect(screen.queryByRole('button', { name: /Verify/ })).toBeNull();
  expect(runtimeReviewer.read).not.toHaveBeenCalled();
});
it('shows missing local review setup before opening a camera, while retaining exact request details', async () => {
  vi.mocked(runtimeReviewer.status).mockResolvedValue({
    ready: false,
    reason: 'CONSOLE_REVIEW_KEY_NOT_CONFIGURED',
  });
  render(<RuntimeReviewPanel />);
  expect(await screen.findByText(/Native review setup is incomplete/)).toBeVisible();
  expect(screen.getByText('{"state":"on"}')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Verify to approve once' })).toBeDisabled();
  expect(screen.queryByTestId('scan')).toBeNull();
});
it('fixes action intent before capture, cancels queued success and requires another scan for rejection', async () => {
  await open();
  expect(camera.intent).toMatchObject({
    runtime_action: 'APPROVE_ONCE',
    request_id: 'request-1',
    decision_id: 'event-2',
  });
  const late = camera.complete!;
  fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }));
  await expect(late(success())).rejects.toThrow('no longer matches');
  expect(runtimeReviewer.submit).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Verify to reject' }));
  expect(camera.intent).toMatchObject({ runtime_action: 'REJECT' });
  await expect(late(success())).rejects.toThrow('no longer matches');
  expect(runtimeReviewer.submit).not.toHaveBeenCalled();
});
it.each(['disconnect', 'identity', 'decision', 'expired verification'] as const)(
  'invalidates a queued facial success after %s',
  async (change) => {
    await open();
    const result = success();
    act(() => {
      if (change === 'disconnect')
        useConsole.setState({ feed: { ...useConsole.getState().feed, state: 'disconnected' } });
      if (change === 'identity')
        useConsole.setState({ technician: { ...technician, technician_id: 'OTHER' } });
      if (change === 'decision') {
        const runtime = useConsole.getState().runtime;
        const request = runtime.requests['request-1']!;
        useConsole.setState({
          runtime: {
            ...runtime,
            requests: {
              ...runtime.requests,
              'request-1': {
                ...request,
                decision: { ...request.decision!, event_id: 'successor' },
              },
            },
          },
        });
      }
      if (change === 'expired verification')
        result.verification!.expires_at = new Date(Date.now() - 1000).toISOString();
    });
    await expect(camera.complete!(result)).rejects.toThrow('no longer matches');
    expect(runtimeReviewer.submit).not.toHaveBeenCalled();
  },
);
it('expires cached review details during a scan', async () => {
  await open();
  vi.useFakeTimers();
  vi.setSystemTime(Date.now() + 56000);
  await expect(camera.complete!(success())).rejects.toThrow('no longer matches');
  expect(runtimeReviewer.submit).not.toHaveBeenCalled();
});
it('retains a submission through feed-before-ack and navigation, without cancelling the completing camera', async () => {
  const delivery = deferred<RuntimeReviewReceipt>();
  vi.mocked(runtimeReviewer.submit).mockReturnValue(delivery.promise);
  await open();
  let completion!: Promise<void>;
  act(() => {
    completion = camera.complete!(success());
  });
  expect(screen.getByText('Sending technician response…')).toBeVisible();
  const accepted = event(3, 'TECHNICIAN_ACTION');
  vi.mocked(runtimeReviewer.read).mockResolvedValue(
    review({
      eligible: false,
      reason: 'REVIEW_ALREADY_RESOLVED',
      review_state: 'APPROVED',
      accepted_action_id: actionId,
      accepted_action: 'APPROVE_ONCE',
      execution_status: 'UNKNOWN',
    }),
  );
  act(() =>
    useConsole.getState().ingest({ ...page([accepted]), event_type: 'alice.runtime_feed' }),
  );
  await waitFor(() => expect(runtimeReviewer.read).toHaveBeenCalledTimes(2));
  expect(screen.getByTestId('scan')).toBeVisible();
  expect(camera.unmount).not.toHaveBeenCalled();
  await act(async () => {
    delivery.resolve(receipt());
    await completion;
  });
  expect(screen.getByRole('heading', { name: 'Approval accepted by Pi' })).toBeVisible();
  expect(screen.getByText(/Execution: UNKNOWN\. Controller receipt/)).toBeVisible();
  cleanup();
  render(<RuntimeReviewPanel />);
  expect(await screen.findByRole('heading', { name: 'Approval accepted by Pi' })).toBeVisible();
  expect(runtimeReviewer.submit).toHaveBeenCalledTimes(1);
});
it('reconciles uncertain delivery using the saved action ID, without a second submission', async () => {
  await open();
  vi.mocked(runtimeReviewer.readSubmission).mockResolvedValue(saved());
  vi.mocked(runtimeReviewer.submit).mockRejectedValue(new Error('Acknowledgment lost'));
  await act(async () => camera.complete!(success()));
  expect(screen.getByRole('heading', { name: 'Delivery outcome is uncertain' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Verify to approve once' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Check recorded outcome' }));
  expect(await screen.findByRole('heading', { name: 'Approval accepted by Pi' })).toBeVisible();
  expect(runtimeReviewer.reconcile).toHaveBeenCalledWith('request-1');
  expect(runtimeReviewer.submit).toHaveBeenCalledTimes(1);
});
it('blocks a duplicate callback while native delivery is in flight', async () => {
  const delivery = deferred<RuntimeReviewReceipt>();
  vi.mocked(runtimeReviewer.submit).mockReturnValue(delivery.promise);
  const first = useRuntimeReview.getState().submit('request-1', 'APPROVE_ONCE', actionId);
  await expect(
    useRuntimeReview.getState().submit('request-1', 'APPROVE_ONCE', actionId),
  ).rejects.toThrow('already has a submission');
  delivery.resolve(receipt());
  await first;
  expect(runtimeReviewer.submit).toHaveBeenCalledTimes(1);
});
it('restores the native journal after renderer restart and never trusts an uncorrelated receipt', async () => {
  vi.mocked(runtimeReviewer.readSubmission).mockResolvedValue(saved());
  render(<RuntimeReviewPanel />);
  expect(
    await screen.findByRole('heading', { name: 'Delivery outcome is uncertain' }),
  ).toBeVisible();
  expect(screen.getByRole('button', { name: 'Verify to reject' })).toBeDisabled();
  expect(
    RuntimeSubmissionSchema.safeParse({
      ...saved('ACCEPTED'),
      receipt: { ...receipt(), action_id: 'other-action' },
    }).success,
  ).toBe(false);
});
it('hides a previously accepted receipt when native revalidation reports a changed runtime binding', () => {
  useRuntimeReview.getState().remember(saved('ACCEPTED'), 'request-1');
  useRuntimeReview
    .getState()
    .remember({ ...saved(), error: 'REVIEW_SUBMISSION_BINDING_CONFLICT' }, 'request-1');
  expect(useRuntimeReview.getState().submissions['request-1']).toMatchObject({
    state: 'UNCERTAIN',
    receipt: null,
  });
});

describe('review display contracts fail closed', () => {
  it('rejects ambiguous action bindings and never reports rejection as execution', () => {
    expect(RuntimeReviewSchema.safeParse(review()).success).toBe(true);
    for (const wrong of [
      review({ authority_interval_ref: null }),
      review({ accepted_action: 'REJECT' }),
      review({ request: { ...review().request!, request_id: 'different' } }),
      review({ execution_status: 'COMPLETED' }),
    ])
      expect(RuntimeReviewSchema.safeParse(wrong).success).toBe(false);
    expect(
      RuntimeReviewReceiptSchema.safeParse({ ...receipt('REJECT'), execution_status: 'COMPLETED' })
        .success,
    ).toBe(false);
    expect(
      matchesRuntimeRequest(
        review({ request_sha256: 'c'.repeat(64) }),
        useConsole.getState().runtime.requests['request-1'],
      ),
    ).toBe(false);
  });
});

it('accepts exact demo fan requests and rejects mixed physical-light authority', () => {
  const id = 'c'.repeat(64);
  const request = {
    schema_version: 'alice-demo-fan-v1',
    request_id: id,
    client_request_id: 'fan-1',
    agent_id: 'cooling-agent-01',
    run_id: 'a'.repeat(32),
    expected_revision: 0,
    action: 'set_demo_fan_pct',
    target: 'DEMO-SERVER-01',
    parameters: { fan_basis_points: 8500 },
  };
  const value = { ...review(), request_id: id, request };
  expect(RuntimeReviewSchema.safeParse(value).success).toBe(true);
  for (const change of [
    { target: 'ESP-LIGHT-01' },
    { action: 'set_light_state' },
    { parameters: { fan_basis_points: 10001 } },
    { parameters: { fan_basis_points: 8500.1 } },
    { parameters: { fan_pct: 85 } },
    { expected_revision: -1 },
    { run_id: 'old-run' },
  ]) {
    expect(
      RuntimeReviewSchema.safeParse({ ...value, request: { ...request, ...change } }).success,
    ).toBe(false);
  }
});
