import assert from 'node:assert/strict';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import {
  cpSync,
  mkdirSync,
  mkdtempSync,
  realpathSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { repositoryRoot } from '../paths.mjs';

function fixture(t) {
  const temporary = realpathSync(mkdtempSync(resolve(tmpdir(), 'alice console ')));
  t.after(() => rmSync(temporary, { recursive: true, force: true }));
  const root = resolve(temporary, 'checkout with spaces');
  const workstation = root;
  for (const area of ['console', 'biometrics'])
    cpSync(resolve(repositoryRoot, 'scripts', area), resolve(root, 'scripts', area), {
      recursive: true,
    });
  for (const directory of ['apps/desktop/src-tauri', 'services/biometrics', '.tools/rustup'])
    mkdirSync(resolve(workstation, directory), { recursive: true });
  writeFileSync(
    resolve(workstation, 'package.json'),
    JSON.stringify({ name: 'alice-technician-console', type: 'module' }),
  );
  writeFileSync(resolve(workstation, '.env'), 'ALICE_RELOCATION_TEST=from-checkout\n');
  const output = resolve(temporary, 'child.json');
  const executable = `#!/usr/bin/env node
import('node:fs').then(({ writeFileSync }) => writeFileSync(process.env.ALICE_TEST_OUTPUT, JSON.stringify({
  cwd: process.cwd(), args: process.argv.slice(2),
  data: process.env.ALICE_BIOMETRIC_DATA_DIR, models: process.env.ALICE_INSIGHTFACE_ROOT,
  cargo: process.env.CARGO_HOME, rustup: process.env.RUSTUP_HOME,
  dotenv: process.env.ALICE_RELOCATION_TEST,
})));
`;
  for (const binary of [
    'node_modules/.bin/tauri',
    '.tools/cargo/bin/cargo',
    'services/biometrics/.venv/bin/python',
  ]) {
    const path = resolve(workstation, binary);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, executable, { mode: 0o755 });
  }
  const env = { ...process.env, ALICE_TEST_OUTPUT: output };
  for (const name of [
    'ALICE_BIOMETRIC_DATA_DIR',
    'ALICE_INSIGHTFACE_ROOT',
    'ALICE_BIOMETRIC_SERVICE_URL',
    'ALICE_RELOCATION_TEST',
  ])
    delete env[name];
  function run(script, args = [], overrides = {}) {
    const result = spawnSync(process.execPath, [resolve(root, script), ...args], {
      cwd: temporary,
      env: { ...env, ...overrides },
      encoding: 'utf8',
      timeout: 10000,
    });
    assert.equal(result.status, 0, result.stderr);
    return JSON.parse(readFileSync(output, 'utf8'));
  }
  return { root, workstation, temporary, run };
}

test('desktop launcher preserves native cwd, local toolchain and dotenv in a copied checkout', (t) => {
  const { workstation, run } = fixture(t);
  const child = run('scripts/console/desktop.mjs', ['build', '--bundles', 'app']);
  assert.equal(child.cwd, resolve(workstation, 'apps/desktop'));
  assert.deepEqual(child.args, ['build', '--bundles', 'app']);
  assert.equal(child.cargo, resolve(workstation, '.tools/cargo'));
  assert.equal(child.rustup, resolve(workstation, '.tools/rustup'));
  assert.equal(child.dotenv, 'from-checkout');
});

test('Rust launcher forwards arguments to the original native package', (t) => {
  const { workstation, run } = fixture(t);
  const child = run('scripts/console/rust.mjs', ['test', 'example', '--', '--ignored']);
  assert.equal(child.cwd, resolve(workstation, 'apps/desktop/src-tauri'));
  assert.deepEqual(child.args, ['test', 'example', '--', '--ignored']);
  assert.equal(child.cargo, resolve(workstation, '.tools/cargo'));
});

test('biometric launcher retains service, model and store paths and respects overrides', (t) => {
  const { workstation, temporary, run } = fixture(t);
  const child = run('scripts/biometrics/biometrics.mjs');
  assert.equal(child.cwd, resolve(workstation, 'services/biometrics'));
  assert.equal(child.data, resolve(workstation, 'services/biometrics/data'));
  assert.equal(child.models, resolve(workstation, 'services/biometrics/models'));
  assert.deepEqual(child.args, [
    '-m',
    'uvicorn',
    'app.main:app',
    '--host',
    '127.0.0.1',
    '--port',
    '8765',
  ]);
  assert.equal(child.dotenv, 'from-checkout');
  const custom = run('scripts/biometrics/biometrics.mjs', [], {
    ALICE_BIOMETRIC_DATA_DIR: resolve(temporary, 'private store'),
    ALICE_INSIGHTFACE_ROOT: resolve(temporary, 'private models'),
    ALICE_BIOMETRIC_SERVICE_URL: 'http://[::1]:9876',
    ALICE_RELOCATION_TEST: 'from-shell',
  });
  assert.equal(custom.data, resolve(temporary, 'private store'));
  assert.equal(custom.models, resolve(temporary, 'private models'));
  assert.equal(custom.dotenv, 'from-shell');
  assert.deepEqual(custom.args.slice(-4), ['--host', '::1', '--port', '9876']);
});

test('Python model/service lookup follows the copied checkout from an unrelated cwd', (t) => {
  const { root, workstation, temporary } = fixture(t);
  const probe = resolve(root, 'scripts/biometrics/probe.py');
  writeFileSync(probe, 'from console_paths import CONSOLE_ROOT\nprint(CONSOLE_ROOT)\n');
  const result = spawnSync('python3', [probe], { cwd: temporary, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), workstation);
});
