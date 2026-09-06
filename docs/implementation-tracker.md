# ALICE implementation tracker

Updated: 2026-09-06 UTC. Scope: the ALICE repository.

This preserves all 118 user-supplied task labels in their original order. IDs
`001`–`118` are stable: update status/evidence without renumbering or silently
renaming tasks. These statuses describe the implementation and evidence included
in this repository; they do not imply a deployed system.
The current [parent PRD][prd], [architecture][architecture] and
[developer handoff][handoff] define the product boundary. The integrated console's
progress and remaining cross-system agreements are documented separately in the [console integration note][console-integration];
it does not change core task status without a working cross-system connection.
The current increment adds the [local Decision Evidence Ledger][audit-guide];
two-mode admission, authority and live transport still need runtime integration.

## Status and current checkpoint

Live dashboard slice published to `origin/main` as `44f4d73`; push confirmed,
no deployment performed. [Configuration and field mapping](integration/live-dashboard.md).
The real local first-light runtime now feeds the existing technician dashboard
automatically through validated authenticated transport. USB-backed SQL storage
and no-fallback mount guards implement the user-approved offline storage direction.
Remote biometric actions, full enterprise snapshot synchronization, SIEM workers and
physical Pi/USB acceptance remain pending. Verification is recorded in the
[live handoff](handoffs/2026-09-06-live-dashboard.md). Task 082 becomes Partial;
all task IDs and labels are preserved.

The local [SQL input snapshot increment](handoffs/2026-09-06-release-snapshot.md)
adds immutable signed first-light packaging and verified startup without replacing
offline audit history. It is uncommitted; the published baseline remains above.

### Historical checkpoints

Architecture correction from Theo's supplied older plan: the root document now
defines the intended Pi pipeline and backend/live-workstation data flow. User
clarification: Pi owns ML classification; the local Mac resolves held actions to
accept or deny after biometric verification. Theo/Jared are configuring the Pi,
Xavi is working on hardware, Merek will implement backend integration next session,
and Alex will adapt workstation scripts/dashboard against the agreed live contract.
The [alignment handoff](handoffs/2026-09-05-theo-architecture-alignment.md) records
remaining codec/storage/proof decisions. This is documentation/coordination only;
all 118 task IDs, labels and implementation statuses remain unchanged.

Integrated architecture/layout review against main `d6e7e55`: preserved the
first-light implementation and task updates alongside the documentation follow-up.
Fresh full Python suite: **265 passed, zero skips** (16.872 seconds with local
loopback access for the mock ESP). All 384 latest-main files survive at original
or mapped paths. Root architecture and active guides now distinguish this signed
request/fixture/mock-controller slice from the full product. See the
[combined review](handoffs/2026-09-05-team-layout-review.md) for scope and checks.

First-light integration slice (branch `first-light-test`, 2026-09-05): one
OFFLINE terminal request (`set_light_state -> ESP-LIGHT-01`) now runs end to end
against a mock ESP: signed-envelope authentication, verified release load,
exact-match permission, explicitly labelled fixture assessment, auto ALLOW,
durable AuditLog trail (EXECUTION_ATTEMPT committed before execution), separate
receipt/result/observed-state, idempotent retry (one ESP command total) and a
verified, acknowledged USB export. **263 tests passed (30 pre-existing skips)**,
including the 6 new [first-light tests][first-light-tests] and a multi-process
local dry run. The assessment is a wiring fixture, not detection; the real ESP
firmware contract and physical run remain. [Evidence][first-light-handoff].

Architecture/layout follow-up before the first-light merge: expanded the root map with deployment, operating
lifecycle, source-backed components, contract boundaries, storage/model lifecycle
and retained scaffolds. Corrected stale active console/ledger descriptions and
setup paths. All 374 baseline files survive at original or mapped paths; no further
relocation was required. Six focused Python path tests and four launcher tests
passed. Product task IDs, statuses and totals are unchanged. Detailed documentation
checks are in the [combined review](handoffs/2026-09-05-team-layout-review.md).

Combined layout review of GitHub main at 3330a07: corrected biometric model
provisioning's missing Path import with two isolated regressions, completed docs
centralization, and refreshed the root project/architecture entry points. Fresh
core suite: **259 passed, zero skips**. Console type-check, lint, 64 frontend tests,
four launcher tests and production build passed. Product task statuses remain
unchanged. [Review and limits](handoffs/2026-09-05-team-layout-review.md).

Technician console layout migration: workstation/ is removed; source is organized
under apps, packages, services, fixtures, tests/console and the shared docs tree.
Launchers are in scripts/console and scripts/biometrics; npm commands run at root.
**64 frontend, 4 relocation, 14 default Rust, 11 Python and 5 browser tests passed**,
plus real public-image ArcFace/native identity checks, app bundling and 257 core
tests (with documented Python dependency setup). All 369 original tracked files
survive; no console contracts or core product statuses changed. The user authorized
committing this migration to local main; that historical publication limit was
superseded by its merge into GitHub main at 3330a07.
[Complete move map and verification](handoffs/2026-09-05-console-layout.md).

Earlier lab developer-tool relocation: implementations now live in scripts/lab with preserved
lab.* imports and a launcher independent of working directory. Pi runtime stays
in dcamr. **257 tests passed, zero skips**, including copied-checkout generation
and unchanged enterprise payloads. [Move map and evidence](handoffs/2026-09-05-lab-script-relocation.md).
This is a path migration; the 118 product task statuses are unchanged.

Combined assessment + ledger verification: **253 tests passed, zero skips**.

Latest decision-boundary increment: [Pi assessment](contracts/decision-assessment.md)
combines trusted permission findings with contextual model evidence for the
technician application's local LLM. Unusual PRE_ACTION observations explicitly
require human approval. This emits no final decision or execution token; transport,
audit, permission resolution and Pi model export remain separate work. The 17 new
checks include real fitted-model integration; the assessment-only checkpoint passed **165 tests**. Older architecture descriptions of
Pi-owned final fusion need a coordinated application/enforcement contract update;
this assessment is not silently substituted for `alice.decision`.

