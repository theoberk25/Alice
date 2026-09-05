# ALICE — Technician Console

This subsystem lives in `workstation/` in the main ALICE repository. Start with the [main workstation guide](../docs/guides/workstation.md) and [migration and contract assessment](docs/integration/main-repository-migration.md). Commands and code paths in these subsystem docs are relative to `workstation/`; from the main repository root, run `cd workstation` first. Dependencies and local configuration are installed separately; source migration does not provision them.

The main [architecture](../docs/prds/ALICE-DCAMR-Architecture.md), [PRD](../docs/prds/ALICE-DCAMR-PRD.md), and [console integration requirements](../docs/integration/technician-console.md) govern product behavior. The existing console retains its legacy DDIL/CONNECTED/DEGRADED contracts. ONLINE/OFFLINE authority transfer and real core transport remain integration work.

**Authenticated Local Identity & Cyber Enforcement.** A native macOS console for reviewing the decisions an independent ALICE edge node makes about autonomous agents. Built with Tauri 2, React, TypeScript, Zustand, Zod, Rust, SQLite, and a local FastAPI/ArcFace service.

The console presents policy results, anomalous behavior, evidence provenance, agent context, and technician actions. It never implements policy evaluation, anomaly training, SIEM, EDR, cyber agents, or protected-system execution. The upstream authority remains responsible for decisions and execution under the main repository's ONLINE/OFFLINE design.

See [HANDOFF.md](HANDOFF.md) for the complete implementation inventory, historical standalone setup and verification evidence, prioritized remaining work, and the deferred full visual/animation update. For real camera setup and an operator test, use [Facial verification quick start](docs/development/facial-verification-quickstart.md).

For a separate chat that will craft implementation prompts, use [PROMPT_CONTEXT.md](PROMPT_CONTEXT.md): it provides a ready-to-paste brief, required attachments, authority rules, and current confirmed versus pending functionality.

## Quick start

Requirements: macOS, Xcode Command Line Tools, Node 22+, and a stable Rust toolchain. Python 3.11 is recommended for the biometric service. See [Mac setup](docs/development/mac-setup.md).

```sh
npm ci
npm run demo
```

This launches native ALICE with mock edge events and a visibly simulated technician identity. The initial record is the supplied HOLD payload: risk 94, one locally verified reference, two external references pending, cloud disconnected. Click **Approve once → Simulate fail → Simulate pass** to exercise the request-bound step-up workflow. The final result is a structured approval submission; no protected action executes.

`npm run dev` starts the same frontend at http://127.0.0.1:1420. Browser preview uses memory, simulated identity, and a structured language fallback. Native authentication, database access, and Ollama calls require ALICE.app. The small sliders control in development exposes ten deterministic scenarios; it is excluded from production builds. The **Simulation** badge remains whenever mock transport is active.

## Real identity with a simulated edge

The biometric mode is independent of the edge transport. This lets the team demonstrate real ArcFace login and approval while the upstream edge is still mocked.

```sh
python3.11 -m venv services/biometrics/.venv
services/biometrics/.venv/bin/python -m pip install -r services/biometrics/requirements-lock.txt
services/biometrics/.venv/bin/python scripts/setup-model.py
# First setup only; preserve an existing private .env.
cp -n .env.example .env
```

Edit `.env` locally. Set a bootstrap `ALICE_ADMIN_USERNAME`, a strong `ALICE_ADMIN_PASSWORD` of at least 12 characters, and a random `ALICE_BIOMETRIC_TOKEN` of at least 32 characters. Set `ALICE_BIOMETRIC_MODE=arcface`; retain `ALICE_TRANSPORT_MODE=mock` until upstream integration. No credentials are provided or committed by this repository.

```sh
# Terminal 1
npm run biometrics
# Terminal 2
npm run demo
```

Open **Administration**, sign in with the bootstrap account, save a technician identity, and capture five usable frames. Then open **Technician identity**, enter that username, and complete face verification. **Approve once** requires a new capture even after login. Enrollment metadata and Argon2id admin password hashes live in native SQLite. Face embeddings are encrypted in the Python service's private store; raw face photos are not saved.

ArcFace matches identity. It does **not** establish liveness or detect deepfakes. The initial threshold is a configurable demo setting requiring environment-specific calibration. Pretrained InsightFace model assets have separate usage terms; consult [biometric architecture](docs/architecture/biometrics.md) before redistribution or commercial use.

