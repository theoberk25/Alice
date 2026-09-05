# Decision Evidence Ledger: first durable slice

> Status clarification (2026-09-05): this design was subsequently approved and
> its bounded ledger component implemented. The original approval status below
> is historical; see the [approval record](../archive/handoffs/2026-09-05-decision-evidence-ledger-handoff.md),
> [current component guide](decision-evidence-ledger.md) and
> [implementation tracker](../implementation-tracker.md).

Date: 2026-09-05

Base: `main`, `e0796d03ffd5d80e94401737836c70ebac129ed6`.

Status: design incorporates the user's accepted direction, physical-sensor
decision, on-premises storage assumption and explicit Ed25519 preference;
awaiting written-spec approval before implementation.

## Purpose and scope

Implement a bounded local Decision Evidence Ledger in `dcamr/audit/audit_log.py`.
ALICE retains the authoritative record of its DDIL activity on non-removable Pi
storage. Enterprise consumers may receive replicated records after reconnection.
SQLite stores canonical append-only event records, signed checkpoints and durable
outbox metadata. This is a component implementation, not an integrated executor.

The target is Raspberry Pi 4 Model B with 2 GB RAM. Python 3.11+ and the existing
`jsonschema` dependency remain supported. SQLite, JSON and hashing use the standard
library. Ed25519 uses a maintained cryptographic library in a separate pinned audit
requirements file; there is no handwritten cryptographic implementation.

Deployment assumption supplied by the user: the physical device will likely
operate on premises, for example at a military base, with substantially greater
site storage capacity available for long-term retention. This is an expected
deployment setting, not a verified storage allocation or availability guarantee.
The USB stick is not the intended long-term archive or the only authoritative
copy of DDIL history. Site retention capacity and the Pi's local DDIL storage
budget are separate concerns; the 2 GB Pi memory target remains unchanged.

Size local storage for the expected disconnected interval, event volume and
recovery reserve. Make that budget configurable rather than assuming a small USB
capacity defines mission retention. Larger site storage can receive replicated
audit/evidence through later integration, but local durability must not depend on
its reachability. Long-term archival and retention management are outside this
first slice, and upstream acknowledgement alone does not authorize local deletion.

Out of scope: policy fusion, endpoint execution, authority-transfer protocols,
sensor drivers, Wazuh integration, enterprise connectors, evidence collection,
full reconciliation, automatic retention/deletion and production key provisioning.

## Product authority

- ONLINE: enterprise systems execute directly. ALICE records authenticated feed
  observations and synchronization/reporting facts supplied by future adapters.
- OFFLINE/DDIL: ALICE governs supported local actions only after endpoint-enforced
  authority transfer. Recording an authority claim does not authenticate it.
- Reconnection is a workflow, not a third mode. Upload, reconciliation, cache
  readiness and execution ownership are independent facts.
- A disconnected network, signed checkpoint or delivery receipt never grants
  execution authority. Unknown state is explicit; it is not inferred as OFFLINE.

Wazuh/EDR context is an authenticated, freshness-bounded Policy Information Point.
It is neither an authorization source nor a machine-learning label. This ledger
does not authenticate external feeds or evaluate their freshness on its own.

## Local storage and transaction boundary

Use one explicitly initialized SQLite database in a protected, non-removable
directory. Initialization and opening an existing ledger are different operations:
an absent existing database must never silently create a fresh history.

Use explicit serialized write transactions, full synchronization and rollback
journaling. Commit the event and its initial outbox metadata together. Successful
append means commit returned successfully. A lost caller response is resolved by
retrying the original event ID, not by allocating another ID.

Store exact canonical event bytes. Deny updates/deletes of history through the
public interface and database triggers. Those controls prevent ordinary writes;
they do not stop an attacker with direct file access from replacing the database.
Current outbox state is a mutable projection with append-only transition history.
Transition history and projection changes commit in the same transaction.

The initial implementation supports one writer service. SQLite transactions
serialize competing append calls and allocate the next sequence from committed
state. Readers use bounded queries and validation streams records without loading
the entire mission into memory.