- **Done component** — the named local computation or record structure is
  implemented and has component-test evidence. It does not imply that admission,
  policy, fusion, transport, enforcement, or Pi deployment is complete.
- **Partial** — a related bounded slice exists, but the task's broader behavior
  or integration remains. The evidence column names the boundary.
- **Planned** — the requested behavior is not implemented in this checkout.
  A PRD proposal or empty skeleton is not completion evidence.

Current totals: **12 Done component, 39 Partial,
67 Planned**. These are task-status counts, not a percentage of product
readiness or an estimate of remaining effort.

The current model increment is a [general contextual Isolation Forest][context-guide]
for separately bound PRE_ACTION and POST_ACTION observations. Jared selected both
phases; synthetic enterprise data is now available, with real ESP collection pending. Context profiles define named
numeric inputs, units and timing; each supported context has a separate forest
and held-out normal reference. Missing/stale readings, unseen context and an
untrained model produce UNKNOWN/null scores. Input/source validation, in-memory
fitting and repeatable scoring are implemented; actual ESP extraction and data
collection, artifact loading, fusion and deployment are not.

The pre-ledger checkpoint passed **148 tests**, including 45 parser/model checks;
both existing cyber fixture replays still pass. New test data is unitless,
synthetic and temporary, not a light/voltage operating baseline. New assessments
retain training-range evidence independently of ML score and use a separate
internal contract, pending the canonical anomaly/decision adapter.


The [durable ledger slice][audit-guide] adds local SQLite recording, strict compact
contracts, trusted Ed25519 checkpoints, bounded delivery bookkeeping and linked
findings. Ledger checkpoint verification: **236 Python tests passed, zero skips**, plus both
cyber replays (8 anomaly fixtures, 7 rank cases, 5 feature vectors) and the
[model-to-ledger replay][context-ledger-replay] (6 synthetic assessment cases).
That replay verifies real PRE/POST scoring and explicit failure outcomes through
compact projection, exact retained evidence, sealing, anchored restart and duplicate
retry; it does not establish live producer integration. Independent
whole-branch review found a runtime metadata-validation gap; a two-line check and
regression test now reject changed stored metadata before further writes. Rereview
has no open material findings. No live producer, sender, admission gate, execution fence,
sensor driver or Pi hardware acceptance is implied. Original history is retained;
acknowledgement does not permit deletion or prove execution.

The probable demo hardware is now an ESP with lights and a voltage sensor.
The [enterprise simulation](handoffs/enterprise-sim-handoff.md) now supplies Wazuh
configuration, demonstration permissions releases 42–44, synthetic voltage
observations and authored audit fixtures. Pi permissions loading/resolution and
live audit integration remain unimplemented. Synthetic electrical limits and
internal-authoritative audit storage are proposals, not accepted hardware rules.
The next model dependency is the device/action/context data contract. **Execution
authority and trusted synchronization** remain required integration work. The product has
exactly two modes:

| Mode | Execution authority | ALICE work to implement |
| --- | --- | --- |
| **ONLINE** | Enterprise systems govern and execute actions directly. | Synchronize authorized permissions, normal behavior and relevant SIEM/EDR/mission caches; consume authenticated upstream/downstream activity feeds and preserve user/agent attribution. |
| **OFFLINE / DDIL** | ALICE governs supported local-agent requests after the protected endpoint has transferred authority to it. | Apply last trusted caches, local ML, telemetry/history and IT technician review; log every request, decision, execution attempt and result. |

ALICE is not a mandatory ONLINE action gateway. Direct enterprise execution
needs an explicit activity-feed coverage/cursor contract so ALICE does not infer
unobserved actions from silence. Local OFFLINE governance needs an endpoint-enforced
single-authority fence; connectivity loss alone does not establish control.
Reject stale commands and outstanding approvals from the previous authority.
The protocol and its implementation remain pending.

Reconnection is a workflow between the two modes, not an additional product mode.
The Pi connects directly to enterprise systems to publish **all** DDIL audit,
flag risks, append reconciliation and verify/atomically update compatible caches.
The Technician Mac is not a manual relay. Returning ONLINE must fence local
commands and approvals; a successful connection or upload does not itself grant
execution authority or prove that the whole audit backlog was acknowledged.

All current **Done component** statuses remain scoped to the existing components
below. The topology, authority transfer, live cache sync and motor path are not
implemented here. See the supplemental planned requirements after the original
118-task tables; they are deliberately excluded from the original status counts.

Jared explicitly selected **trying separate diagnostic and state-changing
calibration references**, and that Mac experiment is now complete. It collected
1,000 distinct normal source requests per reference from fresh held-out sessions;
within-session observations can be correlated. On another fresh evaluation set,
legitimate changes reached elevated/high in 32/68 cases with the shared reference
and 2/68 with separate references. Unseen-destination ML outcomes also fell to
0/20 elevated/high, while independent novelty flags were preserved. Neither
candidate is accepted for deployment. The [training guide][training-guide] records
the paired results, limitations and runnable comparison. At the cyber-only checkpoint, the
suite passed 103 tests; artifact digest links and 1,300 paired score mappings
were checked. A cyber
calibration experiment does not establish a motor reference.

Pending device decisions are the actual ESP/light/voltage sensor, measurement
units/conversion, sampling rate, requested parameters, operating contexts, feature
windows and post-action settling time. Before/after scoring is selected; actual
normal collections and hard permissions remain distinct. Earlier motor angles
are deferred unless that demo returns. Direct Pi-to-enterprise synchronization
remains selected; Wazuh does not itself settle authoritative permissions export,
cache validity, audit retention or offline reconciliation.

