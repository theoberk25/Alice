# ALICE implementation tracker

Updated: 2026-09-05. Scope: the ALICE repository.

This preserves all 118 user-supplied task labels in their original order. IDs
`001`–`118` are stable: update status/evidence without renumbering or silently
renaming tasks. These statuses describe the implementation and evidence included
in this repository; they do not imply a deployed system.
Other team members' work is not assumed present unless it is visible here.

## Status and current checkpoint

- **Done component** — the named local computation or record structure is
  implemented and has component-test evidence. It does not imply that admission,
  policy, fusion, transport, enforcement, or Pi deployment is complete.
- **Partial** — a related bounded slice exists, but the task's broader behavior
  or integration remains. The evidence column names the boundary.
- **Planned** — the requested behavior is not implemented in this checkout.
  A PRD proposal or empty skeleton is not completion evidence.

Current totals: **12 Done component, 24 Partial,
82 Planned**. These are task-status counts, not a percentage of product
readiness or an estimate of remaining effort.

The current priority is the **motor request, baseline and telemetry contract**
described in the [updated data direction][data-direction]. The latest setup uses
one USB drive for `policy/`, `normal_behavior/` and `audit_logs/`, with local
Agent Mac → DCAMR Pi → separate motor controller communication, a Technician Mac
dashboard, and cloud access through the router uplink. These are integration
requirements; the topology and motor path are not implemented here. All current
**Done component** statuses remain scoped to the cyber work below; no motor
feature profile, motor model or motor enforcement exists.

Jared explicitly selected **trying separate diagnostic and state-changing
calibration references**, and that Mac experiment is now complete. It collected
1,000 distinct normal source requests per reference from fresh held-out sessions;
within-session observations can be correlated. On another fresh evaluation set,
legitimate changes reached elevated/high in 32/68 cases with the shared reference
and 2/68 with separate references. Unseen-destination ML outcomes also fell to
0/20 elevated/high, while independent novelty flags were preserved. Neither
candidate is accepted for deployment. The [training guide][training-guide] records
the paired results, limitations and runnable comparison. All 103 tests pass;
artifact digest links and 1,300 paired score mappings were checked. A cyber
calibration experiment does not establish a motor reference.

Pending questions are whether the initial demo is motor-first or includes both
motor and cyber domains, and whether a `10°` command means an absolute target
angle or a relative movement. The protected controller is also unresolved between
a second Pi and an ESP; available position feedback, normal behavior, policy
bounds, USB removal/audit retention and package-update ownership still need
agreement. Angles, limits and anomaly scores suggested by the referenced ChatGPT
assistant have not been adopted as requirements or measurements.

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
USB package-update ownership is also pending; this tracker does not assign that
responsibility to the Pi or workstation.

## Agreed scope and resource constraints

- Target: Raspberry Pi 4 Model B, **2 GB RAM**, Raspberry Pi OS Lite. Confirm OS
  bitness on the device. Training stays on the Mac; the Pi performs frozen-model
  inference only. The local LLM stays on the workstation.
- The implemented profile covers Web-01 cyber requests: routine diagnostics and
  occasional changes to known destination relationships. Its five-action profile
  and example counts are documented in the [feature guide][feature-guide]; counts
  are synthetic, not observed operating limits or policy permissions. Keep this
  profile as regression coverage while agreeing the separate motor contract;
  motor-first versus both domains in the initial demo remains unanswered.
- The intended local path is Agent Mac → DCAMR Pi → protected motor controller,
  with the Technician Mac providing the dashboard and local LLM. The router
  supplies the cloud uplink; disconnecting that uplink is the planned DDIL demo.
  Controller authentication, approval binding, replay prevention and independent
  position feedback are not implemented merely by choosing this topology.