## Event contract

Add `common/schemas/audit_event.json` as a strict, independently versioned local
contract. It does not fill or redefine the empty public request/decision schemas,
claim console wire compatibility or change the anomaly result contract.

Every event contains these groups:

| Group | Fields and semantics |
| --- | --- |
| Identity | Schema and canonicalization version, ledger ID, node ID, stable event ID, positive contiguous sequence, event type |
| Correlation | Correlation ID; request, assessment, action, execution and parent-event IDs where applicable; exact-request digest |
| Time | Local recorded UTC or null, clock source and confidence, boot ID, monotonic reading; source observation time/confidence separately when supplied |
| Attribution | Actor kind/ID, authenticated requester, agent, responsible user/delegator, technician and assignment-source identity; unresolved attribution remains explicit |
| Authority snapshot | Product mode or unreceived value, connectivity, execution owner, authority-interval reference and confirmation state |
| Provenance | `policy`, baseline, model, calibration and snapshot identities; evidence references, content digests, source identities, verification/freshness/availability metadata |
| Event detail | Strict event-specific outcome, reason codes, lineage or compact observation fields; no arbitrary payload object |
| Integrity | Previous-event hash, event hash; fixed genesis predecessor |
| Delivery binding | Stable outbox identity and initial `LOCAL` state; later state is separate |

Require fields relevant to each event type. Nullable non-applicable identifiers
allow authority transitions and pre-admission rejection records without inventing
valid request IDs. Null provenance has an explicit missing/not-applicable reason.
Evidence references are opaque identifiers, never instructions to fetch a URL.
Validation cannot prove a source's identity from its name or a `verified` flag.

Support requests/admission/rejection, assessments/decisions, context challenges and
responses, technician actions, execution attempts, controller receipts, execution
results, observed states, authority transitions, cache activations and later
reconciliation findings. Keep machine decisions, technician intent, controller
results and sensor observations distinct.

Do not store raw prompts, agent explanations, sensor streams, face images,
embeddings, tokens, passwords or private keys in the event record. Store bounded
reason codes and references/digests to separately retained evidence. This is a
structural privacy boundary, not a promise that arbitrary caller-supplied strings
can be automatically recognized as sensitive.

## Canonicalization and hash validation

Define a ledger-specific canonical format, not an assertion of compatibility with
the anomaly helper's internal equality encoding or a shared request hash format.
Use UTF-8 JSON, sorted ASCII schema keys, no insignificant whitespace and no
Unicode normalization of values. Preserve array order; require sorted unique
arrays only where the schema defines set semantics.

Use bounded integers for counters and explicit decimal strings with units for
physical measurements. Exclude JSON floating-point numbers from this initial
ledger schema; reference the original anomaly envelope by identity/digest without
rounding or reinterpreting its floating-point scores.

Reject duplicate keys at every depth, malformed Unicode, unknown fields, excessive
nesting, invalid enum combinations and numbers outside the permitted types/ranges.
Cap canonical events at 16 KiB, evidence references at 16 and read/outbox batches
at 64. Bound identifiers, strings and arrays before expensive schema traversal.
Errors use bounded diagnostics without echoing the submitted payload.

Compute SHA-256 over a versioned domain prefix plus the canonical event excluding
`event_hash`. Include the predecessor hash and all original event metadata in that
input. Validation checks canonical bytes, schema, ledger identity, contiguous
sequence, unique IDs, predecessor links and hashes.

## Replaceable signing and trusted verification

User decision: Ed25519 is the explicit first-choice algorithm and implementation
priority. Keep signing plug and play so a supported alternative can be configured
if Ed25519 proves incompatible with the eventual deployment. This is replacement
capability, not automatic algorithm switching after a signing failure.

