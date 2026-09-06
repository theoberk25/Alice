# Native technician review of live runtime holds

Updated 2026-09-06. Follow [working rules](../../AGENTS.md),
[technician integration](../integration/technician-console.md) and
[upstream console contract](../integration/upstream-alice.md).
This console-specific contract is not promoted into `common/`.

## Scope and authority

The existing Pi `FirstLightRuntime`, permission resolver, signed release, audit
ledger, HTTP/serial controller and Wazuh delivery remain authoritative. This
increment adds retained canonical request details and native review; it creates
no second service, database, hold queue or controller execution path.

An authenticated request whose exact verified grant requires approval and whose
assessment status is usable receives immutable `CHALLENGE` (shown as HOLD).
Missing permission, unverified identity and unusable assessment do not become
reviewable. Subsequent technician intent never rewrites the machine decision.

The current producer is still the **first-light OFFLINE runtime**: its authority
is an explicitly fixed confirmed OFFLINE interval and its contextual assessment
is fixture supplied. It does not implement endpoint fencing, enterprise ownership
transfer, general prohibitions/conditions or live model inference. Connectivity
cannot establish authority. Review requires current confirmed OFFLINE ALICE
ownership and the exact original decision authority/release; ONLINE and unknown
ownership are ineligible. No enterprise-owned execution is enabled.

Review is disabled unless the Pi is started with an explicit `--console-trust-file`.
Local development and mock-controller tests do not provision remote trust or
establish physical-Pi acceptance. Raw traffic visibility means collected ALICE
request/audit records, not every network packet.

## Transport and snapshots

The native boundary targets the existing authenticated loopback bridge, normally
reached through the configured authenticated SSH tunnel. Bearer credentials stay
outside renderer JavaScript. The bridge forwards only `GET /events?after=N`,
`GET /review/<request_id>` and `POST /review`, with no redirects or environment
proxy. Its bearer alone cannot authorize execution; the Pi verifies native proof.
The browser/Vite viewing proxy remains read-only and exposes no review writes.

`GET /review/<request_id>` returns a strict `alice-runtime-review-v1` object:

| Fields | Meaning |
| --- | --- |
| `request_id`, `request_sha256`, `request` | Canonical authenticated request identity/digest and original object; object is null if historical bytes are absent/corrupt. |
| `decision_event_id`, `decision_event_hash`, `decision` | Current immutable machine decision identity/hash/outcome. |
| `release_sha256`, `authority_interval_ref`, `runtime_epoch`, `review_nonce` | Current release, execution-authority interval (nullable when ineligible), process epoch and bounded review challenge. |
| `review_state`, `eligible`, `reason` | PENDING/APPROVED/REJECTED; explicit eligibility and bounded reason. PENDING does not by itself confer a capability. |
| `accepted_action_id`, `accepted_action` | Null before disposition; afterward the exact accepted action ID and APPROVE_ONCE/REJECT for acknowledgment reconciliation. |
| `execution_status` | NOT_EXECUTED, COMPLETED, FAILED or UNKNOWN, independently projected from execution events. |

Request details must pass the existing request schema and canonical hash even when
not reviewable. Historical records stay visible without inventing missing fields.
Reasons distinguish unavailable evidence, nonreviewable machine decision, absent
trust, nonlocal ownership, changed policy/authority, resolved review and conflicting
history. Nonces expire after 120 monotonic seconds, are issued only for eligible
requests, and retain at most 1,024 pending snapshot challenges. Eviction/expiry
requires a new snapshot and facial verification; it never extends authorization.

The derived Pi review index replays the existing ledger once in pages of 64, then
reads only its tail. It retains one compact projection per retained request plus
accepted action identity; it is rebuilt after restart and is never authoritative
storage or an independently managed hold queue. Memory scales with ledger history.

## Signed consent

Both APPROVE_ONCE and REJECT require a newly bound native `alice.live-face.v3`
facial verification. Enrollment rotates once; login/review match automatically.
The renderer selects intent/identifiers, never supplies camera proof, trust keys,
PASS assertions, request bytes or a signed envelope.

