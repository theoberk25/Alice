import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeEnabled();
});
test('HOLD → failed face → fresh retry → structured approval', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
  await page.screenshot({
    path: 'artifacts/console/verification/screenshots/operations-desktop.png',
    fullPage: true,
  });
  await page.getByRole('button', { name: 'Approve once', exact: true }).click();
  await page.getByRole('button', { name: 'Simulate fail', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Approval blocked' })).toBeVisible();
  await page.getByRole('button', { name: 'Simulate pass', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Approval submitted', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Return to console' }).click();
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
});
test('DENY cannot be overridden; DDIL and language outage keep review operational', async ({
  page,
}) => {
  await page.getByRole('button', { name: /disable_edr.*DENIED/ }).click();
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'DENIED', exact: true })).toBeVisible();
  await page.getByRole('button', { name: /allow_outbound.*HELD/ }).click();
  await page.getByRole('button', { name: 'Why was this held?', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Local language gateway is offline');
  await page.getByRole('button', { name: 'Research', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Evidence & context workspace' })).toBeVisible();
});
test('reconciliation retains original decision and cloud-at-decision state', async ({ page }) => {
  await page.getByRole('button', { name: 'Development scenarios' }).click();
  await page.getByRole('combobox').selectOption('08_reconnect_reconciliation');
  await expect(
    page.getByRole('heading', { name: 'Evidence reconciled', exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Cloud was offline at decision time/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
});
test('mobile layout avoids horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
  await expect(page.locator('.mobile-simulation')).toBeVisible();
  await page.screenshot({
    path: 'artifacts/console/verification/screenshots/operations-mobile.png',
    fullPage: true,
  });
});
test('automatic HOLD clarification waits for reassessment and approves only DEC-185 with a fresh face check', async ({
  page,
}) => {
  await page.getByRole('button', { name: 'Development scenarios' }).click();
  await page.clock.install();
  await page.getByRole('combobox').selectOption('04_hold_context_rejustification');
  await expect(page.getByRole('img', { name: 'Behavioral risk 94 of 100, HIGH' })).toBeVisible();
  await expect(page.getByText('Responding to automatic context request')).toBeVisible();
  await page.clock.runFor(1200);
  await expect(page.getByRole('status').filter({ hasText: 'Reassessment pending' })).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Inspect assessment DEC-20260905-000185' }),
  ).toHaveCount(0);
  await page.clock.runFor(1200);
  const lineage = page.getByRole('list', { name: 'Decision reassessment history' });
  for (const text of [
    'Original decision',
    'Automatic context request',
    'Agent response',
    'Reassessment · Current decision',
  ])
    await expect(lineage.getByText(text, { exact: true })).toBeVisible();
  await expect(page.getByText('94 → 62')).toBeVisible();
  await expect(page.locator('.hero-topline')).toContainText('CURRENT ASSESSMENT / 000185');
  await page.screenshot({
    path: 'artifacts/console/verification/screenshots/reassessment-desktop.png',
    fullPage: true,
  });
  await page.getByRole('button', { name: 'Inspect assessment DEC-20260905-000184' }).click();
  await expect(page.locator('.hero-topline')).toContainText('ORIGINAL ASSESSMENT / 000184');
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: /View current assessment/ }).click();
  await page.getByRole('button', { name: 'Approve once', exact: true }).click();
  await expect(page.getByRole('dialog').getByText('DEC-20260905-000185 / REQ-88291')).toBeVisible();
  await page.getByRole('button', { name: 'Simulate pass', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Approval submitted', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Return to console' }).click();
  await page.getByRole('button', { name: 'Audit trail', exact: true }).click();
  const downloading = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export JSON' }).click();
  const download = await downloading;
  const audit = JSON.parse(await readFile((await download.path())!, 'utf8')) as Array<{
    type: string;
    decision_id: string;
    request_id: string;
    detail: string;
  }>;
  const submitted = audit.filter((e) => e.type === 'ACTION_SUBMITTED');
  expect(submitted).toHaveLength(1);
  expect(submitted[0]).toMatchObject({
    decision_id: 'DEC-20260905-000185',
    request_id: 'REQ-88291',
    detail: 'APPROVE_ONCE · ACCEPTED · not executed by console',
  });
  expect(
    audit.some((e) => e.type === 'STEP_UP_PASSED' && e.decision_id === 'DEC-20260905-000185'),
  ).toBe(true);
});
