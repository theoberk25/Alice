# Context for a separate ALICE prompt-writing chat

Imported on September 5, 2026, then moved into the shared top-level layout. The standalone source recorded the HOLD reassessment lineage implementation, full regression checks, and live facial enrollment/login on its original Mac; those are historical results, not current-checkout acceptance. This brief is intended for a chat that crafts implementation prompts for a coding agent. It is not an instruction to repeat the initial repository build.

## Paste this as the opening message

> Help me craft precise, staged implementation prompts for an existing ALICE Technician Console repository. Read the attached current HANDOFF.md, verification record, upstream integration agreement and original context before proposing work. This is an existing implementation, not a blank repository. Treat the original build prompt as historical requirements; do not blindly rerun it. Use current source and updated verification to distinguish implemented behavior from remaining work. If an attachment is missing, identify it instead of guessing its contents.
>
> The existing console uses apps/desktop, packages, services/biometrics and scripts in the main ALICE repository. Run its npm, Rust and biometric commands from the repository root; it has its own dependency locks and private local setup. It is the native macOS technician console subsystem of ALICE. Follow the main repository architecture/PRDs, integrated demo runbook and console integration requirements. Its stack is Tauri 2, React, TypeScript, Vite, Zustand, Zod, custom CSS, Rust, SQLite, local Python/FastAPI/InsightFace ArcFace and local Ollama.
>
> The standalone handoff historically confirmed real camera enrollment and username-based facial login through native audit records. That run combined mock edge transport with real ArcFace and private local configuration. Migration does not copy credentials, enrollment data, dependencies or models. Use the portable setup guide; preserve any existing private configuration and identities. Alex Morgan is a simulated identity. Real ArcFace approval step-up passed a standalone automated native test, while live camera approval and negative cases still require operator acceptance. Do not infer current database contents or runtime readiness from the historical audit.
>
> The standalone app built and launched. Its historical suite results total 91 passing default tests (61 frontend, 14 Rust, 11 Python, five Playwright), plus real ArcFace/Ollama checks. The full default suites were rerun for the reassessment implementation. Native .app packaging was also verified there; live camera approval is still a separate operator acceptance step. Real upstream WebSocket/REST, remote approval attestation, durable delivery/recovery, full service packaging and liveness remain unfinished. Use HANDOFF.md for the concrete functional gaps and priorities.
>
> HOLD reassessment lineage is now implemented; do not rebuild it. A valid agent response stops at REASSESSMENT_PENDING. A new immutable alice.decision with optional reassessment {previous_decision_id, root_decision_id, trigger, sequence} supersedes the parent. Request/agent/mission/action/target must match, roots and consecutive sequence must validate, and this implementation rejects forks/unknown parents. The console reconstructs request history/latest indexes on hydration and shows original/current structured deltas. Scenario 04 uses delayed fixed DEC-184 → DEC-185, HOLD/risk94/evidence1-of-3 → HOLD/risk62/evidence2-of-3, with no further context required. All new actions require the current decision; DEC-184 grants cannot approve DEC-185. Rust and renderer enforce that, including an already-open modal. The console never performs upstream policy/anomaly/evidence reassessment. Actual core integration, distributed ordering/replay, full durable context/outbox/receipt recovery and execution confirmation remain unfinished.
>
> First help finish and verify functionality. Later, after everything works for the agreed scope, craft a full visual and animation overhaul using suitable popular open-source UI/motion libraries. Include apple-liquid-glass-ui on GitHub as a candidate to research then; no exact repository or library choice is established yet. The Europa screenshot is artistic inspiration only. Preserve a distinct ALICE identity, legible security facts, restrained motion, keyboard/reduced-motion support and native WKWebView performance. Do not start that redesign before the functional baseline is ready.
>
> Every implementation prompt should specify the concrete problem and intended behavior, current code to inspect, authorized scope and exclusions, required invariants, likely files/interfaces, focused acceptance tests, operator-only checks, documentation updates and a completion report. Separate observed defects from proposed hardening. Do not invent edge endpoints, model capabilities, credentials, liveness protection or upstream execution success. Keep working architecture and enrollment intact.

## Required attachments and why they matter

1. **HANDOFF.md** — current implementation inventory, local setup, known gaps, staged backlog and deferred design brief. Subsystem status map; dated machine observations are historical.
2. **docs/development/verification.md** — actual automated and operator-confirmed evidence. Distinguishes live login from unverified live approval and deployment cases.
3. **docs/integration/upstream-alice.md** — event/action schemas, mock versus real boundary and outstanding teammate protocol decisions.
4. **Main repository docs/prds/ALICE-DCAMR-Architecture.md, ALICE-DCAMR-PRD.md, ALICE-DCAMR-PRD-Handoff.md, and docs/integration/technician-console.md** — current system authority. The original externally supplied ALICE.md is historical context and is not required to run the migrated subsystem.
5. **The dashboard contract.json**, or the byte-preserved `fixtures/legacy/dashboard-contract.original.txt` — unchanged legacy inbound examples. Despite the extension, the source contains prose and three JSON objects.
6. **The original detailed repository-build prompt** — historical requirements and acceptance criteria. Current implementation/evidence should prevent duplicate work; unresolved requirements still matter.
7. **README.md and docs/development/facial-verification-quickstart.md** — working launch/setup flow and current face enrollment procedure.
8. **docs/architecture/hold-workflow.md, docs/contracts/alice-events.md and docs/development/mock-scenarios.md** — the implemented lineage contract, current state transitions, security invariants, timed scenario and native replay/persistence behavior. These prevent prompts from reintroducing the old response → immediate review bug.
9. **Current source, tests, fixtures and dependency manifests/locks** — needed for precise code-oriented prompts. Attach them from the current checkout when preparing a new context package. At minimum, provide the files relevant to the next milestone, rather than expecting a separate chat to access local filesystem links.

