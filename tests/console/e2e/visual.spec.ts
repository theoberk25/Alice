import { test, expect } from '@playwright/test';

test('shared navigation preserves selected decisions and accessible control names', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: /disable_edr.*DENIED/ }).click();
  await expect(page.getByRole('heading', { name: 'DENIED', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Decision history', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Decision history', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(page.getByRole('heading', { name: 'DENIED', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Operations', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: /disable_edr.*DENIED/ })).toHaveAttribute(
    'aria-current',
    'true',
  );
});

test('identity morph stays visible, traps focus and returns focus on Escape', async ({ page }) => {
  await page.goto('/');
  const trigger = page.getByRole('button', { name: 'Alex Morgan SIMULATED SESSION' });
  await trigger.click();
  const dialog = page.getByRole('dialog', { name: 'Technician identity' });
  await expect(dialog).toBeVisible();
  await expect.poll(async () => (await dialog.boundingBox())?.width ?? 0).toBeGreaterThan(350);
  const box = (await dialog.boundingBox())!;
  expect(box.width).toBeLessThanOrEqual(540);
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(1040);
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    await expect
      .poll(() => dialog.evaluate((el) => el.contains(document.activeElement)))
      .toBe(true);
  }
  await page.screenshot({ path: 'artifacts/console/visual-overhaul/identity.png' });
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test('reduced motion keeps every action and compact layout usable', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
  for (const width of [1024, 800, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.getByRole('button', { name: 'Administration', exact: true })).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    const rail = (await page.locator('.action-bar').boundingBox())!;
    const lastAction = (await page
      .getByRole('button', { name: 'Approve once', exact: true })
      .boundingBox())!;
    expect(lastAction.y).toBeGreaterThanOrEqual(rail.y);
    expect(lastAction.y + lastAction.height).toBeLessThanOrEqual(844);
  }
  await page.getByRole('button', { name: 'Approve once', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  expect(await dialog.evaluate((el) => getComputedStyle(el).transform)).toBe('none');
  const box = (await dialog.boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(390);
  await page.getByRole('button', { name: 'Simulate fail', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Approval blocked' })).toBeVisible();
  await page.screenshot({ path: 'artifacts/console/visual-overhaul/reduced-motion-failure.png' });
});