The supplied `ALICE_TechnicalReview` handoff reports a native console with
fixture-driven review/UI, immutable reassessment history, local approval grants,
real ArcFace enrollment and successful live facial login. Its real camera
approval step-up still needs operator acceptance; remote native transport,
verifiable approval proof, durable outbox/receipts and core execution integration
remain pending. This is local ArcFace facial verification, not Apple Face ID
or implemented liveness. That handoff predates the console's shared-root migration;
current local verification is recorded above. The 118 core statuses remain scoped
to their named components and integrations.

The [output-contract slice][contract-guide] and [feature-builder slice][feature-guide]
are implemented. Existing [contract tests][contract-tests], [rank tests][scoring-tests],
and [feature tests][feature-tests] exercise those components. The replay harnesses
use eight mock anomaly results, seven deterministic rank cases, and five synthetic
feature-input cases. None is a complete request-to-enforcement test.

The **Mac-only synthetic training/evaluation slice** is now implemented. The
first lab run used synthetic data as a stated working assumption after the
training-data question remained unanswered; that choice was not an explicit
user confirmation. The [generator][synthetic-data], [training pipeline][training],
and [CLI][training-cli] produced the published [candidate-002 report][training-report].

That run fitted a real Isolation Forest **in memory** with 64 trees, at most 256
samples per tree, 11 features, one model worker and one numerical-library thread.
The [dataset manifest][training-manifest] records 6,000 synthetic normal requests
from 500 sessions, split by whole session into 3,600 training, 1,200 calibration,
and 1,200 held-out normal requests, plus 100 independent challenge examples used
only for evaluation. The [training tests][training-tests] and [generator tests][synthetic-tests]
cover the component boundaries, including actual bounded fitting.

Only JSON report, calibration-reference and dataset-manifest files were written;
**no fitted model was persisted**. Selected outputs are preserved under `docs/reports/anomaly-lab/`, while
the source and tests provide reproducible component evidence. Synthetic scenario
results do not establish real-world detection quality, and Mac timing does not
establish Pi performance. The report explicitly sets `deployment_ready=false`.
Model artifact format, operational calibration acceptance, runtime model loading,
and mapping feature flags into the anomaly result remain separate decisions.
The Pi owns the direct synchronization/upload integration path. The authoritative
enterprise issuers, release contracts, cache coverage and recovery rules still
need agreement and implementation.

## Agreed scope and resource constraints

- Target: Raspberry Pi 4 Model B, **2 GB RAM**, Raspberry Pi OS Lite. Confirm OS
  bitness on the device. Training stays on the Mac; the Pi performs frozen-model
  inference only when that runtime is implemented. The LLM and ArcFace stay on
  the Technician Mac.
- The implemented profile covers Web-01 cyber requests: routine diagnostics and
  occasional changes to known destination relationships. Its five-action profile
  and example counts are documented in the [feature guide][feature-guide]; counts
  are synthetic, not observed operating limits or policy permissions. Keep this
  profile as regression coverage while agreeing the separate motor contract;
  the latest likely demo uses ESP lights/voltage, with actual data still pending.
- ONLINE enterprise control reaches protected endpoints directly. The intended
  OFFLINE local path is Agent Mac → DCAMR Pi → protected ESP/system controller,
  with the Technician Mac providing review and explanations. The router supplies
  the uplink. Fenced authority transfer, controller authentication, exact approval
  binding, replay prevention and independent position feedback remain requirements.
- The desired USB layout is `permissions/`, `normal_behavior/` and `audit_logs/`.
  Authorized permissions replaces “policy” as the product term; existing `policy`
  keys, `dcamr/policy_engine/` and `packages/mission_policy/` remain legacy code/wire
  names until a coordinated schema migration. Trusted inputs require verification;
  audit logs are a separate ALICE output. Original **Policy**, **SD Card** and
  **SD Package** task labels remain verbatim and track the equivalent permissions/
  USB work. Naming does not implement discovery, signatures, persistence or atomic
  activation.
- A new authenticated agent may use exactly one cohort matching its trusted
  role and mission type. It still carries `agent_known=0` and `AGENT_UNSEEN`.
  An identity/profile mismatch does not trigger an arbitrary fallback.
- The feature vector has 11 fixed numeric fields. History is a complete,
  immutable 300-second window, with session scoping, duplicate handling and
  explicit incomplete-history markers. The component reads history; it does
  not own a persistent history store.
- Implemented input bounds: 8 MiB baseline payload, 1 MiB feature-input bundle,
  16 KiB normalized action, at most 1,024 proposal deliveries and 1,024 execution
  deliveries, and 32 sessions. Anomaly output is bounded to 16 KiB.
- Proposed Pi budgets remain **unmeasured**: one scoring worker, no all-core
  inference, steady worker RSS at most 256 MiB, load peak at most 384 MiB,
  p95 normal latency at most 100 ms, and bounded admission/deadlines. Persistent
  queue supervision, timeout cancellation, total-service memory and actual
  hardware acceptance are not implemented by these component slices.
- Enterprise systems own ONLINE execution authority; DCAMR governs OFFLINE
  local requests only after the endpoint handover. Hard authorized-permission
  denial cannot be overridden by anomaly, context or technician action; a low
  score cannot authorize by itself. User/agent mapping, evidence, approval,
  context attempts and final outcomes remain integration work.

## Boundaries used when marking progress

The **baseline payload schema** is not a signed **package envelope**. Checking its
expected byte digest does not verify an issuer, signature, expiry, rollback rule
or USB replacement. The payload digest and an enclosing archive/manifest digest
must not be silently substituted for each other.

**Feature provenance** and the nested **anomaly result** are not final decision
provenance. The shared action/decision/package skeletons and most system modules
remain empty. The Mac lab report now records actual fitted-model parameters and
runtime metadata, while mock anomaly metadata remains synthetic. Neither supplies
a saved, authenticated model artifact for deployment.

**Fixtures are component evidence.** A timeout record does not supervise a worker;
a skipped-denial record does not evaluate policy; a high result does not hold an
action; and socket-blocked feature replay does not demonstrate the whole DDIL
flow. All 11 end-to-end acceptance tasks remain planned until their actual
workflows run with explicit no-unintended-execution assertions.

