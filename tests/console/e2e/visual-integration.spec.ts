import { expect, test } from '@playwright/test';

const actionNames = ['Reject', 'Research', 'Request more context', 'Hold', 'Approve once'];

test('popup rehearsal keeps context available and can reset after approval', async ({ page }) => {
  test.skip(process.env.VITE_ALICE_MANUAL_CONTEXT_DEMO !== 'true', 'Opt-in popup rehearsal build');
  await page.goto('/');
  const context = page.getByRole('button', { name: 'Request more context', exact: true });
  await expect(context).toBeEnabled();
  await expect(page.getByText('AWAITING YOUR REQUEST', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Clarification progress')).not.toContainText('failed');
  await page.clock.install();
  await page.clock.runFor(30_000);
  await expect(context).toBeEnabled();
  await context.click();
  await page.clock.runFor(1200);
  await expect(page.getByRole('status').filter({ hasText: 'Reassessment pending' })).toBeVisible();
  await expect(context).toBeDisabled();
  await page.getByRole('button', { name: 'Approve once', exact: true }).click();
  await page.getByRole('button', { name: 'Simulate pass', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Approval submitted', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Return to console' }).click();
  await page.getByRole('button', { name: 'Development scenarios', exact: true }).click();
  await page.getByRole('button', { name: 'Reset scenario', exact: true }).click();
  await expect(context).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeEnabled();
});

test('all five integrated rail actions fit without clipping or overlap', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Approve once', exact: true })).toBeEnabled();
  const rail = page.locator('.action-bar');
  await expect(rail.getByRole('button')).toHaveCount(actionNames.length);

  for (const width of [1512, 1024, 801, 800, 601, 600, 390, 360, 320]) {
    await page.setViewportSize({ width, height: 844 });
    const boxes = [];
    const railBox = (await rail.boundingBox())!;
    for (const name of actionNames) {
      const button = rail.getByRole('button', { name, exact: true });
      await expect(button).toBeInViewport({ ratio: 1 });
      const box = (await button.boundingBox())!;
      expect(box.x, `${name} left edge at ${width}`).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width, `${name} right edge at ${width}`).toBeLessThanOrEqual(width);
      expect(box.y, `${name} top edge at ${width}`).toBeGreaterThanOrEqual(railBox.y);
      expect(box.y + box.height, `${name} bottom edge at ${width}`).toBeLessThanOrEqual(844);
      expect(
        await button.evaluate((el) => el.scrollWidth <= el.clientWidth),
        `${name} content must fit at ${width}`,
      ).toBe(true);
      boxes.push(box);
    }
    for (let i = 0; i < boxes.length; i++) {
      for (const other of boxes.slice(i + 1)) {
        const box = boxes[i]!;
        expect(
          box.x + box.width <= other.x ||
            other.x + other.width <= box.x ||
            box.y + box.height <= other.y ||
            other.y + other.height <= box.y,
          `Rail controls must not overlap at ${width}`,
        ).toBe(true);
      }
    }
    expect(
      await page
        .locator('.alice-app')
        .evaluate((el) => parseFloat(getComputedStyle(el).paddingBottom)),
      `Page must reserve space for the rail at ${width}`,
    ).toBeGreaterThanOrEqual(railBox.height);
    if (width >= 390) {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
    }
  }
});

test('the themed context action retains current decision and pending-response guards', async ({
  page,
}) => {
  await page.goto('/');
  const context = page.getByRole('button', { name: 'Request more context', exact: true });
  await expect(context).toBeEnabled();
  await page.getByRole('button', { name: /disable_edr.*DENIED/ }).click();
  await expect(context).toBeDisabled();
  await page.getByRole('button', { name: /allow_outbound.*HELD/ }).click();
  await expect(context).toBeEnabled();

  await page.clock.install();
  await context.click();
  await expect(context).toBeDisabled();
  await page.clock.runFor(1200);
  await expect(page.getByRole('status').filter({ hasText: 'Reassessment pending' })).toBeVisible();
  await expect(context).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'HOLD', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Decision history', exact: true }).click();
  await expect(context).toBeDisabled();
});
