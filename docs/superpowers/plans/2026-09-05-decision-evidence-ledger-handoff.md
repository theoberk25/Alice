# Decision Evidence Ledger — session handoff

**Stopping point:** user requested a clean checkpoint and a new session for final
review before context compaction. Implementation is present and tested; final
whole-branch review is still required. Do not restart design approval or represent
this checkpoint as completed live integration.

## Location and authority

- Checkout: `/Users/mereksoriano/Downloads/Claude_Code/DN_Hacks/Alice`.
- Local feature branch: `codex/decision-evidence-ledger-durable`.
- Base: `b1196370d9e6328c4cb821893d7a800f84940b33` (clean reviewed main; no subsequent changes at start).
- Existing `codex/decision-evidence-ledger` belongs to earlier design work at `89e6dfd`; leave it alone.
- Remote: `git@github.com:theoberk25/Alice.git`, not a repository owned by `mereksor`.
- No push, deploy or merge is authorized. The new branch is local only.
- Keep work in this Alice directory. Do not create another worktree without a new reason.
- The user explicitly confirmed that `docs/superpowers/specs/2026-09-05-decision-evidence-ledger-design.md` is the final approved design. Its old “awaiting approval” line is superseded by that confirmation.
- Plan: `docs/superpowers/plans/2026-09-05-decision-evidence-ledger.md`.
- Usage/recovery guide: `docs/decision-evidence-ledger.md`.
- Original request: `/Users/mereksoriano/.codex/attachments/ad0b87b2-204c-492f-b176-c388eb48e041/pasted-text.txt`.

The user’s latest implementation preference: **lean, modular, compatible scripts;
no functions or abstractions without a concrete purpose.** Keep meaningful trust,
contract and transaction boundaries; avoid speculative frameworks or unrelated ML
and console refactoring. The schema was deduplicated rather than creating a
runtime schema-generation framework.

## Implemented files and responsibilities

- `dcamr/audit/audit_log.py`: explicit initialize/open, SQLite transactions, event
  persistence, checkpoint orchestration, capacity/readiness, separate durable outbox.
- `dcamr/audit/validation.py`: streaming event/lifecycle/checkpoint validation and
  comparison with mutable outbox projections; independent anchor matching.
- `dcamr/audit/event_contract.py`: bounded integer-only canonical JSON, strict event
  validation, exact event hashes, local clock validation, compact contextual projection.
- `dcamr/audit/signing.py`: replaceable Signer/TrustStore interfaces and the only
  shipped concrete algorithm, Ed25519 using cryptography. Algorithm ID `ed25519`.
- `common/schemas/audit_event.json`: 15 strict local event families, independent of
  existing shared request/decision placeholders and workstation/cyber schemas.
- `requirements-audit.txt`: existing contract requirements plus cryptography 46.0.3.
- `tests/audit_fixtures.py`, `tests/test_audit_{contract,signing,log,outbox,integrity}.py`:
  bounded synthetic fixtures, real temporary SQLite files, failure and tamper checks.
- Relevant tracker rows only were updated to Partial component evidence. Totals:
  12 Done component, 34 Partial, 72 Planned; no end-to-end row promoted.

No anomaly, model training, reconciliation executor, console UI, controller, feed,
cache activation service or admission/enforcement implementation was changed.

## Checkpoint verification

Run on the local `.venv` using Python 3.13. The initially present environment lacked
training packages (148 discovered, 28 skipped). Pinned training requirements and
cryptography were installed into `.venv`; final run has **no skips**.

- `.venv/bin/python -m unittest discover -v`: **234 tests passed**, zero failures/errors/skips, 8.475 seconds on this Mac.
- `.venv/bin/python -m lab.replay_anomaly_fixtures`: **8 result fixtures and 7 score cases passed**.
- `.venv/bin/python -m lab.replay_feature_fixtures`: **5 feature vectors passed**.
- `git diff --check`: passed.
- Executed the Python example in `docs/decision-evidence-ledger.md`: passed.
- Temporary full-suite log: `/private/tmp/alice-ledger-checkpoint-tests.log`.
  Tests and counts above are retained here so resuming does not depend on that file.

The storage and contract functionality followed red/green test-first cycles.
Additional independent integrity tests verified actual signature tamper, rehashed
lifecycle tamper against signed checkpoint, alternate test-only signer, unknown
trust, SQLite read-only/denied inserts, noncanonical bytes and sequence gaps.
No actual USB, power-loss, sensor, Pi memory/latency or live integration acceptance
has run.

## Review findings and resolution

Independent focused reviews were performed alongside implementation/testing:

1. Filesystem exhaustion left readiness true: fixed by checking actual free space
   in readiness, with regression coverage.
2. Failed explicit partial seal was forgotten on reopen: fixed with one durable,
   hash-linked `SEAL_REQUESTED` transition before calling the signer. Restart blocks
   normal work until a successful checkpoint covers that pending request. Repeated
   signing failures reuse pending intent without adding unbounded transitions.
3. Matching ACK retry required new reserve capacity: fixed by validated read-only
   duplicate lookup before the write gate, plus serialized recheck for a new ACK.
   Review also reproduced success at actual quota exhaustion.
4. Runtime outbox tampering was missed by append’s idempotent path: fixed by external
   SQLite data-version validation in read snapshots; regression passes.
5. Contextual retained metadata admitted contradictory PRE/POST times and partial
   parsed identity: fixed by all-or-none parsed metadata, PRE cutoff=request time,
   POST request<=execution<=cutoff, and separate retained dispatch for parse failures.
6. RESOLVED attribution could have no actor: fixed to require known actor kind and
   actor ID, without inventing agent/user identities for SYSTEM actors.
7. Schema-valid opaque IDs containing `/` or `@` failed delivery methods: storage
   identifier checks aligned with schema; full append/seal/queue/ACK/reopen test passes.

Focused rereviews have **no open actionable findings**. Latest contract review
reran 36 focused tests; storage/signing rereview ran 15 focused tests plus targeted
quota and repeat-seal reproductions. Reports, if still present:
`/private/tmp/alice-ledger-contract-review.md`,
`/private/tmp/alice-ledger-storage-review.md`,
`/private/tmp/alice-ledger-contract-report.md`,
`/private/tmp/alice-ledger-signing-report.md`,
`/private/tmp/alice-ledger-integrity-tests-report.md`.

Final whole-branch review is deliberately deferred to the new session. The above
reviews are focused component reviews, not a substitute for that final gate.

## Scope decisions to preserve

- Recorder only. ONLINE enterprise directly executes; OFFLINE ALICE requires
  endpoint-enforced transfer. Network loss, a signed record or ACK grants nothing.
- 16 KiB canonical event bound, 16 evidence references, read/outbox batches <=64;
  checkpoint every64 events and explicit smaller sealing. Integers plus physical
  decimal strings; numeric ML values remain referenced original evidence.
- `contextual_projection` validates retained metadata/correspondence; it is not a
  second model-output computation validator. Original factors/source authenticity
  are not established by copying reported source IDs. Exact original bytes/digest
  remain referenced for review. Do not add a duplicate numeric inference validator.
- Compact in-memory model fingerprint is distinct from a top-level deployable
  artifact digest. Do not silently coerce those identities or infer a signed model.
- SQLite DELETE rollback journal, FULL synchronization, 2MiB page cache; serialized
  event+LOCAL transition+outbox commit. Quota conservatively counts database plus
  full journal and overhead. No automatic pruning or alternative store fallback.
- Normal versus restricted recovery budget is not an admission reservation.
  Readiness explicitly returns admission_reserved=False. Trusted future admission
  integration must budget outcome writes and prevent unauditable consequential work.
- Per-event attempt history is capped at64; exhaustion remains QUEUED/visible and
  raises rather than discarding or silently resetting. No transport scheduler exists.
- A controller receipt is not measured effect; observations identify actual source,
  time, unit, quality and command correlation or explicit unsolicited absence.
- Event and transition chains/checkpoints are tamper-evident under protected writer,
  filesystem and key assumptions. Whole-store rollback needs an independent anchor.
- Preserve local DDIL source history even with unavailable site storage or removed
  USB; larger on-premises storage is an assumption, not guaranteed connectivity.
- Production key provisioning, evidence retention, actual feed/receipt authentication,
  sensor drivers, enforcement, full reconciliation and Pi acceptance remain absent.

## Resume checklist

1. Read this handoff, approved spec, implementation plan and component guide.
2. Check current branch/status and changes since the checkpoint; preserve others’ work.
   Use `git log -3 --oneline` to identify the local checkpoint commit.
3. Perform a fresh **whole-branch review** against `b119637`, including untracked or
   subsequent work if any. Prioritize correctness and actual scope gaps; honor the
   lean-code preference. Do not restart design approval.
4. Fix any material review findings with reproducing tests first; do not refactor
   unrelated ML/console code or expand into excluded integrations.
5. Run the full unittest suite and both replays after any changes. Update tracker
   evidence and plan Task5 only with actual results.
6. Commit final reviewed work locally. Do not push, deploy or merge without explicit
   authorization. Report the branch and remaining integration/hardware limitations.
