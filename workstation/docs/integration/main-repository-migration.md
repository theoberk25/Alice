# Main repository migration and contract assessment

The technician console is now a self-contained subsystem under `workstation/`.
This is source integration: authenticated console/core transport, shared wire
contracts, remote approval proof and protected execution remain unfinished.
Use the [main workstation guide](../../../docs/guides/workstation.md) for setup and
current migration verification. Commands and code paths in the subsystem docs
are relative to `workstation/` unless they explicitly say otherwise.

## Provenance and scope

| Item | Recorded migration basis |
| --- | --- |
| Standalone source | `ALICE_TechnicalReview`, commit `50de955737a647b856658bf7a5da6f52d15b4a4a` |
| Main repository baseline | `e0796d0` on `codex/Technician-DashboardImplementation` |
| Imported source set | 127 tracked source files, retaining their internal relative structure |
| Destination | `workstation/`; the pre-existing tracked workstation placeholders were preserved, with no path collisions |
| Dependency boundary | Separate npm workspace and lockfile, Cargo manifest/lock, and Python requirements under `workstation/` |
| Excluded local state | Source `.git`, `.env`, dependencies, toolchains, virtualenvs, model weights, biometric images/embeddings/keys, databases, build output, logs, screenshots and sharing archives |

The original standalone checkout remains the historical source; it is not a
runtime dependency. No symlink or launch command points back to it. Existing
native app identifiers and default data-path behavior are retained. Copying
source does not migrate, reset, provision or inspect an operator's identities.
The separate [historical verification record](../development/verification.md)
retains source-reported checks and original-Mac observations; those outcomes
must not be read as migration validation or a portable installation guarantee.

## Migration map

| Source path | Main repository path | Ownership retained |
| --- | --- | --- |
| `apps/desktop/` | `workstation/apps/desktop/` | React/Vite UI and Tauri/Rust native boundary |
| `packages/contracts/` | `workstation/packages/contracts/` | Executable console Zod schemas and legacy adapter |
| `packages/domain/` | `workstation/packages/domain/` | Review state, immutable lineage and interface contracts |
| `packages/ui/` | `workstation/packages/ui/` | Shared console presentation components |
| `services/biometrics/` | `workstation/services/biometrics/` | Local facial identity service and tests |
| `fixtures/` | `workstation/fixtures/` | Byte-preserved original dashboard contract, extracted/normalized fixtures and deterministic scenarios |
| `tests/`, `scripts/` | `workstation/tests/`, `workstation/scripts/` | Console checks, launchers and provisioning helpers |
| `docs/`, root Markdown | `workstation/docs/`, `workstation/*.md` | Console implementation/reference docs, adapted setup and historical evidence |
| Root manifests, locks and configuration | `workstation/` | Independent subsystem tooling and private `.env` boundary |

The main repository root is not converted to an npm monorepo. Core `common/`,
anomaly, lab, Pi and enterprise boundaries retain their existing roles. No
console contract is promoted into `common/` during this migration, and no
permissions evaluator, anomaly scorer, executor, transport endpoint or
authority-transfer protocol is added to the console.

## Current authority and historical conflicts

The main [architecture](../../../docs/prds/ALICE-DCAMR-Architecture.md),
[product PRD](../../../docs/prds/ALICE-DCAMR-PRD.md),
[team handoff](../../../docs/prds/ALICE-DCAMR-PRD-Handoff.md), and
[console integration requirements](../../../docs/integration/technician-console.md)
govern current product semantics. The supplied external `ALICE.md` is historical
context. Its earlier every-request enforcement model and Pi-dashboard placement
do not supersede the main design. The preserved dashboard contract remains
compatibility data, not an authority-transfer specification.

| Dimension | Current meaning and integration limit |
| --- | --- |
| ONLINE | Enterprise systems control execution directly; the Pi synchronizes trusted caches, consumes available authenticated feeds and reports audit/findings. |
| OFFLINE / DDIL | ALICE governs local actions only after controlled transfer establishes one ready execution authority. |
| Reconnection | A workflow for direct Pi-to-enterprise synchronization, reconciliation, cache updates and controlled transfer; not a third product mode. |
| Existing console status | `DDIL`, `CONNECTED`, `DEGRADED` describe the retained version 1.0 payloads; they do not prove authenticated control ownership. |
| Transport configuration | `mock`/`remote` selects the console transport boundary, not the product authority. Remote remains fail-closed. |
| Facial identity configuration | `mock`/`arcface` selects identity verification, independent of edge transport and execution ownership. |

Trusted owner/generation, transfer acknowledgement/readiness, pending approval
invalidation or revalidation, and late receipt treatment need an agreed versioned
protocol. Network connectivity and a face match cannot confer execution
authority. The Mac keeps camera processing, ArcFace, local identity storage and
Ollama; the Pi remains the constrained edge component. Local console audit is not
the authoritative or tamper-evident mission audit.

The current product term is **permissions**. Existing `policy` keys, filenames,
fixture text and console labels are retained in this migration so a vocabulary
change does not silently change the wire contract or review behavior. Any later
operator-language or schema update must preserve deterministic hard-denial
semantics and distinguish compatibility names from product authority.

## Contract classification

### A. Console-local contracts

These stay under `workstation/`: native IPC and configuration, administrator and
technician sessions, enrollment metadata, loopback biometric request/response
schemas, the in-memory verification grant, SQLite persistence, review state and
lineage indexes, language explanation/informational-intent validation, and UI
components. Local verification UUIDs are not remotely verifiable attestations.
Images, embeddings, credentials and enrollment keys stay local to the Mac.

The HOLD/lineage implementation consumes immutable decisions and enforces
currentness; it is not a policy/anomaly engine. Its invariants remain relevant
to a future shared protocol, but its store shape and IPC are not shared wire
contracts by default.