Separate the storage engine from a checkpoint signer and trusted verifier registry.
A signer exposes its algorithm ID and key ID and signs canonical checkpoint bytes.
A verifier resolves an allowed algorithm/key ID through externally supplied trust
configuration and checks the signature. Ledger-supplied keys or algorithm strings
cannot install trust, load plugins or select arbitrary code.

Ship one concrete Ed25519 implementation in this slice. Future ECDSA/hardware-backed
implementations can implement the same interface without changing event hashes or
storage semantics. Test interface substitution and unsupported algorithm/key
rejection. Do not implement additional algorithms or hardware provisioning now.
Do not silently fall back to an unsigned checkpoint or another algorithm.

Checkpoint bodies bind format version, ledger/node identity, covered sequence,
head event hash, previous-checkpoint digest, algorithm/key IDs and time confidence.
Sign every 64 appended events and explicitly seal smaller pending batches before
queueing them. Checkpoints live outside the event chain to avoid recursive sealing.
Partial-batch sealing is explicit and does not depend on a trusted wall clock.

Private keys stay outside the database/evidence directory and are supplied through
the signer. Existing signatures require their historical trusted verification keys;
opening a ledger cannot silently trust a new key found in the database. Automatic
key rotation and secure-element provisioning are later integration work.

If signing fails after event commit, preserve that event as local/unsealed. Report
sealing failure and blocked readiness; do not suggest the committed event vanished.
An append result must distinguish persistence from checkpoint coverage. A failed
checkpoint transaction does not advance coverage or queue unsigned records.

## Tamper-evidence assumptions

Describe the result as tamper-evident, never tamper-proof or immutable storage.
Assume the trusted writer and verifier configuration are protected and the storage
stack honors synchronization. Software permissions alone do not protect a key from
host compromise. Signatures attest recorded bytes, not the physical truth of them.

Verify checkpoints on restart. Allow the validator to receive an independently
retained trusted checkpoint as an anchor. Detect modification, broken links and
truncation conflicting with that anchor. Without an independent anchor, rollback
of the complete database and its checkpoints may be undetectable. Events after
the last signed checkpoint have weaker protection; report the covered sequence.

## Delivery lifecycle and idempotency

Expose `LOCAL -> SEALED -> QUEUED -> ACKNOWLEDGED -> RECONCILED` separately from
original events. A transport-reported delivery without an authenticated receipt
remains queued and retryable. Persist attempt count, bounded retry metadata,
destination identity and receipt reference/digest. No network sender runs here.

Record lifecycle transitions append-only, hash-link their history and include its
head in signed checkpoints. This history is local bookkeeping, not an automatically
requeued stream of receipt events that recursively generates more receipts.

Same event ID with identical caller content returns the original persisted event;
different content is a conflict. Compare caller content without regenerating local
sequence/time/hash fields. Repeated matching acknowledgements are idempotent;
wrong destination, event/hash binding or conflicting receipt information fails.
Future authenticated adapters provide receipts; this module does not establish
remote authenticity by accepting a receipt-shaped dictionary.

Retry identical event IDs and bytes after lost acknowledgements or restart. A
bounded batch API preserves ordering and does not starve ordinary records. Remote
deduplication remains a required receiver capability, not a local test guarantee.

Reconciliation findings append new source-attributed events linked to original
records, with their own evidence availability and freshness. A reconciliation
marker requires a linked finding and acknowledged delivery of the original; it
does not alter historical decisions or prevent additional findings. This slice
records supplied findings but does not calculate them. Acknowledgement never
authorizes deletion and cannot imply protected execution.

## Physical asset observations

User decision: the physical device will be configured with a sensor and relay what
physically happened. The sensor model, transport and driver are not selected here.

Represent three separate records:

1. ALICE execution attempt: exact command/request binding and authority interval.
2. Controller execution result: accepted/started/completed/failed/unknown report.
3. Sensor observation: measured property/value/unit, asset and sensor IDs, source
   event ID, observation time/confidence, freshness/quality, calibration identity
   where applicable, and evidence reference/digest.

