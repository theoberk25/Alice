import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';
export default defineConfig({
  resolve: {
    alias: {
      '@alice/contracts': resolve('packages/contracts/src/index.ts'),
      '@alice/domain': resolve('packages/domain/src/index.ts'),
      '@alice/ui': resolve('packages/ui/src/index.tsx'),
      '@': resolve('apps/desktop/src'),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['tests/console/**/*.test.{ts,tsx}'],
    setupFiles: ['tests/console/setup.ts'],
  },
});
