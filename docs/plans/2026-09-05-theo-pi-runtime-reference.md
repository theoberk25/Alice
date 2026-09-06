# ALICE — Raspberry Pi runtime software plan

## Context

ALICE/DCAMR is a Zero-Trust gate for autonomous-agent actions. Today the repo
(`/Users/theo/Desktop/DNHacks/Alice`) has **only the anomaly slice implemented**
(`dcamr/anomaly_engine/*` + 3 schemas); every other Pi component is a 0-byte
skeleton (`policy_engine`, `decision_model`, `challenge`, `evidence`,
`enforcement_gateway`, `packages/loader`+`package_verifier`, `provenance`, `audit`,
`state`, `reconcile`, `api`, `main`, `common/protocol.py`, and the 5 empty schemas).

This plan builds **the full Pi runtime** — intake of agent actions, translation to a
compact internal form, permission checks, ML scoring, fusion into a decision, and
translation of the output to every destination — wired around the existing anomaly
slice, tuned for a **Pi 4B / 2 GB / OS Lite** (budgets: p95 ≤100 ms @1 req/s,
steady RSS ≤256 MiB, peak ≤384 MiB, ≤5 s start).

### Locked decisions (from user)
1. **Serialization:** most RAM/latency-efficient for a Pi 4B → **codebook indices +
   CBOR at rest/wire; native frozen structs in-core; canonical JSON only as a
   derived human/console projection.** One swappable codec module.
2. **ML on Pi:** most efficient → **pure-Python exported-forest scorer** (no
   numpy/sklearn on the Pi; no pickle/joblib). Trees exported on the Mac to a
   hash-verified array artifact; Pi runs a dependency-free traversal reproducing
   `score_samples`, then the existing `normal_tail_rank_v1` calibration.
3. **Scope:** **full two-mode.** ONLINE = **logging only** (ingest activity feed,
   append + upload audit; **pull + cache signed policy to the drive**). OFFLINE = **full
   pipeline** (evaluate + log) from the cached policy. Plus a simulated single-authority
   transfer/fence between modes.
4. **Intake:** **Generic + MCP + A2A** adapters → one normalized intermediate.

### Non-negotiable invariants (from PRDs — carry into every module)
- Hard prohibition → `DENY` **without** invoking the model or any override; model
  unavailability must not block that denial.
- Low anomaly never grants permission; a model failure yields `null` score +
  `UNKNOWN` (never fallback-zero). No `risk_score`/`confidence` invented.
- Missing/expired cache, model, ownership, or audit capacity → **fail-closed**
  (blocked state), never an allow path.
- Never rewrite a decision; reassessment/reconciliation are **appended** immutable
  records linked by `previous_*`/`root_*` ids.
- Agent input is untrusted data; match the existing strict house style (frozen
  slotted dataclasses, bounded sizes, dup-key/non-finite rejection, `ContractError`
  with no payload echo, jsonschema 2020-12).