Link command-related observations to the same action/execution ID. Permit
unsolicited observations with explicit correlation absence; do not invent a command
as the cause of physical movement. Distinguish actuator-reported feedback from an
independent sensor and identify simulated observations explicitly.

Before/during/after samples and tolerance/deadline comparisons belong to later
controller/observation integration. That integration must authenticate the relay,
preserve stable source IDs across retries and buffer results durably until recorded.
No feedback means unavailable/unknown, not successful motion. A later mismatch is
a new finding. Detailed traces stay in a bounded evidence store, with local DDIL
retention sufficient to resolve their references; that store is not implemented by
this slice. The ledger never claims an external evidence file exists merely because
its reference was recorded.

## Capacity and recovery

Require explicit database quota and recovery-reserve configuration. Account for
database allocation and transient journal needs, not just JSON payload bytes.
Configure bounded SQLite cache use and cap database growth. No automatic pruning,
compaction of original records, unbounded retry history or background worker.

Expose audit capacity/readiness and explicit storage, integrity and sealing errors.
Normal appends must stop before consuming reserve; a restricted recovery path may
use reserve for already admitted outcomes and failure/receipt records. Mission
integration must budget and reserve the bounded outcome writes before admitting
consequential work. A readiness check alone is not a reservation or execution grant.
This first component must document and test this boundary without claiming to
implement the absent admission or enforcement service.

| Failure | Required component response |
| --- | --- |
| Disk full/quota | Reject transaction without partial success; expose blocked capacity. Do not delete audit or silently discard ordinary events. |
| Read-only/lost storage/I/O failure | No durable success; mark writer unavailable. No in-memory or alternate-path success fallback. |
| USB removal | Non-removable ledger survives; missing required USB caches remain a separate readiness failure. No USB writer in this slice. |
| Crash/restart | Recover SQLite transaction state, validate chains/checkpoints/projections, restore pending outbox and reuse stable IDs. |
| Corruption/anchor mismatch | Refuse new writes; preserve files for investigation. No automatic truncation or history repair. |
| Lost append response | Query/retry original ID; recover committed result or append once if absent. |
| Duplicate delivery/lost ACK | Preserve ID/content, keep unacknowledged record retryable, accept repeated matching receipt once. |
| Missing/uncertain/backward time | Record uncertainty; sequence determines local ledger order. Boot-scoped monotonic time cannot prove cross-boot freshness. |
| Signing failure | Retain local events, report unsealed coverage and block readiness until sealing recovers. |

If storage is completely unavailable, the recorder cannot promise to record that
failure in the same failed store. It must report the error to its caller, which
must prevent new unauditable consequential actions. Already moving hardware and
safe-stop behavior require controller-specific integration, not a ledger heuristic.

## Files and verification scope

- Implement `dcamr/audit/audit_log.py` and a small separate signing module if needed
  to keep cryptographic adapters independent from storage.
- Add the versioned audit schema, focused `unittest` tests and bounded fixtures.
- Add pinned audit dependencies and a component usage/recovery guide.
- Preserve existing anomaly modules/contracts and empty reconciliation executor.
- Update relevant tracker rows as partial/component evidence only after tests pass.

Tests cover strict canonicalization, all event types, caller mutation isolation,
stable retry identity, sequence across reopen and competing writes, transactional
outbox creation, lifecycle legality, duplicate/lost acknowledgements, appended
findings and sensor provenance without historical rewrite. Verify Ed25519 with a
known vector plus altered-message/wrong-key/unknown-algorithm cases and substituted
signer interfaces. Exercise checkpoint boundaries, sealing failure, independent
anchor mismatch, malformed/tampered history and outbox projection disagreement.

Use temporary local databases for quota/reserve, failed-write and subprocess
crash/restart tests. Verify that failed persistence never returns durable success.
Separate injected filesystem failures from claims about actual USB/power-loss
hardware behavior. Run the existing full unittest suite and both anomaly/feature
replays, reporting actual pass/skip counts. Pi storage, power-loss, latency and
combined memory acceptance remain unmeasured until run on the target device.
