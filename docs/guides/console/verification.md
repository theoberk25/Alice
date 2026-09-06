# Historical standalone console implementation verification

The checks and operator observations below were recorded on September 5, 2026 for standalone source commit `50de955737a647b856658bf7a5da6f52d15b4a4a` on its original Apple Silicon Mac. They are preserved historical evidence, not claims that this migrated checkout has those dependencies, accounts, services or results. The source now uses the shared repository layout, with simulated upstream infrastructure. See the [main workstation guide](../workstation.md) and [technician integration contract](../../integration/technician-console.md) for current scope. All commands below are relative to the repository root.

## Executed checks

HOLD lineage update: formatting, TypeScript, ESLint, generated schemas, the complete frontend/native/Python/browser suites and native release packaging were checked for this implementation. Real ArcFace engine and native identity tests plus the configured Ollama inference check also passed. The existing Ollama grammar crash fix remains intact: native sampling omits large string-length bounds while strict Zod output limits remain enforced.

| Check                              | Result                                                         | What it establishes                                                                                                                                                                              |
| ---------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `npm run check`                    | Passed; 61 Vitest tests                                        | Strict TypeScript, ESLint, contract/lineage validation, immutable history, pending/superseded states, hydration, structured deltas, stale grants/dialogs, existing security and production build |
| `npm run test:rust`                | Passed; 14 tests, 2 explicit service tests excluded by default | Native session/admin/security regressions plus lineage/duplicate rejection, old-grant revocation, latest-decision enforcement, fresh successor approval and SQLite lineage retention             |
| `npm run test:python`              | Passed; 11 tests                                               | Claimed-identity matching, encrypted enrollment storage, authentication, input/quality errors, malformed/oversized images, no face, multiple faces, and safe service failure                     |
| `npm run test:e2e`                 | Passed; 5 Playwright tests                                     | Existing four browser workflows plus timed HOLD → response → pending → DEC-185, original/current history, fresh simulated face approval and bound audit export                                   |
| `scripts/biometrics/smoke_arcface.py`         | Passed with the real InsightFace/ArcFace CPU model             | Enrollment from five distinct encodings, identity match, and rejection of blank/multiple-face images                                                                                             |
| `scripts/biometrics/smoke_native_identity.py` | Passed with a real temporary loopback service                  | Rust → FastAPI enrollment, username-based login, disabled-session revocation, rejected capture, fresh ArcFace step-up, one-use structured approval, audit events, and enrollment removal         |
| Native Ollama gateway service test | Passed using installed `llama3.1:8b`                           | Native model health and a structured decision explanation with valid evidence references; no authorization or private reasoning field                                                            |
| `npm run demo`                     | Launched successfully                                          | Tauri desktop process, renderer startup, native decision cache writes, and operational audit persistence                                                                                         |
| `npm run build:app`                | Produced `ALICE.app`                                           | Release Rust executable, bundled frontend/local fonts, application icon, and macOS camera permission metadata                                                                                    |

The preceding release bundle was also launched against a temporary mock database. Its packaged renderer persisted all three fixture decisions through native IPC. Application naming and the camera usage description were verified from the built bundle; the temporary test instance was then closed.

The live service tests are excluded from the default Rust run so normal checks remain deterministic without AI services. Repeat the Ollama check with:

```sh
ALICE_TEST_OLLAMA_MODEL=llama3.1:8b node scripts/console/rust.mjs test ollama_live_gateway -- --ignored --nocapture
```

Use another installed model by changing the environment value. Run the native identity integration with `services/biometrics/.venv/bin/python scripts/biometrics/smoke_native_identity.py`; it creates a temporary bearer token, enrollment store, test images, and local server, then removes them. It does not enroll a person into the normal application database.

Desktop operations, reassessment lineage (1512 × 1040 viewport) and narrow (390 × 844 viewport) screenshots are generated in `artifacts/screenshots/` by Playwright. They were visually reviewed. These capture the shared React frontend in Chromium; native startup was checked separately. They are not represented as screenshots of the macOS camera or webview.

## Operator-confirmed live results

The user completed real camera enrollment and successful facial login on September 5, 2026 after setting `ALICE_BIOMETRIC_MODE=arcface`. A read-only inspection of the active mock-edge database corroborated one admin, one technician, one enrollment, FACE_ENROLLMENT_UPDATED and TECHNICIAN_LOGIN_SUCCESS. Local credentials/token are configured. The service uses port 8766 because Europa occupies 8765; authenticated health returned READY after the launcher port fix.

