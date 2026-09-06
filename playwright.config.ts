import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: 'tests/console/e2e',
  testMatch: [
    'console.spec.ts',
    'runtime-review.spec.ts',
    'visual.spec.ts',
    'visual-refinements.spec.ts',
  ],
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:1420',
    ...devices['Desktop Chrome'],
    channel: process.env.ALICE_TEST_BROWSER_CHANNEL,
    viewport: { width: 1512, height: 1040 },
    screenshot: 'only-on-failure',
  },
  webServer: { command: 'npm run dev', url: 'http://127.0.0.1:1420', reuseExistingServer: false },
  reporter: 'list',
});
