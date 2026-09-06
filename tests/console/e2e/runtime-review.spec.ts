import { test, expect, type Page } from '@playwright/test';
import { event, page as feedPage } from '../runtime-fixtures';

// Browser lifecycle evidence only: all native IPC, camera results and review
// receipts below are synthetic. Rust/Python signed bridge tests cover authority.
interface TestNative {
  holdCamera: boolean;
  delivery: 'normal' | 'late' | 'uncertain';
  sends: number;
  cancelled: string[];
  intents: Array<{ purpose: string; runtime_action?: string }>;
  releaseAck?: () => void;
}
async function installNativeFixture(page: Page) {
  const decision = event(2, 'DECISION');
  decision.detail.outcome = 'CHALLENGE';
  const accepted = event(3, 'TECHNICIAN_ACTION');
  await page.addInitScript(
    ({ feed, actionEvent }) => {
      type Submission = {
        schema_version: string;
        request_id: string;
        action_id: string;
        action: string;
        state: string;
        created_at: string;
        receipt: Record<string, unknown> | null;
        error: string | null;
      };
      type Session = {
        session_id: string;
        purpose: string;
        state: string;
        verification: Record<string, unknown> | null;
        [key: string]: unknown;
      };
      const control = {
        holdCamera: false,
        delivery: 'normal',
        sends: Number(sessionStorage.getItem('synthetic-sends') ?? 0),
        cancelled: [] as string[],
        intents: [] as Array<{ purpose: string; runtime_action?: string }>,
        releaseAck: undefined as (() => void) | undefined,
      };
      Object.assign(window, { isTauri: true, __ALICE_TEST_NATIVE__: control });
      const tech = {
        technician_id: 'TECH-TEST',
        username: 'synthetic',
        display_name: 'Synthetic technician',
        role: 'Technician',
        enabled: true,
        enrolled: true,
        enrollment_version: 'MULTI_POSE_V2',
      };
      let current: Session | undefined;
      let authenticated = false;
      let saved: Submission | null = JSON.parse(
        sessionStorage.getItem('synthetic-submission') ?? 'null',
      );
      const record = () => sessionStorage.setItem('synthetic-submission', JSON.stringify(saved));
      const controls = Object.fromEntries(
        ['identity', 'quality', 'capture_integrity', 'pose', 'pad'].map((key) => [
          key,
          { result: 'PASS', model: 'SYNTHETIC_BROWSER_FIXTURE', reason: 'TEST_ONLY', score: null },
        ]),
      );
      const receipt = () => ({
        schema_version: 'alice-review-receipt-v1',
        request_id: 'request-1',
        action_id: saved!.action_id,
        status: 'ACCEPTED',
        review_state: saved!.action === 'REJECT' ? 'REJECTED' : 'APPROVED',
        execution_status: saved!.action === 'REJECT' ? 'NOT_EXECUTED' : 'UNKNOWN',
        idempotent_replay: false,
      });
      const snapshot = () => ({
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
        review_state: saved ? receipt().review_state : 'PENDING',
        accepted_action_id: saved?.action_id ?? null,
        accepted_action: saved?.action ?? null,
        eligible: !saved,
        reason: saved ? 'REVIEW_ALREADY_RESOLVED' : 'READY',
        execution_status: saved ? receipt().execution_status : 'NOT_EXECUTED',
      });
      Object.assign(window, {
        __TAURI_INTERNALS__: {
          invoke: async (command: string, args: Record<string, unknown> = {}) => {
            if (command === 'runtime_config')
              return {
                transport_mode: 'remote',
                biometric_mode: 'arcface',
                biometric_policy: 'alice.live-face.v3',
                llm_model: '',
                ollama_url: 'http://127.0.0.1:11434',
                biometric_url: 'http://127.0.0.1:8765',
                admin_configured: true,
              };
            if (command === 'append_audit') return null;
            if (command === 'llm_health') return { status: 'UNCONFIGURED', model: '' };
            if (command === 'begin_biometric_session') {
              const intent = args.intent as {
                purpose: string;
                runtime_action?: string;
                request_id?: string;
                decision_id?: string;
              };
              control.intents.push(intent);
              current = {
                schema_version: '2.0',
                session_id: crypto.randomUUID(),
                purpose: intent.purpose,
                state: 'CAPTURING',
                policy: 'alice.live-face.v3',
                prompt: 'CENTER',
                reason: '',
                coverage: {},
                accepted_samples: 0,
                controls: {},
                preview: null,
                technician: null,
                verification: null,
              };
              if (intent.purpose === 'APPROVAL')
                current.verification = {
                  verification_id: crypto.randomUUID(),
                  technician_id: tech.technician_id,
                  request_id: intent.request_id,
                  decision_id: intent.decision_id,
                  timestamp: new Date().toISOString(),
                  expires_at: new Date(Date.now() + 60000).toISOString(),
                  provider: 'arcface',
                  result: 'PASS',
                };
              return structuredClone(current);
            }
            if (command === 'read_biometric_preview') return null;
            if (command === 'read_biometric_session') {
              if (!current || current.session_id !== args.sessionId)
                throw new Error('Unknown synthetic session');
              if (
                current.state !== 'CANCELLED' &&
                (current.purpose === 'LOGIN' || !control.holdCamera)
              ) {
                current.state = 'SUCCEEDED';
                current.controls = controls;
                current.accepted_samples = 3;
                if (current.purpose === 'LOGIN') {
                  authenticated = true;
                  current.technician = tech;
                }
              }
              return structuredClone(current);
            }
            if (command === 'cancel_biometric_session') {
              control.cancelled.push(String(args.sessionId));
              if (current && current.session_id === args.sessionId && current.state !== 'SUCCEEDED')
                current.state = 'CANCELLED';
              return null;
            }
            if (!authenticated) throw new Error('Technician authentication required');
            if (command === 'runtime_review_status') return { ready: true, reason: 'READY' };
            if (command === 'read_runtime_review') return snapshot();
            if (command === 'read_runtime_submission') return saved;
            if (command === 'read_runtime_events') {
              if (!saved) return feed;
              const next = {
                ...actionEvent,
                correlation: { ...actionEvent.correlation, action_id: saved.action_id },
                detail: {
                  intent: saved.action === 'REJECT' ? 'REQUEST_REJECTION' : 'REQUEST_APPROVAL',
                },
              };
              return { ...feed, events: [...feed.events, next] };
            }
            if (command === 'submit_runtime_review') {
              if (
                saved ||
                current?.state !== 'SUCCEEDED' ||
                current.verification?.verification_id !== args.verificationId
              )
                throw new Error('Synthetic fixture requires fresh verification');
              control.sends++;
              sessionStorage.setItem('synthetic-sends', String(control.sends));
              saved = {
                schema_version: 'alice-native-review-submission-v1',
                request_id: 'request-1',
                action_id: String(args.verificationId),
                action: control.intents.at(-1)!.runtime_action!,
                state: 'PENDING',
                created_at: new Date().toISOString(),
                receipt: null,
                error: null,
              };
              record();
              const acknowledge = () => {
                saved = { ...saved!, state: 'ACCEPTED', receipt: receipt(), error: null };
                record();
                return saved.receipt;
              };
              if (control.delivery === 'late')
                return new Promise((resolve) => {
                  control.releaseAck = () => resolve(acknowledge());
                });
              if (control.delivery === 'uncertain') {
                saved.state = 'UNCERTAIN';
                saved.error = 'SYNTHETIC_ACKNOWLEDGMENT_LOSS';
                record();
                throw new Error(saved.error);
              }
              return acknowledge();
            }
            if (command === 'reconcile_runtime_submission') {
              saved = {
                ...saved!,
                state: 'ACCEPTED',
                receipt: { ...receipt(), idempotent_replay: true },
                error: null,
              };
              record();
              return saved;
            }
            if (command === 'logout') {
              authenticated = false;
              return null;
            }
            throw new Error(`Unexpected synthetic native command: ${command}`);
          },
        },
      });
    },
    { feed: feedPage([event(), decision]), actionEvent: accepted },
  );
}
async function signIn(page: Page) {
  await page.getByRole('button', { name: 'Technician sign in', exact: true }).click();
  await page.getByLabel('Technician username').fill('synthetic');
  await page.getByRole('button', { name: 'Continue to facial login' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
}
test.beforeEach(async ({ page }) => {
  await installNativeFixture(page);
  await page.goto('/');
  await signIn(page);
  await expect(page.getByRole('button', { name: 'Log out', exact: true })).toHaveCount(0);
});
test('synthetic native IPC: feed-before-ack preserves camera and original decision, then retains receipt through navigation', async ({
  page,
}) => {
  await page.evaluate(() => {
    (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).delivery = 'late';
  });
  await page.getByRole('button', { name: 'Verify to approve once', exact: true }).click();
  await expect(page.getByText('Sending technician response…')).toBeVisible();
  await expect(page.getByText('#3 TECHNICIAN_ACTION', { exact: true })).toBeVisible();
  await expect(page.getByRole('dialog').getByLabel('Automatic facial verification')).toBeVisible();
  await page.evaluate(() =>
    (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).releaseAck!(),
  );
  await expect(page.getByRole('heading', { name: 'Approval accepted by Pi' })).toBeVisible();
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Audit trail', exact: true }).click();
  await page.getByLabel('Filter collected traffic').fill('REQUEST_APPROVAL');
  await expect(page.getByText('1 / 3 collected events')).toBeVisible();
  await page.getByRole('button', { name: /Decision history/ }).click();
  await expect(page.getByRole('heading', { name: 'Approval accepted by Pi' })).toBeVisible();
  expect(
    await page.evaluate(() => (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).sends),
  ).toBe(1);
  await page.screenshot({ path: '/tmp/alice-native-synthetic-review.png', fullPage: true });
});
test('synthetic native IPC: cancelling approval submits nothing; rejection starts a separate fresh scan', async ({
  page,
}) => {
  await page.evaluate(() => {
    (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).holdCamera = true;
  });
  await page.getByRole('button', { name: 'Verify to approve once', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('Automatic facial verification')).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).intents.length,
      ),
    )
    .toBe(2);
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).cancelled.length,
      ),
    )
    .toBeGreaterThanOrEqual(2);
  expect(
    await page.evaluate(() => (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).sends),
  ).toBe(0);
  await page.evaluate(() => {
    (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).holdCamera = false;
  });
  await page.getByRole('button', { name: 'Verify to reject', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Rejection accepted by Pi' })).toBeVisible();
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  await expect(page.getByText(/Execution: NOT_EXECUTED\. Controller receipt/)).toBeVisible();
  expect(
    await page.evaluate(() =>
      (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).intents
        .slice(-2)
        .map((i) => i.runtime_action),
    ),
  ).toEqual(['APPROVE_ONCE', 'REJECT']);
  expect(
    await page.evaluate(() => (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).sends),
  ).toBe(1);
});
test('synthetic native IPC: uncertain delivery survives renderer restart and reconciles without resubmission', async ({
  page,
}) => {
  await page.evaluate(() => {
    (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).delivery = 'uncertain';
  });
  await page.getByRole('button', { name: 'Verify to approve once', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Delivery outcome is uncertain' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Verify to approve once' })).toBeDisabled();
  await page.reload();
  await signIn(page);
  await expect(page.getByRole('heading', { name: 'Delivery outcome is uncertain' })).toBeVisible();
  await page.getByRole('button', { name: 'Check recorded outcome' }).click();
  await expect(page.getByRole('heading', { name: 'Approval accepted by Pi' })).toBeVisible();
  expect(
    await page.evaluate(() => (Reflect.get(window, '__ALICE_TEST_NATIVE__') as TestNative).sends),
  ).toBe(1);
});