- The current removable medium is one USB drive: `policy/` and `normal_behavior/`
  are trusted inputs after verification; `audit_logs/` is a separate DCAMR output.
  Permissions may be packaged with policy. Original task labels containing
  **SD Card** or **SD Package** are preserved verbatim below and now track the
  equivalent USB package work. This medium clarification does not complete
  discovery, signatures, update ownership, persistence or atomic activation.
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
- DCAMR owns authorization. Policy denial cannot be overridden by anomaly,
  context or technician action; a low score cannot authorize by itself. Evidence,
  approval, context attempts and final outcomes remain with the integration owner.

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
| 001 | Define Agent Action Request Schema | Partial | [Internal feature-request shape][feature-schema] is validated; the public [action-request schema][action-schema] is still an empty skeleton. |
| 002 | Define Context Push-Back Schema | Planned | Challenge messages remain an integration design task; the [challenge skeleton][challenge-schema] is empty. |
| 003 | Define Agent Context Response Schema | Planned | No agent context-response contract is implemented. |
| 004 | Define Policy Package Schema | Planned | The [package manifest skeleton][package-schema] is empty; no signed policy-package contract exists. |
| 005 | Define Normal Operations Package Schema | Partial | [Baseline payload schema][baseline-schema] exists. The signed normal-operations package envelope, manifest and lifecycle are not defined by that payload schema. |
| 006 | Define User Permissions Schema | Planned | No permissions-package or user-permissions schema is implemented. |
| 007 | Define Local Telemetry Schema | Planned | Trusted history input is defined, but the general telemetry/sensor contract is not. |
| 008 | Define Decision Output Schema | Partial | [Nested anomaly result][result-schema] and its [validator][contract] exist; the [complete decision record][decision-schema] is still an empty skeleton. |
| 009 | Define Reconciliation Event Schema | Planned | No reconciliation-event contract is implemented. |

## Initial package loading and trust (010–014)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 010 | Load Policy Data from SD Card | Planned | Current medium: USB `policy/`. No discovery, policy package load or activation path is implemented. |
| 011 | Load Normal Operations Data from SD Card | Planned | Current medium: USB `normal_behavior/`. The baseline byte loader exists, but no removable-media package load path is implemented. |
| 012 | Load User Permissions from SD Card | Planned | Permissions may accompany USB policy input; no permissions-package load path is implemented. |
| 013 | Verify Package Signatures | Planned | Expected byte-digest checks are not signature/issuer verification; [package verifier][package-verifier] remains a skeleton. |
| 014 | Validate Package Versions | Partial | [Schema/profile versions][feature-validation] and baseline labels are checked. Package freshness, rollback prevention and compatible activation are not implemented. |

## Request admission and policy checks (015–024)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 015 | Normalize Incoming Agent Requests | Partial | [Feature-input validation and endpoint normalization][feature-validation] exist. Authenticated external admission and shared canonical request hashing remain. |
| 016 | Identify Agent | Partial | [Builder][features] checks request/subject identity agreement and baseline registration. Caller authentication is still an external prerequisite. |
| 017 | Identify Mission | Partial | [Builder][features] checks the bound mission ID and role/mission profile scope; independent mission authorization is not implemented. |
| 018 | Identify Requested Action | Partial | [Builder][features] resolves the normalized action against the fixed five-action catalog. The public request/admission path remains. |
| 019 | Identify Target Resource | Partial | [Builder][features] identifies and compares the normalized target; the public request/admission path remains. |
| 020 | Identify Requested Parameters | Partial | [Builder][features] validates empty diagnostic parameters or exact outbound endpoint parameters. Other action domains and public admission remain. |
| 021 | Check Agent Permissions | Planned | Permission checks belong to the unimplemented policy/admission path; profile membership is not permission. |
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
| 035 | Build Physical Sensor Features | Planned | The motor/telemetry contract is now a priority; command meaning, controller and measured position feedback remain unresolved. No motor or sensor features are implemented, and cyber columns retain their existing meanings. |
| 036 | Build Local Evidence Features | Planned | Evidence sufficiency remains with DCAMR fusion; the [evidence component][evidence] is a skeleton. |

