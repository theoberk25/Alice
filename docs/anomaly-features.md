# Build Web-01 behavioral features

This increment turns an authenticated, normalized cyber-action request and a trusted local history snapshot into **11 numeric features**, with immutable provenance and explicit novelty observations. It adds no dependency, model training, model loading, model score, policy outcome, network request or device execution.

Jared selected normal diagnostics plus occasional changes to known destinations. Jared also selected a matching role/mission cohort for authenticated agents without a personal baseline, while preserving a new-agent flag. The target is a 2 GB Raspberry Pi 4 running Raspberry Pi OS Lite; hardware measurement and OS bitness confirmation remain separate deployment work.

The [canonical architecture](architecture.md) distinguishes **ONLINE** enterprise-controlled direct execution from **OFFLINE** Pi-governed local actions after a controlled single-authority handover. ONLINE Pi work synchronizes bounded trusted caches/authenticated activity feeds and sends audit upstream; these features do not create a mandatory Pi gateway. OFFLINE feature/model observations advise a separate permissions decision. Direct Pi-to-enterprise reconnection, authority transfer and source adapters are future integration work, not behavior implemented by this pure builder.

## Run the fixtures and tests

From the Alice repository root, using the environment provisioned with `requirements-anomaly.txt`:

```sh
python3 -m lab.replay_feature_fixtures
python3 -m lab.replay_feature_fixtures --json
python3 -m unittest discover -v
```

The default replay prints five cases: routine diagnostics, a known-destination change, an unseen destination, a new agent, and a complete empty history window. `--json` prints complete feature batches, including values and source references. The existing `python3 -m lab.replay_anomaly_fixtures` still checks the separate anomaly-output contract.

The fixture baseline has the following synthetic counts, for both an individual diagnostic agent and the matching cohort:

| Action | Count per 100 normal proposals | Destination parameters |
| --- | ---: | --- |
| `read_logs` | 50 | None |
| `query_status` | 25 | None |
| `query_network` | 20 | None |
| `modify_firewall` | 3 | Destination, port and protocol |
| `allow_outbound` | 2 | Destination, port and protocol |

These counts are illustrative lookup data, not collected observations, model training data, production operating limits, or policy permissions. The normal destination relationships in the fixture are `10.0.0.10:443/tcp` and `10.0.0.20:443/tcp` for Web-01. The action catalog defines parameter and execution-counting semantics only. The active authority separately decides what is permitted: enterprise controls ONLINE, or DCAMR after OFFLINE handover. Use permissions in product language while retaining legacy `policy` identifiers until a versioned adapter is agreed.

## Fixed feature profile

`cyber-behavior-v1` uses this exact order for every successful batch. Values are finite Python floats; zero/one features use `0.0` and `1.0`. There is no per-request column selection or unversioned imputation.

| Index | Name | Definition |
| --- | --- | --- |
| 0 | `agent_known` | Agent appears in the baseline registry with the authenticated role/mission type. New agents use zero. |
| 1 | `action_seen_for_profile` | Selected individual/cohort profile has a positive count for this action. |
| 2 | `target_known` | Target appears in the complete baseline target table for this demo domain. |
| 3 | `profile_target_seen` | Selected profile lists the target. The name intentionally does not claim personal agent history when using a cohort. |
| 4 | `destination_applicable` | The supported action requires an outbound relationship. |
| 5 | `destination_seen` | Exact `(normalized host, port, protocol)` relationship appears for this target. Zero when not applicable, paired with index 4 being zero. |
| 6 | `action_frequency` | Selected profile's action count divided by its total normal action count. |
| 7 | `recent_request_count_5m` | Distinct prior admitted proposals for this agent and mission inside the complete window, excluding the current request. |
| 8 | `recent_executed_state_changes_5m` | Distinct confirmed state-changing executions for that agent and mission, counted by execution time. |
| 9 | `sequence_has_previous` | A prior proposal exists in the complete five-minute window. |
| 10 | `sequence_transition_probability` | Unsmoothed normal transition count from the previous action to the current action, divided by the row's total. Zero with mask 9 off when no prior proposal exists. |

The initial PRD's candidate `agent_target_seen` was refined to `profile_target_seen` to reflect the approved cohort behavior. Operating-window, host/sensor measurements, evidence sufficiency and agent-provided prose are excluded from this first profile. They must not be added without a feature-version change and new training/inference compatibility checks.

For the normal diagnostic fixture, the vector is:

```json
[1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.2, 2.0, 0.0, 1.0, 0.9]
```

For the known-destination change, it is:

```json
[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.02, 2.0, 0.0, 1.0, 0.1]
```

The change has a lower but positive normal frequency and an observed transition. The builder does not label a low positive frequency as malicious. Frequency thresholds and learned joint unusualness belong to the later model/calibration slice.

## Baseline selection and comparisons

The input structures are defined in `common/schemas/anomaly_baseline.json` and `common/schemas/anomaly_feature_input.json`. Nested unknown fields are rejected. No ordinary input supports a `signature_valid` or `verified` flag that could turn an agent claim into authority.