## Shared contracts (001–009)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 001 | Define Agent Action Request Schema | Partial | [Internal feature-request shape][feature-schema] is validated; the public [action-request schema][action-schema] now holds the strict first-light contract (one action/target enum, signed envelope verified in [tests][first-light-tests]). Widening to the general request catalog remains a coordinated contract change. |
| 002 | Define Context Push-Back Schema | Planned | The core [challenge skeleton][challenge-schema] is empty. The integrated console defines `alice.context_request`; cross-system schema agreement and real producer/routing remain. |
| 003 | Define Agent Context Response Schema | Planned | No accepted core agent context-response contract exists. The [integrated console][console-integration] defines a local `alice.agent_response` schema; exchange and adapter validation remain. |
| 004 | Define Policy Package Schema | Planned | The [package manifest skeleton][package-schema] is empty. This original policy task now covers the signed authorized-permissions package; existing code keys have not been renamed. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 005 | Define Normal Operations Package Schema | Partial | [Baseline payload schema][baseline-schema] exists. The signed normal-operations package envelope, manifest and lifecycle are not defined by that payload schema. |
| 006 | Define User Permissions Schema | Planned | No permissions-package or user-permissions schema is implemented. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 007 | Define Local Telemetry Schema | Planned | Trusted history input is defined, but the general telemetry/sensor contract is not. |
| 008 | Define Decision Output Schema | Partial | [Nested anomaly result][result-schema] and [validator][contract] exist; the [core complete decision record][decision-schema] is empty. The reported console `alice.decision` requires an agreed adapter, not a guessed payload. |
| 009 | Define Reconciliation Event Schema | Partial | [Local ledger finding contract][audit-schema] binds an original event ID/hash and source metadata; [ledger tests][audit-outbox-tests] preserve originals. This is independent of the still-unimplemented public reconciliation wire contract, producer and enterprise comparison workflow. |

## Initial package loading and trust (010–014)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 010 | Load Policy Data from SD Card | Planned | Desired medium/path: USB `permissions/`. No discovery, authorized-permissions package load or activation exists; legacy policy keys/paths remain unchanged. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 011 | Load Normal Operations Data from SD Card | Planned | Current medium: USB `normal_behavior/`. The baseline byte loader exists, but no removable-media package load path is implemented. |
| 012 | Load User Permissions from SD Card | Planned | Desired permissions input is USB `permissions/`; trusted user/agent identity and delegated permissions contracts/loaders remain unimplemented. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 013 | Verify Package Signatures | Partial | First-light directory and SQL snapshot inputs share Ed25519/digest verification. Immutable no-overwrite SQL publication and bounded read-only loading are implemented; [snapshot handoff](handoffs/2026-09-06-release-snapshot.md). General enterprise schema/coverage, trust provisioning, freshness, generation rollback protection and activation remain. |
| 014 | Validate Package Versions | Partial | [Schema/profile versions][feature-validation] and baseline labels are checked. Package freshness, rollback prevention and compatible activation are not implemented. |

## Request admission and policy checks (015–024)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 015 | Normalize Incoming Agent Requests | Partial | [Feature validation and endpoint normalization][feature-validation] exist. OFFLINE authenticated admission, user accountability and canonical request hashing remain; ONLINE feeds use a separate observed-activity contract. |
| 016 | Identify Agent | Partial | [Builder][features] checks request/subject identity agreement and baseline registration. Caller authentication is still an external prerequisite. |
| 017 | Identify Mission | Partial | [Builder][features] checks the bound mission ID and role/mission profile scope; independent mission authorization is not implemented. |
| 018 | Identify Requested Action | Partial | [Builder][features] resolves the normalized action against the fixed five-action catalog. The public request/admission path remains. |
| 019 | Identify Target Resource | Partial | [Builder][features] identifies and compares the normalized target; the public request/admission path remains. |
| 020 | Identify Requested Parameters | Partial | [Builder][features] validates empty diagnostic parameters or exact outbound endpoint parameters. Other action domains and public admission remain. |
| 021 | Check Agent Permissions | Partial | The [policy engine][policy] now resolves exact agent/action/target/parameter matches against a verified release's PERMIT grants (default deny, approval-required maps to REVIEW_REQUIRED), feeding the shared PermissionFinding type, with [unit and end-to-end coverage][first-light-tests]. Prohibitions, conditions, generations and the full admission/fusion path remain. |
| 022 | Check Mission Scope | Planned | Behavioral profile matching is not policy mission authorization; [policy engine][policy] remains a skeleton. |
| 023 | Check Hard Deny Rules | Planned | Hard-deny precedence is documented but [policy evaluation][policy] is not implemented. |
| 024 | Check Approval-Required Rules | Planned | Mandatory-review requirements are documented but [policy evaluation][policy] is not implemented. |

## Behavioral features (025–036)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 025 | Check Known Agent Status | Done component | [Baseline selection][baseline] and [tests][feature-tests] distinguish a registered agent from cohort fallback without erasing novelty. |
| 026 | Check Known Target Status | Done component | [Builder][features] and [tests][feature-tests] check the complete baseline target table and selected profile. |
| 027 | Check Known Action Status | Done component | [Builder][features] and [tests][feature-tests] distinguish supported actions with positive versus zero normal counts. |
| 028 | Build Behavioral Feature Vector | Done component | [Fixed 11-feature builder][features] and [five replay fixtures][feature-fixtures] produce bounded immutable vectors. |
| 029 | Build Time-Based Features | Partial | [Five-minute history counts and time boundaries][sequence] exist. Operating-window features are deliberately outside the current profile. |
| 030 | Build Target-Novelty Features | Done component | [Builder][features] exposes target/profile-target novelty and exact destination-relationship novelty; [tests][feature-tests] cover these comparisons. |
| 031 | Build Action-Novelty Features | Done component | [Builder][features] exposes action-count novelty; missing baseline data is distinct from an explicit zero count. |
| 032 | Build Agent-Novelty Features | Done component | [Builder][features] preserves `agent_known=0` and `AGENT_UNSEEN` for new authenticated agents using a valid cohort. |
| 033 | Build Mission-Consistency Features | Partial | [Profile selection][baseline] and [history scoping][sequence] bind role, mission type and mission ID. Policy mission-scope enforcement remains. |
| 034 | Build Action-Sequence Features | Done component | [Sequence extraction][sequence] and [tests][feature-tests] derive predecessor masks and transition frequency with explicit completeness/order rules. |
| 035 | Build Physical Sensor Features | Planned | [Generic named numeric inputs][context-guide] validate units, time and provenance. Raw ESP acquisition, voltage conversion and sensor/history feature extraction still need the actual device contract and data; cyber columns remain unchanged. |
| 036 | Build Local Evidence Features | Planned | Evidence sufficiency remains with DCAMR fusion; the [evidence component][evidence] is a skeleton. |