That operator audit confirms live enrollment/login, not live approval step-up: zero technician actions and no STEP_UP_PASSED/ACTION_SUBMITTED records were present in the active database at this audit. The separate automated real-ArcFace step-up test remains the current proof of that integration path.

## Operator and upstream checks still required

- Complete live approval step-up, wrong/no-face and other negative cases, multiple-device selection, and repeat acceptance in the packaged release. Basic live enrollment/login have now been confirmed; no liveness protection is implemented.
- Administrator credentials and the biometric token are now configured, and a real technician is enrolled. Preserve these local values; new machines still need their own setup.
- ArcFace is identity comparison only. Liveness/deepfake protection is explicitly not configured. Threshold calibration and pretrained model redistribution rights need the team's review before deployment.
- The team's authenticated WebSocket/REST transport and remote attestation protocol remain integration work. The remote skeleton fails visibly and safely. No protected system action executes in this repository.
- Python/ArcFace and Ollama are local services provisioned separately. The local `.app` is not a signed/notarized distribution with bundled AI runtimes. Intel Mac dependency and camera checks have not been run.

Third-party Python test deprecation warnings do not affect the passing tests. Build logs are kept locally in the ignored `.tools/` directory. Generated models, runtime environments, screenshots, local credentials, and databases are excluded from Git.

## Reassessment-specific coverage and assumptions

There are 91 passing default tests: 61 Vitest/React tests, 14 native Rust tests, 11 Python tests and five browser tests. The two service-dependent Rust tests remain explicitly excluded from the default run and were also invoked separately with real local services. No physical camera is required by CI.

- Contract and ingestion tests cover optional backwards-compatible lineage, unknown parents, all five changed request identity fields, wrong root/sequence, branches, second successors, missing lineage and conflicting immutable IDs.
- Store tests prove response-only REASSESSMENT_PENDING, unchanged DEC-184, ordered request IDs/current DEC-185, SUPERSEDED parent, ALLOW/DENY resolution, no extra challenge when not required, unrelated selection preservation, separate timers, unordered hydration, restored pending responses/actions/reconciliation and atomic rejection of corrupt history.
- Security tests create a valid DEC-184 grant, ingest DEC-185, reject the old grant for the same request and require a fresh DEC-185 grant. Rust also revokes the old grant and rejects every historical action. Dashboard tests invalidate an open old approval dialog; a store regression retains late receipts for already-accepted historical actions without reactivating their workflow.
- Browser tests use the actual mock transport and controlled clock to observe both delays and the waiting interval. They inspect both immutable assessments, confirm disabled historical controls, perform a new simulated face check bound to DEC-185 / REQ-88291, and inspect exported ACTION_SUBMITTED/STEP_UP_PASSED audit records. Native/store tests independently assert the structured action's exact binding and NOT_EXECUTED receipt.

The native cache and hydration use a linear chain: parent before child at ingestion, consecutive sequence, no forks, no second unlinked original per request. This is a local integration constraint for the upstream team to confirm, not a claim of an agreed network delivery protocol. Native restart restores the already-seen latest assessment; only a transient browser reload or separate disposable native mock database provides a pristine timed replay. Do not remove operator credentials/enrollment to replay the demo. All actual policy/anomaly/evidence reasoning remains outside this console.

## Main repository migration verification

Verified **2026-09-05** on branch `codex/Technician-DashboardImplementation`,
main baseline `e0796d0`; migration changes are uncommitted. Standalone source:
`50de955737a647b856658bf7a5da6f52d15b4a4a`. No commits, history changes or pushes
were made. See the [technician integration contract](../../integration/technician-console.md)
for the path map and documented authority/contract conflicts.

### Source preservation and environment

At the original import, all **127** tracked standalone files were represented under `workstation/`; the later layout migration moved them into shared folders.
SHA-256 comparison found **113 byte-identical files**; the other 14 are 13
Markdown documents adapted for repository paths/authority/historical evidence,
plus `.gitignore` extended for private runtime artifacts. Application code,
native Rust, Python, contracts, fixtures, scripts, existing tests, manifests,
all three lockfiles, Tauri configuration, camera metadata and icons are unchanged.
Three new repository-boundary tests and the migration assessment are additions.
The original supplied dashboard contract is still byte-identical.

The main root README received a small console section, its existing integration
agreement received a migration note, and `docs/guides/workstation.md` was added.
No existing workstation placeholder or teammate core file changed. No console
contract was moved to `common/`. The preexisting untracked root `.DS_Store`
was left alone.

