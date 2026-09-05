import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: 'tests/console/e2e',
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:1420',
    ...devices['Desktop Chrome'],
    viewport: { width: 1512, height: 1040 },
    screenshot: 'only-on-failure',
  },
  webServer: { command: 'npm run dev', url: 'http://127.0.0.1:1420', reuseExistingServer: true },
  reporter: 'list',
});
