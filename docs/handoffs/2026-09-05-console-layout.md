# Technician console shared-layout migration — 2026-09-05

Baseline: `ce617cf` on main, matching the locally available origin/main revision.
Review branch: `codex/technician-console-layout`. Explicit user direction authorized
both script dependency repairs and removal of the entire workstation tree.
The user subsequently authorized committing the migration to local main.
No push or deployment is part of this change.

## Result and dependency boundaries

The workstation directory is removed. The npm manifest, lock and discovery-based
launchers operate from the repository root. Node workspace membership explicitly
lists the desktop and three console packages so unrelated package placeholders
are not interpreted as npm workspaces. Console tests live in tests/console;
Vite aliases, TypeScript, lint, formatting and Playwright target the new layout.
Scripts live in scripts/console and scripts/biometrics. Python script filenames
now use snake_case. Launchers can be called by absolute path from any cwd.

Native app identifiers, protocol fields, approval behavior and model/service
contracts are unchanged. UI imports remain confined to console packages and
installed dependencies. Core policy, anomaly and execution modules are not
imported into the renderer. Generated contracts stay under docs/contracts and
fixtures stay under fixtures. Legacy empty scaffolds are preserved under
apps/dashboard, services/backend and services/face_verification.

## Local state

Installed node_modules, .tools, .env, Python virtualenv, models, enrollment data,
ignored native build products and caches moved with their owning directories.
No private values were printed or added to Git. The biometric venv's text entry
points/activation metadata and a local Rust setup file had embedded old paths
repaired. npm workspace symlinks still resolve to the moved packages. Default
service paths are now services/biometrics/{models,data}; explicit overrides remain
supported. Native macOS Application Support data stays outside the repository.

Former workstation/artifacts moved to artifacts/console. New browser evidence
uses artifacts/console/verification/screenshots. Former workstation/.DS_Store
and :memory:.ses were preserved under artifacts/local-state/console. Root ignore
rules cover console private/generated files without hiding published enterprise
artifacts. The original console ignore policy is preserved as
[console-original.gitignore](2026-09-05-console-original.gitignore).

## Verification

- `npm run check`: strict TypeScript, lint, 64 Vitest tests, four copied-checkout
  launcher tests and production frontend build passed. The copied checkout has
  spaces in its path and runs commands from an unrelated cwd; it verifies native
  cwd, toolchain, dotenv, Python service/model/store paths and environment overrides.
- `npm run test:rust`: 14 passed, two real-service tests ignored by default.
- `npm run test:python`: 11 passed; dependency deprecation warnings only.
- `PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright" npm run test:e2e -- --config
  .tools/migration-playwright.config.ts`: five passed on isolated port 1421.
  Initial sandbox port denial was resolved with local-server execution permission.
- `NO_ALBUMENTATIONS_UPDATE=1 MPLCONFIGDIR=/tmp/alice-matplotlib
  services/biometrics/.venv/bin/python scripts/biometrics/smoke_arcface.py`: real
  public-image enrollment/matching and blank/multiple-face rejection passed.
- `NO_ALBUMENTATIONS_UPDATE=1 services/biometrics/.venv/bin/python
  scripts/biometrics/smoke_native_identity.py`: isolated loopback service/native
  enrollment, login, revocation, fresh approval and cleanup passed after permitting
  the local test server. Uses temporary private state and public test images.
- `npm run build:app`: release compilation and ALICE.app bundling passed at
  apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app.
- Core regression: **257 passed, zero skips**, using the root Python 3.11 venv
  with PYTHONPATH pointing at the relocated biometric Python 3.11 site-packages.
  System python3 lacked jsonschema; the root venv alone lacked cryptography.
  The successful command was `PYTHONPATH="$PWD/services/biometrics/.venv/lib/python3.11/site-packages"
  .venv/bin/python -m unittest discover`; no dependency installation was needed.
- Absolute-path `node scripts/console/generate-contracts.mjs` from /tmp succeeded:
  all nine generated schema/fixture objects matched the original JSON. Generation
  reformats three schemas; published bytes were restored after this comparison.
