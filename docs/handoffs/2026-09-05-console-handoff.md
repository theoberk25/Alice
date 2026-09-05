# ALICE Technician Console — complete implementation handoff

Standalone source last audited: **September 5, 2026**, at commit `50de955737a647b856658bf7a5da6f52d15b4a4a`. The console now uses the shared top-level layout in the main ALICE repository; see [layout migration](2026-09-05-console-layout.md). This handoff preserves that implementation inventory, dated standalone evidence, and remaining work. Local accounts, processes, installed dependencies and test outcomes below describe the original workstation audit; they are not claims that migration provisioned or revalidated them.

Commands and code paths in this document are relative to the repository root. See the [main workstation guide](../guides/workstation.md) for current setup and migration verification, and the [migration assessment](../integration/main-repository-migration.md) for provenance and contract conflicts. Update evidence when a milestone is completed; do not treat a planned capability as implemented.

Main repository migration verified September 5, 2026: all 127 source files are
represented in the shared app/package/service layout, with application/security code, existing tests,
contracts, fixtures and locks unchanged. The integrated suites pass 64 frontend,
14 Rust, 11 Python and 5 browser tests; two real-service Rust tests remain ignored.
The main core passes 103 tests and both fixture replays. `ALICE.app` builds and
starts with disposable mock data. See [Main repository migration verification](../guides/console/verification.md#main-repository-migration-verification)
for exact commands, environment limits and operator checks not performed. This
does not mark real transport, attestation, liveness or distribution complete.

Runtime follow-up on the same date provisioned the missing ArcFace weights and
restarted the main-checkout face service, which now reports READY. Both explicit
real-service Rust tests (ArcFace enrollment/login/fresh approval and Ollama
explanation) passed in the integrated checkout, along with the real engine smoke
test and all default console suites. See the verification record's
**Follow-up: real-service readiness and functionality** section. An operator's
live capture is still required to populate the new private biometric store;
native enrollment metadata alone does not transfer the original face embedding.

Historical standalone operator update (September 5, 2026): administrator credentials and the biometric token are configured. One technician has enrolled a real face and successfully logged in through the camera. User confirmation is corroborated by native enrollment/login audit records. Live approval step-up has not yet been confirmed. Port `8765` was found occupied by a Python process in the Europa directory; the local `.env` now selects `http://127.0.0.1:8766`. The biometric launcher was updated to honor this configured loopback URL instead of hardcoding port 8765. For a new checkout, choose an available loopback port in its private configuration and restart both launchers after changing it; the historical port choice is not a required setting.

## 1. Current position

Reassessment lineage milestone (September 5): agent responses now stop the automatic path at REASSESSMENT_PENDING until a new immutable `alice.decision` arrives. Scenario 04 replays DEC-184 (HOLD, risk 94, evidence 1/3) → response → pending → DEC-185 (HOLD, risk 62, evidence 2/3), with explicit parent/root/trigger/sequence. The console validates a linear same-request chain, preserves every decision, reconstructs request indexes on hydration, displays original/current records and deterministic deltas, and binds every new action and biometric grant to the latest assessment. Native tests reject old grants/actions; an already-open approval dialog is blocked when superseded. Actual reassessment algorithms and real transport remain upstream work.

Ollama compatibility fix (September 5): automatic summaries were returning HTTP 500 because the runner rejected a JSON-Schema string-length grammar (`char{1,3000}`) and crashed. Native sampling-schema normalization now removes string-length bounds while preserving the original strict Zod output validation. Identical error banners are deduplicated. The corrected bounded-schema request passed against the real local `llama3.1:8b` model; regression tests cover grammar shape, retained output limits and error deduplication. See the verification record for the updated check counts.

The initial console subsystem exists and its native macOS application builds and launches. The main interactive path is implemented: ingest an ALICE HOLD, display policy/anomaly/evidence facts, request clarification automatically, accept technician review, perform fresh identity verification when required, and submit a request-bound `APPROVE_ONCE` record. Original upstream decisions are preserved.

Real ArcFace inference, native enrollment/login/step-up integration, and local Ollama inference have passed automated checks. **Live camera enrollment and facial login were confirmed on the original Mac**, confirmed by the user and native audit records. The recorded standalone demo used real ArcFace biometrics and mock edge events. Live camera approval step-up and its negative cases remain to be exercised; the existing step-up integration test used public test images. It is not a connected deployment of the team's ALICE edge node.

The next priority is functional completion and operator testing. **A full visual and animation update is explicitly planned for later, after the functional system works.** It should evaluate suitable open-source UI and animation libraries, including the user-suggested `apple-liquid-glass-ui` on GitHub. No such library has been selected or installed. See section 12 for the deferred design brief and its prerequisites.

### Historical standalone snapshot, not a portable installation guarantee

| Item                              | Observed state at this audit                                                                                         |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Git                               | Initial source baseline prepared on `main` for integration; see `git log` for commit history                         |
| Root `.env`                       | Exists and is ignored by Git                                                                                         |
| Edge transport                    | `ALICE_TRANSPORT_MODE=mock`                                                                                          |
| Face mode                         | `ALICE_BIOMETRIC_MODE=arcface`                                                                                       |
| Ollama model configuration        | `llama3.1:8b`; this is separate from model names in agent fixtures                                                   |
| Admin username/password           | Configured in the local `.env`; values are deliberately excluded from this handoff                                   |
| Admin accounts                    | One admin in the active mock-edge console database                                                                   |
| Technicians / enrollment metadata | One technician and one enrollment in the active mock-edge database                                                   |
| Biometric bearer token            | Configured; shared by the native app and Python service; value excluded                                              |
| Normal biometric store            | Real face enrollment created through the local service; private runtime data is excluded from Git                    |
| Mock console database             | Previously audited: three cached decisions, zero actions; current counts depend on demo use                          |
| Remote console database           | Exists, with no cached decisions, technicians, enrollments, or admins                                                |
| Python runtime                    | `services/biometrics/.venv` is installed locally                                                                     |
| ArcFace model                     | `buffalo_l` ONNX assets are provisioned locally; detection and recognition are the loaded modules                    |
| Rust and browser tooling          | Isolated local toolchain under `.tools/`; Playwright browser assets also under `.tools/`                             |
| Built macOS bundle                | `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app` exists and passed release startup verification        |
| Installed AI/UI services          | Service availability is process-dependent; do not infer that a server is running just because its dependencies exist |

The former **Alex Morgan / `alex.demo` / `TECH-DEMO`** identity was generated by mock biometric mode and is no longer the intended active identity. It is not an admin account, an enrolled face, or a reusable login credential. Temporary identities used by integration tests were removed with their temporary databases.

For the shortest operator path, use [Facial verification quick start](../guides/console/facial-verification-quickstart.md).

## 2. Scope and authority to preserve

The complete team project is **ALICE — Authenticated Local Identity & Cyber Enforcement**. The technician console owns its technician console, local identity controls, semantic gateway, console persistence, and integration boundary.

The main [architecture](../prds/ALICE-DCAMR-Architecture.md), [PRD](../prds/ALICE-DCAMR-PRD.md), and [console integration requirements](../integration/technician-console.md) are authoritative for current product behavior. The original project brief is historical context; the preserved [dashboard-contract.original.txt](../../fixtures/legacy/dashboard-contract.original.txt) and its three extracted payloads define the existing legacy examples. The Europa screenshot was visual inspiration only.

The main design distinguishes ONLINE enterprise execution from OFFLINE local ALICE authority after controlled transfer. Current DDIL/CONNECTED/DEGRADED fields and mock/remote transport do not implement that authority protocol. Reconnection is a workflow, and direct Pi-to-enterprise synchronization is upstream work. See the [migration assessment](../integration/main-repository-migration.md); the source migration keeps executable schemas and legacy examples intact.

This workstation subsystem must not grow an independent policy engine, Isolation Forest model/training pipeline, SIEM, EDR, cyber-agent implementation, firewall modification service, or protected tool executor. Those are upstream responsibilities. A technician approval is a scoped request to the authoritative edge, not evidence that a protected action ran.

Keep these invariants:

- Incoming policy `DENY` cannot be overridden here. `ALLOW`, `HOLD`, `DENY`, technician `REJECTED`, `APPROVED ONCE`, and evidence `RECONCILED` have different meanings.
- The LLM explains and translates informational intent. It has no authorization tools and cannot replace an explicit technician action or biometric check.
- Evidence verification states, anomaly scores, engine readiness, and execution outcomes come from supplied state, not UI guesses or generated prose.
- Face login is distinct from a fresh approval verification. Grants bind one technician to one decision/request and expire after 60 seconds.
- ArcFace is identity matching. Liveness, replay resistance at the camera, and deepfake detection are separate, unimplemented capabilities.
- Mock mode is visibly identified. Remote mode must fail safely until its real transport is implemented.
- Legacy `dcamr.*` is accepted at ingestion, normalized to `alice.*`, and does not appear as UI branding.
- Reconciliation adds later evidence annotations; it does not rewrite the historical decision.

### Supplied-data ambiguities already documented

The input file is prose containing three JSON objects, despite its `.json` extension. The original is retained byte-for-byte. The example requests `allow_outbound`, while its justification describes preventing communication; the UI flags that inconsistency without changing the action. The original unverified/pending counts overlap and must not be added as independent totals. Known legacy node prefixes are normalized for display, while request, decision, evidence, agent, and package identifiers are retained.

## 3. Repository inventory

| Location                                         | What is implemented there                                                                                                                                                        |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/desktop/src/app/App.tsx`                   | Navigation, operations/history/audit/admin views, identity gate, development scenario controls, modal routing, technician action bar                                             |
| `apps/desktop/src/components/layout/`            | ALICE branding, UTC clock, node/DDIL/cloud/session status, connection/model settings                                                                                             |
| `apps/desktop/src/components/agents/`            | Agent IDs, types, model strings, health, activity and mission display                                                                                                            |
| `apps/desktop/src/components/status/`            | Infrastructure/package/engine state and operational internal-service activity                                                                                                    |
| `apps/desktop/src/components/decisions/`         | Active decision, risk dial, policy/anomaly factors, justification, research workspace; reusable DecisionLineage and state-driven clarification progress                          |
| `apps/desktop/src/components/evidence/`          | Evidence source/status ledger, verified and pending counts, later reconciliation                                                                                                 |
| `apps/desktop/src/components/audit/`             | Recent/expanded decision history, original versus technician outcomes, local audit presentation and JSON export control                                                          |
| `apps/desktop/src/components/command/`           | Text question input, contextual shortcuts, concise gateway response/error display                                                                                                |
| `apps/desktop/src/components/technicians/`       | Admin login, technician metadata, enable/disable, enrollment/re-enrollment/removal, username-first face login and logout                                                         |
| `apps/desktop/src/components/biometrics/`        | Camera selection/capture, five-frame enrollment capture, step-up binding, simulated pass/fail controls, real score display, blocked/submitted states                             |
| `apps/desktop/src/features/biometrics/verify.ts` | Frontend adapter selecting native mock or ArcFace verification and validating the returned grant                                                                                 |
| `apps/desktop/src/state/console.ts`              | Zustand immutable ingestion, validated reassessment indexes, automatic context/response binding, transitions, hydration, current-decision action guards and gateway coordination |
| `apps/desktop/src/lib/native.ts`                 | Narrow Tauri IPC wrapper and public runtime configuration; browser-preview distinction                                                                                           |
| `apps/desktop/src/lib/transport.ts`              | Working fixture transport and fail-closed remote transport skeleton                                                                                                              |
| `apps/desktop/src/lib/llm.ts`                    | Ollama provider, deterministic clarification fallback, strict informational intent parsing, explanation/evidence-reference checks                                                |
| `apps/desktop/src/styles/`                       | Custom dark mission-control CSS, semantic tokens, responsive rules, restrained CSS motion and reduced-motion handling                                                            |
| `apps/desktop/src-tauri/src/config.rs`           | Runtime modes, service URLs/model, database configuration, loopback URL validation                                                                                               |
| `apps/desktop/src-tauri/src/db.rs`               | SQLite tables, first-admin bootstrap, Argon2id hash storage and audit insertion                                                                                                  |
| `apps/desktop/src-tauri/src/security.rs`         | Native sessions, approval envelopes, fresh exact-request proof validation, policy and mock/real restrictions                                                                     |
| `apps/desktop/src-tauri/src/commands.rs`         | Admin/technician commands, biometric HTTP gateway, enrollment metadata, trusted mock cache, action persistence, local Ollama communication                                       |
| `apps/desktop/src-tauri/src/commands_tests.rs`   | Native command tests and explicitly enabled real Ollama/ArcFace integration checks                                                                                               |
| `apps/desktop/src-tauri/` configuration          | Tauri 2 app/bundle settings, CSP/capabilities, camera usage description/entitlement, ALICE icon, Cargo manifest/lock                                                             |
| `packages/contracts/src/legacy/`                 | Zod schemas for the supplied legacy decision, status and reconciliation payloads                                                                                                 |
| `packages/contracts/src/adapters/`               | Legacy-to-ALICE normalization and validation                                                                                                                                     |
| `packages/contracts/src/alice/`                  | New event, context-request, action, receipt, explanation, informational intent and verification schemas/types                                                                    |
| `packages/domain/src/`                           | HOLD state machine with SUPERSEDED, lineage.ts chain validation/index rebuilding, action guards/builders, transport/LLM/biometric interfaces, future authenticity interface      |
| `packages/ui/src/`                               | Shared panels, badges, modal, empty state and centralized semantic status presentation                                                                                           |
| `services/biometrics/app/`                       | FastAPI/configuration, image decoding and quality checks, InsightFace/ArcFace engine, encrypted SQLite enrollment store, strict request schemas                                  |
| `services/biometrics/tests/`                     | Isolated API/identity/quality/storage/error tests with injected deterministic inference                                                                                          |
| `fixtures/legacy/`                               | Preserved original contract plus extracted source payloads                                                                                                                       |
| `fixtures/alice/`                                | Generated normalized decision/status/reconciliation, sample agent status and complete reassessment fixture                                                                       |
| `fixtures/scenarios/`                            | Ten named deterministic development scenarios and synthetic agents/services/history                                                                                              |
| `tests/`                                         | Contract, state/security, status, component, login-gate and browser workflow tests                                                                                               |
| `docs/`                                          | Architecture, contracts/JSON Schemas, setup, verification evidence, scenario instructions and upstream agreement                                                                 |
| `scripts/`                                       | Native dev/build launcher, Rust-toolchain wrapper, Python-service launcher, model provisioning, schema/fixture generation and real-inference checks                              |
| Root configuration                               | npm workspaces, package lock, strict TS config, ESLint, Vitest, Playwright, formatting, environment example, Git ignores, README and contribution guide                          |

The frontend uses React, TypeScript, Vite, Zustand, Zod, Lucide icons, and locally bundled IBM Plex/Barlow fonts. The desktop boundary uses Rust/Tauri 2 and SQLite. The biometric service uses Python/FastAPI, InsightFace/ArcFace, ONNX Runtime CPU, OpenCV, NumPy and Fernet encryption. The language gateway uses local Ollama. No external model API key is required.

## 4. Implemented behavior and its limits

| Capability               | Existing behavior                                                                                                 | Remaining boundary                                                                                  |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Native application       | Development app and release bundle launch; packaged renderer invokes native persistence                           | Interactive packaged-camera and distribution checks remain                                          |
| Dashboard                | Bespoke dark three-column operations view, decision/evidence/status/history/command areas, responsive layout      | Complete visual/animation redesign is deferred                                                      |
| Legacy ingestion         | Runtime validation and normalization; malformed/conflicting events fail visibly                                   | Real authenticated native ingestion is not implemented                                              |
| Live status presentation | Receives separate infrastructure, agent and service schemas                                                       | Current producers are fixtures; stale/heartbeat handling needs work                                 |
| HOLD review              | State machine, four technician controls, immutable reassessment lineage and current assessment guards             | Real upstream reassessment producer and execution confirmation remain unconnected                   |
| Automatic clarification  | First request is generated/sent automatically; mock response arrives after a short delay                          | Real agent routing, durable correlation and timeout/retry behavior remain                           |
| Research                 | Expanded policy/anomaly/mission/evidence/justification inspection and text questions                              | Latest-response context composition and richer follow-up handling need completion                   |
| Approval                 | Exact action confirmation; fresh biometric flag honored; one-use native grant; original HOLD retained             | Remote delivery/attestation, durable outbox and acknowledgement recovery remain                     |
| Admin authentication     | Environment bootstrap, Argon2id, password verification, 15-minute session and failed-attempt cooldown             | Admin configured and used; no credential rotation/recovery UI                                       |
| Technician management    | Create/update metadata; list; enable/disable; enroll/re-enroll/remove face                                        | Live enrollment/login confirmed; management negative cases and cross-store recovery remain          |
| Technician login         | Claim username, verify its stored face, grant an 8-hour native session; dashboard hidden until login in real mode | Live camera acceptance and immediate UI session-expiry synchronization remain                       |
| ArcFace                  | Detection/alignment, quality filtering, multi-sample embedding, claimed-identity cosine comparison                | Threshold calibration and representative live-person evaluation remain                              |
| Liveness                 | Separate future interface and honest NOT CONFIGURED UI                                                            | No anti-spoof implementation or camera replay detection                                             |
| Ollama                   | Model-configurable native health/inference, strict response/intent schemas, no authorization tools                | Broader model coverage, current-context handling and more detailed operational activity remain      |
| Outage behavior          | Structured fallback for unavailable LLM; DDIL fixtures preserve local review; face failures block approval        | Real network loss/reconnect and sidecar lifecycle need integration tests                            |
| Persistence              | Local identity, original decisions, actions, annotations, settings, audit                                         | Versioned migrations, durable workflow/outbox, retention, backup and full-history pagination remain |
| Audit                    | Native security/action events plus separately identified renderer operational events; JSON export UI              | Packaged native file-save verification, complete history export and upstream export protocol remain |
| Packaging                | Frontend/fonts/icon/native backend and camera metadata in ALICE.app                                               | Python/weights/Ollama are separately installed; signed distribution/sidecar lifecycle remain        |

### HOLD flow in this build

The automatic sequence is `HOLD_RECEIVED → AUTO_CONTEXT_REQUEST → AWAITING_AGENT_RESPONSE → AGENT_RESPONSE_RECEIVED → REASSESSMENT_PENDING`. It stops there until a new immutable decision arrives; `REASSESSMENT_RECEIVED` then makes the parent `SUPERSEDED`. The new HOLD with no further required context starts its own `AWAITING_TECHNICIAN` flow; ALLOW/DENY start `RESOLVED`. The technician can begin review while clarification is pending. HOLD leads to `HELD_BY_TECHNICIAN`; RESEARCH leads to `RESEARCHING`; REJECT records a final technician rejection. APPROVE enters `APPROVAL_REQUESTED`, then the required biometric states, then `APPROVAL_SUBMITTED` on successful submission.

The Technician Console never performs the policy/anomaly reassessment itself. Only HOLD with `context_challenge.required=true` starts an automatic request. Scenario 04's response and new decision are separated by 1.2-second timers; DEC-185 has context required=false, avoiding another loop. Other scenarios do not manufacture successors. Human intervention remains distinct from the automatic path. Execution confirmation still needs a separate upstream contract; an approval receipt is not execution confirmation.

`DecisionSchema.reassessment` is optional and contains previous_decision_id, root_decision_id, trigger and positive sequence. Shape validation is additive for legacy/original events; relationship validation requires a known current parent, same request/agent/mission/action/target, a correct original root and sequence +1. Branches and a second unlinked original for a request are rejected. Immutable decision objects stay in the ID-keyed store; requestDecisionHistory/latestDecisionByRequest contain only IDs and are rebuilt during hydration. The native cache validates the same relationships, inserts snapshots/audit transactionally and revokes old grants. All persisted snapshots/annotations/actions are read so an ancestor cannot fall outside a 500-row decision window; the audit view remains bounded to 500.

DecisionLineage displays original → context → response → reassessment/current and root-to-current risk/evidence/result deltas. History groups requests while preserving selectable individual records, parents, roots and current labels. Approval dialogs capture the original selected ID; supersession blocks them instead of retargeting a capture. Every action checks currentness in the store and Rust, including after asynchronous persistence/inference. An already-accepted old action's late receipt stays historical. Agent responses/reconciliation/actions survive ordinary restart; pending reassessment and superseded states are reconstructed. Issued context IDs, receipts and the entire transient workflow still need durable recovery.

For biometric approval, Rust validates the cached HOLD/policy/capability, active technician, exact IDs, native grant and expiry. A missing/failed/expired/cross-request grant blocks submission. An identical already-recorded action ID is idempotent locally; a second final action for the same decision is rejected. After successful local recording, the grant is consumed. The model and renderer cannot replace it with a supplied boolean PASS.

## 5. Contracts and integration points

The detailed wire agreement is [docs/integration/upstream-alice.md](../integration/upstream-alice.md). Keep that file as the console executable-contract reference under the main repository integration requirements; this subsystem handoff is the wider implementation/backlog map.

Inbound events currently defined:

- `alice.decision`: immutable upstream decision snapshot, request, policy, anomaly, evidence, source package and system-at-decision data, capability list and biometric flag.
- `alice.status`: current node, connectivity, operating mode, packages and engines, separate from historical snapshots.
- `alice.reconciliation`: original decision ID plus later evidence/discrepancy results; original decision must remain unchanged.
- `alice.agent_status`: agent identity/type/model, mission, health, activity and status.
- `alice.service_status`: concise operational service status/detail, never private model reasoning.
- `alice.agent_response`: decision/request/agent/challenge bindings and structured new justification.

Outbound schemas currently defined:

- `alice.context_request`: command ID, timestamp, decision/request/agent/challenge IDs, requested context fields and concise question.
- `alice.technician_action`: action ID, timestamp, decision/request/technician IDs, `APPROVE_ONCE | HOLD | RESEARCH | REJECT`, optional verification ID, note and mock/remote mode.
- Action receipt: echoed action ID, `ACCEPTED | PENDING | REJECTED`, message and currently `NOT_EXECUTED`. This is a submission acknowledgement, not an execution confirmation contract.

Zod schemas live in `packages/contracts`; generated JSON Schemas live in `docs/contracts`. Regenerate with `npm run contracts:generate` after contract changes. No new protocol should require views to consume legacy names or direct WebSocket/HTTP calls.

`RemoteAliceTransport` has no real socket/client behind it. Native `cache_decision` and annotation injection are mock-only. Replacing only the frontend class with an unauthenticated POST client would bypass the intended trust design; the team must implement native authenticated ingestion/cache and action delivery while retaining the existing domain/UI interface.

## 6. Identity, configuration and data

### Historical standalone identity status

At the standalone audit, the selected mock-edge database contained one administrator, one technician and one face enrollment. At that audit, local `.env` values for admin credentials and the biometric token were configured; none were imported into this checkout. Read-only audit inspection found FACE_ENROLLMENT_UPDATED and TECHNICIAN_LOGIN_SUCCESS. No STEP_UP_PASSED or ACTION_SUBMITTED events were present in this database at this audit, and zero technician actions were recorded. The user independently confirmed that face login worked. No passwords, hashes, tokens or embeddings were printed or copied into documentation.

The bootstrap runs whenever the selected console database has zero admin rows and both admin environment values are nonempty. It is not restricted to a brand-new database file. A password shorter than 12 characters fails startup. Once an admin exists, changing `.env` does not rotate its password. The stored hash is Argon2id; the application does not recover plaintext from it.

The mock and real transport databases are separate. Switching from `ALICE_TRANSPORT_MODE=mock` to `remote` selects another default console database, so admin/technician metadata does not automatically migrate. The Python face store is configured independently; plan identity-store migration/consistency deliberately when changing modes or paths.

### Configuration reference

| Variable                                        | Purpose / default                                                                                                       |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `ALICE_ENV`                                     | Declared environment label; currently not a general feature-flag/security boundary                                      |
| `ALICE_TRANSPORT_MODE`                          | `mock` or `remote`; repository launcher defaults to mock; an unconfigured direct packaged executable defaults to remote |
| `ALICE_BIOMETRIC_MODE`                          | `mock` or `arcface`; independent of mock edge transport; remote transport refuses mock biometrics                       |
| `ALICE_ADMIN_USERNAME` / `ALICE_ADMIN_PASSWORD` | Bootstrap when the selected database has no admin; password at least 12 characters                                      |
| `ALICE_BIOMETRIC_TOKEN`                         | Shared local service bearer token, at least 32 characters; required for real identity                                   |
| `ALICE_BIOMETRIC_SERVICE_URL`                   | Loopback service, default `http://127.0.0.1:8765`                                                                       |
| `ALICE_BIOMETRIC_DATA_DIR`                      | Python encrypted enrollment database/key location; launcher default `services/biometrics/data`                          |
| `ALICE_INSIGHTFACE_ROOT`                        | Provisioned model root; default `services/biometrics/models`                                                            |
| `ALICE_FACE_THRESHOLD`                          | Cosine comparison threshold, default `0.45`; needs environment-specific calibration                                     |
| `ALICE_DATABASE_PATH`                           | Override the native console database; use a private dedicated directory                                                 |
| `OLLAMA_BASE_URL`                               | Default `http://127.0.0.1:11434`                                                                                        |
| `ALICE_LLM_MODEL`                               | Installed local Ollama model; historical standalone `.env` selected `llama3.1:8b`                                                      |
| `VITE_ALICE_PREVIEW_MODE`                       | Browser-preview configuration; cannot enable native authentication in a browser                                         |

Launchers load `.env` as literal `KEY=value` entries without evaluating shell expressions, and already-exported process environment variables take precedence. Restart the launchers to apply native environment changes. Never put credentials in `VITE_*` variables. Finder does not automatically load this repository's `.env`.

### Storage inventory

Native default directory: `~/Library/Application Support/org.alice.technician-console/`. Default files: `console-mock.sqlite3` and `console.sqlite3` according to transport mode.

| Native table           | Contents                                                            |
| ---------------------- | ------------------------------------------------------------------- |
| `admin_accounts`       | Username and Argon2id password hash                                 |
| `technicians`          | Technician ID, username, display name, role and enabled flag        |
| `face_enrollments`     | Native enrollment/provider/update metadata, not embeddings          |
| `decision_cache`       | Original decision/request IDs and immutable normalized JSON         |
| `decision_annotations` | Agent response/reconciliation JSON keyed by event kind and decision |
| `technician_actions`   | Action IDs, decision binding and submitted payload                  |
| `local_audit_events`   | Local timestamped security/action/operational records               |
| `settings`             | Local settings such as the chosen LLM model                         |

The Python service separately stores encrypted embeddings, model/sample metadata, and its encryption key. Raw camera frames stay in memory. Its directory is private and files are mode 0600. Native database contents are access-restricted but not wholly encrypted. Neither file permissions nor a key accessible to the same user provide protection from compromise of that OS account.

Sessions, grants, failure counters, some workflow correlation, receipts and language summaries are in memory. History hydration reconstructs review state from persisted records; it is not durable event replay. Decision snapshots, actions and annotations are now read in full so hydration retains every lineage ancestor; only audit presentation/export retains its 500-event window. Database retention is not automatically bounded by that display limit.

### Local files excluded from source control

`.env`, databases, `.tools`, Python virtualenv/model/data folders, `node_modules`, Tauri `target`, frontend `dist`, generated build bindings, logs, Playwright results and screenshots are ignored. A new teammate needs setup steps; copying or cloning source does not include the installed model, local credentials, enrollments or built application. Dependency locks and the original fixtures are intended source files.

## 7. Existing demo scenarios

| Scenario                          | Behavior                                                                                  |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| `01_normal_allow`                 | Selects the synthetic allowed read-only request                                           |
| `02_hard_policy_deny`             | Selects the synthetic prohibited EDR-disable request; approval unavailable                |
| `03_hold_high_anomaly`            | Default supplied HOLD, risk 94, partial evidence and DDIL                                 |
| `04_hold_context_rejustification` | Timed response → pending → static DEC-185; risk 94→62 and verified evidence 1→2           |
| `05_hold_face_approval_pass`      | Uses the shared successful simulated step-up path                                         |
| `06_hold_face_approval_fail`      | Forces the simulated approval control to return failure                                   |
| `07_ddil_cloud_offline`           | Uses the shared disconnected infrastructure fixture                                       |
| `08_reconnect_reconciliation`     | Adds connected current status and a later discrepancy annotation; original HOLD unchanged |
| `09_agent_failure`                | Marks a mock network agent failed                                                         |
| `10_llm_offline`                  | Forces the gateway unavailable while manual review continues                              |

Several named scenarios intentionally share the same base dataset rather than ten independent datasets. Agent model names are sample upstream data, not proof those models are installed. The development sliders expose selection/reset; production builds omit that scenario panel. Reset clears mock actions/annotations/grants while retaining all immutable original/reassessed decisions and local audit history. Therefore a persisted DEC-185 remains current after reset or restart. Use a fresh browser reload for the timed replay, or a separate disposable native mock database, preserving the normal enrolled identity. It is not a real-history deletion feature.

## 8. Historical standalone verification

Detailed evidence: [verification.md](../guides/console/verification.md).

| Check                                                  | Most recent recorded outcome                                                                                                                                          |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Strict TypeScript / ESLint / production frontend build | Passed                                                                                                                                                                |
| Vitest / React Testing Library                         | 61 tests passed                                                                                                                                                       |
| Default native Rust suite                              | 14 passed; two service-dependent integration tests intentionally excluded                                                                                             |
| Python pytest                                          | 11 passed; third-party deprecation warnings noted                                                                                                                     |
| Playwright                                             | Five passed: previous workflows plus timed lineage, historical controls, fresh DEC-185 approval and audit binding                                                     |
| Real ArcFace CPU smoke                                 | Enrollment/match passed; no-face and multiple-face rejected                                                                                                           |
| Real ArcFace through native Rust                       | Temporary service/token/store; enrollment, claimed-identity login, disabled-session revocation, failed capture, new step-up, exact approval, audit and removal passed |
| Real native Ollama                                     | Installed `llama3.1:8b` health and structured explanation passed                                                                                                      |
| Native development launch                              | Confirmed renderer-to-native cache/audit writes                                                                                                                       |
| Final release bundle launch                            | Temporary mock database received all three decisions through IPC; bundle name and camera usage metadata verified                                                      |
| Visual review                                          | Shared frontend screenshots at desktop and narrow widths reviewed; no horizontal overflow in the tested narrow layout                                                 |

That is **91 default tests across the full rerun suites**, plus the explicitly executed real-service checks. The automated results alone do not establish live camera operation. Separately, the user has now confirmed live enrollment/login, corroborated by native audit records. Live approval step-up, liveness, real upstream connectivity and signed distribution are not established. The reassessment implementation reruns formatting, typechecking, linting, all default suites, real-service checks and the native bundle build; see verification.md for exact results and evidence limits.

Useful commands from the repository root:

```sh
npm run demo
npm run check
npm run test:rust
npm run test:python
npm run test:e2e
services/biometrics/.venv/bin/python scripts/biometrics/smoke_arcface.py
services/biometrics/.venv/bin/python scripts/biometrics/smoke_native_identity.py
ALICE_TEST_OLLAMA_MODEL=llama3.1:8b node scripts/console/rust.mjs test ollama_live_gateway -- --ignored --nocapture
npm run build:app
```

The original workspace installed Playwright browsers under `.tools/playwright`. If separately installed there in this checkout, use `PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright" npm run test:e2e`, or install Chromium into Playwright's normal location. `npm run dev` is a browser preview and does not exercise native credentials, SQLite or real biometric commands.

## 9. Functional work to finish next

These are implementation/verification tasks, not a request to change the design now. Resolve them before declaring the system fully working.

### F1 — Finish live approval and negative-case acceptance (enrollment/login complete)

- Historically confirmed on the standalone Mac: administrator/token configuration, ArcFace mode on a configured loopback port, real technician enrollment and live facial login against the mocked edge. Current-checkout setup and acceptance require their own evidence.
- Next: approve the supplied HOLD using a fresh live camera capture; the successful login must not replace this step-up.
- Verify rejected/blank/multiple-face/poor-light captures, another person's claimed-identity failure, retry/cooldown, camera denial, no camera, and multiple camera selection.
- Verify disable, enable, removal and re-enrollment, including revocation of sessions/grants and surviving a normal app/service restart.
- Repeat in the actual built macOS webview, not just Chromium. Record machine/OS/camera/model/threshold and observed outcomes without retaining face photos in test reports.

Done when a person completes the positive and negative paths and any camera/runtime bugs found are fixed. Current automated inference tests remain useful regression checks but do not replace this.

### F2 — Finish workflow correlation and recovery

- Persist issued context command/challenge IDs and their lifecycle. The automatic path currently tracks generated challenge IDs in memory; a later model-generated clarification can produce a new ID without updating that map when the original contract has no challenge ID. Add a regression case and consistent tracking for every outbound request.
- Define response timeout, failed-agent, duplicate/late response, repeated-question and cancellation behavior. Current mock transport always returns a short delayed response; it is not a reliability implementation.
- Completed for reassessment: modal/action decision binding, stale-grant rejection, selected-request promotion and supersession during approval. Remaining: broader logout/disable/session-switch and cancellation cases while inference/submission is in flight.
- Persist/recover receipts, context correlation and meaningful pending workflow state. Hydration now rebuilds validated lineage, current/superseded states and pending reassessment from persisted responses, plus saved human actions. It still does not restore every transient state or receipt.
- Completed locally: optional reassessment contract, chain validation, native immutable cache, original/current dashboard and a deterministic mock successor. Have the upstream team confirm the linear delivery assumptions and implement its producer. Execution-confirmation events remain unagreed.

### F3 — Complete language-context and status behavior

- Build an explicit read-only language context containing the immutable original decision **and separately labelled latest agent response/reconciliation**. The generic question path currently passes the original decision object, so it can omit newer response/annotation data.
- Complete distinct handling for context summaries, evidence summaries and research questions. Provider methods and strict informational intents exist; much of the question path currently routes to the generic explanation call.
- Handle a response that arrives before Ollama is ready or before real technician login. Automatic summarization is attempted only when the response arrives and health is READY; later readiness/login does not automatically retry it.
- Add actual freshness/last-success timestamps and refresh/reconnect behavior to service and model health. The face panel currently says ON DEMAND rather than probing `/health`; status must not falsely imply readiness.
- Represent unknown/unreceived infrastructure values distinctly from confirmed offline. Some infrastructure rows currently turn absent fields into OFFLINE/UNAVAILABLE.
- Add richer concise service activity such as summarizing response or requesting context, without exposing model-private reasoning. Expand malformed-output, prompt-injection-in-agent-claims and selected-decision-change tests.

### F4 — Finish native operator operations

- Verify audit JSON export in the packaged macOS webview. It currently uses a browser Blob/download link; add a native save-dialog/write command if that does not reliably save the file.
- Synchronize UI lock/session state with native expiry/revocation. Rust rejects expired/disabled sessions, but the visible header or an already-open admin area can remain optimistic until the next command.
- Improve enrollment feedback after live testing: count usable accepted samples, explain specific quality failures, and make metadata-only editing distinct from enrollment if needed. Current capture collects five frames and then the server validates the batch.
- Add an explicit first-run configuration guide/state and a supported admin password-change/recovery procedure. There is no default password and changing environment variables does not rotate an existing account.
- Exercise closing/changing camera or leaving enrollment/login while work is pending; ensure cancellation, camera tracks and session state are predictable.

## 10. Upstream integration still to implement

### I1 — Real authenticated native transport

Agree edge endpoints, authentication, event versions and ownership with the team. Implement the WebSocket/read stream and REST/write clients in Rust; validate/cache inbound decisions at that trusted boundary, then notify the renderer through the existing transport interface. Implement agent clarification routing and action receipts. Keep source authentication and secrets outside React.

Done when real ALLOW/HOLD/DENY/status/agent/response/reconciliation events appear in the existing views and a technician request is acknowledged by the actual edge. No protected execution code should be added to the console.

### I2 — Durable delivery and reconciliation

Implement a persisted outbox with stable idempotency IDs, delivery states, bounded retries and recovery after restart. The current action builder creates a new ID for each invocation; a future network timeout must not cause retries to become unrelated authorizations. Define native transaction boundaries around grant consumption, durable submission and acknowledgements.

Add stream cursors, replay, ordering rules, reconnect backoff, missed-event recovery, unknown-decision response handling, stale-state indicators, and conflict diagnostics. Test real cloud/DDIL transitions and reconnection without overwriting historical evidence/decisions. Persist confirmed receipt state separately from original decision state.

### I3 — Remote biometric approval proof

Agree a signed short-lived attestation or authenticated verification-ID redemption protocol. A random local verification UUID is not a remote cryptographic proof. Bind console identity, technician, exact decision/request, verification issuance/expiry, provider and replay restrictions. Specify whether action parameters need a canonical digest/version and how upstream rejects stale or superseded requests.

Done when the real edge independently rejects fabricated, expired, cross-request, replayed or wrong-console proof and accepts the intended one-use action without treating face matching as a policy override.

### I4 — Contract completion

Confirm the implemented optional reassessment lineage and linear parent-before-child rule with upstream. Agree execution outcomes, receipt PENDING behavior, distributed cancellation/supersession, agent response retry/challenge semantics and compatibility/version negotiation. The existing receipt only declares NOT_EXECUTED. Update executable schemas, generated JSON, fixtures, integration docs and boundary tests together.

## 11. Reliability, security and distribution work

### R1 — Biometric hardening and separate liveness

Calibrate the identity threshold using representative consenting demo operators, cameras, lighting and expected failures. Record false-match/nonmatch behavior instead of treating `0.45` as a universal production setting. Add a liveness/anti-spoof provider only through the separate authenticity boundary and define its required policy before displaying it as active.

Current freshness means a new short-lived native verification operation, not cryptographic proof of a newly captured live scene. The renderer supplies images and ArcFace can match a photo/replay. If stronger capture authenticity is required, design a challenge/capture attestation boundary along with liveness.

Use typed/strict validation for native biometric HTTP responses, including provider, result, score/threshold shape and enrollment acknowledgement; the current native client consumes JSON values from the trusted local service. Add malformed-success-response tests. Tighten decoded-image resource limits before expensive image decoding for hostile local input, and test concurrent requests and cancellation.

### R2 — Identity storage and credential lifecycle

Coordinate failure recovery between native enrollment metadata and the separate Python embedding store. Enrollment/removal are two operations in two databases; a service success followed by native failure can leave them inconsistent. Store enrollment versions and reconcile interrupted operations. Define backups, key recovery/rotation, deletion, and mode/database migration.

Move long-lived secrets to an appropriate native credential store for a distribution, and pass only required configuration to each child process. Current `.env` launchers inherit the broader environment. No hardware-backed trust anchor, admin recovery, persistent lockout or complete credential rotation is implemented. Preserve current explicit native security checks while improving these areas.

### R3 — Database and audit lifecycle

Add schema versions/migrations rather than relying indefinitely on `CREATE TABLE IF NOT EXISTS`. Define retention, full-history pagination/export, backup, corruption/disk-full behavior and record reconciliation. Local audit is not tamper-evident and is not the upstream mission audit. Native security events and renderer operational events must stay distinguishable; avoid treating renderer statements as proof of successful authorization.

### R4 — Managed service startup and distributable packaging

Choose a supported macOS architecture/OS matrix. Build/manage the Python service as a signed sidecar or maintain an explicitly provisioned service installer, with startup readiness, restart/shutdown, private token handoff, logs and actionable failures. Do not download models during login or offline operation. Ollama should have an explicit availability/setup experience and a configurable model.

The existing bundle contains frontend/fonts/icon/Rust, not the Python runtime, model weights or Ollama. Implement signed/notarized distribution, validate hardened runtime/camera permission, and exercise a clean Mac install. The Python lock was resolved on Apple Silicon; Intel and older macOS compatibility remain untested. Confirm pretrained model distribution rights separately from library source-code licensing.

### R5 — Expand repeatable validation

Add CI or a documented clean-machine runner for frontend/native/Python checks; no hosted CI pipeline exists yet. Add the real native camera/operator acceptance record, request/selection race cases, no-biometric approval confirmation, receipt/outbox failures, service crash/restart, expired/revoked session presentation, credential cooldown and DB failure cases. Browser screenshots do not certify WKWebView capture or native export.

Create a reproducible demo runbook with service readiness, enrollment status and the intended scenario. Consolidate local dependency/model setup for teammates. Existing local environments and successful test logs are helpful evidence, not a replacement for reproducibility.

## 12. Deferred full visual and animation update

**User-requested future phase: rebuild the visual and motion experience after functionality works. Do not begin it as part of this handoff.**

The existing custom CSS dashboard is an initial functional design, not the final artistic direction. Plan a full pass across the application rather than isolated cosmetic edits: operations, history/audit, research, command answers, settings, first-run setup, admin/enrollment, facial login, camera capture, errors, approval and success states.

Evaluate maintained, suitable open-source animation and UI libraries. Include the user's `apple-liquid-glass-ui` GitHub suggestion as a candidate; its exact repository, license, maintenance status, package API and suitability have not been verified or selected. Library popularity and compatibility should be researched at the time of this phase, not assumed from the name. No liquid-glass or third-party motion library is currently part of this build.

The design implementation brief:

- Establish a cohesive material, typography, spacing, elevation, border and motion system while retaining a distinct ALICE identity and meaningful contract-driven visuals.
- Explore glass/translucency/refraction where it helps hierarchy; preserve legibility of dense security facts and warnings. Maintain an inexpensive opaque fallback for unsupported or costly effects.
- Use a reusable motion system for navigation, panels, status changes, research/approval modals, evidence updates, loading, camera guidance and success/failure feedback.
- Tie motion to real operational states. Never animate an approval success, completed verification or execution before the corresponding validated state exists.
- Keep the action bar and trust/evidence hierarchy stable during incoming events. Motion must not cause accidental clicks, move a decision under a confirmation, or obscure request binding.
- Preserve keyboard operation, focus management, escape/cancel behavior, accessible labels/contrast, reduced-motion support, non-color status cues, and visible simulation/liveness boundaries.
- Measure performance in macOS WKWebView while ArcFace and a local LLM are running. Avoid expensive permanent blur/shader/animation work that interferes with capture or review.
- Update shared tokens/components first, then all application flows, responsive layouts and screenshots. Keep domain/security/transport logic unchanged unless an independent functional defect requires correction.

Start this phase only after the live identity acceptance run and critical F/I work are complete for the intended demo scope, outstanding failures are visible and controlled, and a reproducible functional baseline is recorded. Finish with real native visual QA, keyboard/reduced-motion checks, measured performance and rerun workflow/security checks.

## 13. Recommended execution order and completion evidence

1. **Finish live face approval acceptance against the mocked edge.** Enrollment and login are complete; exercise fresh approval, negative captures, retry and identity-management cases next.
2. **Close functional gaps F2–F4.** Add focused regression cases for the concrete correlation/context/recovery issues and native operator checks.
3. **Agree and implement I1–I4 with upstream teammates.** Exercise the whole real-event/review/proof/receipt path and disconnect/reconnect recovery without adding an executor here.
4. **Make the chosen demo setup reproducible.** Complete the service/identity/storage/distribution reliability items appropriate to that deployment; record any explicitly deferred production requirements.
5. **Freeze and record a working baseline.** Capture exact setup and tests, operator acceptance, supported Mac configuration, remaining known limits and the intended demo scenario.
6. **Perform the complete visual and animation update.** Research/select open-source libraries at this point and implement the section 12 brief against that stable baseline.
7. **Reverify the final experience.** Native app, camera, disabled/expired identities, one-use approvals, outages, real receipts, keyboard/reduced motion and performance must all survive the redesign.

Do not mark the subsystem integrated merely because it builds or because a simulated approval says ACCEPTED. Completion evidence must identify the actual transport, identity provider, runtime, tested operator flow and whether execution was independently reported by upstream.

## 14. Reading order for the next contributor

1. [README](../guides/technician-console.md): setup, run/test/build commands and initial scope.
2. [Facial verification quick start](../guides/console/facial-verification-quickstart.md): current credentials/enrollment state and exact operator steps.
3. [Upstream agreement](../integration/upstream-alice.md): wire events/actions and team integration decisions.
4. [Architecture overview](../architecture/overview.md), [HOLD workflow](../architecture/hold-workflow.md), [LLM boundary](../architecture/llm-boundary.md), [biometric boundary](../architecture/biometrics.md).
5. [Contract reference](../contracts/alice-events.md), [legacy compatibility](../contracts/legacy-dashboard-contract.md), [agent/service status](../contracts/agent-status.md).
6. [Verification evidence](../guides/console/verification.md), [Mac setup](../guides/console/mac-setup.md), [mock scenarios](../guides/console/mock-scenarios.md), [contribution guide](../guides/console-contributing.md).

This handoff records subsystem status and migration scope. Copying source does not create credentials, enroll a face, switch runtime modes, implement remote transport, or start the deferred redesign.

## 15. Reassessment implementation file map

This milestone extends the existing architecture. No policy/evidence/anomaly algorithm, external UI animation library, remote endpoint or new authentication protocol was added.

- Contract and index rules: `packages/contracts/src/alice/events.ts`, `packages/domain/src/lineage.ts` (new), `packages/domain/src/hold.ts`, `packages/domain/src/index.ts`.
- Store, timed simulation and fixture: `apps/desktop/src/state/console.ts`, `apps/desktop/src/lib/transport.ts`, `fixtures/scenarios/index.ts`, `fixtures/alice/reassessment.json` (new).
- Dashboard/history/current action binding: `apps/desktop/src/components/decisions/DecisionLineage.tsx` (new), `DecisionWorkspace.tsx` beside it, `apps/desktop/src/components/audit/History.tsx`, `apps/desktop/src/components/biometrics/ApprovalModal.tsx`, `apps/desktop/src/components/evidence/EvidencePanel.tsx`, `apps/desktop/src/app/App.tsx`, `apps/desktop/src/styles/global.css`.
- Native authority and persistence: `apps/desktop/src-tauri/src/commands.rs`; matching command/security regression coverage in `commands_tests.rs`. Existing SQLite schema and identity/enrollment storage remain compatible; no database reset/migration is required for this optional event field.
- Tests: `tests/contracts.test.ts`, `tests/store.test.ts`, `tests/security.test.ts`, `tests/dashboard.test.tsx`, `tests/e2e/console.spec.ts`. Existing status/login/Python suites continue to run.
- Generated/documented contracts: `scripts/console/generate-contracts.ts`, `docs/contracts/alice-events.schema.json`, `docs/contracts/alice-events.md`.
- Integration and operating context: `docs/architecture/hold-workflow.md`, `docs/architecture/overview.md`, `docs/development/mock-scenarios.md`, `docs/development/facial-verification-quickstart.md`, `docs/development/verification.md`, `docs/integration/upstream-alice.md`, `README.md`, this handoff and `PROMPT_CONTEXT.md`.
- Historical standalone review/sharing outputs: refreshed `artifacts/screenshots/reassessment-desktop.png`, operations/narrow screenshots, and `artifacts/ALICE_Prompt_Context.zip` with source, docs and preserved reference inputs. These artifacts were not imported and remain ignored by Git; no secrets, enrolled faces, runtime databases, weights or build caches belong in the sharing package.

Remaining integration assumptions: one linear assessment chain per request; live parent-before-child delivery; changes to any of the five fixed request identity fields require a new request; other action parameters are preserved in the supplied full decision and are not reinterpreted by the console. Missing-parent replay, competing assessments, upstream attestation, real ACK semantics, cancellation and final execution confirmation require team agreements. The actual ALICE core, outside this workstation subsystem, must produce future reassessments; Ollama cannot do so.
