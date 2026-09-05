# Local Decision Evidence Ledger

The first durable ledger is a **recorder component**, centered on
`dcamr/audit/audit_log.py`. It stores canonical events, Ed25519 checkpoints and
separate delivery bookkeeping in a local SQLite database. It does not receive live
requests, authenticate enterprise feeds, admit actions, execute commands, enforce
authority transfer, send uploads or compute reconciliation findings.

Use Python 3.11+ and `pip install -r requirements-audit.txt`. The audit dependency
set includes the existing contract dependency and pinned `cryptography==46.0.3`.
Training dependencies remain separate and are not required by the ledger.

## Local usage

Provision a protected **non-removable** parent directory. `initialize` exclusively
creates a new file; `open` requires an existing store and validates it before use.
An absent, corrupt or untrusted existing store is never replaced automatically.
The caller supplies a signer, historical verification keys and a clock provider.
Production key provisioning and detecting the physical mount type are deployment
responsibilities; a pathname alone cannot establish non-removable storage.

This runnable example uses a temporary directory, ephemeral test key and explicitly
synthetic request fixture. It exercises storage only, and creates no controller or
enterprise connection. Run from the Alice root:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from dcamr.audit.audit_log import AuditLog
from dcamr.audit.signing import Ed25519Signer, Ed25519Verifier, TrustStore
from tests.audit_fixtures import event, clock

key = Ed25519PrivateKey.generate()
signer = Ed25519Signer(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()), 'lab-key')
trust = TrustStore({('ed25519', 'lab-key'): Ed25519Verifier(
    key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))})
options = dict(signer=signer, trust=trust, clock=clock)
with TemporaryDirectory() as directory:
    path = Path(directory) / 'ledger.sqlite'
    ledger = AuditLog.initialize(path, ledger_id='lab-ledger', node_id='lab-node',
        quota_bytes=8 * 1024 * 1024, reserve_bytes=256 * 1024, **options)
    result = ledger.append(event())
    assert result.persisted and result.covered_sequence == 0
    checkpoint = ledger.seal()
    ledger.queue('event-1', 'lab-destination')
    ledger.record_attempt('event-1', retry_after_ms=1000, error_code='ACK_LOST')
    assert ledger.pending()[0]['state'] == 'QUEUED'
    ledger.close()
    ledger = AuditLog.open(path, anchor=checkpoint, **options)
    assert ledger.append(event()).event == result.event
    assert ledger.validate().covered_sequence == 1
    ledger.close()