## Model and sequence scoring (037–044)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 037 | Train Isolation Forest | Done component | [Mac training pipeline][training] and [actual-fit tests][training-tests] fit a bounded Isolation Forest on synthetic normal sessions; [candidate-002][training-report] is an in-memory lab fit, not an accepted deployment model. |
| 038 | Save Isolation Forest Model | Planned | A real model was fitted in memory, but no fitted artifact was persisted. [JSON run outputs][training-report] are not a deployable model; format and trusted loading remain pending. |
| 039 | Load Isolation Forest Model on Boot | Planned | No trusted artifact loader, boot integration or model worker exists. |
| 040 | Score Incoming Requests | Partial | [Lab pipeline][training] replays source requests through the runtime feature builder and actual Isolation Forest. No live DCAMR evaluator, model worker or anomaly-result adapter exists. |
| 041 | Calculate Anomaly Percentile | Done component | [Rank mapper][scoring] and [tests][training-tests] map cyber model outputs against 1,200 frozen held-out normal calibration scores; [reference JSON][training-calibration] preserves the global lab reference, which is not accepted for deployment. Separate diagnostic/change references are approved for experimentation but pending, with at least 1,000 independent held-out normal observations required per reference. |
| 042 | Calculate Individual Anomaly Factors | Partial | [Feature comparisons and source references][features] exist. A live anomaly evaluator has not yet combined these observations with actual model output; factors are not learned attribution. |
| 043 | Build Action-Sequence Model | Partial | [Validated transition-count tables][baseline] and [synthetic rows][feature-fixtures] exist; no sequence-training pipeline or learned sequence artifact exists. |
| 044 | Score Action Sequences | Done component | [History component][sequence] computes unsmoothed transition frequency for a complete row and masks no-predecessor cases. This is not an attack probability or authorization score. |

## Decision fusion and context exchange (045–057)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 045 | Combine Policy and Anomaly Results | Planned | The [decision-model skeleton][fusion] is empty; no policy/anomaly fusion runs. |
| 046 | Define ALLOW Logic | Planned | [PRD][prd] proposes conditions; executable authorization logic and team agreement remain. |
| 047 | Define REQUEST_CONTEXT Logic | Planned | [PRD][prd] proposes conditions; executable push-back/fusion logic and context limits remain. |
| 048 | Define HOLD Logic | Planned | [PRD][prd] proposes conditions; high-anomaly context-versus-hold behavior remains a product decision. |
| 049 | Define DENY Logic | Planned | [PRD][prd] requires hard-deny precedence; no executable denial path exists. |
| 050 | Trigger Automated Context Push-Back | Planned | The [challenge component][challenge] is a skeleton; no automated exchange runs. |
| 051 | Receive Agent Context Response | Planned | No agent context-response transport or receiver runs. |
| 052 | Validate Context Response | Planned | No context-response schema/admission validation is implemented. |
| 053 | Verify Context Evidence Locally | Planned | No local evidence authenticity, relevance or freshness verifier is implemented. |
| 054 | Recalculate Features After Context | Partial | [Builder/tests][feature-tests] preserve context-round counting and reject later-history substitution. The context workflow and evaluator re-dispatch are not implemented. |
| 055 | Recalculate Anomaly Score | Planned | No live model scorer or context re-scoring adapter exists. |
| 056 | Re-run Policy Evaluation | Planned | No initial or repeated policy evaluation exists. |
| 057 | Produce Final Decision | Planned | No authoritative final decision is produced by the [fusion skeleton][fusion]. |

## Provenance and audit (058–065)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 058 | Generate Decision Provenance | Partial | [Immutable feature provenance][feature-types] and [anomaly provenance fields][result-schema] exist; final DCAMR decision provenance is not generated. |
| 059 | Record Source of Every Decision Factor | Partial | [Builder][features] supplies a source for every feature. Policy, evidence and final fused decision factors are not yet produced. |
| 060 | Record Model Metadata | Partial | [Mac report][training-report] records actual fit parameters, tree counts and runtime versions; [anomaly contract][result-schema] supports binding metadata. No persisted/signed model artifact or live decision metadata exists. |
| 061 | Record Policy Metadata | Planned | No live policy result or policy-metadata recorder exists. |
| 062 | Record Baseline Metadata | Done component | [Baseline loader][baseline] records payload identity/version and verified expected byte digest; [FeatureBatch][feature-types] preserves them. Enclosing package identity stays separate. |
| 063 | Record Evidence Metadata | Planned | No live evidence-verification result or evidence-metadata recorder exists. |
| 064 | Record Connectivity State | Planned | No authoritative connectivity monitor/state recorder exists. |
| 065 | Write Tamper-Evident Audit Record | Planned | The [audit writer][audit] is a skeleton; no tamper-evident chain or persistence exists. |

