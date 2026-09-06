import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: 'tests/console/e2e',
  testMatch: 'runtime.spec.ts',
  workers: 1,
  timeout: 45000,
  reporter: 'list',
  outputDir: '/tmp/alice-live-e2e-results',
  use: {
    channel: process.env.ALICE_TEST_BROWSER_CHANNEL,
    headless: true,
    viewport: { width: 1512, height: 1040 },
  },
});