- All 369 original tracked paths survive either in place or at their mapped
  destinations. 150 paths moved; 114 moved files are byte-identical. Changes to
  the others are documented links, launch/config paths, test imports, and the
  missing-model setup hint. Original fixtures and schemas remain byte-identical.

Live camera/liveness, authenticated upstream transport and physical execution
remain separate operator/integration acceptance. Historical lab migration evidence
remains in [the lab relocation record](2026-09-05-lab-script-relocation.md), including
its prior 257-test result; it is not a current console integration claim.

## Complete tracked move map

Old paths below are historical names. No compatibility directory or duplicate
implementation remains at workstation/.

| Old path | New path |
| --- | --- |
| `scripts/workstation/README.md` | `scripts/console/README.md` |
| `workstation/.env.example` | `.env.example` |
| `workstation/.gitignore` | `docs/handoffs/2026-09-05-console-original.gitignore` |
| `workstation/.prettierignore` | `.prettierignore` |
| `workstation/.prettierrc.json` | `.prettierrc.json` |
| `workstation/CONTRIBUTING.md` | `docs/guides/console-contributing.md` |
| `workstation/HANDOFF.md` | `docs/handoffs/2026-09-05-console-handoff.md` |
| `workstation/PROMPT_CONTEXT.md` | `docs/guides/console/prompt-context.md` |
| `workstation/README.md` | `docs/guides/technician-console.md` |
| `workstation/apps/desktop/index.html` | `apps/desktop/index.html` |
| `workstation/apps/desktop/package.json` | `apps/desktop/package.json` |
| `workstation/apps/desktop/src-tauri/Cargo.lock` | `apps/desktop/src-tauri/Cargo.lock` |
| `workstation/apps/desktop/src-tauri/Cargo.toml` | `apps/desktop/src-tauri/Cargo.toml` |
| `workstation/apps/desktop/src-tauri/Entitlements.plist` | `apps/desktop/src-tauri/Entitlements.plist` |
| `workstation/apps/desktop/src-tauri/Info.plist` | `apps/desktop/src-tauri/Info.plist` |
| `workstation/apps/desktop/src-tauri/build.rs` | `apps/desktop/src-tauri/build.rs` |
| `workstation/apps/desktop/src-tauri/capabilities/default.json` | `apps/desktop/src-tauri/capabilities/default.json` |
| `workstation/apps/desktop/src-tauri/icons/128x128.png` | `apps/desktop/src-tauri/icons/128x128.png` |
| `workstation/apps/desktop/src-tauri/icons/128x128@2x.png` | `apps/desktop/src-tauri/icons/128x128@2x.png` |
| `workstation/apps/desktop/src-tauri/icons/32x32.png` | `apps/desktop/src-tauri/icons/32x32.png` |
| `workstation/apps/desktop/src-tauri/icons/app-icon.svg` | `apps/desktop/src-tauri/icons/app-icon.svg` |
| `workstation/apps/desktop/src-tauri/icons/icon.icns` | `apps/desktop/src-tauri/icons/icon.icns` |
| `workstation/apps/desktop/src-tauri/src/commands.rs` | `apps/desktop/src-tauri/src/commands.rs` |
| `workstation/apps/desktop/src-tauri/src/commands_tests.rs` | `apps/desktop/src-tauri/src/commands_tests.rs` |
| `workstation/apps/desktop/src-tauri/src/config.rs` | `apps/desktop/src-tauri/src/config.rs` |
| `workstation/apps/desktop/src-tauri/src/db.rs` | `apps/desktop/src-tauri/src/db.rs` |
| `workstation/apps/desktop/src-tauri/src/lib.rs` | `apps/desktop/src-tauri/src/lib.rs` |
| `workstation/apps/desktop/src-tauri/src/main.rs` | `apps/desktop/src-tauri/src/main.rs` |
| `workstation/apps/desktop/src-tauri/src/security.rs` | `apps/desktop/src-tauri/src/security.rs` |
| `workstation/apps/desktop/src-tauri/tauri.conf.json` | `apps/desktop/src-tauri/tauri.conf.json` |
| `workstation/apps/desktop/src/app/App.tsx` | `apps/desktop/src/app/App.tsx` |
| `workstation/apps/desktop/src/components/agents/AgentsPanel.tsx` | `apps/desktop/src/components/agents/AgentsPanel.tsx` |
| `workstation/apps/desktop/src/components/audit/History.tsx` | `apps/desktop/src/components/audit/History.tsx` |
| `workstation/apps/desktop/src/components/biometrics/ApprovalModal.tsx` | `apps/desktop/src/components/biometrics/ApprovalModal.tsx` |
| `workstation/apps/desktop/src/components/biometrics/CameraCapture.tsx` | `apps/desktop/src/components/biometrics/CameraCapture.tsx` |
| `workstation/apps/desktop/src/components/command/CommandPanel.tsx` | `apps/desktop/src/components/command/CommandPanel.tsx` |
| `workstation/apps/desktop/src/components/decisions/DecisionLineage.tsx` | `apps/desktop/src/components/decisions/DecisionLineage.tsx` |
| `workstation/apps/desktop/src/components/decisions/DecisionWorkspace.tsx` | `apps/desktop/src/components/decisions/DecisionWorkspace.tsx` |
| `workstation/apps/desktop/src/components/decisions/ResearchModal.tsx` | `apps/desktop/src/components/decisions/ResearchModal.tsx` |
| `workstation/apps/desktop/src/components/evidence/EvidencePanel.tsx` | `apps/desktop/src/components/evidence/EvidencePanel.tsx` |
| `workstation/apps/desktop/src/components/layout/Header.tsx` | `apps/desktop/src/components/layout/Header.tsx` |
| `workstation/apps/desktop/src/components/layout/SettingsModal.tsx` | `apps/desktop/src/components/layout/SettingsModal.tsx` |
| `workstation/apps/desktop/src/components/status/SystemPanel.tsx` | `apps/desktop/src/components/status/SystemPanel.tsx` |
| `workstation/apps/desktop/src/components/technicians/AdminPanel.tsx` | `apps/desktop/src/components/technicians/AdminPanel.tsx` |
| `workstation/apps/desktop/src/components/technicians/IdentityPanel.tsx` | `apps/desktop/src/components/technicians/IdentityPanel.tsx` |
| `workstation/apps/desktop/src/features/biometrics/verify.ts` | `apps/desktop/src/features/biometrics/verify.ts` |
| `workstation/apps/desktop/src/lib/llm.ts` | `apps/desktop/src/lib/llm.ts` |
| `workstation/apps/desktop/src/lib/native.ts` | `apps/desktop/src/lib/native.ts` |
| `workstation/apps/desktop/src/lib/transport.ts` | `apps/desktop/src/lib/transport.ts` |
| `workstation/apps/desktop/src/main.tsx` | `apps/desktop/src/main.tsx` |
| `workstation/apps/desktop/src/state/console.ts` | `apps/desktop/src/state/console.ts` |
| `workstation/apps/desktop/src/styles/global.css` | `apps/desktop/src/styles/global.css` |
| `workstation/apps/desktop/src/styles/tokens.css` | `apps/desktop/src/styles/tokens.css` |
| `workstation/apps/desktop/vite.config.ts` | `apps/desktop/vite.config.ts` |
| `workstation/backend/__init__.py` | `services/backend/__init__.py` |
| `workstation/backend/dcamr_gateway.py` | `services/backend/dcamr_gateway.py` |
| `workstation/backend/llm_explainer.py` | `services/backend/llm_explainer.py` |
| `workstation/backend/server.py` | `services/backend/server.py` |
| `workstation/dashboard/index.html` | `apps/dashboard/index.html` |
| `workstation/dashboard/package.json` | `apps/dashboard/package.json` |
| `workstation/dashboard/src/App.jsx` | `apps/dashboard/src/App.jsx` |
| `workstation/dashboard/src/DecisionView.jsx` | `apps/dashboard/src/DecisionView.jsx` |
| `workstation/dashboard/src/ProvenanceTable.jsx` | `apps/dashboard/src/ProvenanceTable.jsx` |
| `workstation/dashboard/src/RawDecisionViewer.jsx` | `apps/dashboard/src/RawDecisionViewer.jsx` |
| `workstation/dashboard/src/SwarmView.jsx` | `apps/dashboard/src/SwarmView.jsx` |
| `workstation/dashboard/src/TechnicianControls.jsx` | `apps/dashboard/src/TechnicianControls.jsx` |
| `workstation/dashboard/src/api.js` | `apps/dashboard/src/api.js` |
| `workstation/docs/architecture/biometrics.md` | `docs/architecture/biometrics.md` |
| `workstation/docs/architecture/hold-workflow.md` | `docs/architecture/hold-workflow.md` |
| `workstation/docs/architecture/llm-boundary.md` | `docs/architecture/llm-boundary.md` |
| `workstation/docs/architecture/overview.md` | `docs/architecture/overview.md` |
| `workstation/docs/contracts/agent-status.md` | `docs/contracts/agent-status.md` |
| `workstation/docs/contracts/agent-status.schema.json` | `docs/contracts/agent-status.schema.json` |
| `workstation/docs/contracts/alice-events.md` | `docs/contracts/alice-events.md` |
| `workstation/docs/contracts/alice-events.schema.json` | `docs/contracts/alice-events.schema.json` |
| `workstation/docs/contracts/context-request.schema.json` | `docs/contracts/context-request.schema.json` |
| `workstation/docs/contracts/legacy-dashboard-contract.md` | `docs/contracts/legacy-dashboard-contract.md` |
| `workstation/docs/contracts/technician-action.schema.json` | `docs/contracts/technician-action.schema.json` |
| `workstation/docs/development/facial-verification-quickstart.md` | `docs/guides/console/facial-verification-quickstart.md` |
| `workstation/docs/development/mac-setup.md` | `docs/guides/console/mac-setup.md` |
| `workstation/docs/development/mock-scenarios.md` | `docs/guides/console/mock-scenarios.md` |
| `workstation/docs/development/verification.md` | `docs/guides/console/verification.md` |
| `workstation/docs/integration/main-repository-migration.md` | `docs/integration/main-repository-migration.md` |
| `workstation/docs/integration/upstream-alice.md` | `docs/integration/upstream-alice.md` |
| `workstation/eslint.config.js` | `eslint.config.js` |
| `workstation/face_verification/__init__.py` | `services/face_verification/__init__.py` |
| `workstation/face_verification/arcface.py` | `services/face_verification/arcface.py` |
| `workstation/face_verification/camera.py` | `services/face_verification/camera.py` |
| `workstation/face_verification/enroll.py` | `services/face_verification/enroll.py` |
| `workstation/face_verification/enrolled/.gitkeep` | `services/face_verification/enrolled/.gitkeep` |
| `workstation/face_verification/face_detect.py` | `services/face_verification/face_detect.py` |
| `workstation/face_verification/verify.py` | `services/face_verification/verify.py` |
| `workstation/fixtures/alice/agent-status.json` | `fixtures/alice/agent-status.json` |
| `workstation/fixtures/alice/decision.json` | `fixtures/alice/decision.json` |
| `workstation/fixtures/alice/reassessment.json` | `fixtures/alice/reassessment.json` |
| `workstation/fixtures/alice/reconciliation.json` | `fixtures/alice/reconciliation.json` |
| `workstation/fixtures/alice/status.json` | `fixtures/alice/status.json` |
| `workstation/fixtures/legacy/dashboard-contract.original.txt` | `fixtures/legacy/dashboard-contract.original.txt` |
| `workstation/fixtures/legacy/decision.json` | `fixtures/legacy/decision.json` |
| `workstation/fixtures/legacy/reconciliation.json` | `fixtures/legacy/reconciliation.json` |
| `workstation/fixtures/legacy/status.json` | `fixtures/legacy/status.json` |
| `workstation/fixtures/scenarios/index.ts` | `fixtures/scenarios/index.ts` |
| `workstation/package-lock.json` | `package-lock.json` |
| `workstation/package.json` | `package.json` |
| `workstation/packages/contracts/package.json` | `packages/contracts/package.json` |
| `workstation/packages/contracts/src/adapters/legacy.ts` | `packages/contracts/src/adapters/legacy.ts` |
| `workstation/packages/contracts/src/alice/commands.ts` | `packages/contracts/src/alice/commands.ts` |
| `workstation/packages/contracts/src/alice/events.ts` | `packages/contracts/src/alice/events.ts` |
| `workstation/packages/contracts/src/index.ts` | `packages/contracts/src/index.ts` |
| `workstation/packages/contracts/src/legacy/schemas.ts` | `packages/contracts/src/legacy/schemas.ts` |
| `workstation/packages/domain/package.json` | `packages/domain/package.json` |
| `workstation/packages/domain/src/biometrics.ts` | `packages/domain/src/biometrics.ts` |
| `workstation/packages/domain/src/hold.ts` | `packages/domain/src/hold.ts` |
| `workstation/packages/domain/src/index.ts` | `packages/domain/src/index.ts` |
| `workstation/packages/domain/src/lineage.ts` | `packages/domain/src/lineage.ts` |
| `workstation/packages/domain/src/llm.ts` | `packages/domain/src/llm.ts` |
| `workstation/packages/domain/src/transport.ts` | `packages/domain/src/transport.ts` |
| `workstation/packages/ui/package.json` | `packages/ui/package.json` |
| `workstation/packages/ui/src/index.tsx` | `packages/ui/src/index.tsx` |
| `workstation/playwright.config.ts` | `playwright.config.ts` |
| `workstation/scripts/biometrics.mjs` | `scripts/biometrics/biometrics.mjs` |
| `workstation/scripts/desktop.mjs` | `scripts/console/desktop.mjs` |
| `workstation/scripts/generate-contracts.ts` | `scripts/console/generate-contracts.ts` |
| `workstation/scripts/rust.mjs` | `scripts/console/rust.mjs` |
| `workstation/scripts/setup-model.py` | `scripts/biometrics/setup_model.py` |
| `workstation/scripts/smoke-arcface.py` | `scripts/biometrics/smoke_arcface.py` |
| `workstation/scripts/smoke-native-identity.py` | `scripts/biometrics/smoke_native_identity.py` |
| `workstation/services/biometrics/README.md` | `services/biometrics/README.md` |
| `workstation/services/biometrics/app/__init__.py` | `services/biometrics/app/__init__.py` |
| `workstation/services/biometrics/app/config.py` | `services/biometrics/app/config.py` |
| `workstation/services/biometrics/app/engine.py` | `services/biometrics/app/engine.py` |
| `workstation/services/biometrics/app/imaging.py` | `services/biometrics/app/imaging.py` |
| `workstation/services/biometrics/app/main.py` | `services/biometrics/app/main.py` |
| `workstation/services/biometrics/app/schemas.py` | `services/biometrics/app/schemas.py` |
| `workstation/services/biometrics/app/storage.py` | `services/biometrics/app/storage.py` |
| `workstation/services/biometrics/requirements-lock.txt` | `services/biometrics/requirements-lock.txt` |
| `workstation/services/biometrics/requirements.txt` | `services/biometrics/requirements.txt` |
| `workstation/services/biometrics/tests/conftest.py` | `services/biometrics/tests/conftest.py` |
| `workstation/services/biometrics/tests/test_identity.py` | `services/biometrics/tests/test_identity.py` |
| `workstation/tests/contracts.test.ts` | `tests/console/contracts.test.ts` |
| `workstation/tests/dashboard.test.tsx` | `tests/console/dashboard.test.tsx` |
| `workstation/tests/e2e/console.spec.ts` | `tests/console/e2e/console.spec.ts` |
| `workstation/tests/login-boundary.test.tsx` | `tests/console/login-boundary.test.tsx` |
| `workstation/tests/repository-integration.test.tsx` | `tests/console/repository-integration.test.tsx` |
| `workstation/tests/security.test.ts` | `tests/console/security.test.ts` |
| `workstation/tests/setup.ts` | `tests/console/setup.ts` |
| `workstation/tests/status.test.ts` | `tests/console/status.test.ts` |
| `workstation/tests/store.test.ts` | `tests/console/store.test.ts` |
| `workstation/tsconfig.json` | `tsconfig.json` |
| `workstation/vitest.config.ts` | `vitest.config.ts` |