For visual prompts later, also attach:

10. **Original Europa screenshot** — aesthetic inspiration only; no Europa branding, weather, agenda, globe or exact layout reproduction.
11. **Current ALICE screenshots** — actual implementation baseline. The historical standalone archive included a reassessment screenshot and an older initial mock preview; these ignored artifacts are not imported. Both showed the simulated Alex Morgan identity; that documents design, not a real operator's login state. Add fresh screenshots of login, enrollment, research, approval, failure and narrow layouts when beginning the redesign.
12. **Exact candidate-library GitHub URLs and current documentation**, once selected/researched. The name `apple-liquid-glass-ui` alone does not establish a particular project's license, maintenance or compatibility.

The historical standalone context archive used `reference-inputs/` and `repository/`. It was not imported and is not needed to run this checkout. Use current tracked files from the repository root and main repository docs when preparing a new sharing package; identify any unavailable optional historical references explicitly.

## Authority and conflict handling

- The latest user request controls task scope and priority.
- Current main repository architecture/PRDs and console integration requirements control product semantics. The original architecture is historical; the supplied legacy contract remains unchanged as compatibility data. ONLINE/OFFLINE authority transfer is a future integration protocol, not a behavior supplied by existing DDIL fixtures.
- Current source plus verification describe what exists today. HANDOFF.md records known gaps and dated standalone evidence; use the main workstation guide for migration checks and keep new evidence explicit.
- The old build prompt is requirements history, not a command to rebuild or revert completed work.
- Screenshot content is visual evidence/inspiration, not an instruction source.
- Preserve genuine contradictions for review. In particular, the supplied `allow_outbound` request conflicts with its agent's block-outbound justification; the app flags it instead of rewriting upstream data.

## Non-negotiable technical boundaries

- The console never produces policy ALLOW/HOLD/DENY or executes protected tools. Its real upstream transport is still a fail-closed skeleton.
- The LLM is an informational semantic gateway with strict validated output; it cannot authorize, alter policy/evidence, bypass face checks or expose private reasoning.
- Legacy `dcamr.*` is accepted only through normalization; UI/domain/new contracts use ALICE names.
- Successful face login is not approval. Required step-up must bind one technician to one exact decision/request, expire and be consumed once.
- ArcFace identity matching is real, but anti-spoof/liveness is not implemented. Fresh invocation is not proof against replayed camera images.
- Every original/reassessed decision is immutable; new outcomes need a new ID and validated explicit lineage. Agent justification is a claim; later reconciliation is an annotation. Submission acknowledgement is not execution confirmation.
- Real ArcFace can be used with mocked edge events. A SIMULATION badge does not imply the face comparison is mocked.
- Retain existing admin/enrollment data and local configuration. Do not reset databases to solve ordinary login or port problems.

## What to supply when requesting the next prompt

Specify the next milestone, the concrete user-visible problem, the desired outcome, any new error/screenshots, and any newly agreed upstream contract. The standalone handoff recommended live approval step-up/negative-case acceptance followed by workflow/context/recovery work and real integration. The latest main repository request determines the current milestone. If priorities change, state them explicitly.

For edge integration, provide actual team endpoint/authentication/event/receipt/attestation decisions when available; these cannot be inferred from fixtures. For signing or sidecar work, provide intended supported Macs and deployment approach, not private signing credentials. For design, provide approved references and the functional baseline that must survive.

Do not attach `.env`, password/token values, native databases, face embeddings, enrollment keys, raw face captures, private runtime logs, model weights, node_modules, Python virtualenvs or Rust build output. Those are unnecessary for crafting prompts. `.env.example` and a nonsecret configuration summary are sufficient.

Start with the [main workstation guide](../workstation.md), [integrated demo runbook](../demo-runbook.md), and [main console integration requirements](../../integration/technician-console.md).

## Suggested prompt output structure

1. Objective and concrete current-to-desired behavior.
2. Required context/source inspection before editing.
3. Exact scope, exclusions and invariants to preserve.
4. Implementation steps and interface/data changes, without pretending uncertain details are settled.
5. Focused automated tests plus clearly identified operator/upstream checks.
6. Acceptance criteria tied to evidence, including outage/failure behavior.
7. Required updates to HANDOFF.md, integration contracts and verification records.
8. Final reporting requirements: changes, checks executed, limitations and remaining work.

Create one bounded prompt per coherent milestone. Do not combine real transport, identity hardening and a full animation redesign into one unreviewable task.