### Moving from an existing standalone installation

Copying private `.env` configuration does not install Rust, ArcFace weights or
the encrypted face-enrollment store. Run the setup commands above in this
checkout and restart `npm run biometrics` after model provisioning: the service
loads models at startup. `MODEL_FILES_MISSING` means the model files are absent,
not that the captured face failed identity matching.

The native bundle identifier is unchanged, so existing administrator/technician
metadata may appear from macOS Application Support while the new Python store
has no enrollment. In that case, select **Re-enroll** and capture five frames
against the new ready service, then use username-first facial login. Do not
delete accounts or reset either database to repair missing models. The original
private enrollment store remains separate unless explicitly configured otherwise.

Quit the standalone preview before starting `npm run dev` or `npm run demo` here.
The current desktop launcher reuses an available server on port 1420; leaving the
old preview there would serve the old checkout's renderer. All local processes
used for the main console should be launched from `workstation/`.

## Local language assistance

```sh
ollama serve
ollama pull <your-chosen-model>
```

Set `ALICE_LLM_MODEL` in `.env`, or choose an installed model in **Connection settings**. `OLLAMA_BASE_URL` defaults to `http://127.0.0.1:11434`. No particular model size is required. The gateway supports decision explanations, evidence summaries, agent clarification, agent-response summaries, and strictly validated informational intents. It never authorizes actions. If Ollama is unavailable, review buttons and structured evidence remain usable.

## Checks and packaging

```sh
npm run check            # strict TypeScript, lint, Vitest, frontend build
npm run test:rust        # native approval-boundary tests
npm run test:python      # biometric API/storage/error tests
npx playwright install chromium
npm run test:e2e         # UI approval/retry, DENY, outage, reconciliation, responsive layout
services/biometrics/.venv/bin/python scripts/smoke-arcface.py
services/biometrics/.venv/bin/python scripts/smoke-native-identity.py
npm run build:app
```

The app bundle is produced at `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`. It includes the frontend, local fonts, Rust backend, icon, and camera permission metadata. Python/ArcFace and Ollama run as separately provisioned local services in this first build; see [packaging and service lifecycle](docs/development/mac-setup.md). There is no signing identity or notarization credential committed here.

To run the packaged demo with shell environment configuration, launch its executable rather than relying on Finder to inherit shell variables:

```sh
ALICE_TRANSPORT_MODE=mock ALICE_BIOMETRIC_MODE=mock \
  apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app/Contents/MacOS/alice-technician-console
```

Without explicit mock configuration, the packaged executable defaults to remote transport and real identity. The remote transport currently fails visibly until the team supplies its real connection. It does not silently fall back to simulated security.

## Repository map

```text
apps/desktop/src/          React app, feature adapters, Zustand state, components, design tokens
apps/desktop/src-tauri/    Native auth, SQLite, one-use grants, loopback service gateways
packages/contracts/       Legacy schemas, ALICE schemas, compatibility adapter
packages/domain/          HOLD machine, approval guard, transport/LLM/biometric interfaces
packages/ui/              Shared semantic badges, panels, modal, status language
services/biometrics/       FastAPI, image quality, ArcFace, encrypted enrollment store
fixtures/                 Original supplied payloads and ten deterministic scenarios
tests/                    Contract, security, state, component, Playwright tests
docs/                     Architecture, integration contracts, setup and test evidence
scripts/                  Native launcher, local service launcher, model and inference checks
```

Start the team handoff with [upstream-alice.md](docs/integration/upstream-alice.md). It lists exactly what the console consumes and emits, what is mocked, and the remaining integration decisions. [Verification status](docs/development/verification.md) distinguishes tested functionality from unverified deployment requirements.

## Reassessment demo

Select Development scenarios → `04_hold_context_rejustification`. Watch DEC-184 (HOLD, risk 94, evidence 1/3) receive an agent response and remain REASSESSMENT_PENDING; after another delay, immutable DEC-185 becomes the current HOLD (risk 62, evidence 2/3). Original and current records remain selectable, and approval requires a fresh DEC-185-bound face check. Risk/evidence changes are deterministic mock fixtures, not console or LLM calculations. See [HOLD workflow](docs/architecture/hold-workflow.md) and [scenario replay/persistence instructions](docs/development/mock-scenarios.md).