## Dashboard, technician and execution (066–076)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 066 | Export Raw Decision Data to Dashboard | Partial | [Serializable anomaly contract][contract] and [mock replay][anomaly-replay] exist. No full raw-decision record or dashboard transport is implemented. |
| 067 | Export Live Pi Status to Dashboard | Planned | No Pi status endpoint, telemetry transport or dashboard integration exists. |
| 068 | Export Available Technician Actions | Planned | No authoritative technician-action list or export exists. |
| 069 | Receive Technician Decision | Planned | No technician decision endpoint or state transition exists. |
| 070 | Require Technician Authentication for Approval | Planned | No technician authentication/approval binding is implemented. |
| 071 | Execute Approved Action | Planned | The [enforcement gateway][enforcement] is a skeleton; no action execution exists. |
| 072 | Record Technician Decision | Planned | No persisted technician-decision audit event exists. |
| 073 | Record Action Execution Result | Planned | The builder consumes supplied confirmed execution history; it does not execute or persist action results. |
| 074 | Monitor Resulting Physical/System State | Planned | No post-execution physical/system-state monitor exists. |
| 075 | Compare Expected vs Actual Result | Planned | No expected-versus-observed execution-outcome comparison exists. |
| 076 | Flag Post-Execution Anomalies | Planned | No post-execution anomaly detector exists. |

## DDIL and reconciliation (077–092)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 077 | Detect Cloud Connectivity Loss | Planned | No cloud connectivity detector exists. |
| 078 | Enter DDIL Mode | Planned | No DDIL state machine exists. |
| 079 | Continue Local Policy Enforcement | Planned | No policy engine is running in either connected or DDIL mode. |
| 080 | Continue Local Anomaly Scoring | Partial | [Local lab scoring][training] runs actual Isolation Forest without a cloud dependency, alongside [offline feature checks][feature-tests]. Pi runtime inference and connected/DDIL mode orchestration remain unimplemented. |
| 081 | Continue Local Context Push-Back | Planned | No context push-back loop is running in either connectivity mode. |
| 082 | Continue Local Dashboard Output | Planned | No local dashboard transport is running in either connectivity mode. |
| 083 | Cache Unverified External Evidence Requests | Planned | No bounded persistent external-evidence request cache exists. |
| 084 | Detect Cloud Reconnection | Planned | No cloud reconnection detector exists. |
| 085 | Exit DDIL Mode | Planned | No DDIL exit transition exists. |
| 086 | Reconnect to SIEM | Planned | The SIEM connector is a skeleton; no reconnection workflow exists. |
| 087 | Reconnect to EDR | Planned | The EDR connector is a skeleton; no reconnection workflow exists. |
| 088 | Fetch Pending External Evidence | Planned | No pending external-evidence fetch workflow exists. |
| 089 | Reconcile Local Evidence with Cloud Evidence | Planned | The [reconciliation component][reconciliation] is a skeleton. |
| 090 | Detect Evidence Discrepancies | Planned | No local/cloud evidence discrepancy detector exists. |
| 091 | Append Reconciliation Results | Planned | No reconciliation event appender or persistent audit integration exists. |
| 092 | Preserve Original Decision History | Planned | Feature/dispatch objects are immutable, but a persistent original-decision history has not been implemented. |

## Package updates and connected recovery (093–107)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 093 | Fetch Updated User Permissions | Planned | Permissions-update source and owner are not connected. |
| 094 | Validate Updated User Permissions | Planned | No updated permissions schema, signature or validity checks exist. |
| 095 | Write Updated User Permissions to SD Card | Planned | Current medium is USB; no permission-update writer exists and package-update ownership is pending. |
| 096 | Fetch Updated Policy Package | Planned | No authenticated policy-update fetch path exists. |
| 097 | Validate Updated Policy Package | Planned | No updated policy package signature, validity or compatibility verifier exists. |
| 098 | Write Updated Policy Package to SD Card | Planned | No USB `policy/` update writer exists; package-update ownership is pending. |
| 099 | Fetch Updated Normal Operations Package | Planned | No authenticated normal-operations update fetch path exists. |
| 100 | Validate Updated Normal Operations Package | Partial | [Baseline payload validation][baseline] checks digest, schema and table consistency. An updated package still needs signature/issuer/expiry checks and activation handling. |
| 101 | Write Updated Normal Operations Package to SD Card | Planned | No USB `normal_behavior/` update writer exists; package-update ownership is pending. |
| 102 | Reload Updated Permissions | Planned | No atomic permissions activation/reload path exists. |
| 103 | Reload Updated Policy | Planned | No atomic policy activation/reload path exists. |
| 104 | Reload Updated Baseline | Partial | [Loader][baseline] creates a fresh immutable payload instance. USB watching, atomic replacement and in-flight evaluation coordination are not implemented. |
| 105 | Version All Updated Packages | Planned | Per-payload baseline labels exist; versioning and compatibility across all package types are not implemented. |
| 106 | Reject Invalid or Tampered Updates | Partial | [Payload digest/schema checks][feature-validation] reject altered or malformed supplied bytes. Signed update verification, rollback prevention and replacement recovery remain. |
| 107 | Restore Full Connected Decision Context | Planned | No connected/DDIL reconciliation state machine can restore the full decision context. |