Load the baseline once from bytes whose expected digest came from DCAMR's verified package path. Package signature/issuer/expiry verification is not implemented here. `load_baseline` verifies the exact data-blob digest, validates tables and cross-references, normalizes host representations, and freezes the resulting lookup maps. The output baseline identity includes the package label/version plus the digest of this baseline payload. If an enclosing package uses a separate manifest/archive digest, preserve that separately in the package layer rather than silently substituting it.

A registered agent selects its named profile. A mismatch between its registered scope and the trusted subject's role/mission type is unavailable; it does not fall through to another profile. An unregistered authenticated agent selects exactly one cohort matching both role and mission type. No matching cohort is unavailable; ambiguous duplicate cohort keys make the baseline invalid. Personal absence still produces `agent_known=0` and `AGENT_UNSEEN`.

Every profile has an explicit count for every supported action, including zeros; missing counts are incomplete data. The total must be positive. Transition rows must reference supported actions and have positive totals. An absent transition cell in an existing complete row means zero observations; an absent previous-action row means unavailable. These are unsmoothed empirical frequencies, not predictive probabilities of an attack. Rows and action counts must not contradict whether an action was ever observed. Individual counts and totals stay within the portable JSON integer range `0..2^53-1`.

The first cyber action catalog is deliberately limited to the five listed actions. Its state-changing/destination semantics cannot be redefined by a baseline package. Unknown actions or another role/mission domain are unsupported. Policy-denied actions such as `disable_edr` should short-circuit before this builder in the future OFFLINE pipeline; the builder itself does not implement denial or gate ONLINE enterprise execution.

Diagnostics take empty parameters in this internal profile. Outbound changes require exactly destination, port and protocol. IP addresses are normalized locally; DNS names are compared case-insensitively after removing a trailing dot. There is no DNS resolution. URLs, paths, malformed numeric addresses and invalid hostnames are rejected. Port/protocol changes can make the relationship unseen even when the host is familiar; the `DESTINATION_UNSEEN` flag therefore means an unseen endpoint relationship, not necessarily a new host name.

Within an otherwise supported mission, a target absent from the complete target table produces novelty, not a fabricated target profile. For an outbound action its relationship is also absent. Baseline tables supplied to this version must actually be complete for the declared demo domain; partial external query results must not be presented as complete baseline tables.

## History rules

The builder is a pure reader of a trusted snapshot; it does not maintain a history store. DCAMR must provide the admission and execution records, authoritative ordering, and completeness markers. Agent-supplied logs cannot establish these facts.

ONLINE activity feeds may support trusted cached state only after authenticated, bounded import with explicit coverage/freshness. A partial enterprise execution feed does not establish complete proposal history or reveal denied proposals. Missing coverage must remain incomplete under the rules below. Import, cache maintenance and control-transfer continuity are not implemented by the feature-input schema.

- The window is **`[observed_at - 300 seconds, observed_at)`**, anchored to the immutable snapshot. The builder never calls the current wall clock to derive features. UTC strings use `Z` or `+00:00`, no leap-second notation, and at most six fractional digits.
- `complete_since` must be at or before the window start. A missing/restarted/truncated history is unavailable. An empty but complete window produces inactive sequence masks; it does not prove that the entire agent lifetime has no prior actions.
- `incomplete_until` must remain set by the history owner after dropped/overflowed events. Evaluation is unavailable while `observed_at <= incomplete_until`. It can recover only once omitted events have aged out or trustworthy records have been restored; freeing one slot or restarting a process is insufficient.
- Proposals use `admitted_at`; confirmed executions use `executed_at`. A proposal before the window can have an execution within it, and that execution counts. Proposing or denying a state change does not count as executing it. If both records exist, execution cannot precede admission.
- Exact duplicate deliveries count once. Conflicting records under the same request/execution ID, inconsistent request digests, and multiple different executions of the same once-only request are invalid. An already executed current request must use DCAMR's recorded idempotent result instead of being freshly feature-scored.
- Sequence/count features are scoped to the current authenticated agent and mission. Admission time and a unique per-session ordinal establish order. Equal timestamps are permitted with distinct authoritative ordinals; conflicting time/order data is invalid. Input array order and lexical IDs never define the predecessor.
- The current request and its context rounds are not extra proposals. **Context-only re-evaluation must pin its original behavioral snapshot**, changing only context metadata that does not affect this profile. If the current request appears before later same-session proposals in a supplied window, reject that snapshot rather than use a later proposal as its predecessor. New trusted behavior requiring a different evaluation boundary needs an explicitly normalized new snapshot/request in the future DCAMR adapter.
- Records at or after the snapshot time are invalid snapshots, not silently dropped future observations. Out-of-range calendar/window arithmetic produces a typed failure rather than an uncaught exception.

The builder checks completeness markers but cannot create or authenticate them. A persistent history owner that prevents omission/poisoning and manages overflow remains team-owned future integration work.