## Model and sequence scoring (037–044)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 037 | Train Isolation Forest | Done component | [Mac training pipeline][training] and [actual-fit tests][training-tests] fit a bounded Isolation Forest on synthetic normal sessions; [candidate-002][training-report] is an in-memory lab fit, not an accepted deployment model. |
| 038 | Save Isolation Forest Model | Planned | A real model was fitted in memory, but no fitted artifact was persisted. [JSON run outputs][training-report] are not a deployable model; format and trusted loading remain pending. |
| 039 | Load Isolation Forest Model on Boot | Planned | No trusted artifact loader, boot integration or model worker exists. |
| 040 | Score Incoming Requests | Partial | [Contextual scorer][context-model] now assesses captured PRE/POST observations using exact-context forests and frozen references; [cyber lab][training] remains. Live request transport, supervised Pi worker and canonical result adapter remain. |
| 041 | Calculate Anomaly Percentile | Done component | [Rank mapper][scoring] and [tests][training-tests] map cyber scores against 1,200 frozen normal calibration scores. The [completed separate-reference experiment][training-guide] used 1,000 distinct normal source requests per family; within-session correlation remains, and no reference is accepted for deployment. |
| 042 | Calculate Individual Anomaly Factors | Partial | [Cyber comparisons][features] and [contextual training-range factors][context-model] retain source/timing and deviations, including changed constant features with LOW ML bands. These are observations, not learned attribution; final fusion remains. |
| 043 | Build Action-Sequence Model | Partial | [Validated transition-count tables][baseline] and [synthetic rows][feature-fixtures] exist; no sequence-training pipeline or learned sequence artifact exists. |
| 044 | Score Action Sequences | Done component | [History component][sequence] computes unsmoothed transition frequency for a complete row and masks no-predecessor cases. This is not an attack probability or authorization score. |

## Decision fusion and context exchange (045–057)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 045 | Combine Policy and Anomaly Results | Partial | [Assessment boundary](contracts/decision-assessment.md) combines trusted permission outcomes and contextual scores, preserves blockers and requires human approval for unusual actions. Permission resolution and final technician-application decision/enforcement integration remain pending. |
| 046 | Define ALLOW Logic | Planned | [Current PRD][prd] defines the OFFLINE authority boundary; executable ALLOW logic and endpoint binding remain. |
| 047 | Define REQUEST_CONTEXT Logic | Planned | [Current PRD][prd] defines OFFLINE context escalation; executable core push-back/fusion, one challenge authority and bounded attempts remain. |
| 048 | Define HOLD Logic | Planned | [Current PRD][prd] defines OFFLINE blocking/review; high-anomaly context-versus-hold specifics and executable fusion remain. |
| 049 | Define DENY Logic | Planned | [Current PRD][prd] requires hard-deny precedence for local governance; no executable core denial/enforcement path exists. |
| 050 | Trigger Automated Context Push-Back | Planned | The core [challenge component][challenge] is empty. Console mock automation is reported separately; real OFFLINE agent routing and a single challenge authority remain. |
| 051 | Receive Agent Context Response | Planned | No real core agent context-response receiver runs. Console mock response ingestion does not complete authenticated upstream delivery. |
| 052 | Validate Context Response | Planned | Core context response admission/correlation remains unimplemented; console-local schema checks are reported evidence, not completed cross-system validation. |
| 053 | Verify Context Evidence Locally | Planned | No local evidence authenticity, relevance or freshness verifier is implemented. |
| 054 | Recalculate Features After Context | Partial | [Builder/tests][feature-tests] preserve context-round counting and reject later-history substitution. The context workflow and evaluator re-dispatch are not implemented. |
| 055 | Recalculate Anomaly Score | Planned | No live model scorer or context re-scoring adapter exists. |
| 056 | Re-run Policy Evaluation | Planned | No initial or repeated policy evaluation exists. |
| 057 | Produce Final Decision | Planned | No authoritative OFFLINE final decision is produced by the [fusion skeleton][fusion]. ONLINE enterprise decisions are observed/audited through a separate feed contract. |

