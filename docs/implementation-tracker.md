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
two-mode admission and authority transfer still need runtime integration; live
read-only transport and Wazuh delivery are described below.

Environmental demo software now integrates the plant, signed ALICE fan adapter,
native review compatibility and Pi/XIAO pattern delivery. Xavier's display contract
is yellow=power, blue=actual fan speed, red=temperature and white=battery remaining.
[Validation](reports/2026-09-06-environmental-demo-validation.md) distinguishes
software tests from outstanding hardware/full-native-build acceptance. The original
eight-test mapping increment is historical, not full hardware evidence.

## Status and current checkpoint

Current local redesign integration: source preserved at `db73071`, merged first
with team `4531277` at `4b1f67e`, then with latest `d5a0d56`. Both team behavior
and all aesthetic work survive; the late battery/LED documentation update is
included. [Integration evidence](reports/2026-09-06-main-redesign-integration.md)
records validation and remaining operator acceptance. No publication/deployment.


Machine-metrics reconciliation: upstream `237c307` is integrated. The public
`get_metrics` / `set_fan_speed` MCP now defaults to the shared ALICE thermal
runtime, with agent credentials, exact retry bindings and authenticated pollers.
[Evidence](reports/2026-09-06-metrics-reconciliation.md): 467 Python tests passed;
no deployment or physical acceptance is implied. Existing task statuses remain.

Historical September 6 follow-up: approved visual refinements and device-local dashboard
clock are implemented locally on `codex/dashboard-visual-refinements` from `5bb092a`.
Final check passed frontend 163/scripts 8/typecheck/lint/build; Rust 60 (2 ignored),
Python 166 and all 20 browser regressions passed. These are synthetic/component
checks, not physical acceptance. [Validation](reports/2026-09-06-dashboard-visual-refinements.md).
[Specification](handoffs/dashboard-visual-refinement-spec.md) and
[live state](handoffs/dashboard-visual-refinement-live-state.md) record scope,
current evidence and recovery. No publication or deployment is authorized.


