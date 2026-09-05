import process from 'node:process';
import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { URL } from 'node:url';
const root = resolve(import.meta.dirname, '..');
if (existsSync(resolve(root, '.env')))
  for (const line of readFileSync(resolve(root, '.env'), 'utf8').split(/\r?\n/)) {
    const match = line.match(/^([A-Z][A-Z0-9_]*)=(.*)$/);
    if (match && process.env[match[1]] === undefined)
      process.env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
process.env.ALICE_BIOMETRIC_DATA_DIR ||= resolve(root, 'services/biometrics/data');
process.env.ALICE_INSIGHTFACE_ROOT ||= resolve(root, 'services/biometrics/models');
const serviceUrl = new URL(process.env.ALICE_BIOMETRIC_SERVICE_URL || 'http://127.0.0.1:8765');
if (
  serviceUrl.protocol !== 'http:' ||
  !['127.0.0.1', 'localhost', '[::1]'].includes(serviceUrl.hostname) ||
  serviceUrl.username ||
  serviceUrl.password ||
  serviceUrl.pathname !== '/' ||
  serviceUrl.search ||
  serviceUrl.hash
)
  throw new Error('ALICE_BIOMETRIC_SERVICE_URL must be a loopback HTTP origin.');
const serviceHost = serviceUrl.hostname === '[::1]' ? '::1' : '127.0.0.1';
const servicePort = serviceUrl.port || '80';
const child = spawn(
  resolve(root, 'services/biometrics/.venv/bin/python'),
  ['-m', 'uvicorn', 'app.main:app', '--host', serviceHost, '--port', servicePort],
  { cwd: resolve(root, 'services/biometrics'), env: process.env, stdio: 'inherit' },
);
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', (code) => process.exit(code ?? 1));