The strict envelope has exactly `proof` and base64 `signature`. Proof has exactly:

```
schema_version = alice-review-action-v1
console_id, technician_id, action_id, action
biometric_session_id, biometric_policy = alice.live-face.v3
issued_at, expires_at
request_id, request_sha256, decision_event_id, decision_event_hash
release_sha256, authority_interval_ref, runtime_epoch, review_nonce
```

Ed25519 signs `b"alice-native-review-v1\0" + canonical_bytes(proof)`.
Canonicalization is the existing `alice-json-v1`: compact sorted ASCII keys,
UTF-8 Unicode values, signed 64-bit integer numbers only, duplicate-key rejection,
maximum depth 16, 64 fields/items per container, strings at most 4,096 characters,
and total payload at most 16 KiB. No float coercion or Unicode normalization.

Proof issuance/expiry preserve the original successful face grant times; signing
or retrying must not extend them. Admission allows at most 60 seconds from issuance
and at most five seconds of positive clock skew. All request/decision/release/
authority/epoch/nonce bindings must match the current eligible Pi snapshot.
Each console's biometric session ID can admit only one action, including across
requests and restart; the proof evidence source retains that session identity.
Action IDs are unique globally and at most 120 characters so suffixed ledger
identities remain bounded. Identifiers begin with an ASCII alphanumeric character
and otherwise contain alphanumerics or `_.:-`.

Pi trust is strict `alice-console-trust-v1` JSON containing `consoles`, each with
`console_id`, lowercase raw Ed25519 `public_key` hex and unique `technician_ids`.
The file has the same 16 KiB JSON bound; malformed trust aborts startup before
controller acquisition. Missing trust disables review. Keys are provisioned only
through an explicit separate operation; no private key is distributed in source.

## Admission, cancellation and recovery

One runtime process owns a retained `runtime-owner.lock` file in the data directory.
A nonblocking OS lock refuses a competing runtime before it opens a controller;
inherited runtime objects cannot execute after fork. Thread review/request handling
uses the existing owner mutex. This local ownership guard is not endpoint fencing
or an enterprise handover protocol. Read-only ledger access remains available.

Pi writes the canonical signed envelope and the configured public key as immutable
existing-ledger evidence, then commits `TECHNICIAN_ACTION` before any controller
command. Its evidence references retain both digests for later verification.
A global action-ID collision, altered proof, stale snapshot, expired unaccepted
proof or second disposition cannot issue a command. REJECT issues none.

After durable admission, retries and restart only return recorded state; they
never reissue execution. A crash between admission and execution, or after command
but before result, may leave APPROVED with UNKNOWN execution. This is an explicit
reconciliation condition, not permission to retry. An identical previously admitted
signed envelope can retrieve its receipt after expiry; that readback grants no
new authority. Native recovery should use GET and compare `accepted_action_id`.

Native consumes authority before transport and durably retains the submission
identity for reconciliation. Cancelling an unused grant revokes it, including
after biometric success. Once transport begins, UI cancellation is not a claim
that delivery or execution was cancelled. A lost HTTP response requires checking
Pi history; it must never cause an automatic newly signed approval.

`alice-review-receipt-v1` has `action_id`, `request_id`, `status: ACCEPTED`,
`review_state`, `execution_status` and `idempotent_replay`.
ACCEPTED means Pi recorded consent. The existing correlated CONTROLLER_RECEIPT,
EXECUTION_RESULT and OBSERVED_STATE remain distinct immutable records; an
acknowledgment is not physical execution or observation evidence.

## Verification scope

`tests/test_technician_review.py` exercises real Ed25519 signatures, signed test
releases, the real ledger/runtime, a mock controller, concurrent reviewers,
process exclusion, stale bindings, restart, storage failures, signed evidence,
strict JSON, bridge HTTP and dropped acknowledgment. The public vector at
`tests/fixtures/runtime-review/golden.json` checks Python/Rust canonicalization
and signature compatibility without distributing its private key.
These automated tests do not qualify the face model, operate physical hardware,
prove actual network coverage, or establish camera → physical-Pi acceptance.