## API and output

```python
from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.features import build_features
from dcamr.anomaly_engine.feature_types import FeatureError

# These values come from trusted package verification / DCAMR snapshot capture.
baseline = load_baseline(baseline_bytes, expected_sha256=verified_baseline_digest)
features = build_features(feature_input_bytes, baseline,
                          expected_sha256=captured_feature_input_digest)
wire_copy = features.to_dict()
```

The expected digests must be captured from trusted sources. Computing a digest from arbitrary incoming bytes and immediately trusting it only checks self-consistency; it does not authenticate the source. The local fixture runner does that solely for committed synthetic fixtures.

`FeatureBatch` is an immutable internal result with:

- Fixed feature version, names and numeric values.
- Exact feature-input byte digest, baseline identity/digest, request ID/digest, snapshot ID/digest and context attempt.
- Selected profile ID and whether selection used `AGENT` or `COHORT`.
- A source reference for every feature and separate comparison factors.
- Sorted novelty flags, independent of model scores.

The feature-input byte digest binds the entire supplied bundle. Inner request/snapshot digests are correlation labels supplied by the trusted caller; this slice does not define their cross-team canonical serialization or independently recompute them. A later consumer must compare the batch to the previously captured feature-input/baseline digests, in addition to its outer request/snapshot binding. Exact input bytes can differ while producing the same semantic vector, such as reordered duplicate deliveries; that still changes the byte digest as intended.

Mode/authority-generation and remote approval-proof binding remain outside the current batch/input fields. The future trusted adapter must establish the active owner and handle stale decisions across handover; unchanged feature bytes are not proof of continuing execution permission. This system requirement does not alter the tested cyber columns or digest semantics.

Feature flags currently include `AGENT_UNSEEN`, `ACTION_UNSEEN`, `TARGET_UNSEEN`, `PROFILE_TARGET_UNSEEN`, `DESTINATION_UNSEEN`, and `SEQUENCE_UNUSUAL`. These belong to **FeatureBatch**, not the older AnomalyResult reason enum. In particular, do not copy new flags wholesale into the existing anomaly schema. The later evaluator must agree on/version the mapping and combine them with a real model result. A feature batch does not contain `status=OK`, a risk score, or an authorization outcome.

Factors distinguish an expected comparison, an unusual comparison, and an inapplicable comparison. Count/frequency features have source references rather than invented normal ranges. Factors are observations, not learned feature attribution. Source references use content digests and JSON-pointer-style paths as opaque labels; no code dereferences them.

`FeatureError` exposes `status`, `code`, and a bounded `field` path. Invalid input, unsupported scope, missing history/baseline information and integrity mismatch produce no feature vector. The future evaluator should convert these to the corresponding non-OK anomaly result with null scores, while preserving deterministic policy denial. This builder does not manufacture that outer envelope or fabricate missing timestamps/hashes.

## Resource limits and verification

The first implementation uses the standard library plus the existing JSON-schema dependency. Baseline lookup maps are frozen once; each call creates a bounded local input snapshot and fixed-size output. It scans/sorts at most the accepted history limit; it does not scan the audit database, launch subprocesses, use NumPy/pandas, or load a model.

| Limit | Implemented bound |
| --- | --- |
| Baseline payload | 8 MiB maximum before parsing; bounded map/table sizes in schema |
| Feature-input bundle | 1 MiB maximum before parsing; includes trusted history, not just the action |
| Normalized action portion | 16 KiB maximum |
| Proposal / execution deliveries | At most 1,024 per stream before deduplication |
| Active agent/mission sessions | At most 32 across supplied history and current request |
| Features | Exactly 11 |
| Input nesting | At most 16 levels |

The separate execution stream extends the PRD's original proposal-only history estimate; both streams and the entire bundle are bounded. These are validation limits, not a claim that persistent queue/capacity management exists. The Pi's 256 MiB worker RSS and 384 MiB load-peak targets remain unmeasured. The feature schema and tables must stay compatible with the later frozen model.

Tests cover exact vectors, new-agent cohort scope, endpoint novelty, complete versus missing history, immutable outputs, duplicate/conflicting records, timestamp boundaries/order, delayed executions, overflow recovery markers, malformed JSON, digest mismatches and resource limits. Offline replay is exercised with socket connection attempts blocked. These are component tests, not evidence of ML detection quality or Pi performance.

## Next checkpoint

The separate [Mac training lab](anomaly-training.md) now uses these exact features with independent normal sessions and synthetic challenge scenarios. It fits in memory and exports JSON reports; model artifact format and Pi deployment remain separate decisions. The [latest motor/USB data direction](data-direction-2026-09-05.md) requires a new motor profile rather than silently changing these cyber columns. Package verification, queue supervision, outer decision fusion and real Pi measurements remain outside this builder.

The [technician-console integration document](technician-console-integration.md) describes a separate team's reported Mac implementation and its unconnected boundaries. Console displays, local facial grants and explanation output do not supply trusted history, new feature semantics or authority to this builder.
