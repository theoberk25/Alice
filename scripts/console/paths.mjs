import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Discover the checkout from this module, never from the caller's working directory.
export function findRepositoryRoot(start = dirname(fileURLToPath(import.meta.url))) {
  for (let candidate = resolve(start); ; candidate = dirname(candidate)) {
    const manifest = resolve(candidate, 'package.json');
    if (
      existsSync(manifest) &&
      JSON.parse(readFileSync(manifest, 'utf8')).name === 'alice-technician-console'
    )
      return candidate;
    if (dirname(candidate) === candidate) throw new Error('ALICE console checkout not found.');
  }
}

export const repositoryRoot = findRepositoryRoot();
export const consoleRoot = repositoryRoot;