### B. Candidate cross-system contracts retained locally

| Contract | Existing console definition and unresolved boundary |
| --- | --- |
| `alice.decision` | Full immutable outer decision, request, policy, anomaly, evidence, context, capabilities and optional reassessment lineage; shared outer schema and authority binding still need agreement. |
| `alice.status` | Node, legacy mode, connectivity, package and engine state; current authority owner/generation, freshness and transfer readiness are not defined. |
| `alice.reconciliation` | Later evidence results bound to the original decision, with `original_decision_changed=false`; enterprise delivery/recovery remains upstream work. |
| `alice.agent_status`, `alice.service_status` | Agent/model/activity and operational service facts; real producers, authenticity and freshness are unconnected. |
| `alice.context_request`, `alice.agent_response` | Exact decision/request/agent/challenge correlation and structured claims; durable routing, retries, cancellation and replay remain incomplete. |
| `alice.technician_action` | Exact `APPROVE_ONCE`, HOLD, RESEARCH or REJECT with technician and optional local verification reference; remote proof and authority binding remain unagreed. |
| Action receipt | Local schema echoes action ID with ACCEPTED/PENDING/REJECTED and `NOT_EXECUTED`; it has no separate event name/version envelope and does not confirm protected execution. |

Executable definitions remain in [events.ts](../../packages/contracts/src/alice/events.ts)
and [commands.ts](../../packages/contracts/src/alice/commands.ts), with generated
JSON Schemas in [the contract directory](../contracts/alice-events.md). The
[console contract reference](upstream-alice.md) documents current behavior.
Promoting any candidate requires agreement with the core owners, mapping,
version negotiation, authenticated delivery and boundary tests.

Potential future integration locations already exist as empty placeholders:
`dcamr/api/dashboard_api.py`, `agent/dcamr_client.py`, and
`agent/challenge_responder.py`, relative to the main repository root. They are
candidate ownership locations, not working dashboard endpoints, clients or
challenge-routing services. This migration leaves them untouched.

### C. Concepts already represented under common

The main repository has implemented anomaly contracts for
[results](../../../common/schemas/anomaly_result.json),
[feature inputs](../../../common/schemas/anomaly_feature_input.json), and
[baselines](../../../common/schemas/anomaly_baseline.json). These are separate
from the console's legacy anomaly display object and remain authoritative for
their core component boundary.

The existing `common/schemas/action_request.json`, `decision_record.json`,
`challenge.json`, `evidence.json`, and `package_manifest.json` are zero-byte
placeholders at the recorded main baseline. Their names overlap console
concepts, but they provide no executable outer wire contract to import or
overwrite. They remain untouched. No shared status, receipt, remote biometric
proof or execution-result schema is established merely by adding the console
source to this repository.

### D. Version, vocabulary and semantic conflicts

| Difference | Required handling |
| --- | --- |
| Console `schema_version="1.0"` versus core anomaly `1.0.0-draft.1` | Agree versioned composition or adaptation; matching ALICE naming is not compatibility. |
| Main handoff's planned ALLOW/REQUEST_CONTEXT/HOLD/DENY outer outcomes versus console ALLOW/HOLD/DENY plus `context_challenge.required` | Agree a versioned adapter and one authoritative challenge issuer/router. Do not automatically collapse REQUEST_CONTEXT into HOLD, issue competing challenges, or let the console perform reassessment. |
| Console 0–100 `risk_score`, percentile, severity and model strings versus core nullable `[0,1]` `score`, independent `status`/`result`, calibration and provenance | Preserve both contracts. Dividing by 100 or multiplying by 100 does not establish equivalent calibration or authorization. Represent unavailable scores honestly. |
| `DDIL`/`CONNECTED`/`DEGRADED` versus ONLINE/OFFLINE authority | Preserve existing schemas/fixtures while specifying a future trusted mode/owner protocol. Do not treat connectivity or UI labels as a handover. |
| Legacy `dcamr.*`, native `alice.*`, and `policy`/permissions | Keep the current validated legacy adapter, identifiers and wire keys; negotiate future terminology/schema changes explicitly. |
| Outer decision lineage versus anomaly evaluation lineage | Console `reassessment` is a linear new-decision parent/root/trigger/sequence chain. Core `previous_evaluation_id` is anomaly evaluation provenance; it is not interchangeable. |
| APPROVE capability, APPROVE_ONCE action, accepted receipt and execution | Preserve their distinct meanings. Hard denial is non-overridable; a technician request and successful identity comparison cannot establish execution. |
| Five fixed request identity comparisons versus complete action binding | Current console checks request/agent/mission/action/target; canonical parameter digest, action version and authority-generation proof need agreement. |

The supplied outbound-open action conflicts with its agent's outbound-block
justification, and pending/unverified evidence counts overlap. Preserve and
display those facts; do not silently rewrite them. Legacy source bytes, current
generated contracts and fixtures are retained unchanged by this migration.

## Preserved safety and implementation boundaries

Agent responses remain claims and stop at REASSESSMENT_PENDING. Only a validated
new immutable decision supersedes the current assessment. Historical decisions,
evidence and late receipts retain their original binding. New actions and fresh
one-use biometric grants must address the latest exact decision/request;
login cannot substitute for approval step-up. ArcFace matches identity without
implemented liveness or camera replay protection.

Ollama explains supplied facts and cannot authorize, override denial, modify
scores/evidence or execute protected actions. Real transport must validate and
cache authenticated inbound state at the native boundary. Replacing a fixture
adapter with renderer HTTP would not complete that trust boundary. Durable
delivery/outbox, attestation, execution results and ONLINE/OFFLINE transfer are
future coordinated work; this migration neither invents their endpoints nor
claims them connected. A full visual and animation redesign remains deferred.