Validation host: macOS 26.6.2 arm64, Xcode Command Line Tools, Node 22.23.1,
npm 10.9.8, Python 3.11.15 and Rust/cargo 1.98.1. Fresh ignored npm, Python,
Cargo and Playwright environments were installed in this checkout. Rust was
an already-installed external compiler, invoked read-only using `RUSTC` and
`PATH`; no toolchain or target directory was copied from the source repository.
`CARGO_HOME` selected `workstation/.tools/cargo-cache`, and all native outputs
were rebuilt under this checkout. A normal installed stable Rust toolchain can
build the same source; the standalone checkout is not a build dependency.

The following commands ran from the repository root unless marked as main-root
commands. Native commands used the toolchain environment described above.

| Command | Actual outcome |
| --- | --- |
| `npm ci --cache .tools/npm-cache --no-audit --no-fund` | Passed, 279 packages installed from the unchanged npm lock. |
| `npm run typecheck` | Passed. |
| `npm run lint` | Passed. |
| `npm test` | **64 passed** across 7 files: 61 original tests and 3 migration tests. |
| `npm run build` | Passed through Tauri's unchanged `npm run build --prefix ../..` hook; strict typecheck and Vite production assets completed from the nested workspace. |
| `npm run test:rust -- --locked` | **14 passed, 2 ignored**, no failures; ignored tests explicitly require real ArcFace/Ollama services. |
| `python3.11 -m venv services/biometrics/.venv` | Passed, fresh service environment. |
| `services/biometrics/.venv/bin/python -m pip install --cache-dir .tools/pip-cache -r services/biometrics/requirements-lock.txt` | Passed with all 65 supplied pins preserved. |
| `services/biometrics/.venv/bin/python -m pip check` | Passed, no broken requirements. |
| `npm run test:python` | **11 passed**, two dependency deprecation warnings. |
| `PLAYWRIGHT_BROWSERS_PATH=.tools/playwright node_modules/.bin/playwright install chromium` | Passed; fresh Chromium 1243, headless shell and FFmpeg assets. |
| `PLAYWRIGHT_BROWSERS_PATH=.tools/playwright npm run test:e2e -- --config .tools/migration-playwright.config.ts` | **5 passed**, 14.5 seconds. |
| `CARGO_NET_OFFLINE=true npm run build:app` | Passed; fresh release build produced `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`. |
| Main root: `python3.11 -m venv .venv` | Passed, separate core test environment. |
| Main root: `PIP_CACHE_DIR=/private/tmp/alice-main-pip-cache .venv/bin/python -m pip install -r requirements-anomaly.txt -r requirements-anomaly-training.txt` | Passed, existing core dependency pins unchanged. |
| Main root: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -v` | **103 passed**, 26.173 seconds, zero skips/errors/failures, including real estimator tests. |
| Main root: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m lab.replay_anomaly_fixtures` | **8 result fixtures and 7 score cases passed**. |
| Main root: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m lab.replay_feature_fixtures` | **5 feature vectors passed**. |
| Main root: `git diff --check`, source hash comparison, local documentation-link check | Passed; only intended integration changes, source preservation as detailed above, no broken local links. |

This is **94 passing console tests** across frontend/native/Python/browser
suites, plus **103 passing core tests**. Real-service Rust checks are explicitly
excluded from those totals.

The original standalone Vite server occupied port 1420. To verify the migrated
checkout without reusing or terminating that server, the ignored temporary
Playwright configuration imported the unchanged main Playwright configuration,
set absolute `tests/e2e` and `test-results` paths, changed the base URL to
`http://127.0.0.1:1421`, and used `npm run dev -- --port 1421` with
`reuseExistingServer: false`. No tracked launch or test configuration changed.
On a free port 1420, the documented `npm run test:e2e` remains the normal command.

### Launch and functional evidence

- The new integration test mounts the actual App, loads the migrated legacy
  HOLD, renders its risk 94, runs a simulated step-up and spies on the real
  mock transport. Exactly one `APPROVE_ONCE` carries the selected decision,
  request, technician and verification ID. Its receipt is `NOT_EXECUTED`, the
  original decision remains unchanged, and duplicate approval controls disable.
- Static import checks cover resolved TypeScript aliases and local paths,
  Python core imports, native crate/include paths, and runtime path injection.
  These guard repository isolation; they are not an upstream authentication
  protocol or a replacement for native security tests.
