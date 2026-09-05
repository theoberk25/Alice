import js from '@eslint/js';
import ts from 'typescript-eslint';
export default ts.config(
  {
    ignores: [
      '**/dist/**',
      '**/target/**',
      '**/.venv/**',
      '.tools/**',
      'test-results/**',
      'playwright-report/**',
      'apps/desktop/src-tauri/gen/**',
    ],
  },
  js.configs.recommended,
  {
    files: ['scripts/**/*.mjs'],
    languageOptions: {
      globals: { fetch: 'readonly', AbortSignal: 'readonly', console: 'readonly', URL: 'readonly' },
    },
  },
  ...ts.configs.recommended,
  { files: ['**/*.{ts,tsx}'], rules: { '@typescript-eslint/no-explicit-any': 'error' } },
);