## Provenance and audit (058–065)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 058 | Generate Decision Provenance | Partial | [Immutable feature provenance][feature-types] and [anomaly provenance][result-schema] remain; the [local ledger][audit-guide] durably records supplied bounded provenance and exact bindings. Final authoritative decision generation and live adapters remain. |
| 059 | Record Source of Every Decision Factor | Partial | [Builder][features] supplies feature sources. The [ledger][audit-guide] records compact evidence references and contextual source IDs; it does not produce or verify policy/evidence/fused factors. Numeric contextual factors remain referenced evidence. |
| 060 | Record Model Metadata | Partial | [Mac report][training-report] records fitted metadata. [Compact ledger projection][audit-contract] preserves model ID, in-memory fingerprint, profile/input/calibration digests and independent dispatch binding without copying numeric scores/factors. Signed deployable artifacts and live inference integration remain. |
| 061 | Record Policy Metadata | Partial | [Local ledger schema][audit-schema] persists supplied policy identity/digest or explicit absence; [contract tests][audit-contract-tests] cover it. Permissions evaluation, authenticated release loading and live recording remain absent. |
| 062 | Record Baseline Metadata | Done component | [Baseline loader][baseline] records payload identity/version and verified expected byte digest; [FeatureBatch][feature-types] preserves them. Enclosing package identity stays separate. |
| 063 | Record Evidence Metadata | Partial | [Ledger contract][audit-schema] and [tests][audit-contract-tests] record bounded evidence references/digests, source identity, verification, freshness and availability. Evidence collection, authentication, retention and verification are not implemented. |
| 064 | Record Connectivity State | Partial | [Ledger][audit-guide] captures supplied mode/connectivity/owner/interval/confirmation with events. [Tests][audit-contract-tests] enforce claim consistency; no live connectivity detector or endpoint authority transfer exists. |
| 065 | Write Tamper-Evident Audit Record | Partial | Existing SQLite/hash-chain/Ed25519 ledger retained. USB runtime guards, durable evidence writes and unavailable responses added; no logger rewrite. [Live handoff](handoffs/2026-09-06-live-dashboard.md). Physical USB/power-loss and independent rollback-anchor deployment remain. |

## Dashboard, technician and execution (066–076)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 066 | Export Raw Decision Data to Dashboard | Partial | Real first-light ledger history/increments now reach the existing dashboard through a validated authenticated bridge and remote transport. Numeric risk/full request fields remain unavailable instead of invented. [Mapping and local acceptance](integration/live-dashboard.md). Physical Pi and richer producers remain. |
| 067 | Export Live Pi Status to Dashboard | Planned | The live display reports feed reachability/staleness and retained authority metadata honestly. Current Pi hardware/engine/cloud/SIEM readiness telemetry is still unavailable; no status fields are inferred from HTTP success. |
| 068 | Export Available Technician Actions | Planned | No authoritative core technician-action capability export exists. Console controls consume supplied capabilities; they do not create authority. |
| 069 | Receive Technician Decision | Planned | Target clarified: local Mac resolves held actions to accept/deny after biometric verification; Merek's backend must deliver that bound response to the Pi. No real receiver is connected; authentication, proof/currentness checks and receipts remain. |
| 070 | Require Technician Authentication for Approval | Planned | Local ArcFace enrollment/login and native approval grants exist. Target held-action accept/deny choice is biometric-gated on the Mac; both response paths and Pi-verifiable proof bound to current request/assessment/authority need agreement and acceptance. |
| 071 | Execute Approved Action | Partial | The [enforcement gateway][enforcement] now commands the first-light ESP light over HTTP (receipt and state readback separated; idempotency owned by the runtime), verified against a mock ESP in [tests][first-light-tests]. The real ESP firmware contract, endpoint fence and general action execution remain; ONLINE enterprise control remains direct. |
| 072 | Record Technician Decision | Partial | [Ledger contract][audit-schema] records supplied technician intent and identity separately from decisions/results; [contract tests][audit-contract-tests] cover it. Authenticated console transport, proof validation and actual approval integration remain absent. |
| 073 | Record Action Execution Result | Partial | Runtime records controller receipt, execution result and observed state separately; live dashboard updates these after the immutable decision. Real local runtime/mock-controller browser acceptance passed; physical endpoint and sensor acceptance remain. [Live handoff](handoffs/2026-09-06-live-dashboard.md). |
| 074 | Monitor Resulting Physical/System State | Planned | No post-execution physical/system-state monitor exists. |
| 075 | Compare Expected vs Actual Result | Planned | No expected-versus-observed execution-outcome comparison exists. |
| 076 | Flag Post-Execution Anomalies | Partial | [POST_ACTION scoring][context-model] requires a separately trained profile/context and at least one temporally valid resulting-state feature. [Tests][context-model-tests] cover post timing and scoring; real execution/sensor ingestion, outcome validation and response remain unimplemented. |

## DDIL and reconciliation (077–092)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 077 | Detect Cloud Connectivity Loss | Planned | No cloud connectivity detector exists. |
| 078 | Enter DDIL Mode | Planned | No automatic failover/state machine or endpoint authority transfer exists; loss of cloud reachability cannot by itself authorize local control. |
| 079 | Continue Local Policy Enforcement | Planned | OFFLINE authorized-permission enforcement remains unimplemented. ONLINE enterprise direct control is intentionally not replaced by a Pi policy gate. |
| 080 | Continue Local Anomaly Scoring | Partial | [Local lab scoring][training] runs real Isolation Forest offline, alongside [feature checks][feature-tests]. Live Pi inference for OFFLINE governance and authority-mode orchestration remain unimplemented. |
| 081 | Continue Local Context Push-Back | Planned | No real OFFLINE core context exchange runs. Console fixture automation does not establish agent routing, bounded retries or a single authoritative challenge loop. |
| 082 | Continue Local Dashboard Output | Partial | Existing dashboard now loads runtime ledger history and polls incremental events automatically, with reconnect, duplicate/conflict and malformed-input handling. Local runtime/mock-ESP browser acceptance passed; physical Pi/USB and full DDIL authority lifecycle remain. [Live guide](integration/live-dashboard.md). |
| 083 | Cache Unverified External Evidence Requests | Planned | No bounded persistent external-evidence request cache exists. |
| 084 | Detect Cloud Reconnection | Planned | No direct Pi/enterprise reconnection detector or authenticated readiness check exists. |
| 085 | Exit DDIL Mode | Planned | No fenced return to ONLINE enterprise execution exists; outstanding local commands/approvals must not remain valid after transfer. |
| 086 | Reconnect to SIEM | Planned | The SIEM connector is empty; direct Pi/enterprise source authentication, replay/cursors and reconnection remain. |
| 087 | Reconnect to EDR | Planned | The EDR connector is empty; direct Pi/enterprise source authentication, replay/cursors and reconnection remain. |
| 088 | Fetch Pending External Evidence | Planned | No direct Pi/enterprise pending-evidence fetch workflow exists; the technician is not the manual relay. |
| 089 | Reconcile Local Evidence with Cloud Evidence | Planned | The core [reconciliation component][reconciliation] is empty. Direct Pi comparison/upload and append-only findings remain. |
| 090 | Detect Evidence Discrepancies | Planned | No local/cloud evidence discrepancy detector exists. |
| 091 | Append Reconciliation Results | Partial | [Ledger finding append][audit] and [outbox tests][audit-outbox-tests] require original ID/hash and source attribution; reconciliation marker requires original ACK plus linked finding. Actual evidence fetching/comparison and enterprise reconciliation remain absent. |
| 092 | Preserve Original Decision History | Partial | Original audit events remain immutable through display/reconnect and explicit snapshot selection at restart. Snapshot tests preserve old event bytes, replay outcomes and queued delivery state while a changed release governs new requests. [Snapshot handoff](handoffs/2026-09-06-release-snapshot.md). SIEM delivery and full reassessment exchange remain. |

