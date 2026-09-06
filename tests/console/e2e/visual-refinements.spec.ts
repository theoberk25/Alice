import { expect, test, type Page } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import type { LiveBiometricSession } from '@alice/contracts';

// Presentation/lifecycle evidence only. The browser entry is replaced by this
// test's component harness; IPC and the landscape image are synthetic. Nothing
// here grants authority or uses a native camera, identity store, or face service.
interface VisualFixture {
  begins: number;
  starts: number;
  completions: number;
  cancellations: number;
  cancelled: string[];
  previewReads: number;
  jpeg?: string;
  next: Partial<LiveBiometricSession>;
  releaseStart?: () => void;
  rejectStart?: () => void;
  releaseCompletion?: () => void;
  controls: LiveBiometricSession['controls'];
  originalImage?: HTMLImageElement;
}

async function fixture(page: Page, component: 'camera' | 'admin' | 'identity' = 'camera') {
  await page.addInitScript(() => {
    const controls = Object.fromEntries(
      ['identity', 'quality', 'capture_integrity', 'pose', 'pad'].map((key) => [
        key,
        { result: 'PASS', model: 'SYNTHETIC_BROWSER_FIXTURE', reason: 'TEST_ONLY', score: null },
      ]),
    );
    const state = {
      begins: 0,
      starts: 0,
      completions: 0,
      cancellations: 0,
      cancelled: [] as string[],
      previewReads: 0,
      next: {},
      controls,
    } as VisualFixture;
    let session: LiveBiometricSession;
    let sequence = 0;
    let adminAuthorized = false;
    Object.assign(window, {
      isTauri: true,
      __ALICE_VISUAL_FIXTURE__: state,
      __TAURI_INTERNALS__: {
        invoke: async (command: string, args: Record<string, unknown> = {}) => {
          if (command === 'begin_biometric_session') {
            state.begins++;
            state.next = {};
            session = {
              schema_version: '2.0',
              session_id: crypto.randomUUID(),
              purpose: (args.intent as { purpose: 'ENROLLMENT' | 'LOGIN' }).purpose,
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
            await new Promise<void>((resolve, reject) => {
              state.releaseStart = resolve;
              state.rejectStart = () => reject(new Error('CAMERA_PERMISSION_DENIED'));
            });
            return structuredClone(session);
          }
          if (command === 'read_biometric_session') {
            if (args.sessionId !== session.session_id) throw new Error('Unknown test session');
            return structuredClone({ ...session, ...state.next });
          }
          if (command === 'read_biometric_preview') {
            state.previewReads++;
            return state.jpeg
              ? { session_id: session.session_id, sequence: ++sequence, jpeg: state.jpeg }
              : null;
          }
          if (command === 'cancel_biometric_session') {
            state.cancelled.push(String(args.sessionId));
            return null;
          }
          if (command === 'admin_login') {
            if (args.username !== 'synthetic-admin' || args.password !== 'synthetic-test-only')
              throw new Error('Synthetic credentials only');
            adminAuthorized = true;
            return null;
          }
          if (command === 'admin_logout') {
            adminAuthorized = false;
            return null;
          }
          if (command === 'list_technicians') {
            if (!adminAuthorized) throw new Error('Synthetic administrator required');
            return [
              {
                technician_id: 'TECH-SYNTHETIC-01',
                username: 'enrolled.example',
                display_name: 'Synthetic enrolled technician',
                role: 'Technician',
                enabled: true,
                enrolled: true,
                enrollment_version: 'MULTI_POSE_V2',
              },
              {
                technician_id: 'TECH-SYNTHETIC-02',
                username: 'pending.example',
                enrollment_pending: true,
                display_name: 'Synthetic pending identity',
                role: 'Technician',
                enabled: true,
                enrolled: false,
              },
              {
                technician_id: 'TECH-SYNTHETIC-03',
                username: 'disabled.example',
                enrollment_pending: true,
                display_name: 'Synthetic disabled technician with a longer display name',
                role: 'Technician',
                enabled: false,
                enrolled: false,
              },
            ];
          }
          throw new Error(`Unexpected visual fixture command: ${command}`);
        },
      },
    });
  });
  // Vite keeps the real component, adapters, schemas, React runtime, and styles.
  // Only the browser test entry and IPC transport are substituted.
  await page.route('**/src/main.tsx*', (route) =>
    route.fulfill({
      contentType: 'text/javascript',
      body: `
        import React from '/node_modules/.vite/deps/react.js';
        import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
        import '/src/styles/tokens.css';
        import '/src/styles/global.css';
        import '/src/styles/shell.css';
        import '/src/styles/workspace.css';
        import { CameraCapture } from '/src/components/biometrics/CameraCapture.tsx';
        import { AdminPanel } from '/src/components/technicians/AdminPanel.tsx';
        import { IdentityPanel } from '/src/components/technicians/IdentityPanel.tsx';
        import { useConsole } from '/src/state/console.ts';
        useConsole.setState({ biometricMode: 'arcface' });
        const state = window.__ALICE_VISUAL_FIXTURE__;
        const root = ReactDOM.createRoot(document.getElementById('root'));
        const camera = React.createElement(CameraCapture, {
          intent: { purpose: 'ENROLLMENT', technician_id: 'TECH-SYNTHETIC' },
          onStarted: () => state.starts++,
          onComplete: async () => {
            state.completions++;
            await new Promise(resolve => state.releaseCompletion = resolve);
          },
          onCancel: () => state.cancellations++,
        });
        root.render(React.createElement('main', {
          style: {
            width: 'min(${component === 'admin' ? 1200 : 640}px, calc(100% - 40px))',
            margin: '24px auto',
          }
        }, React.createElement('h1', { style: { fontSize: '16px' } },
          'Synthetic ${component === 'admin' ? 'administration' : 'enrollment'} · browser fixture'),
          ${component === 'admin' ? 'React.createElement(AdminPanel)' : component === 'identity' ? 'React.createElement(IdentityPanel, { onClose: () => root.unmount() })' : 'camera'}));
      `,
    }),
  );
  await page.goto('/');
}
async function startPreview(page: Page) {
  await expect
    .poll(() => page.evaluate(() => !!Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').releaseStart))
    .toBe(true);
  await page.evaluate(() => {
    const state = Reflect.get(window, '__ALICE_VISUAL_FIXTURE__') as VisualFixture;
    const canvas = document.createElement('canvas');
    canvas.width = 1280;
    canvas.height = 720;
    const context = canvas.getContext('2d')!;
    context.fillStyle = '#203744';
    context.fillRect(0, 0, 1280, 720);
    context.strokeStyle = '#8298a5';
    context.lineWidth = 4;
    context.strokeRect(6, 6, 1268, 708);
    context.fillStyle = '#d5dce0';
    context.font = '26px sans-serif';
    context.fillText('SYNTHETIC 16:9 PREVIEW · NO CAMERA', 32, 48);
    state.jpeg = canvas.toDataURL('image/jpeg').split(',')[1];
    state.releaseStart!();
  });
  await expect(page.getByAltText('Mirrored live camera preview')).toBeVisible();
  await page.evaluate(() => {
    Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').originalImage =
      document.querySelector('.biometric-preview img');
  });
}
async function updateSession(page: Page, next: Partial<LiveBiometricSession>) {
  await page.evaluate((patch) => {
    const state = Reflect.get(window, '__ALICE_VISUAL_FIXTURE__') as VisualFixture;
    state.next = { ...state.next, ...patch };
  }, next);
}
async function geometry(page: Page) {
  return {
    preview: (await page.locator('.biometric-preview').boundingBox())!,
    cancel: (await page.locator('.biometric-actions').boundingBox())!,
    instruction: (await page
      .locator('.biometric-guidance strong:not([aria-hidden="true"])')
      .boundingBox())!,
  };
}
async function expectStable(
  page: Page,
  baseline: Awaited<ReturnType<typeof geometry>>,
  resizingCopy = false,
) {
  await expect
    .poll(async () => {
      const current = await geometry(page);
      return Math.max(
        Math.abs(current.preview.width - baseline.preview.width),
        Math.abs(current.preview.height - baseline.preview.height),
        Math.abs(current.preview.y - baseline.preview.y),
        resizingCopy ? 0 : Math.abs(current.cancel.y - baseline.cancel.y),
        Math.abs(current.instruction.y - baseline.instruction.y),
      );
    })
    .toBeLessThan(1)
    .catch(async (error) => {
      throw new Error(
        `${error.message}\nGeometry: ${JSON.stringify({ baseline, current: await geometry(page) })}`,
      );
    });
}
const completedExceptLeft = {
  CENTER: 2,
  LEFT: 0,
  RIGHT: 2,
  UP: 2,
  DOWN: 2,
  UP_LEFT: 2,
  UP_RIGHT: 2,
};

for (const [width, height] of [
  [1512, 1040],
  [1280, 720],
  [1024, 844],
  [800, 844],
  [390, 844],
] as const) {
  test(`synthetic enrollment keeps viewport, instructions and Cancel stable at ${width}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    await fixture(page);
    await expect(page.getByText('Finding your face', { exact: true })).toBeVisible();
    const baseline = await geometry(page);
    await mkdir('artifacts/console/premium-face-id', { recursive: true });
    await writeFile(
      `artifacts/console/premium-face-id/geometry-${width}.json`,
      JSON.stringify({ viewport: { width, height }, startup: baseline }, null, 2),
    );
    expect(baseline.preview.width / baseline.preview.height).toBeCloseTo(16 / 9, 2);
    await startPreview(page);
    await expectStable(page, baseline);
    await expect(page.getByAltText('Mirrored live camera preview')).toHaveCSS(
      'object-fit',
      'contain',
    );
    await expect(page.getByAltText('Mirrored live camera preview')).toHaveCSS(
      'transform',
      'matrix(-1, 0, 0, 1, 0, 0)',
    );
    await updateSession(page, { coverage: completedExceptLeft, accepted_samples: 12 });
    await expect(page.getByText('Turn slightly left', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Left: 0 of 2 samples accepted')).not.toHaveClass(
      /angle-complete/,
    );
    await expect(page.locator('.face-id-poses [data-accepted="2"]')).toHaveCount(6);
    await expectStable(page, baseline);
    await expect(page.locator('[data-region="RIGHT"] .face-id-pose-progress')).toHaveCSS(
      'stroke-opacity',
      '0.84',
    );
    await page.screenshot({
      path: `artifacts/console/premium-face-id/enrollment-left-${width}.png`,
      fullPage: true,
    });
    await updateSession(page, {
      state: 'EVALUATING',
      coverage: { ...completedExceptLeft, LEFT: 2 },
      accepted_samples: 14,
    });
    await expect(page.locator('.face-id-scan')).toHaveAttribute('data-complete', 'false');
    expect(
      await page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').completions),
    ).toBe(0);
    await expect(page.getByText('Checking identity', { exact: true })).toBeVisible();
    await expectStable(page, baseline);
    await page.evaluate(() => {
      const state = Reflect.get(window, '__ALICE_VISUAL_FIXTURE__') as VisualFixture;
      state.next = {
        ...state.next,
        state: 'SUCCEEDED',
        coverage: { ...state.next.coverage, LEFT: 2 },
        accepted_samples: 14,
        controls: state.controls,
      };
    });
    await expect
      .poll(() => page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').completions))
      .toBe(1);
    // Completion callback is deliberately pending: authoritative result text and
    // cleared preview must be observable before the parent action finishes.
    await expect(page.getByText('Identity verified', { exact: true })).toBeVisible();
    await expect(page.getByAltText('Mirrored live camera preview')).toBeHidden();
    await expect(page.getByAltText('Mirrored live camera preview')).not.toHaveAttribute('src');
    await expectStable(page, baseline);
    expect(
      await page.evaluate(() => {
        const state = Reflect.get(window, '__ALICE_VISUAL_FIXTURE__') as VisualFixture;
        return {
          begins: state.begins,
          starts: state.starts,
          sameImage: state.originalImage === document.querySelector('.biometric-preview img'),
        };
      }),
    ).toEqual({ begins: 1, starts: 1, sameImage: true });
    await page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').releaseCompletion());
    await expect(page.getByRole('button', { name: 'Cancel', exact: true })).toBeEnabled();
    await expect(page.getByText('Identity verified', { exact: true })).toBeVisible();
    await expectStable(page, baseline);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: `artifacts/console/premium-face-id/enrollment-success-${width}.png`,
      fullPage: true,
    });
  });
}

for (const width of [1512, 390]) {
  test(`synthetic permission failure, retry and cancellation keep the frame and release preview at ${width}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: width === 1512 ? 1040 : 844 });
    await fixture(page);
    await expect(page.getByText('Finding your face', { exact: true })).toBeVisible();
    const baseline = await geometry(page);
    await page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').rejectStart());
    await expect(page.getByText('Camera permission needed', { exact: true }).first()).toBeVisible();
    await expectStable(page, baseline, true);
    await expect(page.locator('.biometric-actions')).toBeInViewport({ ratio: 1 });
    await page.screenshot({
      path: `artifacts/console/premium-face-id/enrollment-permission-error-${width}.png`,
      fullPage: true,
    });
    await page.getByRole('button', { name: 'Retry with new session', exact: true }).click();
    await expect
      .poll(() => page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').begins))
      .toBe(2);
    await startPreview(page);
    await expectStable(page, baseline, true);
    await expect(page.locator('.biometric-actions')).toBeInViewport({ ratio: 1 });
    await updateSession(page, { state: 'FAILED', reason: 'CAMERA_DISCONNECTED' });
    await expect(page.getByText('Camera disconnected', { exact: true }).first()).toBeVisible();
    await expect(page.getByAltText('Mirrored live camera preview')).toBeHidden();
    await expectStable(page, baseline, true);
    await expect(page.locator('.biometric-actions')).toBeInViewport({ ratio: 1 });
    await page.getByRole('button', { name: 'Retry with new session', exact: true }).click();
    await expect
      .poll(() => page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').begins))
      .toBe(3);
    await startPreview(page);
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect
      .poll(() =>
        page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').cancellations),
      )
      .toBe(1);
    await expect(page.getByAltText('Mirrored live camera preview')).toBeHidden();
    await expect(page.getByAltText('Mirrored live camera preview')).not.toHaveAttribute('src');
    expect(
      await page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').completions),
    ).toBe(0);
  });
}

test('reduced motion keeps outstanding pose feedback complete and the camera untransformed', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await fixture(page);
  await startPreview(page);
  await updateSession(page, { coverage: completedExceptLeft, accepted_samples: 12 });
  await expect(page.getByText('Turn slightly left', { exact: true })).toBeVisible();
  await expect(page.locator('.face-id-poses [data-accepted="2"]')).toHaveCount(6);
  await expect(page.locator('.biometric-preview')).toHaveCSS('transform', 'none');
  await expect(page.locator('.biometric-session')).toHaveCSS('transform', 'none');
  expect(
    await page
      .locator('.biometric-session')
      .evaluate(
        (element) =>
          element
            .getAnimations({ subtree: true })
            .filter((animation) => animation.playState === 'running').length,
      ),
  ).toBe(0);
  await page.getByRole('button', { name: 'Cancel', exact: true }).focus();
  await expect(page.getByRole('button', { name: 'Cancel', exact: true })).toBeFocused();
  await page.screenshot({
    path: 'artifacts/console/premium-face-id/enrollment-reduced-motion-390.png',
    fullPage: true,
  });
});

test('synthetic administrator rows retain labels, availability and readable responsive alignment', async ({
  page,
}) => {
  await fixture(page, 'admin');
  await page.getByLabel('Admin username', { exact: true }).fill('synthetic-admin');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-test-only');
  await page.getByRole('button', { name: 'Authenticate administrator', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Enrolled technicians' })).toBeVisible();
  const rows = page.locator('.technician-row');
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0).getByText('MULTI_POSE_V2', { exact: true })).toBeVisible();
  await expect(rows.nth(1).getByText('PENDING ENROLLMENT', { exact: true })).toBeVisible();
  await expect(
    rows.nth(1).getByRole('button', { name: 'Discard pending enrollment' }),
  ).toBeEnabled();
  await expect(rows.nth(2).getByRole('button', { name: 'Begin enrollment' })).toBeDisabled();
  for (const width of [1512, 520, 390]) {
    await page.setViewportSize({ width, height: width === 1512 ? 1040 : 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    for (const row of await rows.all()) {
      const box = (await row.boundingBox())!;
      for (const button of await row.getByRole('button').all()) {
        const action = (await button.boundingBox())!;
        expect(action.x).toBeGreaterThanOrEqual(box.x);
        expect(action.x + action.width).toBeLessThanOrEqual(box.x + box.width + 1);
      }
    }
    await page.screenshot({
      path: `artifacts/console/premium-face-id/administration-rows-${width}.png`,
      fullPage: true,
    });
  }
  await page.getByRole('button', { name: 'Lock administration', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Authenticate administrator' })).toBeVisible();
});

for (const viewport of [
  { width: 760, height: 640 },
  { width: 1280, height: 720 },
  { width: 390, height: 844 },
]) {
  for (const kind of ['admin', 'identity'] as const) {
    test(`focused ${kind} Face ID fits without scrolling at ${viewport.width}×${viewport.height}`, async ({
      page,
    }) => {
      await page.setViewportSize(viewport);
      await fixture(page, kind);
      if (kind === 'admin') {
        await page.getByLabel('Admin username').fill('synthetic-admin');
        await page.getByLabel('Password', { exact: true }).fill('synthetic-test-only');
        await page.getByRole('button', { name: 'Authenticate administrator' }).click();
        await page.getByRole('button', { name: 'Begin enrollment', exact: true }).first().click();
      } else {
        await page.getByLabel('Technician username').fill('synthetic-user');
        await page.getByRole('button', { name: 'Continue to facial login' }).click();
      }
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await startPreview(page);
      const verifyFit = async () => {
        const box = await dialog.boundingBox();
        expect(box!.y).toBeGreaterThanOrEqual(0);
        expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
        await expect
          .poll(() =>
            dialog.evaluate((el) => el.scrollHeight <= el.clientHeight + 1 && el.scrollTop === 0),
          )
          .toBe(true);
        await expect(page.getByRole('button', { name: 'Cancel', exact: true })).toBeInViewport({
          ratio: 1,
        });
        await expect(page.locator('.biometric-preview')).toBeInViewport({ ratio: 1 });
      };
      await verifyFit();
      await expect(page.locator('.face-id-morph-surface')).toHaveCount(0);
      const baseline = await geometry(page);
      if (kind === 'admin') {
        await updateSession(page, {
          coverage: { CENTER: 2, LEFT: 1, RIGHT: 2, UP: 2, DOWN: 2, UP_LEFT: 2, UP_RIGHT: 2 },
          accepted_samples: 13,
          prompt: 'HOLD_LEFT',
        });
        await expect(page.getByText('Hold this angle briefly')).toBeVisible();
        await expectStable(page, baseline);
      }
      await verifyFit();
      await updateSession(page, {
        controls: {
          quality: {
            result: 'PASS',
            model: 'SYNTHETIC_BROWSER_FIXTURE',
            reason: 'TEST_ONLY',
            score: null,
          },
        },
      });
      await expect(page.locator('.face-id-scan')).toHaveAttribute('data-face-detected', 'true');
      await expect(page.getByText('Face detected', { exact: true })).toBeVisible();
      if (kind === 'identity') await expect(page.locator('[data-region]')).toHaveCount(0);
      await expect(page.locator('.biometric-guidance strong')).toHaveCount(1);
      await expect(page.locator('.face-id-contour-line').first()).toHaveCSS('opacity', '0.3');
      await mkdir('artifacts/console/premium-face-id', { recursive: true });
      await page.screenshot({
        path: `artifacts/console/premium-face-id/${kind}-${viewport.width}.png`,
      });
      await page.getByRole('button', { name: 'Cancel', exact: true }).click();
      await expect
        .poll(() =>
          page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').cancelled.length),
        )
        .toBe(1);
      await expect(page.locator('.biometric-preview')).toHaveCount(0);
    });
  }
}

for (const reduced of [false, true]) {
  test(`Face ID morph preserves focus and immediate Escape cleanup${reduced ? ' with reduced motion' : ''}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    if (reduced) await page.emulateMedia({ reducedMotion: 'reduce' });
    await fixture(page, 'identity');
    await page.getByLabel('Technician username').fill('synthetic-user');
    await page.getByRole('button', { name: 'Continue to facial login' }).click();
    await expect
      .poll(() => page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').begins))
      .toBe(1);
    // Focus the existing control explicitly: the original CLAIM submitter unmounts.
    // The decorative top-layer surface must not take focus from a real control.
    const cancel = page.getByRole('button', { name: 'Cancel', exact: true });
    await cancel.evaluate((button) => button.focus({ preventScroll: true }));
    const surface = page.locator('.face-id-morph-surface');
    if (reduced) await expect(surface).toHaveCount(0);
    else {
      await expect(surface).toHaveCount(1);
      await expect(surface).toHaveAttribute('aria-hidden', 'true');
      await expect(surface).toHaveCSS('pointer-events', 'none');
      expect(await surface.evaluate((element) => element.children.length)).toBe(0);
    }
    await expect(cancel).toBeFocused();
    // Escape acts during opening decoration, before the pending native begin resolves.
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.locator('.biometric-preview')).toHaveCount(0);
    await expect(surface).toHaveCount(0);
    await page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').releaseStart());
    await expect
      .poll(() =>
        page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').cancelled.length),
      )
      .toBe(1);
    expect(
      await page.evaluate(() => Reflect.get(window, '__ALICE_VISUAL_FIXTURE__').completions),
    ).toBe(0);
  });
}
