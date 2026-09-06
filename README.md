# ALICE

**Authenticated Local Identity & Cyber Enforcement** is a prototype for accountable
agent operations when enterprise connectivity is unavailable. ALICE combines trusted
permissions, behavioral assessment, technician review and durable evidence so a
local action can be understood, reviewed and eventually reconciled upstream.

**Current delivery:** a first-light signed terminal request can run through the
USB-backed Pi runtime to a physical USB-serial XIAO ESP32-S3 light, with automatic verified audit delivery to
Wazuh and a native technician console. The full product loop is still being integrated.
Moving code into the shared layout does not make the live system complete.

The intended decision split is **Pi ML classification → local Mac held-action
accept/deny after biometric verification → Pi validation/enforcement**. Physical light-on is verified; authenticated held-action responses are next; use the
[ESP handoff](docs/integration/esp-handoff.md) and
[automatic Wazuh runbook](docs/integration/wazuh-audit-sync.md).

Start with [architecture.md](architecture.md) for the whole-system picture,
[current.md](current.md) for the current checkpoint, and
[AGENTS.md](AGENTS.md) for every contributor's working rules.
The [documentation map](docs/README.md) and [script catalog](docs/scripts/README.md)
lead to detailed setup and component guides. Archived content is excluded from
normal sessions unless the user explicitly requests it.

## How ALICE is intended to work

| Mode | Execution owner | ALICE responsibility |
| --- | --- | --- |
| ONLINE | Enterprise control systems | Synchronize trusted context, observe authenticated activity, and upload audit/findings. ALICE is not a mandatory online action gateway. |
| OFFLINE / DDIL | Local ALICE system after controlled authority transfer | Assess supported requests from accepted caches and observations, require review where needed, and preserve request/decision/execution evidence. |

Reconnection is a workflow, not a third mode. A lost network connection, a face
match, an LLM explanation or an uploaded record does not grant execution authority.
The protected endpoint must enforce one current controller; that integration remains
unfinished. The target edge device is a Raspberry Pi 4 Model B with 2 GB RAM and
OS Lite. Training, facial identity and the local LLM run on the development or
technician Mac. ESP lights/voltage sensing are the proposed physical demo; actual
sensor contracts, operating limits and hardware acceptance remain open.

## What exists today

| Area | Implemented here | Remaining boundary |
| --- | --- | --- |
| Behavioral analysis | Schema validation, cyber features, contextual PRE/POST scoring, synthetic training and calibration experiments | Trusted live observations, persistent model export/load and Pi resource acceptance |
| First-light runtime | Signed terminal envelope, verified demo release, exact grant resolver, fixture assessment, durable attempt/result audit, mock light transport and verified USB export | Physical Pi/ESP acceptance, real model/review, full permissions and authority lifecycle; [scope](docs/reports/2026-09-05-pi-backend-status.md) |
| Pi assessment | `assess_for_technician` combines supplied permission findings and anomaly evidence into `alice-decision-assessment-v1` | Full permission semantics, real assessment integration, authenticated console transport and app response binding |
| Decision Evidence Ledger | SQLite recorder, canonical event contracts, hash chains, Ed25519 checkpoints and durable outbox state | Real assessment/lifecycle producers, semantic reconciliation and production trust provisioning; first-light supplies a fixture-based producer |
| Enterprise audit delivery | Automatic in-process USB ledger uploader, verified TLS, exact read-back, persistent receipts and retry/backoff | Live outage/reboot acceptance, semantic reconciliation and cache downloads; [runbook](docs/integration/wazuh-audit-sync.md) |
| Technician console | React/Vite UI, Tauri/Rust boundary, local storage, immutable reassessment lineage and approval guards | Real core transport and execution confirmation; remote mode fails closed |
| Facial identity | FastAPI/ArcFace service, enrollment storage and native verification boundary | Live operator acceptance on each installation; liveness/deepfake detection is not implemented |
| Enterprise simulation | Synthetic activity, permission releases, Wazuh configuration, baseline/training data and local console | Authenticated enterprise sync, production feeds, trusted cache activation and real hardware |

The Pi assessment keeps `decision` and `explanation` null and
`execution_authorized` false. The intended technician application interprets its
evidence; unusual PRE_ACTION observations require human approval. Hard prohibitions
and missing prerequisites must be enforced outside the LLM. The existing console's
`alice.decision` event is a different contract, so a validated adapter is still
required. See the [assessment contract](docs/contracts/decision-assessment.md).

The [implementation tracker](docs/implementation-tracker.md) retains the 118 stable
product task IDs. Its component statuses are not a product-readiness percentage.

## Repository layout