- All existing browser workflows passed: failed face/retry/approval, hard DENY,
  DDIL and offline language fallback, research, reconciliation immutability,
  mobile overflow and timed original/pending/successor DEC-185 review with
  exact-bound approval and audit export. The newly captured browser operations
  screenshot was visually inspected. Screenshots remain ignored under
  `artifacts/screenshots/`; they show Chromium simulation, not a native camera.
- The migrated `npm run biometrics` launcher started using disposable token,
  private data/model directories and an available configured loopback port.
  Authenticated `/health` returned `UNAVAILABLE`, `MODEL_FILES_MISSING`,
  `liveness: NOT_CONFIGURED`; unauthenticated health returned 401 and verify
  returned 503. This confirms safe startup without models, not real inference.
- The newly built packaged executable started with explicit mock transport,
  mock biometrics and temporary `ALICE_DATABASE_PATH`. Its temporary database
  contained **3 fixture decisions, 8 audit events, 0 admins and 0 actions**,
  confirming renderer-to-native IPC/persistence. Bundle identifier and
  `NSCameraUsageDescription` were checked. The probe stopped only its child
  process and deleted its disposable database/logs. Operator data was untouched.

The exact previously executed service/native startup probes are retained as
ignored local verification artifacts in `.tools/migration-verification/`, with
no secrets. Their logic generates temporary state, starts the migrated launcher
or packaged executable, checks responses/SQLite, and removes temporary state.
They are evidence helpers, not required build inputs or shipped service code.

### Failures, warnings and limits

Before migration, system Python 3.14.4 lacked `jsonschema`: root unittest
discovery ran six passing score tests with five module-import errors, and both
fixture replays failed before running. Installing existing pins into the fresh
Python 3.11 root environment resolved this; no core source fix was needed.

Initial npm/pip/browser downloads failed on sandbox DNS, and the first
Playwright server could not bind loopback inside the sandbox. Scoped execution
escalations resolved these environment restrictions. The native GUI startup
probe also required a scoped escalation. No approval rejection remains.

The newly added integration test initially had authoring/runner errors
(syntax, Testing Library options and Vite URL handling); these were corrected
without changing migrated application behavior. Independent review also adjusted
the static checks for legitimate CSS imports and service-local test path setup.
The final full suite passed. No application migration regression remains known.

Nonfatal output included locked npm package deprecation notices, Rollup/Zod
annotation warnings, Python Starlette/AnyIO deprecations, and external compiler
`rust-objcopy`/`libLLVM.dylib` lookup warnings while stripping build-script debug
information. Native packaging still exited successfully. Dependencies were not
upgraded to remove these warnings.

**Not performed in this migration:** live camera enrollment/login/approval,
negative operator camera cases, real ArcFace inference/model provisioning,
real Ollama inference, the two service-dependent Rust tests, signing/notarization,
Intel Mac validation, remote ALICE communication, protected execution or
ONLINE/OFFLINE authority transfer. Earlier real-service/operator evidence above
remains historical. All freshly launched probe processes were stopped; no
biometric model, enrolled identity or private credential was imported.

### Security and remaining integration

The renderer gained no authorization authority. Native Argon2id authentication,
session expiry/cooldowns, disabled-identity handling, cached immutable HOLD and
capability checks, fresh 60-second exact-technician/decision/request grants,
one-use consumption and supersession revocation remain unchanged. Login is
separate from approval. Hard DENY remains non-overridable; the LLM remains
informational. ArcFace is identity matching, with liveness still unconfigured.

Tracked-file-only copying, source filename/content checks and Git ignore checks
found no imported real secrets, `.env`, biometric records, encryption keys, raw
captures, SQLite files, model weights or dependency/build caches. `.env.example`
contains empty credential slots; intentional test credentials stay test-only.
No commits or pushes were made.

Real transport, upstream biometric attestation/redemption, execution confirmation,
durable reconnect/outbox/receipts, shared schema/version and authority semantics,
liveness/deepfake detection and service packaging/distribution remain unfinished.
This completes source migration and local verification, not full ALICE deployment.

### Follow-up: local demo toolchain setup

On 2026-09-05, the operator's ordinary `npm run demo` failed because Cargo was
not on their shell PATH; migration verification had selected an external
compiler explicitly. Installed a fresh official Rust 1.98.1 minimal toolchain
under ignored `.tools/cargo` and `.tools/rustup`, using rustup's
`--no-modify-path` option. The existing desktop/Rust launchers detect those
directories automatically, so no source or global shell changes were needed.
The normal `npm run demo` then completed a development build and started
`target/debug/alice-technician-console`, loading the operator-supplied local
`.env` through the existing launcher. Credentials were not displayed or edited.

