import { readdirSync, readFileSync, realpathSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from '../../apps/desktop/src/app/App';
import { MockAliceTransport } from '../../apps/desktop/src/lib/transport';
import { useConsole } from '../../apps/desktop/src/state/console';
import suppliedHold from '../../fixtures/legacy/decision.json';

const workspace = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const coreModule = /^(?:agent|cloud|common|dcamr|lab|protected_systems)(?:[./]|$)/;
const insideWorkspace = (path: string) => {
  const local = relative(workspace, path);
  return (
    !isAbsolute(local) &&
    /^(apps\/desktop|packages\/(contracts|domain|ui)|services\/biometrics|fixtures|node_modules)(\/|$)/.test(
      local,
    )
  );
};
const insideConsoleTools = (path: string) =>
  /^scripts\/(console|biometrics)\//.test(relative(workspace, path));
function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (['node_modules', 'target', 'dist', 'gen', '.venv', '__pycache__'].includes(entry.name))
      return [];
    const path = resolve(directory, entry.name);
    return entry.isDirectory() ? sourceFiles(path) : [path];
  });
}
const files = [
  'apps/desktop',
  'packages/contracts',
  'packages/domain',
  'packages/ui',
  'services/biometrics',
  'fixtures',
  'scripts/console',
  'scripts/biometrics',
].flatMap((directory) => sourceFiles(resolve(workspace, directory)));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it('keeps console and tooling imports inside their ownership boundaries', () => {
  const config = ts.readConfigFile(resolve(workspace, 'tsconfig.json'), ts.sys.readFile);
  const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, workspace);
  const imports: Array<{ file: string; name: string }> = [];
  for (const file of files.filter((path) => /\.(?:[cm]?[jt]s|[jt]sx)$/.test(path))) {
    const source = ts.createSourceFile(
      file,
      readFileSync(file, 'utf8'),
      ts.ScriptTarget.Latest,
      true,
    );
    const visit = (node: ts.Node) => {
      let specifier: ts.Node | undefined;
      if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node))
        specifier = node.moduleSpecifier;
      if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference))
        specifier = node.moduleReference.expression;
      if (
        ts.isCallExpression(node) &&
        (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
          (ts.isIdentifier(node.expression) && node.expression.text === 'require'))
      )
        specifier = node.arguments[0];
      if (specifier && ts.isStringLiteralLike(specifier))
        imports.push({ file, name: specifier.text });
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  expect(imports.length).toBeGreaterThan(0);
  for (const { file, name } of imports) {
    expect(name, `${relative(workspace, file)} imports core module ${name}`).not.toMatch(
      coreModule,
    );
    const result = ts.resolveModuleName(name, file, parsed.options, ts.sys).resolvedModule;
    // Checking the resolved path also catches aliases that reach a sibling core module.
    if (result) {
      const resolved = realpathSync(result.resolvedFileName);
      expect(
        insideWorkspace(resolved) || (insideConsoleTools(file) && insideConsoleTools(resolved)),
        `${file}: ${name}`,
      ).toBe(true);
    }
    if (name.startsWith('.') && name.endsWith('.css')) {
      expect(insideWorkspace(realpathSync(resolve(dirname(file), name))), `${file}: ${name}`).toBe(
        true,
      );
      continue;
    }
    if (name.startsWith('.') || name.startsWith('@/') || name.startsWith('@alice/'))
      expect(result, `${file}: unresolved local import ${name}`).toBeDefined();
  }
});

it('keeps native and biometric source independent of core implementations', () => {
  for (const file of files.filter((path) => path.endsWith('.py'))) {
    const source = readFileSync(file, 'utf8');
    for (const match of source.matchAll(/^\s*(?:from\s+([\w.]+)\s+import|import\s+([^#\n]+))/gm)) {
      for (const module of (match[1] ?? match[2]!).split(','))
        expect(module.trim(), relative(workspace, file)).not.toMatch(coreModule);
    }
    // Smoke scripts and conftest intentionally add the service's own app directory.
    if (relative(workspace, file).startsWith('services/biometrics/app/'))
      expect(source, relative(workspace, file)).not.toMatch(/sys\.path\.(?:append|insert)/);
  }
  for (const file of files.filter((path) => path.endsWith('.rs') || path.endsWith('Cargo.toml'))) {
    const source = readFileSync(file, 'utf8');
    const paths = file.endsWith('.rs')
      ? source.matchAll(/include(?:_str|_bytes)?!\s*\(\s*"([^"]+)"/g)
      : source.matchAll(/\bpath\s*=\s*"([^"]+)"/g);
    for (const match of paths)
      expect(insideWorkspace(resolve(dirname(file), match[1]!)), `${file}: ${match[1]}`).toBe(true);
    if (file.endsWith('.rs'))
      expect(source, relative(workspace, file)).not.toMatch(
        /\b(?:use|extern crate)\s+(?:dcamr|protected_systems|policy_engine|anomaly_engine)\b/,
      );
  }
});

it('renders the migrated HOLD and submits only an exact-request mock APPROVE_ONCE', async () => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
  };
  const submitted = vi.spyOn(MockAliceTransport.prototype, 'submitTechnicianAction');
  render(<App />);
  const approve = await screen.findByRole('button', { name: 'Approve once' });
  await waitFor(() => expect(approve).toBeEnabled());
  expect(screen.getByRole('heading', { name: 'HOLD' })).toBeInTheDocument();
  expect(screen.getByRole('img', { name: 'Behavioral risk 94 of 100, HIGH' })).toBeInTheDocument();
  const before = structuredClone(useConsole.getState().decisions[suppliedHold.decision_id]);
  fireEvent.click(approve);
  fireEvent.click(screen.getByRole('button', { name: 'Simulate pass' }));
  await screen.findByRole('heading', { name: 'Approval submitted' });
  expect(submitted).toHaveBeenCalledTimes(1);
  const action = submitted.mock.calls[0]![0];
  expect(action).toMatchObject({
    event_type: 'alice.technician_action',
    action: 'APPROVE_ONCE',
    decision_id: suppliedHold.decision_id,
    request_id: suppliedHold.request.request_id,
    technician_id: 'TECH-DEMO',
    mode: 'mock',
    biometric_verification_id: expect.any(String),
  });
  expect(useConsole.getState().receipts[action.decision_id]).toMatchObject({
    action_id: action.action_id,
    status: 'ACCEPTED',
    execution_status: 'NOT_EXECUTED',
  });
  expect(useConsole.getState().decisions[action.decision_id]).toEqual(before);
  expect(approve).toBeDisabled();
});
