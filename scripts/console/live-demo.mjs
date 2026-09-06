// Explicit synthetic session. No saved database, key or environment is replaced.
import process from 'node:process';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { consoleRoot as root } from './paths.mjs';
const token = randomBytes(32).toString('hex');
const directory = join(tmpdir(), `alice-synthetic-${randomBytes(6).toString('hex')}`);
const python = process.env.ALICE_TEST_PYTHON ?? resolve(root, '.venv/bin/python');
const driver = spawn(python, ['-m', 'lab.first_light.live_demo', '--directory', directory], {
  cwd: root,
  env: { ...process.env, ALICE_FEED_TOKEN: token },
  stdio: ['pipe', 'pipe', 'inherit'],
});
let vite;
const lines = createInterface({ input: driver.stdout });
let ready = false;
lines.on('line', (line) => {
  if (ready) {
    console.log(line);
    return;
  }
  ready = true;
  const info = JSON.parse(line);
  const port = process.env.ALICE_DEMO_PORT ?? '1422';
  vite = spawn(
    process.execPath,
    ['node_modules/vite/bin/vite.js', '--config', 'apps/desktop/vite.config.ts', '--port', port],
    {
      cwd: root,
      env: {
        ...process.env,
        VITE_ALICE_PREVIEW_MODE: 'remote',
        ALICE_FEED_TOKEN: token,
        ALICE_FEED_URL: `http://127.0.0.1:${info.bridge}`,
      },
      stdio: ['ignore', 'inherit', 'inherit'],
    },
  );
  console.log(
    `SYNTHETIC SESSION: http://127.0.0.1:${port}\nSQLite: ${info.database}\nType on, off or deny and press Enter to submit a signed runtime request. Type stop to finish.\nFixture assessment + mock controller; no physical Pi/USB claims.`,
  );
  vite.on('exit', () => driver.stdin.end('stop\n'));
  vite.on('error', (error) => {
    console.error(error.message);
    driver.stdin.end('stop\n');
  });
});
process.stdin.on('data', (data) => {
  if (driver.stdin.writable) driver.stdin.write(data);
});
process.stdin.on('end', () => driver.stdin.end('stop\n'));
driver.on('exit', (code) => {
  vite?.kill();
  process.exit(code ?? 1);
});
driver.on('error', (error) => {
  console.error(error.message);
  process.exit(1);
});
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, () => {
    vite?.kill();
    driver.kill(signal);
  });