### Follow-up: real-service readiness and functionality

On 2026-09-05 the operator reported `MODEL_FILES_MISSING` during camera
enrollment. The copied private configuration selected real ArcFace, but the new
checkout had no model files. This was a runtime provisioning gap: the original
migration had verified fail-closed startup without models, not real-service
readiness. Source/configuration comparison again found no changes in application
code, native security, biometric source, fixtures, existing tests, manifests or
lockfiles relative to standalone source `50de955`.

Ran the existing model setup script with the migrated Python environment:

```sh
NO_ALBUMENTATIONS_UPDATE=1 MPLCONFIGDIR="$PWD/.tools/matplotlib" \
  services/biometrics/.venv/bin/python scripts/biometrics/setup_model.py
```

The script downloaded `buffalo_l` from InsightFace's release and initialized
its real detection and recognition models on CPU. Weights are newly provisioned
under the ignored `services/biometrics/models/` directory; they were not copied
from the standalone checkout. Restarted the identified main-checkout biometric
service with the existing private configuration. Authenticated health now
returns HTTP 200, `status: READY`, `identity: ArcFace`, empty error detail and
`liveness: NOT_CONFIGURED`. Model info confirms `buffalo_l`, ready=true and
configured threshold 0.45. Credentials were neither displayed nor changed.

The old standalone Vite process was still serving port 1420. Stopped that
identified development process and started `npm run dev` from the repository root,
so the running native app now uses the main checkout's renderer. The original
source files and private enrollment database were not modified.

| Follow-up check | Actual outcome |
| --- | --- |
| `services/biometrics/.venv/bin/python scripts/biometrics/smoke_arcface.py` with update checks disabled and a writable Matplotlib cache | Passed real five-sample enrollment, claimed-identity match, no-face rejection and multiple-face rejection using the public astronaut test image and temporary encrypted store. |
| `services/biometrics/.venv/bin/python scripts/biometrics/smoke_native_identity.py` | Passed the previously ignored native real-identity test: administrator authentication, create/enroll, username-first login, blank-image failure, disable/re-enable/session revocation, login insufficient for approval, fresh ArcFace grant, exact-request action with `NOT_EXECUTED`, audit events and enrollment removal. Uses disposable service/database and public test image. |
| `node scripts/console/rust.mjs test ollama_live_gateway_returns_only_structured_operational_content -- --ignored --nocapture` with `ALICE_TEST_OLLAMA_MODEL` set from the configured local model | Passed against local `llama3.1:8b`; validated structured explanation with supplied evidence IDs, without authorization or private reasoning output. |
| `npm run typecheck`, `npm run lint`, `npm test` | Passed; all 64 frontend tests. |
| `npm run test:rust -- --locked` | Passed 14 default tests; the two service-dependent tests remain ignored by default and both passed separately above. |
| `npm run test:python` | Passed; all 11 tests, existing two deprecation warnings. |
| `PLAYWRIGHT_BROWSERS_PATH=.tools/playwright npm run test:e2e -- --config .tools/migration-playwright.config.ts` | Passed all 5 workflows against the main source, 5.7 seconds. |

The first real Ollama test attempt used offline Cargo with the newly installed
toolchain cache and lacked a test-only crate. Downloading the unchanged locked
test dependencies resolved it; the test then passed. Real inference also emits
an existing InsightFace/scikit-image alignment deprecation warning. No dependency
upgrade or application/security code change was required.

The follow-up therefore passes **96 console tests** including the two explicit
real-service Rust checks, plus the real ArcFace engine smoke assertions. Core
source was unchanged; the earlier 103-test core baseline was not rerun for this
runtime-only provisioning follow-up.

At the follow-up read-only count check the integrated Python store contained
zero enrollments. The native metadata could still show the operator as enrolled
because the bundle identifier and native Application Support path were preserved.
The operator must complete re-enrollment against the ready new service to populate
that separate encrypted store. No embeddings or encryption keys were inspected
or copied, and no real identity was removed or reset. The real-service tests
above do not substitute for the operator's successful live camera capture.

This follow-up establishes real ArcFace and Ollama operation through the migrated
code. Live operator enrollment/login/approval remain awaiting user confirmation;
remote ALICE transport, protected execution, authority transfer and liveness are
still the original unfinished boundaries.
