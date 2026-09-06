import { test, expect } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { createInterface } from 'node:readline';
import { randomBytes } from 'node:crypto';
let driver: ChildProcess, vite: ChildProcess;
let info: { pi: number; bridge: number; envelope: unknown };
const token = randomBytes(32).toString('hex');
test.beforeAll(async () => {
  driver = spawn(
    process.env.ALICE_TEST_PYTHON ?? '.venv/bin/python',
    ['tests/console/e2e/runtime_driver.py'],
    {
      env: { ...process.env, PYTHONPATH: '.', ALICE_FEED_TOKEN: token },
      stdio: ['pipe', 'pipe', 'inherit'],
    },
  );
  info = await new Promise((resolve, reject) => {
    const lines = createInterface({ input: driver.stdout! });
    lines.once('line', (line) => resolve(JSON.parse(line)));
    driver.once('exit', (code) => reject(new Error(`Runtime driver exited ${code}`)));
  });
  vite = spawn(
    'node',
    ['node_modules/vite/bin/vite.js', '--config', 'apps/desktop/vite.config.ts', '--port', '1421'],
    {
      env: {
        ...process.env,
        VITE_ALICE_PREVIEW_MODE: 'remote',
        ALICE_FEED_URL: `http://127.0.0.1:${info.bridge}`,
        ALICE_FEED_TOKEN: token,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  await expect
    .poll(async () => {
      try {
        return (await fetch('http://127.0.0.1:1421')).status;
      } catch {
        return 0;
      }
    })
    .toBe(200);
});
test.afterAll(async () => {
  vite?.kill();
  driver?.stdin?.write('stop\n');
});
test('real request automatically updates technician dashboard, replays history and recovers a disconnected bridge', async ({
  page,
  request,
}) => {
  await page.goto('http://127.0.0.1:1421');
  await expect(page.getByRole('heading', { name: 'ALLOW', exact: true })).toBeVisible();
  await expect(page.getByText('FIXTURE ASSESSMENT')).toBeVisible();
  await expect(page.getByText('MOCK CONTROLLER')).toBeVisible();
  await expect(page.getByText('Risk score: unavailable')).toBeVisible();
  const response = await request.post(`http://127.0.0.1:${info.pi}/request`, {
    data: info.envelope,
  });
  expect(response.status()).toBe(200);
  await expect(page.getByRole('button', { name: /new-live-request/ })).toBeVisible({
    timeout: 10000,
  });
  await page.getByRole('button', { name: /new-live-request/ }).click();
  await expect(page.getByText('ESP-LIGHT-01 · light_state: 0 bool')).toBeVisible();
  await expect(page.getByText('COMPLETED', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Approve once/ })).toBeDisabled();
  const retry = await request.post(`http://127.0.0.1:${info.pi}/request`, { data: info.envelope });
  expect((await retry.json()).idempotent_replay).toBe(true);
  await page.reload();
  await expect(page.getByRole('button', { name: /new-live-request/ })).toBeVisible();
  await expect(page.getByText('14', { exact: false }).filter({ hasText: 'Ledger:' })).toBeVisible();
  driver.stdin!.write('disconnect\n');
  await expect(page.getByText('FEED DISCONNECTED').first()).toBeVisible({ timeout: 12000 });
  await expect(page.getByRole('button', { name: /new-live-request/ })).toBeVisible();
  driver.stdin!.write('reconnect\n');
  await expect(page.getByText('FEED LIVE').first()).toBeVisible({ timeout: 12000 });
  await page.screenshot({ path: '/tmp/alice-live-dashboard.png', fullPage: true });
});