```

The fixture clock is intentionally fixed. A deployment clock provider returns
`recorded_at` (UTC ending in `Z`, or null), `clock_source`, `confidence`
(`TRUSTED`, `UNCERTAIN`, `UNAVAILABLE`), `boot_id`, and integer `monotonic_ns`.
Null timestamps require `UNAVAILABLE`. Backward or uncertain wall time is retained;
sequence determines local order. A boot-scoped monotonic value cannot establish
freshness across restarts. Clock trust and backward-clock detection are supplied
by the caller, not inferred by this recorder.

## Event and evidence boundary

[`audit_event.json`](../common/schemas/audit_event.json) is an independently
versioned **local** contract. It does not replace the empty shared request/decision
schemas, the cyber anomaly schema or the workstation's contracts. `validate_input`
accepts exactly these caller fields:

| Field | Meaning |
| --- | --- |
| `event_id`, `event_type` | Stable caller retry identity and event family. |
| `correlation` | Nullable correlation/request/digest/assessment/action/execution/parent identities; required relationships depend on family. |
| `attribution` | Actor, requester, agent, responsible user/delegator, technician and assignment source; unresolved attribution is explicit. |
| `authority` | Product mode, connectivity, owner, interval and confirmation captured with the event. These remain supplied claims. |
| `provenance` | Policy, baseline, model, calibration, snapshot identities with explicit absence reasons, plus bounded evidence references and source metadata. |
| `detail` | Strict family-specific outcome, intent, reasons, observation or lineage; no arbitrary payload. |

The writer adds ledger/node identity, positive contiguous sequence, local time,
versions, predecessor/event hashes and the original `LOCAL` outbox binding.
Successful append means the event **and** initial delivery transition/projection
committed together. Retrying the same event ID and identical caller content returns
the original event, without regenerating its time or sequence. Different content
under that ID raises `IdempotencyConflict`.

Supported families: REQUEST (received/admitted), REJECTION, ASSESSMENT, DECISION,
CONTEXT_CHALLENGE, CONTEXT_RESPONSE, TECHNICIAN_ACTION, EXECUTION_ATTEMPT,
CONTROLLER_RECEIPT, EXECUTION_RESULT, OBSERVED_STATE, AUTHORITY_TRANSITION,
CACHE_ACTIVATION, RECONCILIATION_FINDING and RECORDER_FAILURE. Parent links must
reference earlier local history. Findings bind the original ID and event hash.
Additional findings append new records; they never change the original event.

Physical outcomes remain three separate records: execution attempt, controller
receipt/result and sensor observation. Observations retain asset/sensor/source IDs,
source-event identity, time/confidence, decimal-string value, units, quality,
simulation/independence label and evidence reference. Command-related observations
use the action/execution binding; unsolicited observations state correlation
absence. Missing feedback is unknown, not a successful physical effect. Calibration
identity can be carried by the provenance calibration slot.

Canonicalization `alice-json-v1` uses UTF-8 JSON, sorted ASCII keys and compact
separators, preserving Unicode values without normalization and preserving array
order. Reason-code sets are sorted and unique. Hashes use SHA-256 with the domain
`alice-audit-event-v1` followed by a zero byte, over canonical event fields excluding
only `event_hash`. Integers are signed 64-bit, with narrower nonnegative limits
where defined. JSON floats, duplicate keys, malformed Unicode, unknown fields and
excessive depth/aggregate size are rejected. Events are at most **16 KiB**, evidence
references at most **16**, and read/outbox pages at most **64** records.

No raw prompts, unrestricted explanations, credentials, keys, biometric material or
sensor streams belong here. The structural contract limits fields but cannot
recognize every sensitive string a caller might misuse as an identifier. Evidence
references are opaque identities, never fetch instructions. The recorder does not
store the referenced files or prove they exist. A future evidence store must retain
them locally through DDIL with appropriate access and capacity controls.

### Contextual ML compatibility

`event_contract.contextual_projection(assessment_bytes, dispatch=..., evidence_ref=...)`
returns an ASSESSMENT `detail` object. It preserves PRE_ACTION/POST_ACTION,
observation identity, exact context, source IDs, profile/input digests, model ID and
fingerprint, calibration digest, status, reasons and timing. The dispatch contains
`assessment_id`, `request_id`, `request_sha256`, `input_sha256`, `execution_id`,
`profile_sha256`, and `phase`. Independently captured dispatch identity remains
separate from parsed observation identity, including when parse failures leave the
latter null. The event correlation must match dispatch, and its evidence list must
bind the exact assessment reference/digest.

The full assessment bytes are bounded to 16 KiB for this projection. Numeric scores
and factors are excluded from the ledger projection and retained only through that
original evidence digest. Oversized assessments must use a separately bounded
reference representation rather than silently truncating facts. The projection is
not a cyber anomaly envelope or an authoritative decision adapter. Training ranges
are observations, model scores are not permissions, and an in-memory fingerprint
is not a signed deployable artifact. Existing ML computation remains unchanged. Top-level artifact provenance slots
remain separate from the compact in-memory model fingerprint; a missing deployable
artifact does not erase an available in-memory assessment identity. Source IDs are
the reported assessment metadata; factor authenticity and model computation are not
revalidated by this compact projection.

## Checkpoints and delivery

Every 64 committed events triggers sealing; `seal()` explicitly covers a smaller
batch, or later delivery transitions without new events. Recovery-only appends can
extend a backlog; each seal covers at most the next 64 events, so repeat sealing
until the desired range is covered. A durable `SEAL_REQUESTED` transition retains
failed partial-seal intent across restart. No fallback algorithm or unsigned
checkpoint is used. After event commit, `AppendResult` distinguishes `persisted`,
`covered_sequence` and `sealing_error`. A sealing error does not erase that event.
New normal work is blocked while a requested seal is pending or a full interval
is unsealed; recovery writes are still subject to their reserve.

Checkpoints sign ledger/node identity, sequence/head, prior checkpoint digest,
algorithm/key identity, time/confidence and the hash-linked delivery-transition
head. `TrustStore` resolves only externally configured `(algorithm_id, key_id)`
pairs. Keep historical keys available for old checkpoints. A replacement signer
and verifier can implement the interfaces, but this slice ships only Ed25519;
replacement is explicit configuration, not automatic downgrade after failure.
Private keys are never written to the ledger. Keep production key material outside
the ledger/evidence directory and protect the writer and trust configuration.

| API/state | Behavior |
| --- | --- |
| `append` → LOCAL | Durable event plus initial transition/projection; not necessarily signed yet. |
| `seal` → SEALED | Verified signed checkpoint covers the event; unchanged original bytes. |
| `queue(event_id, destination)` → QUEUED | Requires checkpoint coverage and fixes destination. |
| `pending(after=0, limit=64)` | FIFO by event sequence; includes stable event/hash identity and durable retry metadata. No sender runs. |
| `record_attempt(..., retry_after_ms, error_code)` | Remains QUEUED regardless of transport success without ACK. Delay 0–86,400,000 ms; at most 64 attempts per event. |
| `acknowledge(..., destination, event_hash, receipt_ref, receipt_sha256)` → ACKNOWLEDGED | Requires exact identity and supplied receipt binding. Matching repeated ACK is read-only even at full reserve; conflicts fail. |
| `reconcile(event_id, finding_event_id)` → RECONCILED | Requires original ACK and a locally appended linked finding. Additional findings remain separate events. |

Attempt exhaustion leaves the event queued and visible; further attempt recording
raises `LifecycleError`. There is no silent reset, unbounded retry history or claim
that all deliveries succeed. A later transport/operations integration must establish
an explicit recovery policy. `retry_after_ms` is a recorded backoff duration, not a
trusted cross-boot deadline. The future sender schedules it and authenticates ACKs.
A receipt-shaped dictionary alone establishes neither remote authenticity nor
execution. Remote deduplication is a required receiver capability. Acknowledgement
never authorizes local deletion. Delivery bookkeeping itself is not requeued as a
new deliverable event, avoiding recursive receipt generation.

## Capacity, recovery and trust assumptions

Explicit quota/reserve settings are persisted at initialization. The initial quota
minimum is 256 KiB, reserve minimum 64 KiB, and at least 128 KiB remains outside the
reserve. Choose substantially larger budgets for real DDIL duration/volume; these
are parser/configuration floors, not operational recommendations. This slice does
not migrate quota configuration on an existing database.

SQLite uses serialized `BEGIN IMMEDIATE` writes, rollback journaling (`DELETE`),
`FULL` synchronization, a 2 MiB page cache and file-backed temporary storage. The
conservative allocation estimate is `page_count * (2 * page_size + 8) + 65536` bytes:
one full database copy, one full journal copy, page framing and fixed overhead.
`max_page_count` constrains growth per transaction. Normal writes stay below quota
minus reserve; recovery writes may use total quota. Free-space checks also budget
another database-sized journal plus overhead. These checks do not reserve disk
against other processes or include separately stored evidence, filesystem snapshots
or arbitrary directory files. A SQLite full/I/O/commit failure remains authoritative.

Recovery appends are restricted to controller receipts, execution results,
observations and recorder failures. Acknowledgement and sealing may use reserve.
This is a recorder privilege boundary, **not a reservation for an admitted action**;
the future trusted admission service must budget outcome writes before starting
consequential work and restrict callers who can select recovery mode. The ledger
cannot stop already moving hardware or provide a controller safe-stop procedure.

`readiness()` reports local storage/capacity/sealing status and explicitly returns
`admission_reserved=False`. It does not grant execution. A caller must not silently
continue consequential actions after a recorder failure. When the store itself is
lost, recording that loss in the same store is impossible; the error must reach the
caller. No in-memory or alternate-path success fallback is used.

Opening streams schema/canonical/hash/sequence/identity checks, validates trusted
checkpoint signatures and compares outbox projections to transition history.
Ordinary SQL updates/deletes to event, transition, checkpoint and metadata history
are rejected by triggers. File replacement/loss blocks the open writer; external
SQLite changes trigger validation before further reads/writes. Corruption is
preserved for investigation, never automatically truncated or repaired.

This is **tamper-evident under protected storage/writer/key assumptions**, not
tamper-proof. Direct file access can bypass triggers. Signatures attest recorded
bytes, not their physical truth. Unsealed event and lifecycle tails have weaker
protection. `validate()` reports both covered sequences. Provide an independently
retained trusted checkpoint envelope as `anchor` to detect truncation/rollback
conflicting with it. Rolling back the entire database and all its checkpoints may
be undetectable without that independent anchor.

USB removal does not affect the local ledger; any required cache lost with USB is
a separate readiness failure for future integration. Site storage is likely
available on premises (for example at a military base), but is not assumed reachable
during DDIL. USB capacity does not define retention, and this slice never deletes
local source history or depends on site storage to commit.

## Verification scope

Run the existing contextual model through the ledger locally with:

```sh
.venv/bin/python -m pip install -r requirements-audit.txt -r requirements-anomaly-training.txt
.venv/bin/python -m lab.replay_contextual_ledger
```

This replay fits small PRE_ACTION and POST_ACTION models from the existing
unitless synthetic test fixtures. It records six real assessment outcomes: scored
PRE/POST, untrained model, unseen context, missing telemetry and invalid input.
Independent dispatch bindings survive failed input parsing. Exact assessment bytes
retain numeric scores/factors; the compact ledger records their evidence digest.

The replay explicitly seals and queues the six records, reopens with the signed
checkpoint as an anchor, retries the same event IDs, and checks original events,
coverage, evidence digests and pending delivery. It uses a disposable test key and
temporary directory that is removed on exit. Its evidence files are test artifacts,
not a production evidence store. No upload, permissions decision or physical action
runs, and the models are not ESP operating baselines. The integration test is
`tests/test_contextual_ledger.py`; core model and ledger implementations are unchanged.

Focused tests use real temporary SQLite databases, known Ed25519 vectors, controlled
write failures and subprocess exits. They cover canonicalization, event families,
context projection, durable retry/restart, competing connections, sealing/trust,
anchors/tamper, delivery/ACK/reconciliation, reserve exhaustion and lost storage.
Simulated USB removal and process crashes are component tests; they are not Pi
power-loss, physical-media or actual sensor acceptance.

Run `.venv/bin/python -m unittest discover -v` with the pinned training dependencies
installed to avoid skipping the existing model tests. Run both
`lab.replay_anomaly_fixtures` and `lab.replay_feature_fixtures`. Actual counts are in
the [implementation tracker](implementation-tracker.md). Pi 4 Model B (2 GB RAM)
latency, combined memory, physical power-loss behavior and live system integration
remain unmeasured.