## Package updates and connected recovery (093–107)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 093 | Fetch Updated User Permissions | Planned | Direct Pi synchronization is the selected path; authoritative enterprise permissions source, trust and update adapters remain unimplemented. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 094 | Validate Updated User Permissions | Planned | A candidate permissions release shape exists in the simulation; Pi-side schema, signature and validity checks do not. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 095 | Write Updated User Permissions to SD Card | Planned | Desired medium/path is USB `permissions/`; no verified permission-update writer exists. Pi synchronization is selected, while release/retention/failure rules remain to be agreed. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 096 | Fetch Updated Policy Package | Planned | This original policy task now covers authorized-permissions releases; no authenticated direct Pi/enterprise fetch path exists. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 097 | Validate Updated Policy Package | Planned | No updated authorized-permissions signature, validity or compatibility verifier exists; the original policy label and current code keys remain. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 098 | Write Updated Policy Package to SD Card | Planned | Desired path is USB `permissions/`; no update writer exists. Existing policy-named code is not migrated by this documentation change. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 099 | Fetch Updated Normal Operations Package | Planned | No authenticated direct Pi/enterprise normal-behavior update fetch path exists. |
| 100 | Validate Updated Normal Operations Package | Partial | [Baseline payload validation][baseline] checks digest, schema and table consistency. An updated package still needs signature/issuer/expiry checks and activation handling. |
| 101 | Write Updated Normal Operations Package to SD Card | Planned | No USB `normal_behavior/` update writer exists; direct Pi sync is selected, while verified release and failure handling remain. |
| 102 | Reload Updated Permissions | Planned | No atomic permissions activation/reload path exists. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 103 | Reload Updated Policy | Planned | No atomic authorized-permissions activation/reload exists; the original task label and current policy keys remain legacy names. [Enterprise simulation](handoffs/enterprise-sim-handoff.md) supplies candidate releases/contracts and fixtures; Pi runtime remains pending. |
| 104 | Reload Updated Baseline | Partial | [Loader][baseline] creates a fresh immutable payload instance. USB watching, atomic replacement and in-flight evaluation coordination are not implemented. |
| 105 | Version All Updated Packages | Planned | Per-payload baseline labels exist; versioning and compatibility across all package types are not implemented. |
| 106 | Reject Invalid or Tampered Updates | Partial | [Payload digest/schema checks][feature-validation] reject altered or malformed supplied bytes. Signed update verification, rollback prevention and replacement recovery remain. |
| 107 | Restore Full Connected Decision Context | Planned | No fenced ONLINE return plus direct Pi audit upload, risk/reconciliation append and verified atomic cache refresh exists. ONLINE execution need not wait for every retained audit event to upload, but transfer and backlog state must be explicit. |

## End-to-end acceptance (108–118)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 108 | Run End-to-End Normal Request Test | Planned | Normal feature/anomaly fixtures are component evidence only. No complete OFFLINE request-to-execution or ONLINE direct-control/activity-audit acceptance path exists. |
| 109 | Run New-Agent Push-Back Test | Planned | New-agent novelty/cohort fixtures exist. Console mock clarification is reported separately; no real cross-system new-agent push-back test exists. |
| 110 | Run Slight-Anomaly Push-Back Test | Planned | An elevated mock result exists; no actual slight-anomaly push-back exchange is tested. |
| 111 | Run Hard Policy Denial Test | Planned | A skipped-denial fixture validates result shape; no policy evaluation, zero-model-call assertion or enforcement denial is tested end to end. |
| 112 | Run High-Anomaly Hold Test | Planned | Actual lab model outputs and a high mock result exist; no integrated model/fusion hold or no-execution acceptance test exists. |
| 113 | Run Technician Approval Test | Planned | No real console-proof/core-approval/controller-execution acceptance test exists. Reported live facial login is not approval step-up or execution evidence. |
| 114 | Run DDIL Decision Test | Planned | Socket-blocked feature replay proves that component is local, not a complete DDIL decision flow. |
| 115 | Run Cloud Reconnection Test | Planned | No endpoint handover plus direct Pi/enterprise reconnect, audit delivery and cache refresh integration test exists. |
| 116 | Run Evidence Reconciliation Test | Planned | No evidence reconciliation workflow or integration test exists. |
| 117 | Run User-Permissions Update Test | Planned | No permissions-update workflow or integration test exists. |
| 118 | Run Tampered SD Package Test | Planned | Payload integrity unit tests exist; no signed removable-package tamper/update integration test exists. This original SD label now applies to the USB input packages. |

## Supplemental planned requirements from the two-mode revision

These requirements supplement the unchanged original list. **Every item below is
Planned**, and none is included in the 118-task totals or represents implementation
progress. The [architecture][architecture] and [console integration note][console-integration]
describe the required boundaries; protocol details still need agreement.