## End-to-end acceptance (108–118)

| ID | Task | Status | Evidence and remaining work |
| --- | --- | --- | --- |
| 108 | Run End-to-End Normal Request Test | Planned | Normal feature and anomaly fixtures pass component assertions only; no full request-to-execution path exists. |
| 109 | Run New-Agent Push-Back Test | Planned | New-agent novelty/cohort fixtures exist; no actual push-back exchange is tested. |
| 110 | Run Slight-Anomaly Push-Back Test | Planned | An elevated mock result exists; no actual slight-anomaly push-back exchange is tested. |
| 111 | Run Hard Policy Denial Test | Planned | A skipped-denial fixture validates result shape; no policy evaluation, zero-model-call assertion or enforcement denial is tested end to end. |
| 112 | Run High-Anomaly Hold Test | Planned | Actual lab model outputs and a high mock result exist; no integrated model/fusion hold or no-execution acceptance test exists. |
| 113 | Run Technician Approval Test | Planned | No authentication-to-approval-to-execution integration test exists. |
| 114 | Run DDIL Decision Test | Planned | Socket-blocked feature replay proves that component is local, not a complete DDIL decision flow. |
| 115 | Run Cloud Reconnection Test | Planned | No reconnection workflow or integration test exists. |
| 116 | Run Evidence Reconciliation Test | Planned | No evidence reconciliation workflow or integration test exists. |
| 117 | Run User-Permissions Update Test | Planned | No permissions-update workflow or integration test exists. |
| 118 | Run Tampered SD Package Test | Planned | Payload integrity unit tests exist; no signed removable-package tamper/update integration test exists. This original SD label now applies to the USB input packages. |

## Maintaining this tracker

After each small implementation increment, update only the relevant rows with
the completed component, its tests, and any remaining integration boundary.
Keep unresolved product choices explicit. Promote the end-to-end rows only
after the corresponding real multi-component workflow runs; model-quality and
Pi resource results should identify actual artifact/runtime/hardware versions.
Do not treat fixture scores or Mac resource measurements as Pi acceptance.

[prd]: prds/anomaly-model-prd.md
[contract-guide]: anomaly-contract.md
[feature-guide]: anomaly-features.md
[data-direction]: data-direction-2026-09-05.md
[training-guide]: anomaly-training.md
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
[feature-fixtures]: ../tests/fixtures/features/README.md
[anomaly-replay]: ../lab/replay_anomaly_fixtures.py
[package-verifier]: ../dcamr/packages/package_verifier.py
[policy]: ../dcamr/policy_engine/policy_engine.py
[fusion]: ../dcamr/decision_model.py
[challenge]: ../dcamr/challenge/challenge.py
[evidence]: ../dcamr/evidence/evidence_interface.py
[audit]: ../dcamr/audit/audit_log.py
[enforcement]: ../dcamr/enforcement/enforcement_gateway.py
[reconciliation]: ../dcamr/reconcile/reconciliation.py
[training]: ../lab/anomaly_training.py
[training-cli]: ../lab/train_anomaly_model.py
[synthetic-data]: ../lab/synthetic_anomaly_data.py
[training-tests]: ../tests/test_anomaly_training.py
[synthetic-tests]: ../tests/test_synthetic_anomaly_data.py
[training-report]: reports/anomaly-lab/candidate-002/training-report.json
[training-calibration]: reports/anomaly-lab/candidate-002/calibration-reference.json
[training-manifest]: reports/anomaly-lab/candidate-002/dataset-manifest.json