- **Liveness is security (#1):** a *hung* enforcing process is a failure equal to a
  crash — a watchdog must force it back to fail-closed. Fail-closed covers a blocked
  thread, not just missing prerequisites.
- **Durable-before-consequential (#7):** no enforcing action executes until its intent is
  fsync'd to the WAL; a power cut mid-pipeline must yield a bounded audit record on
  restart (outcome `UNKNOWN`, reconciled), never a silent executed-but-unaudited decision.
- **Time is attested, not assumed (#6):** in OFFLINE (no NTP) every decision/audit record
  carries `time_source` + `clock_uncertainty`; freshness checks fail-closed when
  uncertainty exceeds the window.

## Reuse (do NOT rebuild)
- `dcamr/anomaly_engine/{features,scoring,baseline,sequence,contract,feature_*}.py`
  — the feature builder, `normal_tail_rank_v1` scorer, baseline loader, strict
  result contract, and `EvaluationBinding`. The runtime **calls** these.
- `common/schemas/anomaly_result.json`, `anomaly_baseline.json`,
  `anomaly_feature_input.json` — the L2 I/O contracts.
- `lab/*` (Mac) — training/replay/compare harness; add the forest exporter here.
- Fill the empty `dcamr/anomaly_engine/anomaly_engine.py` as the live L2 adapter
  boundary (loads exported forest + calibration, builds features, emits a validated
  `anomaly_result`, honors `EvaluationBinding`).

## Architecture — the OFFLINE pipeline (module → responsibility)

Stage-by-stage; each maps to a currently-empty file. Data moves as native frozen
structs (R2); CBOR/codebook only at boundaries and audit.

| # | Stage | Module(s) to build | Notes / efficiency |
|---|---|---|---|
| 1 | **Intake + translate** | `dcamr/intake/adapters/{generic,mcp,a2a}.py`, `dcamr/intake/normalize.py` (new pkg) | Each adapter maps its envelope → one normalized action `(principal, action, target, args, evidence_refs, sig)`. Parse agent JSON once (stdlib `json`, C-accel). |
| 2 | **Codebook resolve** | `common/codebook.py` (new) | Resolve action/agent/target/rule strings → integer indices into the **signed package version**. Out-of-vocabulary = reject (free security check). This is the RAM/disk win. |
| 3 | **Normalize + canonical hash** | `dcamr/intake/normalize.py`, `common/codec.py` (new) | Freeze canonical serialization (resolves the OPEN item): `request_sha256 = SHA-256(codec.encode(normalized_body))`. Bind exact params/target/history snapshot. |
| 4 | **Identity/attribution** | `dcamr/identity.py` (new) | Resolve agent → responsible user → mission from the **permissions cache**; preserve unresolved attribution explicitly (never from agent prose). |
| 5 | **Permissions (L1)** | `dcamr/policy_engine/policy_engine.py`, `rules.py` | Deterministic allowed/review-required/prohibited over codebook indices (O(1) table lookup / bitmask). Hard prohibition → `DENY`, short-circuit (`SKIPPED`/`POLICY_DENY_SHORT_CIRCUIT`), model call count 0. |
| 6 | **Readiness/ownership** | `dcamr/state/ownership.py` (new), `state/local_cache.py` | Confirm ALICE holds execution authority + usable caches/model + audit capacity. Missing → fail-closed blocked. |
| 7 | **Features + L2** | `dcamr/anomaly_engine/anomaly_engine.py` (fill) + reuse `features`/`scoring` | Build 11-feature `cyber-behavior-v1` vector from cache+history; run pure-Python forest; emit validated `anomaly_result` under `raw_decision.anomaly`. |
| 8 | **Evidence** | `dcamr/evidence/evidence_interface.py` + schema `evidence.json` | Verify agent-referenced evidence against cached SIEM/EDR; record present/stale/unverifiable/contradicted. Presence ≠ authenticity. |
| 9 | **Fusion (4 states)** | `dcamr/decision_model.py` | Combine L1+L2+evidence+context → `ALLOW/REQUEST_CONTEXT/HOLD/DENY` per the PRD fusion table. No risk formula. Precedence invariants above. |
| 10 | **Challenge loop** | `dcamr/challenge/challenge.py` + schema `challenge.json` | Bounded, schema-only context round(s); pin original behavioral snapshot; increment `context_attempt`; re-eval → new immutable assessment linked by `previous_evaluation_id`. Hard policy never enters loop. |
| 11 | **Provenance + decision record** | `dcamr/provenance/provenance.py` + schema `decision_record.json` | Assemble outer immutable record (embeds anomaly under `raw_decision.anomaly`); capture sources/versions/attribution/reason codes. |
| 12 | **Enforcement (translate out)** | `dcamr/enforcement/enforcement_gateway.py`, `protected_systems/{firewall_sim,web01/host_sim}.py` | Only a currently-authorized exact request → target-native command; idempotent execution binding; capture receipt/completion/observed-effect **separately**. |
| 13 | **Audit** | `dcamr/audit/audit_log.py`, `dcamr/audit/wal.py` (new) | Append-only hash-chained **CBOR** + periodic signed checkpoints; **intent WAL fdatasync'd before any enforcing action** (#7); **local audit-append full → fail-closed block**, but **upload-outbox full ≠ block eval** (#9). Per-request fsync only on the execute path; other appends group-commit. |

### Per-stage latency budget (#3) — target internal p95 ≤ 75 ms, ≥ 25 ms headroom under the 100 ms SLO

Each stage records its own `monotonic_ns` delta into the decision/audit record, so an
overrun is attributable to a stage instead of discovered only at the aggregate p95.

| Stage | Budget (ms, p95) | Notes |
|---|---|---|
| 1 Intake + translate (incl. byte cap + `json`) | 8 | after the ≤64 KiB read cap |
| 2 Codebook resolve | 3 | O(1) table lookups |
| 3 Normalize + canonical hash (CBOR encode + SHA-256) | 8 | ~40 B records; C-accel cbor2 |
| 4 Identity/attribution | 3 | cache lookup |
| 5 Permissions L1 | 2 | O(1) table / bitmask; hard-prohibition short-circuits earlier |
| 6 Readiness/ownership | 2 | cached flags |
| 7 Features + L2 forest traversal | **20** | dominant stage — pure-Python forest; watch closely |
| 8 Evidence | 5 | cached SIEM/EDR lookups |
| 9 Fusion | 2 | table logic, no float model |
| 11 Provenance + decision record | 5 | assemble + encode |
| 13 Audit append | 6 | group-commit; non-execute path |
| **Core subtotal** | **~64** | non-enforcing request |
| 12 Enforcement (execute path only, incl. intent-WAL `fdatasync`) | +10 | conditional — only on ALLOW+execute |
| 10 Challenge loop | off hot path | only on `REQUEST_CONTEXT`; a *new* bounded re-eval, not inline |

Enforcing requests target **~74 ms**; the WAL fsync (the one unavoidably slow op) lands
only on that rare path. If any stage exceeds budget on the Pi, tune before deploy;
stage 7 is the first suspect.

Cross-cutting: `dcamr/main.py` orchestrator; `common/protocol.py` (normalized
structs + record dataclasses); `common/codec.py` + `common/codebook.py`; `api/dashboard_api.py` (emit decisions/status to console).

## Modes, authority, and the ONLINE (log-only) path
- `dcamr/mode.py` (new): current mode + execution-owner state machine. Simulated
  **fence/lease** so enterprise and ALICE can never both execute; failed/ambiguous
  transfer → block. Bind commands/approvals to their authority interval.
- **ONLINE (log-only):** the Pi **pulls** signed policy packages from a **cloud policy
  endpoint** (`cloud/policy_pull.py`, new) over a cert-pinned channel, then **verifies the
  Ed25519 signature + digest before caching to the policy cache drive and activating**
  (transport TLS is not trust — the signature is; see packages below). `cloud/feed_ingest.py`
  (new) ingests the authenticated activity feed (event ids, cursors, coverage/gaps) →
  audit; `cloud/uploader.py` (new) drains the outbox idempotently. No local evaluation.
  The **enterprise SIEM/EDR are evidence sources on a *separate* channel**
  (`cloud/{siem,edr}_connector.py`) — never a policy authority, so a compromised feed can
  never change rules. (Simulated enterprise SIEM incoming — see integration seams.)
- **OFFLINE:** full pipeline (stages 1–13).
- **Reconnection:** `dcamr/reconcile/reconciliation.py` — append verified/not-found/
  contradicted findings (never rewrite); fenced handback; resume uploads.

## Trusted inputs — packages (the codebook source)
- Schemas: fill `common/schemas/package_manifest.json`; add `permissions.json`
  schema; reuse `anomaly_baseline.json`. Package tooling `packages/tooling/
  {sign_package,verify_package}.py` (**Ed25519 via PyNaCl**, detached sig over canonical
  bytes; sign on the Mac, verify on the Pi at activate-time only — off the hot path, #4).
- `dcamr/packages/{loader,package_verifier}.py`: verify signature/issuer/expiry +
  content digest, **stage → validate fully → atomic activate**, keep last-known-good,
  expose rejection reason. On activation, **build the codebook** (`common/codebook.py`)
  and the L2 baseline maps. Agent-provided `verified=true` never trusted.
- **Distribution = pull, not push (this session):** in ONLINE the Pi fetches the signed
  package from the cloud policy endpoint and writes it to the policy cache drive; in
  OFFLINE it loads/activates **only** from that cached, signature-verified copy. Network
  down → keep last-known-good (never an allow path). The **loader/verifier is the single
  trust seam**: whoever writes the drive (incl. Merek/Jared's cacher), the Pi re-verifies
  signature + digest before activation — a tampered/partial cache is rejected.
- **USB layout & isolation — mechanism, not convention (#8):** signed inputs and audit
  live on **separate partitions with enforced mount flags**, not shared directories.
  - **Inputs** (`permissions/ normal_behavior/` + manifests) → mounted
    **`ro,noexec,nosuid,nodev`**. Audit code physically cannot write here, so an audit
    bug can never mutate the signed input hash set. Startup **verifies the mount is
    actually `ro`** (parse `/proc/mounts`) and **fail-closes** if writable.
  - **Audit** (`audit_logs/` + WAL + outbox) → a **separate `rw` partition** (separate
    device if the reader allows), so disk-full on audit cannot touch inputs.
  - **Feed credential (#10):** **not** on the signed-package USB — else one USB
    compromise = package-tamper surface **and** feed access. Store on a distinct secrets
    location (separate partition/device, mode `0600`, service-user owned), loaded **only**
    when in/entering ONLINE authority, never opened on the OFFLINE path. Stock Pi 4B has
    no TPM/secure element → **flag for Xavier** (use an ATECC608/TPM if the build allows);
    rotate the feed key on each reconnection.

## Timing, durability & isolation (gap fixes — latency-first)
- **WAL / crash safety (#7)** — `dcamr/audit/wal.py` (new). Order per **enforcing**
  request: (1) append + `fdatasync` an **intent** {`request_sha256`, chosen action,
  authority interval} → (2) execute (idempotent binding) → (3) append receipt/outcome →
  (4) fold into the hash-chained audit + checkpoint. Non-enforcing requests (DENY,
  log-only, REQUEST_CONTEXT) **skip the per-request fsync** and ride batched/group-commit
  appends, so the fsync cost lands only on the rare execute path — protecting the p95
  budget. Restart **replays the WAL**: any intent without a receipt → bounded
  `UNKNOWN`-outcome record + reconciliation entry (never assume non-execution).
- **Time-source ladder (#6)** — durations/deadlines: `monotonic_ns` only. Record
  timestamps use best-available in order: **live NTP** (ONLINE) → package **signed build
  time** as last-known-good + monotonic delta since load → **pure monotonic estimate**.
  Every record stamps `time_source` + `clock_uncertainty`; evidence freshness compares
  monotonic deltas where possible and **fail-closes when uncertainty ≥ the freshness
  window** (unreliable wall time never silently passes freshness). Stock Pi has no RTC —
  noted for Xavier.
- **Two independent capacities (#9)** — (a) **local audit-append capacity** is
  security-critical: exhausted → **fail-closed block** of consequential work. (b) the
  **upload outbox** is downstream delivery of *already-durable* records: network-down /
  full → **keep evaluating**, apply a bounded ring with signed **coverage-gap markers**,
  resume on reconnect. Outbox pressure **never** blocks OFFLINE evaluation; separate
  partitions (per #8) keep the two from colliding.

## Serialization design (`common/codec.py` + `common/codebook.py`)
- **In-core:** native frozen dataclasses in `common/protocol.py` holding integer
  codebook indices — no serialization between stages (RAM/CPU optimal).
- **Codec:** one module, deterministic. Default **CBOR** (`cbor2`);
  `encode/decode/canonical_hash`. Swappable (JSON fallback) behind the same API.
  **Startup assertion (#5):** confirm `cbor2` resolved its **C** encoder/decoder (not the
  pure-Python fallback); if not, emit a loud degraded-mode warning, surface it in
  readiness/status, and re-check the latency budget. Records are tiny (~40 B
  codebook-CBOR) so the fallback *may* still fit — but that must be **measured**, not
  assumed (see benchmark + acceptance).
- **At rest / wire / audit:** codebook-CBOR records (tiny — indices + ids + numbers).
- **Human/console/export:** canonical JSON **projected on demand** from the CBOR via
  the codebook label tables (decision-vs-explanation split; not stored on the Pi).
- **Caveat baked in:** archive each package/codebook version with the log so old
  records stay decodable; batch/checkpoint-sign the audit (per-record signature would
  dominate a ~40-byte record).

## ML inference (pure-Python exported forest)
- **Mac exporter** (`lab/export_forest.py`, new): from the trained sklearn
  IsolationForest emit a compact array artifact per tree (feature idx, threshold,
  left/right child, leaf `n_node_samples`) + the average-path-length `c(n)` constants,
  content-hashed; **no pickle**. Store thresholds as **exact float64 bit patterns** (hex)
  and pin the `c(n)` harmonic-number formula to sklearn's, so the Pi reproduces identical
  comparisons — near bit-exact parity (see #11). Include `model.sha256`,
  `feature_schema_version`.
- **Pi scorer** (`dcamr/anomaly_engine/forest.py`, new): dependency-free traversal
  computing per-tree path length + `c(size)` leaf adjustment → mean → sklearn-parity
  `score_samples`; then existing `CalibrationReference.score` → `normal_tail_rank_v1`.
- **Parity test (tolerance pinned — #11):** on the Mac, assert exported-forest
  `score_samples` vs sklearn at **`atol=1e-9`, `rtol=0`** across all replay fixtures,
  **and** assert **zero band-classification flips** (the calibrated band is what actually
  drives decisions). Any fixture landing within `atol` of a band boundary **fails the
  gate** pending review. `1e-9` is feasible because thresholds are stored as exact
  float64 bits and `c(n)`/summation order mirror sklearn; loosen to `1e-6` **only** if a
  measured, documented float-summation difference forces it — never silently.
- **Pi deps (pinned, prebuilt aarch64 wheels — no compiler on OS Lite):**
  `jsonschema`, `cbor2`, and `PyNaCl` only. No numpy/sklearn/joblib on the Pi.
  - `cbor2`: install the prebuilt `manylinux/aarch64` wheel (piwheels), which ships the
    C accelerator; **never** build from source on a minimal image. Startup assertion
    below (#5) fails loud if only the pure-Python fallback loaded.
  - **Ed25519 = PyNaCl** (#4): its aarch64 wheel **bundles libsodium** — self-contained,
    no separate C dep to compile, resolving both "unnamed lib" and "not dependency-free."
    Used **only off the request hot path** — package/manifest verification at
    *load/activate* and periodic audit-checkpoint signing, never per request — so it
    costs the p95 budget nothing. `cryptography` is explicitly rejected (heavier, more
    transitive C).

## Main orchestrator (`dcamr/main.py`)
- Preload verified caches + forest + calibration at start (≤5 s), warm the scorer.
- **Intake byte cap (#12):** at the raw transport boundary, read **≤64 KiB** per action
  envelope *before* `json.loads`, and bound JSON depth/key-count; over-cap →
  `PAYLOAD_TOO_LARGE` (audited), no full buffering. Runs **before** the admission queue,
  so a 100 MB payload never reaches the parser or a worker.
- Admission queue ≤8, **one request in flight, one scoring worker, threads=1**.
  **Deadline ≠ throughput (#2):** the 500 ms is a per-request *SLO ceiling*, not the
  service time; throughput = 1 / service_time. With measured service ~60–90 ms (see
  per-stage budget), single-thread capacity is **~11–16 req/s**, so a steady 10 req/s
  burst is absorbed with few/no rejections. `CAPACITY_EXCEEDED` is a **valid,
  deterministic, audited, fail-closed** outcome under genuine overload — not an error to
  design away. (Acceptance criterion restated in Verification.)
- **Watchdog (#1) — liveness is security:** the in-flight worker publishes a monotonic
  heartbeat at each stage; a tiny monitor thread strokes `/dev/watchdog` (systemd
  `RuntimeWatchdogSec`) **only while heartbeats advance**. A *hung* (not crashed)
  pipeline stops the heartbeat → hardware watchdog reboots → service returns
  **fail-closed with no execution authority** until re-armed. Latency cost ≈ 0.
- **Graceful shutdown (#7):** SIGTERM → stop admitting, drain in-flight, flush audit,
  release the authority lease, exit. Power-cut durability via the intent WAL (below).
- **Clocks (#6):** deadlines/intervals/latency use `time.monotonic_ns` **only** (never
  wall clock); record timestamps use the attested time-source ladder (below).
- Per request run the mode-appropriate path; every request (incl. malformed/blocked)
  gets a bounded audit record.
- Fail-closed on any missing prerequisite; expose readiness/ownership/freshness.

## Critical files
Fill (empty today): `common/protocol.py`; `common/schemas/{action_request,
decision_record,challenge,evidence,package_manifest}.json`;
`dcamr/policy_engine/{policy_engine,rules}.py`; `dcamr/decision_model.py`;
`dcamr/challenge/challenge.py`; `dcamr/evidence/evidence_interface.py`;
`dcamr/enforcement/enforcement_gateway.py`; `dcamr/provenance/provenance.py`;
`dcamr/audit/audit_log.py`; `dcamr/packages/{loader,package_verifier}.py`;
`dcamr/state/local_cache.py`; `dcamr/reconcile/reconciliation.py`;
`dcamr/api/dashboard_api.py`; `dcamr/main.py`; `dcamr/anomaly_engine/anomaly_engine.py`;
`packages/tooling/{sign_package,verify_package}.py`;
`protected_systems/{firewall_sim.py,web01/host_sim.py}`.
New: `common/{codec,codebook}.py`; `dcamr/{identity,mode}.py`;
`dcamr/intake/{normalize.py,adapters/{generic,mcp,a2a}.py}`;
`dcamr/state/ownership.py`; `dcamr/anomaly_engine/forest.py`;
`dcamr/audit/wal.py`; `dcamr/watchdog.py` (heartbeat + `/dev/watchdog` monitor);
`cloud/{feed_ingest,uploader,policy_pull}.py`; `lab/export_forest.py`.
Ops: systemd unit with `RuntimeWatchdogSec`; `ro` mount for the inputs partition,
separate `rw` partition for audit/WAL/outbox.

## Build sequence (milestones)
1. **Contracts + codec:** `protocol.py`, `codec.py`, `codebook.py`, the 5 schemas,
   canonical hashing. (Unblocks everything.)
2. **Packages:** manifest/permissions schema, verifier+loader, codebook build, sign tool.
3. **Intake:** generic→normalize, then MCP + A2A adapters.
4. **L1 + identity + readiness/ownership + state cache.**
5. **L2 live:** forest exporter (Mac) + Pi scorer + `anomaly_engine.py` + parity test.
6. **Evidence + fusion (4 states) + provenance/decision record.**
7. **Challenge loop.**
8. **Audit (hash-chained CBOR + intent WAL + fsync ordering + outbox split) +
   enforcement gateway + protected sims.**
9. **Modes + authority fence + ONLINE log-only (policy pull→cache, feed ingest, upload)
   + reconciliation (incl. WAL replay of un-acked intents).**
10. **main.py orchestrator + dashboard API + watchdog/heartbeat + intake byte cap +
    monotonic-clock / time-source ladder + SIGTERM drain.**
11. **Efficiency pass:** measure RSS + **per-stage** latency + startup; tune stage 7;
    benchmark codebook-CBOR vs JSON and C vs pure-Python cbor2.

## Verification
- **Unit/contract tests** per module in `tests/` matching existing style; reuse
  `tests/fixtures/`. New: codec round-trip + canonical-hash stability; codebook OOV
  rejection; forest parity vs sklearn; fusion truth-table; fail-closed paths;
  audit hash-chain tamper detection; adapter normalization (MCP/A2A/generic → same
  normalized action).
- **End-to-end demo run** (extend `lab/scenario_runner.py`): normal→ALLOW,
  `disable_edr`→DENY (no model call), ambiguous→REQUEST_CONTEXT→HOLD, package
  tamper→rejected, ONLINE(log-only)→OFFLINE fence→full pipeline→reconnect
  reconciliation. Assert every step audited and no decision rewritten.
- **Pi acceptance** (Xavier): 1,000 warm reqs @1/s + 10 req/s 60 s burst + 1 h
  nominal; record p50/p95/p99, **per-stage p95 vs the budget table (#3)**, queue wait,
  RSS, temp/throttle, startup. Verify ≤256/384 MiB and p95 ≤100 ms.
  - **Burst criterion (#2), restated:** at 10 req/s the pass bar is **p95 ≤100 ms and
    rejection rate ≤1%**, every `CAPACITY_EXCEEDED` audited + fail-closed. Mass rejection
    means measured service time > budget — a bug to fix, not the intended outcome.
  - **Watchdog (#1):** inject a synthetic worker hang; assert `/dev/watchdog` reboots the
    Pi and it returns fail-closed (no execution authority) within a pinned bound.
  - **Power-cut (#7):** cut power between enforcement and audit-write across N trials; on
    restart assert WAL replay yields a bounded `UNKNOWN`-outcome record for every un-acked
    intent and **no** un-audited executed decision.
  - **Isolation (#8):** assert the inputs partition is mounted `ro` and audit writes
    cannot reach it; fill the audit partition and assert eval fail-closes while inputs
    stay intact.
  - **Outbox cascade (#9):** with the outbox full / network down, assert OFFLINE eval
    still runs and only delivery degrades (coverage-gap flag raised).
  - **Codec accel (#5):** assert the cbor2 C impl is active at startup; benchmark the
    pure-Python fallback to confirm it stays within budget.
  - **Clock (#6):** with no NTP, assert records carry `time_source`/`clock_uncertainty`
    and freshness fail-closes when uncertainty exceeds the window.
- **Benchmark artifact:** record codebook-CBOR vs canonical-JSON size + encode/decode
  time + audit-drive growth, to justify the encoding.

## Incoming work — integration seams (Merek + Jared)
Merek + Jared are pushing **offline action logging**, **policy caching to the drive**, and a
**simulated enterprise SIEM**. Do **not** rebuild these — pin the contract now so their
modules drop in behind a fixed interface. This plan owns the contract; they own the
implementation.
- **Offline action logging → audit (stage 13 + WAL).** Seam = the append-only
  **hash-chained CBOR record schema**, WAL/fsync ordering, and on-drive log layout
  (`audit_logs/`, rw partition). Their logger must never rewrite (append + `previous_*`),
  fsync intent before any enforcing action, and emit a bounded record for *every* request.
  If it supersedes `dcamr/audit/audit_log.py`, ours becomes a thin adapter to the
  record/chain contract — not a second implementation.
- **Policy caching to the drive → packages loader.** Seam = the **on-drive package layout +
  signed-manifest format**. They own **fetch + write** of the signature-verified package to
  the cache drive; we own **verify + activate** — the Pi re-checks Ed25519 sig + digest
  before activation regardless of who wrote it, keeps last-known-good. The signature is the
  trust boundary between the two.
- **Simulated enterprise SIEM → evidence + feed.** Seam = the `cloud/siem_connector.py`
  interface: evidence queries (present/stale/unverifiable/contradicted) for stage 8, plus
  the authenticated activity feed for ONLINE ingest. **Evidence/feed source only** — if the
  signed-policy pull endpoint is co-located with it, that endpoint stays a *separate,
  signature-verified* path (policy authority ≠ SIEM).
- **Merge discipline:** land these three contracts (record schema, drive layout, connector
  API) in milestones 1–2 so incoming code integrates without touching the hot path.

## Coordination / simulated for demo (flag explicitly)
- **Offline action logging + policy caching to the drive + simulated enterprise SIEM
  → Merek + Jared** (incoming — integrate via the seams above; land contracts first).
- Forest export contract + parity **with Jared** (anomaly owner).
- Pi bitness, storage/readers, power/thermal, acceptance run **with Xavier**.
- Decision-record / event / proof schema mappings **with Alex** (console;
  `alice.*` events, `NOT_EXECUTED` receipt, reassessment lineage).
- **Simulated** for the demo: cloud policy pull endpoint, enterprise SIEM/EDR feed, the
  authority fence/lease protocol, motor/controller (cyber model only — no servo features),
  real remote biometric proof transport.

## Risks
- Forest parity error → wrong bands: gate on the parity test before deploy.
- Combined RAM over budget: codebook + no-numpy chosen for this reason; measure early.
- Over-scoping online mode: keep ONLINE strictly log-only per the locked decision.
- Canonical-serialization drift breaking hashes: single `codec` module is the only
  place bytes are produced; freeze it first.
- **Hung-not-crashed enforcer silently stops gating** → hardware watchdog + heartbeat
  (#1); tested by synthetic hang.
- **fsync-per-execute latency** → WAL fsync only on the *enforcing* path (most requests
  don't execute); batch/`fdatasync` other appends; keep WAL on the fast partition;
  measured in the per-stage budget (#3, #7).
- **cbor2 pure-Python fallback blows the budget** → prebuilt C wheel + startup assertion
  + fallback benchmark (#5).
- **Clock drift in OFFLINE mis-ages evidence** → monotonic deltas + attested time-source
  + uncertainty-aware fail-closed freshness (#6).
- **Shared-USB compromise = packages + feed key** → separate partitions/mount flags +
  off-USB, ONLINE-only feed credential (#8, #10).
- **Oversized payload parse-bomb** → ≤64 KiB read cap + depth/key bounds at intake,
  before the parser and the queue (#12).
