import process from 'node:process';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
const root = resolve(import.meta.dirname, '..'),
  cargo = resolve(root, '.tools/cargo');
const env = { ...process.env };
if (existsSync(cargo)) {
  env.CARGO_HOME = cargo;
  env.RUSTUP_HOME = resolve(root, '.tools/rustup');
  env.PATH = `${cargo}/bin:${env.PATH}`;
}
const args = process.argv.slice(2);
if (!args.length) args.push('test');
spawn('cargo', args, { cwd: resolve(root, 'apps/desktop/src-tauri'), env, stdio: 'inherit' }).on(
  'exit',
  (code) => process.exit(code ?? 1),
);
