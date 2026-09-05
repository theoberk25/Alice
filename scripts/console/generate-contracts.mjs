import process from 'node:process';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { consoleRoot } from './paths.mjs';

const child = spawn(
  resolve(consoleRoot, 'node_modules/.bin/vite-node'),
  [
    '--config',
    resolve(consoleRoot, 'vitest.config.ts'),
    fileURLToPath(new URL('./generate-contracts.ts', import.meta.url)),
  ],
  { cwd: consoleRoot, env: process.env, stdio: 'inherit' },
);
child.on('error', (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
child.on('exit', (code) => process.exit(code ?? 1));