Historical September 6 initial visual overhaul: team PR #5 merged at `e1e7506`; the presentation-only
feature is isolated in `../alice-dashboard-visual-overhaul` on
`codex/dashboard-visual-overhaul`. Shell, both workspace modes, history/audit,
identity/Face ID, motion and accessibility are redesigned. Existing core task
statuses remain unchanged. [Visual validation](reports/2026-09-06-console-visual-overhaul.md)
records actual tests, baseline/screens, 11 passing browser regressions and completed local integration.
Team [PR #6](https://github.com/theoberk25/Alice/pull/6) was opened, then closed
at the user’s request while a teammate prepares changes. The previously pushed
feature branch remains; subsequent status changes stay local. Local main was never
pushed. The original Dock-linked ALICE.app was rebuilt and reopened.
The [previous current snapshot](handoffs/2026-09-06-before-visual-overhaul.md) is preserved.

Historical September 6 native backend continuation: biometric PR #4 is merged in Theodore's
`upstream/main` at `d57c660`. Root checkout now uses `codex/native-live-backend`;
original dirty work, WIP and retired trees are [verified preserved](handoffs/2026-09-06-native-live-backend-workspace.md).
Native request visibility and signed review are locally implemented with exact
bindings, durable one-use admission and reconciliation. [Parity](plans/native-live-backend-parity.md)
and [current validation](reports/2026-09-06-native-live-backend-validation.md) distinguish
local automated evidence from unperformed real camera/physical-Pi acceptance.
Dock/Finder launch follow-up: existing private settings now select the same remote
rehearsal as the tested launch; original settings are backed up and direct launch
was verified. This does not provision a physical Pi or change execution authority.
Publication: the user authorized updating `Adaoud03/Alice:main` and submitting
[upstream PR #5](https://github.com/theoberk25/Alice/pull/5). Latest upstream pitch
deliverables at `966632e` are included unchanged; tested runtime/native/frontend
sources are unchanged by that rebase. Upstream merge and physical acceptance remain pending.


Historical September 6 biometric delivery: `codex/live-face-upstream-integration` starts from
Theodore's `upstream/main` `f79cd8e` and ports the completed native live facial
upgrade only. Automatic multi-pose enrollment, passive gallery login, encrypted
generations, native session protections and fresh local fixture approval are
included, with no deepfake detection. See the [delivery report](reports/2026-09-06-live-face-main-integration.md)
for tests/build and the remaining operator acceptance. Original branch/worktree
preserved. Unfinished live HOLD review is saved on local
`codex/live-runtime-review-wip` (`aa5bae8`), excluded from delivery. No live Pi
control, output adjustments or full-network packet visibility is claimed.
That delivery preserved all 118 task IDs and existing core statuses; the current
native increment updates the affected rows below without changing their IDs.


Current transition instructions are consolidated in `docs/guides/demo-runbook.md`.
The superseded ESP handoff, live-dashboard guide, joint acceptance checklist,
live-dashboard plan and five completed September 6 session handoffs were moved
intact under `docs/archive/`. Current hardware, SIEM and technician contracts stay
in their focused guides; no implementation evidence or task IDs were deleted.

| Superseded active path | Preserved archive path |
| --- | --- |
| `docs/integration/esp-handoff.md` | `docs/archive/integration/2026-09-06-esp-handoff.md` |
| `docs/integration/live-dashboard.md` | `docs/archive/integration/2026-09-06-live-dashboard.md` |
| `docs/integration/pi-technician-acceptance.md` | `docs/archive/integration/2026-09-06-pi-technician-acceptance.md` |
| `docs/plans/2026-09-06-live-dashboard.md` | `docs/archive/plans/2026-09-06-live-dashboard.md` |
| `docs/handoffs/2026-09-06-backend-continuation.md` | `docs/archive/handoffs/2026-09-06-backend-continuation.md` |
| `docs/handoffs/2026-09-06-jared-main-integration.md` | `docs/archive/handoffs/2026-09-06-jared-main-integration.md` |
| `docs/handoffs/2026-09-06-live-dashboard.md` | `docs/archive/handoffs/2026-09-06-live-dashboard.md` |
| `docs/handoffs/2026-09-06-release-snapshot.md` | `docs/archive/handoffs/2026-09-06-release-snapshot.md` |
| `docs/handoffs/2026-09-06-xavier-serial-integration.md` | `docs/archive/handoffs/2026-09-06-xavier-serial-integration.md` |

Slow-blink firmware deployed (1 second lit/dark); operator All lights off uses
eight signed requests with per-light outcomes. Timing/cancellation tests pass.

Eight-light production now includes v2 serial addressing, signed target validation,
operator ON/OFF buttons, per-target provenance and opt-in all-light demo grants.
Live: 16 signed commands, eight replays, 112 correlated USB events verified.
Quota-only migration preserved all history and recovered Wazuh delivery. Existing
118 IDs/statuses remain; broader grid/ML/technician acceptance is not implied.


Eight-LED identification completed with all colors visually confirmed; pin/color
map is in the ESP handoff. Original firmware restored with hash verification and
runtime resumed. Subsequent dim D7 report led to an idle-low firmware fix;
readback/tests passed; Jared confirmed D7 fully dark. Runtime grants unchanged.

Local merge `bf6fee0` preserves main `d3502e3` and Jared's SIEM/cache work.
Physical Pi USB-serial light-on now passed: ALLOW/COMPLETED/on, external D0 LED
visually confirmed by Jared, seven events delivered to Wazuh. All 97 original
canonical events preserved; 104 total. Python: 357 passed plus 261 subtests.
npm check passed typecheck/lint, 73 frontend tests, 5 script tests and build.
[Deployment and evidence](guides/first-light-hardware.md).
Earlier physical checkpoint preceded the later idle-low firmware deployment.
ESP handoff publication includes the verified mapping; real ML and remote human
approval remain.


Enterprise presentation now models the DN-Hacks energy-infrastructure server room
instead of Sentinel AFB. The Wazuh index received 434 deterministic, idempotent and
internally labelled scenario records covering authentication, vulnerabilities,
MITRE ATT&CK, configuration assessment, file integrity, malware, endpoint behavior
and ALICE agent governance. New SOC views derive their counts from indexed records;
actual Wazuh Pi audit records remain a separate stream. EDR response remains
unavailable and no permissions or task completion statuses changed.
[Existing runbook and research](integration/wazuh-audit-sync.md).

Local enterprise-download follow-up: real generation 44 permissions now verified
and cached on USB by a 30-second systemd timer; rollback anchor stays internal.
This is cache-only: first-light grants unchanged, full enterprise activation and
normal-behavior/model synchronization remain. [Existing runbook](integration/wazuh-audit-sync.md).

Legacy enterprise operator fixture: actual local indexer
login `ssgt.a.okafor`, scoped read-only ALICE data role, and descriptive ESP profile
provisioned. Authentication/read tests passed; security administration denied.
No signed permissions, Pi grants, technician authority or task status changed.

[hardware runbook](guides/first-light-hardware.md) documents
current service/storage paths, firmware interface, client setup and the recommended
authenticated held-action response sequence. Recommendations do not change task status.

Published `2aaf021` integrates Xavier's `290699b` USB-serial transport with the preserved
snapshot/Wazuh/dashboard work. Hardware testing was reported on his development Mac;
That checkpoint predates the successful Pi physical light-on acceptance below. [Hardware evidence](guides/first-light-hardware.md).

Integrated locally from Jared's `origin/main` checkpoint `ef413b6` and the preserved
SQL snapshot checkpoint `73dfa91`. [Integrated runbook](guides/demo-runbook.md)
and [Wazuh runbook](integration/wazuh-audit-sync.md) define the provisioned paths.

Jared's [automatic USB proof](reports/2026-09-06-automatic-usb-wazuh-sync.md) reports
seven new events delivered from physical ext4 USB, reaching 83 Wazuh records,
with identical retry causing no extra mock-controller command. These are Jared's
historical observations. SSH and physical light-on now work; live outage/reboot
and semantic reconciliation acceptance remain pending.

Our [signed SQL input snapshot](integration/release-snapshot.md), existing audit
history and live dashboard are retained alongside the automatic owner-integrated
Wazuh worker. General enterprise SQL synchronization, activation/freshness/rollback
protection and remote biometric actions remain separate work. Task 086 is Partial;
all task IDs and labels are preserved. Combined verification belongs in the
[integrated runbook](guides/demo-runbook.md).

### Historical checkpoints

Architecture correction from Theo's supplied older plan: the root document now
defines the intended Pi pipeline and backend/live-workstation data flow. User
clarification: Pi owns ML classification; the local Mac resolves held actions to
accept or deny after biometric verification. Theo/Jared are configuring the Pi,
Xavi is working on hardware, Merek will implement backend integration next session,
and Alex will adapt workstation scripts/dashboard against the agreed live contract.
The [technician integration contract](integration/technician-console.md) records
remaining codec/storage/proof decisions. This is documentation/coordination only;
all 118 task IDs, labels and implementation statuses remain unchanged.

Integrated architecture/layout review against main `d6e7e55`: preserved the
first-light implementation and task updates alongside the documentation follow-up.
Fresh full Python suite: **265 passed, zero skips** (16.872 seconds with local
loopback access for the mock ESP). All 384 latest-main files survive at original
or mapped paths. Root architecture and active guides now distinguish this signed
request/fixture/mock-controller slice from the full product. See the
[current checkpoint](../current.md) for scope and checks.

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
checks are in the [current checkpoint](../current.md).

Combined layout review of GitHub main at 3330a07: corrected biometric model
provisioning's missing Path import with two isolated regressions, completed docs
centralization, and refreshed the root project/architecture entry points. Fresh
core suite: **259 passed, zero skips**. Console type-check, lint, 64 frontend tests,
four launcher tests and production build passed. Product task statuses remain
unchanged. [Review and limits](../current.md).

Technician console layout migration: workstation/ is removed; source is organized
under apps, packages, services, fixtures, tests/console and the shared docs tree.
Launchers are in scripts/console and scripts/biometrics; npm commands run at root.
**64 frontend, 4 relocation, 14 default Rust, 11 Python and 5 browser tests passed**,
plus real public-image ArcFace/native identity checks, app bundling and 257 core
tests (with documented Python dependency setup). All 369 original tracked files
survive; no console contracts or core product statuses changed. The user authorized
committing this migration to local main; that historical publication limit was
superseded by its merge into GitHub main at 3330a07.
[Console layout verification](guides/console/verification.md).

Earlier lab developer-tool relocation: implementations now live in scripts/lab with preserved
lab.* imports and a launcher independent of working directory. Pi runtime stays
in dcamr. **257 tests passed, zero skips**, including copied-checkout generation
and unchanged enterprise payloads. [Lab layout and evidence](lab/README.md).
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

Current totals: **12 Done component, 45 Partial,
61 Planned**. These are task-status counts, not a percentage of product
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
The [enterprise simulation](lab/README.md) now supplies Wazuh
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
flow. The native review task now has local automated evidence; all remaining
end-to-end acceptance claims require their actual
workflows run with explicit no-unintended-execution assertions.

## Shared contracts (001–009)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 001 | Define Agent Action Request Schema | Partial | [Internal feature-request shape][feature-schema] is validated; the public [action-request schema][action-schema] now holds the strict first-light contract (one action/target enum, signed envelope verified in [tests][first-light-tests]). Widening to the general request catalog remains a coordinated contract change. |
| 002 | Define Context Push-Back Schema | Partial | The [challenge producer](../dcamr/challenge/challenge.py) now emits a schema-valid `CONTEXT_CHALLENGE` bounded audit record (technician-attributed) with unit tests; the console defines `alice.context_request` and a technician-initiated request control (mock mode). The standalone [challenge-schema][challenge-schema] JSON stays an empty placeholder; cross-system routing to the agent and the Pi HTTP intake remain. [Handoff](handoffs/2026-09-06-request-more-context-pipeline.md). |
| 003 | Define Agent Context Response Schema | Partial | The [challenge producer](../dcamr/challenge/challenge.py) emits a schema-valid `CONTEXT_RESPONSE` record (agent-attributed) plus a separate `alice.agent_response` projection carrying the blurb (the ledger detail is bounded and holds no free text); an [agent responder](../agent/challenge_responder.py) generates the 1–2 sentence blurb with a deterministic fallback. Live exchange, MCP delivery and feed-mapping adapter remain. [Handoff](handoffs/2026-09-06-request-more-context-pipeline.md). |
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
| 013 | Verify Package Signatures | Partial | First-light directory and SQL snapshot inputs share Ed25519/digest verification. Immutable no-overwrite SQL publication and bounded read-only loading are implemented; see the [snapshot contract](integration/release-snapshot.md). General enterprise schema/coverage, trust provisioning, freshness, generation rollback protection and activation remain. |
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
| 024 | Check Approval-Required Rules | Partial | Exact verified first-light grants export approval_required; usable assessment plus REVIEW_REQUIRED now becomes immutable CHALLENGE pending native review. General mandatory-review policy catalog remains broader work. [Review contract](contracts/technician-runtime-review.md). |

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
| 035 | Build Physical Sensor Features | Partial | The simulated plant supplies fan, temperature, power and battery with explicit units; Xavier's read-only display projects yellow=power, blue=fan, red=temperature and white=battery. The deployed anomaly scorer uses fan/temperature/power context. Real sensor acquisition, calibration and battery/model features remain open. |
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
| 048 | Define HOLD Logic | Planned | [Current PRD][prd] defines the demo mapping from a permission-eligible `ELEVATED`/`HIGH` abrupt fan shutdown to required human review and a displayed HOLD. Executable fusion and final app/core decision transport remain. |
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
| 065 | Write Tamper-Evident Audit Record | Partial | Existing SQLite/hash-chain/Ed25519 ledger retained. USB runtime guards, durable evidence writes and unavailable responses added; no logger rewrite. [Integrated runbook](guides/demo-runbook.md). Physical USB/power-loss and independent rollback-anchor deployment remain. |

## Dashboard, technician and execution (066–076)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 066 | Export Raw Decision Data to Dashboard | Partial | Native and web share authenticated request/audit history, incremental updates, evidence and explicit source/freshness. Native now reads retained canonical request/action/target/parameters through the existing bridge. The thermal runtime authenticates `/events`; the runbook now requires `ALICE_UPSTREAM_TOKEN` for the bridge while keeping the token private. Missing historical fields and packet-wide visibility remain unavailable. [Parity](plans/native-live-backend-parity.md). |
| 067 | Export Live Pi Status to Dashboard | Planned | The live display must distinguish enterprise reachability, last contact/staleness, synchronization and confirmed execution owner. The target enterprise UI shows ALICE EDGE OFFLINE when its Pi link is lost without claiming authority transfer. Current Pi hardware/engine/cloud/SIEM readiness telemetry is still unavailable. |
| 068 | Export Available Technician Actions | Partial | Pi review snapshots now export current eligible approve/reject for exact first-light HOLD/request/release/authority bindings; absent trust, missing bytes, DENY and ONLINE/unconfirmed ownership fail closed. General rich action catalog remains unavailable. [Contract](contracts/technician-runtime-review.md). |
| 069 | Receive Technician Decision | Partial | Existing Pi runtime receives native Ed25519 review proofs via the existing fixed-path bridge, verifies scoped console/technician trust, freshness and current bindings, and acknowledges durable consent. Rust→Python local mock-controller integration passed; physical-Pi trust/deployment/acceptance remain. The upstream fan-shutdown target additionally needs its fan contract/model/controller integration; rejection must preserve the last approved fan state. [Validation](reports/2026-09-06-native-live-backend-validation.md). Simulation-only fan integration additionally verified; see [environmental validation](reports/2026-09-06-environmental-demo-validation.md). Full native build and physical acceptance limitations remain. |
| 070 | Require Technician Authentication for Approval | Partial | Both native first-light approve and reject require fresh action-bound ArcFace sessions; cancellation, expiry, changed enrollment/identity/snapshot and consumed grants cannot submit. Exact signed proof lifetime is checked independently by the Pi. Automated synthetic-session evidence is separate from real camera/Pi acceptance. [Validation](reports/2026-09-06-native-live-backend-validation.md). Simulation-only fan integration additionally verified; see [environmental validation](reports/2026-09-06-environmental-demo-validation.md). Full native build and physical acceptance limitations remain. |
| 071 | Execute Approved Action | Partial | Existing HTTP/serial execution path is reused after durable technician admission. Thread/process exclusion, replay/restart and crash-window tests enforce at-most-once local mock-controller execution; rejection never executes. Prior physical serial/light evidence is historical; fresh camera→physical-Pi review remains untested. [Review contract](contracts/technician-runtime-review.md). Simulation-only fan integration additionally verified; see [environmental validation](reports/2026-09-06-environmental-demo-validation.md). Full native build and physical acceptance limitations remain. |
| 072 | Record Technician Decision | Partial | Pi durably appends TECHNICIAN_ACTION plus immutable signed-envelope/public-key evidence before execution; original machine decisions remain unchanged. Native existing SQLite stores submission identity and GET reconciliation separately from execution/observation. Physical integrated acceptance remains. [Validation](reports/2026-09-06-native-live-backend-validation.md). |
| 073 | Record Action Execution Result | Partial | Runtime records controller receipt, execution result and observed state separately; live dashboard updates these after the immutable decision. Real local runtime/mock-controller browser acceptance passed; physical serial light-on receipt and visual LED acceptance now passed; independent sensor acceptance remains. [Integrated runbook](guides/demo-runbook.md). Simulation-only fan integration additionally verified; see [environmental validation](reports/2026-09-06-environmental-demo-validation.md). Full native build and physical acceptance limitations remain. |
| 074 | Monitor Resulting Physical/System State | Planned | No post-execution physical/system-state monitor exists. |
| 075 | Compare Expected vs Actual Result | Planned | No expected-versus-observed execution-outcome comparison exists. |
| 076 | Flag Post-Execution Anomalies | Partial | [POST_ACTION scoring][context-model] requires a separately trained profile/context and at least one temporally valid resulting-state feature. [Tests][context-model-tests] cover post timing and scoring; real execution/sensor ingestion, outcome validation and response remain unimplemented. |

## DDIL and reconciliation (077–092)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 077 | Detect Cloud Connectivity Loss | Planned | No cloud connectivity detector exists. |
| 078 | Enter DDIL Mode | Planned | No automatic failover/state machine or endpoint authority transfer exists; loss of cloud reachability cannot by itself authorize local control. |
| 079 | Continue Local Policy Enforcement | Planned | OFFLINE authorized-permission enforcement remains unimplemented. ONLINE enterprise direct control is intentionally not replaced by a Pi policy gate. |
| 080 | Continue Local Anomaly Scoring | Partial | The environmental runtime loads the bounded data-only hybrid Isolation Forest artifact, scores each authenticated fan proposal against current fan/temperature/power context and records model/calibration provenance. Mac integration tests pass; Pi deployment, measured data and authority-mode orchestration remain. |
| 081 | Continue Local Context Push-Back | Planned | No real OFFLINE core context exchange runs. Console fixture automation does not establish agent routing, bounded retries or a single authoritative challenge loop. |
| 082 | Continue Local Dashboard Output | Partial | Existing dashboard loads runtime ledger history and polls incremental events with reconnect, duplicate/conflict and malformed-input handling. Authenticated LAN web access to the physical Pi/USB feed passed. This interim web surface is read-only; native LLM/face/accept-reject integration and the full DDIL authority lifecycle remain. [Integrated runbook](guides/demo-runbook.md). |
| 083 | Cache Unverified External Evidence Requests | Planned | No bounded persistent external-evidence request cache exists. |
| 084 | Detect Cloud Reconnection | Planned | No direct Pi/enterprise reconnection detector or authenticated readiness check exists. |
| 085 | Exit DDIL Mode | Planned | No fenced return to ONLINE enterprise execution exists; outstanding local commands/approvals must not remain valid after transfer. |
| 086 | Reconnect to SIEM | Partial | [Bounded Wazuh uploader](integration/wazuh-audit-sync.md) uses strict TLS, create-only delivery, exact read-back and existing ledger acknowledgements. The integrated Pi thermal service now writes the ext4 USB ledger and automatically delivered through its live anomalous decision with no uploader error. Outage/reboot acceptance and semantic reconciliation remain. |
| 087 | Reconnect to EDR | Planned | The EDR connector is empty; direct Pi/enterprise source authentication, replay/cursors and reconnection remain. |
| 088 | Fetch Pending External Evidence | Planned | No direct Pi/enterprise pending-evidence fetch workflow exists; the technician is not the manual relay. |
| 089 | Reconcile Local Evidence with Cloud Evidence | Planned | The core [reconciliation component][reconciliation] is empty. Direct Pi comparison/upload and append-only findings remain. |
| 090 | Detect Evidence Discrepancies | Planned | No local/cloud evidence discrepancy detector exists. |
| 091 | Append Reconciliation Results | Partial | [Ledger finding append][audit] and [outbox tests][audit-outbox-tests] require original ID/hash and source attribution; reconciliation marker requires original ACK plus linked finding. Actual evidence fetching/comparison and enterprise reconciliation remain absent. |
| 092 | Preserve Original Decision History | Partial | Original audit decisions remain immutable through native/web reconnect and review. Late acknowledgment and restart reconciliation bind exact request/decision/action; reused IDs cannot inherit another request receipt. Existing Wazuh/snapshot history is preserved. Full reassessment and enterprise semantic reconciliation remain. [Review contract](contracts/technician-runtime-review.md). |

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
| 108 | Run End-to-End Normal Request Test | Partial | On the Pi, authenticated MCP → signed ALICE request → permission → model result → ALLOW → simulated plant execution → serial-v3 display → USB ledger → Wazuh delivery passed for 60→70→80→90 fan requests from a 90 F start. The deployed MCP upstream was corrected to runtime port 8080, pollers use MCP port 8790, and a fresh authenticated metrics read passed. The ESP acknowledged configured output; visible illumination and ONLINE direct-control acceptance remain. |
| 109 | Run New-Agent Push-Back Test | Planned | New-agent novelty/cohort fixtures exist. Console mock clarification is reported separately; no real cross-system new-agent push-back test exists. |
| 110 | Run Slight-Anomaly Push-Back Test | Planned | An elevated mock result exists; no actual slight-anomaly push-back exchange is tested. |
| 111 | Run Hard Policy Denial Test | Planned | A skipped-denial fixture validates result shape; no policy evaluation, zero-model-call assertion or enforcement denial is tested end to end. |
| 112 | Run High-Anomaly Hold Test | Partial | On the Pi, authenticated power-agent 90→0 at a hot-room state produced a real HIGH model result, `ANOMALY_REVIEW_REQUIRED`, eligible native HOLD and no execution. USB and Wazuh retained the decision. Earlier signed-review tests cover rejection and one-use approval; this specific integrated HOLD still needs a technician outcome and visible hardware confirmation. |
| 113 | Run Technician Approval Test | Partial | Automated Rust native snapshot/consume/sign/HTTP→real Python bridge/runtime/temporary ledger test approves once, rejects and replays with exactly one mock command. Cross-language vectors, cancellation, concurrency and uncertain/restart tests pass. Real camera→physical Pi→hardware acceptance remains unperformed. [Validation](reports/2026-09-06-native-live-backend-validation.md). |
| 114 | Run DDIL Decision Test | Planned | Socket-blocked feature replay proves that component is local, not a complete DDIL decision flow. |
| 115 | Run Cloud Reconnection Test | Planned | No endpoint handover plus direct Pi/enterprise reconnect, audit delivery and cache refresh integration test exists. |
| 116 | Run Evidence Reconciliation Test | Planned | No evidence reconciliation workflow or integration test exists. |
| 117 | Run User-Permissions Update Test | Planned | No permissions-update workflow or integration test exists. |
| 118 | Run Tampered SD Package Test | Planned | Payload integrity unit tests exist; no signed removable-package tamper/update integration test exists. This original SD label now applies to the USB input packages. |

## Supplemental planned requirements from the two-mode revision

These requirements supplement the unchanged original list and are excluded from
the 118-task totals. The entries distinguish available component evidence from
remaining integrated acceptance. The [architecture][architecture] and
[console integration note][console-integration] describe the required boundaries.

| Supplemental ID | Planned requirement | Required acceptance boundary |
| --- | --- | --- |
| SUP-01 | Endpoint-enforced single-authority handover | Demonstrate exactly one current controller across ONLINE/OFFLINE transfer; reject competing authority, stale commands and outstanding approvals. Select and implement the authenticated fence/recovery protocol rather than treating network state as authority. |
| SUP-02 | ONLINE activity-feed coverage and cursors | Existing collected ALICE request/audit feed is shared natively with honest freshness and bounded replay. The enterprise ingress validates the signed thermal fan schema, creates and reads back a Wazuh receipt, retains it on Pi USB and forwards the unchanged envelope through a loopback SSH tunnel. Live cloud request `2d6b2842…098291` produced a model-backed CHALLENGE, fresh-face technician approval, completed 70% fan execution and correlated Wazuh/Pi/USB evidence. The SIEM exposes the latest governed request on its overview and refreshes every five seconds. No enterprise-wide producer or packet capture was added. [Parity](plans/native-live-backend-parity.md). |
| SUP-03 | Bounded trusted cache synchronization | Bound permissions, normal behavior and relevant SIEM/EDR/mission caches; verify issuer/signature/version/validity and complete coverage, preserve usable active data, and activate compatible replacements atomically. |
| SUP-04 | Console/core executable schema adapter and native transport | Latest team `d5a0d56` retained through local visual integration, including fan review and telemetry contracts. Native tests62 passed; browser review/reconciliation remains synthetic. [Integration evidence](reports/2026-09-06-main-redesign-integration.md). Historical source continuation: User-requested local bridge recovery: stopped personal rehearsal resumed with same ports/keys and22 unchanged events; native FEED LIVE verified. New safe resume mode survives stdin EOF without creating HOLDs. Helper tests15 passed; physical Pi not tested. [Recovery evidence](reports/2026-09-06-runtime-bridge-recovery.md). Native compact audit ingestion and exact signed review use the existing bridge/runtime. Null/unknown and original decisions are preserved. Rich decision/reassessment producers and general cross-system adapters remain unavailable. [Parity](plans/native-live-backend-parity.md). |
| SUP-05 | Remote approval proof bound to current authority | Implemented locally for the first-light runtime: exact signed request/decision/release/authority/epoch/nonce/action and fresh session, with replay/concurrency/uncertain-delivery tests. General enterprise authority transfer and real camera/physical-Pi acceptance remain. [Contract](contracts/technician-runtime-review.md). |
| SUP-06 | Durable context/action outboxes and receipt recovery | Native review persists the exact signed submission before transmission, consumes grants once and reconciles via GET after timeout/restart. Automatic retransmission is absent. General context outboxes and enterprise recovery remain. [Contract](contracts/technician-runtime-review.md). |
| SUP-07 | Independent execution attempt and result records | First-light native review separates action acknowledgment, controller receipt, execution result and observed state with authority/request/action bindings. Real hardware and broader controller/domain acceptance remain. [Validation](reports/2026-09-06-native-live-backend-validation.md). |
| SUP-08 | Direct Pi reconnection audit and reconciliation | Publish every DDIL request/decision/attempt/result directly upstream with durable upload IDs/cursors and acknowledgements, flag risks, append later findings, preserve original history and refresh verified caches without technician relay. |
| SUP-09 | Trusted agent-to-user accountability | Establish authoritative user/agent/mission mappings and revocation/expiry behavior for ONLINE feeds and OFFLINE requests; agent-supplied identity claims cannot establish their own permissions. |
| SUP-10 | Contextual fan-sequence escalation | Implemented for current-state context: bounded synthetic model permits tested +10 cooling steps and escalates a hot-room 60→0 cut to eligible native review; rejection sends no simulated command. Sequence-history features, real sensor training and Pi acceptance remain. |
| SUP-11 | Enterprise edge-offline presentation | Show loss/staleness of authenticated Pi and sync feeds, last contact and unknown authority accurately on the disconnected enterprise host; an offline banner must not claim handover completion. |

| SUP-12 | Technician console visual and motion system | [PR #7](https://github.com/theoberk25/Alice/pull/7) opened against Theo’s main at user request; includes team `4f98a14`, final repository Python543/266 subtests passed. User will merge; no deployment. PR publication authorized by user; latest team thermal deployment `4f98a14` merged with upstream files preserved unchanged. User subsequently requested live runtime: restored saved remote/ArcFace/database/feed profile and reopened rebuilt app at sign-in. Feed read-only check HTTP200/22 events, existing local-runtime/mock controller; test profile/history preserved. [Profile history](reports/2026-09-06-popup-testing-app.md). Historical popup work: User-authorized popup app rebuild: real ArcFace with private simulated-history copy; opt-in manual-context wait and reset controls, default/live behavior unchanged. Frontend192/scripts8/check/app build passed; default browser31 + opt-in popup1 passed, final app reopened and Face ID service READY. Launch/browser evidence in [popup report](reports/2026-09-06-popup-testing-app.md). Historical integration: Complete source `db73071` integrated over latest team `d5a0d56` in `codex/main-redesign-integration`. Context fifth action and fan details retain behavior with shared styling; all design/animation files and licenses survive. Frontend190/scripts8/browser31/native62 and web/app builds passed; Biometrics176 passed (1 model skip), full repository Python541/266 subtests passed. Details in [integration evidence](reports/2026-09-06-main-redesign-integration.md). Real camera/native appearance/physical Pi acceptance remain; no push/deployment/Dock replacement. Historical preparation/source evidence follows: Complete since-PR-5 merge context/export prepared; includes closed/unmerged PR #6 plus all15 local commits and tracked/untracked follow-ups. Newer context-request/fan-review conflicts documented; no integration performed. [Merge handoff](handoffs/2026-09-06-new-repository-merge.md). Presentation-only Face ID redesign completed: shared Motion Primitives morph/Transition Panel, Anime.js contour/check sequence, larger camera, native-only pose/progress and reduced motion. Existing handlers/lifecycle/security unchanged against pre-task snapshot. Frontend177/scripts8/browser28 and native build passed; Dock bundle rebuilt/reopened. Real-camera visual acceptance remains pending. [Premium Face ID evidence](reports/2026-09-06-premium-face-id.md). Historical previous follow-up: User-authorized Face ID follow-up: actual pending-state discard feedback, cardinal pose hysteresis/final-angle coaching, MIT liquid-glass-react adapted focused dialogs, signed-in Change user/Sign out menu and native second-login refusal. Dock app rebuilt/reopened; local face service READY. Frontend167/scripts8/Rust61 (2 ignored)/Python177/browser26 and typecheck/lint/build passed; physical camera acceptance pending. [Face ID validation](reports/2026-09-06-face-id-fixes.md). Historical prior stage: User subsequently authorized Dock app update: native app build/launch passed and native EDT/IANA clock verified; existing settings/enrollment stores untouched. Approved follow-up implemented locally from `5bb092a`: stable biometric viewport/remaining-pose feedback, restrained surfaces and device-local dashboard clock (only functional exception). Camera lifecycle/actions unchanged. Frontend 163, scripts 8, Rust 60 (2 ignored), Python 166, all 20 browser regressions and typecheck/lint/build passed; no real-camera/physical acceptance or publication. [Refinement validation](reports/2026-09-06-dashboard-visual-refinements.md). Historical initial redesign: presentation implemented on team `e1e7506`: shared motion, semantic surfaces, decision/evidence hierarchy, compact identity/biometrics, responsive controls and accessibility. Existing business/security handlers unchanged. Integrated local main: frontend 145 + script 8; Rust 60 (2 opt-in ignored), Python biometrics 166, web/native builds and 11 browser regressions passed. Dock-linked ALICE.app rebuilt/reopened. [PR #6](https://github.com/theoberk25/Alice/pull/6) closed at user request, unmerged; redesign retained locally, no further publication. Local main not pushed. Exact results in [visual validation](reports/2026-09-06-console-visual-overhaul.md). |

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
[first-light-handoff]: reports/2026-09-05-first-light-test-log.md
