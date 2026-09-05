# Decision Evidence Ledger Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver the first bounded durable local recorder, checkpoint and outbox component, without claiming admission or execution integration.

**Architecture:** Store canonical event bytes and separate append-only lifecycle transitions in SQLite rollback-journal transactions with FULL synchronization. Sign event and lifecycle heads with externally configured signers; validate history and projections on restart. Retain history regardless of upload progress.

**Tech Stack:** Python 3.11+, SQLite, jsonschema, pinned cryptography Ed25519 adapter.

**Spec:** docs/superpowers/specs/2026-09-05-decision-evidence-ledger-design.md (user confirmed this is the approved final document).

## Global Constraints

- Work in Alice on codex/decision-evidence-ledger-durable from b119637. No push, merge or deployment.
- Raspberry Pi 4 Model B, 2 GB RAM; component checks on Mac do not establish Pi acceptance.
- 16 KiB events, 16 evidence references, 64-record batches, checkpoint every 64 events; integers and decimal strings only.
- Non-removable local authoritative storage, explicit initialization versus opening; configurable quota and recovery reserve, no deletion.
- ONLINE enterprise owns execution; OFFLINE requires endpoint transfer; connection state, signatures and receipts never grant authority.
- Strict compact records, no prompts, biometric data, credentials or unrestricted payloads. External source trust is supplied by future adapters.
- Preserve original history, exact request binding, separate attempts/results/observations; contextual ML uses its own compact projection.
- Whole-store rollback detection requires an independent trusted anchor. Recorder readiness is not admission reservation.

## Task 1: Strict contract and compact contextual projection

Files: common/schemas/audit_event.json, dcamr/audit/event_contract.py, tests/test_audit_contract.py, tests/audit_fixtures.py.

Interfaces: canonical_bytes(value)->bytes (bounded JSON, no floats); parse_json(bytes)->object; validate_event(dict)->None; validate_input(dict)->None; event_hash(dict)->str. Input fields: event_id, event_type, correlation, attribution, authority, provenance, detail. Recorder adds schema_version='alice-audit-event-v1', canonicalization_version='alice-json-v1', ledger_id, node_id, sequence, time, previous_hash, event_hash, outbox_id=event_id, initial_state='LOCAL'. Correlation is a strict object with nullable correlation_id/request_id/request_sha256/assessment_id/action_id/execution_id/parent_event_id. Time is {recorded_at: UTC string|null, clock_source: ID, confidence: TRUSTED|UNCERTAIN|UNAVAILABLE, boot_id: ID, monotonic_ns: nonnegative integer}. Expose LedgerInputError(ValueError).

- [x] Write failing canonical byte, invalid type/depth/duplicate/Unicode/size, event family and binding tests. Example:
```python
self.assertEqual(canonical_bytes({'b': 2, 'a': 'é'}), b'{"a":"\xc3\xa9","b":2}')
with self.assertRaises(LedgerInputError):
    canonical_bytes({'score': 0.1})
```
- [x] Run `.venv/bin/python -m unittest tests.test_audit_contract` and observe missing behavior.
- [x] Implement strict schema and validation; explicit contextual projection keeps dispatch bindings independently of parse-derived IDs and never copies numeric factors/scores. Evidence reference binds original assessment bytes.
- [x] Rerun focused tests and review contract against every specified event family.

## Task 2: Replaceable trusted checkpoint signing

Files: dcamr/audit/signing.py, requirements-audit.txt, tests/test_audit_signing.py.

Interfaces: Signer protocol algorithm_id/key_id/sign(bytes)->bytes; TrustStore mapping (algorithm_id,key_id) to verifier objects exposing verify(signature, message), raises on failure; TrustStore.verify(algorithm_id,key_id,message,signature)->None. Ed25519Signer(private_key_bytes,key_id), Ed25519Verifier(public_key_bytes). SigningError and TrustError bounded exceptions. No keys stored in ledger.

- [x] Write RFC8032 known-vector test, changed-message/wrong-key/unknown algorithm or key tests and explicit substituted signer test.
```python
with self.assertRaises(TrustError):
    trust.verify('unknown', 'key', b'message', b'signature')
```
- [x] Run `.venv/bin/python -m unittest tests.test_audit_signing`, confirm red, then implement maintained-library adapter and pinned dependency.
- [x] Rerun focused tests. Review no algorithm fallback or ledger-installed trust.

## Task 3: Durable SQLite recorder, validation and signed sealing

Files: dcamr/audit/audit_log.py, optionally dcamr/audit/storage.py and dcamr/audit/validation.py; tests/test_audit_log.py.

Interfaces: AuditLog.initialize(path, ledger_id, node_id, quota_bytes, reserve_bytes, signer, trust, clock); AuditLog.open(path, signer, trust, clock, anchor=None); append(input, recovery=False)->AppendResult(event, persisted, covered_sequence, sealing_error); read(after=0,limit=64); seal()->checkpoint; validate(anchor=None)->ValidationReport; readiness()->dict; close(). Clock callable returns the contract time object. Initialization never replaces a file. Public reads return copies.