| Supplemental ID | Planned requirement | Required acceptance boundary |
| --- | --- | --- |
| SUP-01 | Endpoint-enforced single-authority handover | Demonstrate exactly one current controller across ONLINE/OFFLINE transfer; reject competing authority, stale commands and outstanding approvals. Select and implement the authenticated fence/recovery protocol rather than treating network state as authority. |
| SUP-02 | ONLINE activity-feed coverage and cursors | Ingest attributed enterprise requests, execution attempts and downstream results without forcing actions through ALICE; authenticate sources, define IDs/coverage/cursors/order and surface gaps or unknown state explicitly. |
| SUP-03 | Bounded trusted cache synchronization | Bound permissions, normal behavior and relevant SIEM/EDR/mission caches; verify issuer/signature/version/validity and complete coverage, preserve usable active data, and activate compatible replacements atomically. |
| SUP-04 | Console/core executable schema adapter and native transport | Exchange actual schemas/fixtures and version mappings; implement authenticated native event ingestion and command delivery, preserve null/unknown and reassessment semantics, and keep one core challenge authority. |
| SUP-05 | Remote approval proof bound to current authority | Independently validate technician identity and short-lived one-use proof against exact action parameters/digest, request, current assessment and current execution authority; reject forged/replayed/expired/superseded proof. Complete real camera approval acceptance separately. |
| SUP-06 | Durable context/action outboxes and receipt recovery | Persist stable idempotency/correlation IDs, bounded retries, grant consumption and acknowledgements transactionally; recover across timeout/restart without issuing duplicate unrelated authorizations. |
| SUP-07 | Independent execution attempt and result records | Separate submitted/accepted/pending/rejected receipts from protected-controller execution and measured state; bind each event to authority/request/user/agent and preserve failed or unknown results. |
| SUP-08 | Direct Pi reconnection audit and reconciliation | Publish every DDIL request/decision/attempt/result directly upstream with durable upload IDs/cursors and acknowledgements, flag risks, append later findings, preserve original history and refresh verified caches without technician relay. |
| SUP-09 | Trusted agent-to-user accountability | Establish authoritative user/agent/mission mappings and revocation/expiry behavior for ONLINE feeds and OFFLINE requests; agent-supplied identity claims cannot establish their own permissions. |

## Maintaining this tracker

After each small implementation increment, update only the relevant rows with
the completed component, its tests, and any remaining integration boundary.
Keep unresolved product choices explicit. Promote the end-to-end rows only
after the corresponding real multi-component workflow runs; model-quality and
Pi resource results should identify actual artifact/runtime/hardware versions.
Do not treat fixture scores or Mac resource measurements as Pi acceptance.

[context-guide]: architecture/contextual-behavior-model.md
[context-model]: ../dcamr/anomaly_engine/contextual_model.py
[context-model-tests]: ../tests/test_contextual_model.py
[prd]: prds/ALICE-DCAMR-PRD.md
[architecture]: prds/ALICE-DCAMR-Architecture.md
[handoff]: prds/ALICE-DCAMR-PRD-Handoff.md
[console-integration]: integration/technician-console.md
[contract-guide]: contracts/anomaly-contract.md
[feature-guide]: contracts/anomaly-features.md
[data-direction]: decisions/2026-09-05-data-direction.md
[training-guide]: guides/anomaly-training.md
[result-schema]: ../common/schemas/anomaly_result.json
[baseline-schema]: ../common/schemas/anomaly_baseline.json
[feature-schema]: ../common/schemas/anomaly_feature_input.json
[action-schema]: ../common/schemas/action_request.json
[decision-schema]: ../common/schemas/decision_record.json
[challenge-schema]: ../common/schemas/challenge.json
[package-schema]: ../common/schemas/package_manifest.json
[contract]: ../dcamr/anomaly_engine/contract.py
[scoring]: ../dcamr/anomaly_engine/scoring.py
[features]: ../dcamr/anomaly_engine/features.py
[feature-types]: ../dcamr/anomaly_engine/feature_types.py
[feature-validation]: ../dcamr/anomaly_engine/feature_validation.py
[baseline]: ../dcamr/anomaly_engine/baseline.py
[sequence]: ../dcamr/anomaly_engine/sequence.py
[contract-tests]: ../tests/test_anomaly_contract.py
[scoring-tests]: ../tests/test_anomaly_engine.py
[feature-tests]: ../tests/test_feature_builder.py
[feature-fixtures]: tests/fixtures/features.md
[anomaly-replay]: ../scripts/lab/replay_anomaly_fixtures.py
[package-verifier]: ../dcamr/packages/package_verifier.py
[policy]: ../dcamr/policy_engine/policy_engine.py
[fusion]: ../dcamr/decision_model.py
[challenge]: ../dcamr/challenge/challenge.py
[evidence]: ../dcamr/evidence/evidence_interface.py
[audit]: ../dcamr/audit/audit_log.py
[enforcement]: ../dcamr/enforcement/enforcement_gateway.py
[reconciliation]: ../dcamr/reconcile/reconciliation.py
[training]: ../scripts/lab/anomaly_training.py
[training-cli]: ../scripts/lab/train_anomaly_model.py
[synthetic-data]: ../scripts/lab/synthetic_anomaly_data.py
[training-tests]: ../tests/test_anomaly_training.py
[synthetic-tests]: ../tests/test_synthetic_anomaly_data.py
[training-report]: reports/anomaly-lab/candidate-002/training-report.json
[training-calibration]: reports/anomaly-lab/candidate-002/calibration-reference.json
[training-manifest]: reports/anomaly-lab/candidate-002/dataset-manifest.json

[audit-guide]: architecture/decision-evidence-ledger.md
[audit-schema]: ../common/schemas/audit_event.json
[audit-contract]: ../dcamr/audit/event_contract.py
[audit-contract-tests]: ../tests/test_audit_contract.py
[audit-tests]: ../tests/test_audit_log.py
[audit-outbox-tests]: ../tests/test_audit_outbox.py
[audit-integrity-tests]: ../tests/test_audit_integrity.py
[context-ledger-replay]: ../scripts/lab/replay_contextual_ledger.py
[first-light-tests]: ../tests/test_first_light.py
[first-light-handoff]: handoffs/2026-09-05-first-light-test.md