| Path | Owns |
| --- | --- |
| `dcamr/` | Core anomaly/assessment/audit and first-light runtime, verifier, exact permissions and light transport; other boundaries include empty scaffolds |
| `common/` | Shared JSON schemas and checkout-resource lookup |
| `apps/desktop/` | Active technician UI and native Tauri application |
| `packages/contracts/`, `packages/domain/`, `packages/ui/` | Console contracts, state/approval rules and shared UI |
| `cloud/` | Wazuh delivery adapter/worker; other enterprise connector scaffolds remain |
| `services/systemd/` | Pi deployment service configuration; adapt documented demo paths |
| `services/biometrics/` | Local facial identity service |
| `scripts/lab/` | Implemented ML, calibration, replay, enterprise simulation and first-light tools |
| `scripts/console/`, `scripts/biometrics/` | Console launch/build helpers and model/identity tooling |
| `lab/` | Compatibility namespace for `lab.*` imports, plus preserved empty placeholders |
| `tests/`, `tests/console/`, `services/biometrics/tests/` | Core, console and biometric tests |
| `fixtures/`, `tests/fixtures/` | Console scenarios and core contract/feature fixtures |
| `artifacts/` | Selected published synthetic evidence; generated/private outputs follow `.gitignore` |
| `docs/` | All substantive guides, contracts, plans, handoffs and reference documentation |
| `agent/`, `protected_systems/`, `apps/dashboard/`, `services/backend/`, `services/face_verification/` | Preserved integration or legacy scaffolding; existence is not implementation evidence |

Npm workspaces are declared explicitly so console packages do not absorb the
unrelated permission/baseline packages. `workstation/` is no longer a tracked
source root. Any ignored files left there on an older local checkout are private
local state; preserve and migrate them deliberately rather than deleting them.

## Run the console

From the repository root, with Node.js 22+:

```sh
npm ci
npm run dev
```

Open the reported local URL (normally `http://127.0.0.1:1420`). This browser preview
uses mock edge events, simulated identity and structured language fallback.
For native Tauri operation on macOS, install Rust stable and Xcode Command Line
Tools, then use `npm run demo`. Follow the
[technician console guide](docs/guides/technician-console.md) for native setup,
private `.env` configuration, packaging and Ollama.

For real facial identity, use the separate Python 3.11 environment and provisioning
steps in the [facial verification guide](docs/guides/console/facial-verification-quickstart.md).
Do not assume a Git pull installed models, copied credentials or migrated enrollment
storage. Model provisioning is explicit; no model download happens at app login.

## Run the Python components and lab

Use Python 3.12 for a fresh environment matching the pinned numerical dependencies.
Preserve any existing environment instead of recreating it blindly. From root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-audit.txt -r requirements-anomaly-training.txt
.venv/bin/python -m lab.replay_anomaly_fixtures
.venv/bin/python -m lab.replay_feature_fixtures
.venv/bin/python -m lab.replay_contextual_ledger
.venv/bin/python -m unittest discover -v
```

Core contract/ledger work uses `requirements-audit.txt`; training dependencies are
separate, and estimator tests skip when they are absent. The public `lab.*` commands
still work even though their implementations moved to `scripts/lab/`. From another
working directory, use the absolute path to `scripts/lab/run.py COMMAND`.
See the [lab guide](docs/lab/README.md), [training guide](docs/guides/anomaly-training.md)
and [enterprise simulation handoff](docs/handoffs/enterprise-sim-handoff.md) before
generating data. Synthetic fixtures do not establish physical safety limits.

## Verify changes

| Command from root | Scope |
| --- | --- |
| `.venv/bin/python -m unittest discover -v` | Core, lab relocation and isolated model-provisioning entry-point tests |
| `npm run check` | TypeScript, ESLint, console tests, launcher tests and frontend build |
| `npm run test:python` | Biometric service tests; requires its separate environment |
| `npm run test:rust` | Native Rust tests; requires the native toolchain |
| `npm run test:e2e` | Browser scenarios; requires Playwright Chromium |
| `npm run contracts:generate` | Explicitly regenerates selected schemas/fixtures; review resulting bytes |

Fresh results and environment limitations belong in [current.md](current.md) and
its linked verification record. Camera, native identity, enterprise services and
Pi hardware acceptance require their own checks; passing mocked scenarios does
not establish those integrations.

## Contribute

Read [AGENTS.md](AGENTS.md), [current.md](current.md), the relevant
[PRD](docs/prds/ALICE-DCAMR-PRD.md), and the component guide before creating files.
Put new developer utilities in `scripts/<area>/`, application code in its owning
package, and substantive documentation under `docs/`. Keep `current.md` below
80 lines and 800 words. Preserve teammates' changes, archived evidence, published
fixtures and private state; coordinate contract changes before promotion.
