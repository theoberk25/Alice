import process from 'node:process';
import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { consoleRoot as root } from './paths.mjs';
// Load dotenv-style KEY=value entries without evaluating shell expressions.
if (existsSync(resolve(root, '.env')))
  for (const line of readFileSync(resolve(root, '.env'), 'utf8').split(/\r?\n/)) {
    const match = line.match(/^([A-Z][A-Z0-9_]*)=(.*)$/);
    if (match && process.env[match[1]] === undefined)
      process.env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
const localCargo = resolve(root, '.tools/cargo');
if (existsSync(localCargo)) {
  process.env.CARGO_HOME = localCargo;
  process.env.RUSTUP_HOME = resolve(root, '.tools/rustup');
  process.env.PATH = `${localCargo}/bin:${process.env.PATH}`;
}
const args = process.argv.slice(2);
if (!args.length) args.push('dev');
if (args[0] === 'dev') {
  try {
    const response = await fetch('http://127.0.0.1:1420', { signal: AbortSignal.timeout(500) });
    if (response.ok) args.push('--config', JSON.stringify({ build: { beforeDevCommand: '' } }));
  } catch {
    /* Tauri will start Vite when it is not already listening. */
  }
}
process.env.ALICE_TRANSPORT_MODE ??= 'mock';
const child = spawn(resolve(root, 'node_modules/.bin/tauri'), args, {
  cwd: resolve(root, 'apps/desktop'),
  env: process.env,
  stdio: 'inherit',
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', (code) => process.exit(code ?? 1));
