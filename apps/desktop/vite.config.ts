import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  envDir: fileURLToPath(new URL('../..', import.meta.url)),
  plugins: [react()],
  clearScreen: false,
  resolve: {
    alias: {
      '@alice/contracts': fileURLToPath(
        new URL('../../packages/contracts/src/index.ts', import.meta.url),
      ),
      '@alice/domain': fileURLToPath(
        new URL('../../packages/domain/src/index.ts', import.meta.url),
      ),
      '@alice/ui': fileURLToPath(new URL('../../packages/ui/src/index.tsx', import.meta.url)),
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 1420,
    strictPort: true,
    watch: { ignored: ['**/src-tauri/**'] },
  },
  build: { target: 'es2022' },
});