- [x] Write temp-database tests before implementation: append/reopen/idempotent retry/conflict, multiple writers, mutation isolation, missing open, uncertainty/backward time, hash/sequence/canonical tamper, trigger protection, signed boundaries and anchored truncation.
```python
first = ledger.append(event)
ledger.close()
ledger = AuditLog.open(path, signer=signer, trust=trust, clock=clock)
self.assertEqual(ledger.append(event).event, first.event)
```
- [x] Run focused tests red; implement serialized BEGIN IMMEDIATE event+LOCAL transition+projection commits. Use FULL sync, DELETE journal, bounded cache and max_page_count, conservative journal-inclusive quota accounting; unavailable file identity refuses success.
- [x] Add tests for signer failure after the 64th event (persisted/unsealed), seal recovery, transaction rollback, quota/reserve and subprocess crash/restart. Implement separate checkpoint transaction binding event head, transition head and previous checkpoint digest; validate signatures before writes after open.
- [x] Validate by streaming bounded rows and SQL projection reconstruction/comparison, not unbounded Python history. Reject integrity errors without repair. Independent anchors must exist and match verified checkpoint bytes.

## Task 4: Durable delivery and history preservation

Files: dcamr/audit/audit_log.py, tests/test_audit_outbox.py.

Interfaces: queue(event_id,destination), pending(limit=64,after=0), record_attempt(event_id,retry_after_ms,error_code), acknowledge(event_id,destination,event_hash,receipt_ref,receipt_sha256), reconcile(event_id,finding_event_id). Lifecycle: LOCAL -> SEALED -> QUEUED -> ACKNOWLEDGED -> RECONCILED. Repeat identical operations are idempotent; conflicting receipts fail. No network sender.

- [x] Write failing lifecycle tests, including unsigned queue rejection, wrong ACK binding, attempts and lost ACK across restart, FIFO bounded batches, linked finding requirement and original bytes preservation.
```python
ledger.queue(event_id, 'enterprise')
ledger.record_attempt(event_id, retry_after_ms=1000, error_code=None)
self.assertEqual(ledger.pending()[0]['state'], 'QUEUED')
```
- [x] Implement transactional hash-linked transitions and projection updates, with bounded retry count/history by explicit attempt ceiling (exhaustion remains QUEUED and observable). Sealing includes prior transitions and creates SEALED transitions in the same signed transaction.
- [x] Add projection tamper/restart and signed lifecycle tamper tests; rerun focused tests.

## Task 5: Review, complete verification and component documentation

Files: docs/decision-evidence-ledger.md, docs/implementation-tracker.md, plan checkboxes.

- [ ] Review requirement-to-test coverage and dispatch independent code review; fix material issues with regression tests first.
- [x] Run `.venv/bin/python -m unittest discover -v`, `.venv/bin/python -m lab.replay_anomaly_fixtures`, `.venv/bin/python -m lab.replay_feature_fixtures`, and `git diff --check`. Require training dependencies for no skips.
- [x] Document initialization/open, trust provisioning boundary, capacity formula/reserve limits, recovery, sealing failures, ACK trust prerequisite, anchored rollback limits and simulated failure scope. Provide runnable local example without provisioning production keys.
- [x] Update only relevant tracker rows with component evidence; leave actual adapters/enforcement/hardware acceptance pending. Record measured test counts and preserve all original task labels.
- [ ] Commit reviewed feature locally and report branch, tests and residual integration limits. Do not push, deploy or merge.

## Execution record

- Source reviewed: approved spec, all requested project documents; audit and reconciliation files empty; existing contextual and console contracts remain separate.
- Baseline on current .venv: 148 discovered, 28 training skips. Restore pinned training dependencies before final verification.
- User requested this checkout; branch isolation used without another worktree.
- Shared interfaces checked: Task 1 event/time shape consumed by Tasks 3/4; Task 2 sign/trust interface consumed by Task 3; Task 4 transitions included in Task 3 checkpoints. Storage writer remains owned by coordinator to avoid shared-file concurrent edits.

- Checkpoint at user request: implementation Tasks 1–4 are complete; 234 full-suite tests pass with zero skips and both cyber replays pass. Focused independent contract/signing/storage reviews are resolved. Final whole-branch review is deferred to the next session; do not imply finished feature acceptance.
- Lean-code preference: preserve four focused modules, avoid speculative abstractions and unrelated changes. Deduplicated schema identifier/digest constraints reduced the schema from 1,799 to 596 lines without changing validation.
- See `docs/superpowers/plans/2026-09-05-decision-evidence-ledger-handoff.md` for the exact resume checklist, review findings, commands, compatibility boundaries and original request path.
