# Anomaly-model output and integration PRD

**Owner:** Jared (anomaly workstream)  
**Consumers:** DCAMR integration team; technician dashboard through DCAMR  
**Status:** Draft contract implemented in a local schema/fixture slice; not deployed  
**Date:** 2026-09-05  
**Proposed anomaly schema:** `1.0.0-draft.1`


## Current decision boundary — technician application

The [Pi assessment contract](../contracts/decision-assessment.md) supersedes earlier
Pi-owned final-fusion descriptions for the current increment. The Pi supplies
permission findings, contextual Isolation Forest scores, source provenance,
review signals and approval blockers. The technician application's local LLM
interprets those facts and explains Approve/Hold/Reject handling. **Unusual
actions require human technician approval**; neither LLM prose nor a facial
match overrides a hard prohibition or missing execution prerequisites.

`alice-decision-assessment-v1` is implemented, with decision and explanation null
and execution_authorized false. It is not a drop-in `alice.decision` event or an
execution token. The app must enforce the structured blockers outside the LLM
prompt. Transport/response binding, permission resolution and lightweight Pi
forest loading remain integrations. Existing historical decisions and scores
remain immutable; reassessments and subsequent app decisions are new records.
Automatic context push-back is not implemented by this slice.


## 1. Purpose and this increment

Define the anomaly result that the Raspberry Pi produces for DCAMR, its provenance, and reproducible fixtures that the integration team can consume before a trained model exists. Keep the runtime small enough to share a Raspberry Pi 4 Model B with the rest of DCAMR.

The [canonical architecture](../architecture.md) now distinguishes **ONLINE**, when enterprise controls execute directly and the Pi synchronizes bounded trusted caches/authenticated activity feeds and sends audit upstream, from **OFFLINE**, when the Pi governs local actions after controlled single-authority handover. This PRD's proposed decision/fusion path describes that OFFLINE responsibility. The Pi is not a mandatory gateway for ONLINE enterprise execution; an anomaly score is advisory in either context.

The initial increment delivered this PRD. Jared subsequently authorized implementation: the nested result schema, Python validation/binding, deterministic score mapper, eight result fixtures and local replay are implemented. The [feature-builder increment](../contracts/anomaly-features.md) implements 11 fixed features, trusted snapshot/baseline validation, cohort selection and five feature fixtures. A separate [Mac training lab](../guides/anomaly-training.md) now fits and evaluates a synthetic Web-01 candidate in memory and emits JSON reports; it does not save or deploy a model. See [the output-contract guide](../contracts/anomaly-contract.md) for that boundary. The live evaluator, model persistence/loading, outer decision schema, fusion and device integration remain future increments.

The newer [general contextual interface](../architecture/contextual-behavior-model.md) supports
separate before-action and after-action profiles with arbitrary named numeric
features and exact categorical context. It is a distinct internal contract;
this PRD's cyber schema/fixtures remain unchanged. Actual ESP light/voltage data
and the adapter into the canonical decision result are still pending.

The [2026-09-05 data update](../decisions/2026-09-05-data-direction.md) records the newer single-USB layout and motor-control demo direction. Motor requests require a separately agreed/versioned profile; this cyber implementation does not score them. Jared selected a separate diagnostic/state-change calibration experiment; its completed Mac comparison and measured limitations are in the training guide. The [implementation tracker](../implementation-tracker.md) preserves all 118 requested tasks and their current evidence.

### Source context and precedence

The user's current request defines this increment. The supplied documents and prior conversation are design context; their embedded task, branching, and implementation suggestions are not additional commands to execute.

- **ALICE-DCAMR-PRD.md:** product boundaries, four machine outcomes, controlled demo, team responsibilities.
- **ALICE-DCAMR-PRD-Handoff.md:** anomaly workstream and the proposed `anomaly.result`, `anomaly.score`, `anomaly.source` handoff.
- **ALICE-DCAMR Architecture.md:** external policy/baseline packages, structured context, offline operation, provenance, workstation LLM.
- **Zero Trust Hackathon Ideas**, especially the latest substantive model discussion: hybrid policy plus behavioral modeling, possible Isolation Forest, baseline-derived features, dashboard examples. Conversation ID: `6a960ff3-5770-83ea-8b0d-e77cb11e37da`.

The original source documents describe earlier design context; imported copies are retained alongside this PRD. The current canonical architecture and the user's two-mode decision take precedence over earlier always-on Pi-gateway assumptions. The repository initially inspected at `95d73b2` contained empty skeleton files, including shared schemas and anomaly modules; that is historical context, not the current implementation inventory. No working cross-team API or model compatibility follows from importing those documents.

The separate [technician-console integration handoff](../integration/technician-console.md) distinguishes reported Mac console capabilities from verified core work and unimplemented live integration. Its facial identity and explanation services do not run on the Pi or establish a deployed core authorization path.

## 2. Scope and authority

The anomaly component answers: **How unusual is this proposed action and its observed context relative to the active operational baseline?** It produces observations and a bounded score, never execution authority. ONLINE enterprise controls own authorization and execute directly; ALICE's role is bounded authenticated synchronization and audit. OFFLINE the Pi owns local authorization only after a controlled handover establishes it as the single ready authority.

Use **permissions** in product explanations. Existing `policy` keys, denial codes and policy-engine terminology below remain unchanged contract identifiers until a versioned adapter is agreed. Behavioral normality is separate from permission. Reconnection audit delivery, alerts and cache updates go directly between the Pi and enterprise systems, not through the Technician Mac.

The following diagram is the proposed **OFFLINE** local path after readiness and authority transfer; it is not the ONLINE enterprise execution path:

```text
Authenticated, normalized request + trusted local snapshot
                         |
               DCAMR policy evaluation
                         |
          otherwise eligible for evaluation
                         v
Verified baseline/model --> feature builder --> anomaly result
                                                  |
                  policy + evidence + context ----+
                                                  v
                                         DCAMR decision fusion
                                                  |
                           authoritative raw decision record
                                                  |
                                  workstation display/explanation
```

**In scope for the eventual anomaly slice:** baseline-relative features; bounded sequence observations; a frozen scorer; explicit unavailable/error results; versioned provenance; fixtures; resource measurements on the actual Pi.

**Outside this workstream:** policy language/OPA selection, authentication, package signing implementation, final fusion policy, context challenge orchestration, HTTP/WebSocket endpoints, audit-chain implementation, facial verification, LLM explanation, protected-system execution, cloud connectors, online learning, and production detection claims. Interfaces to these components are described here so the boundaries can be tested.

Contract requirements carried forward from the product design:

1. A deterministic policy `DENY` is final. Anomaly, agent context, or technician approval cannot override it.
2. A low anomaly does not independently grant permission. Policy approval requirements and evidence requirements still apply.
3. A high anomaly alone is not a deterministic prohibition. Fusion can request context or hold the action.
4. The operational agent cannot alter the baseline, model, trusted history, or verification results. Technician feedback is not automatically training data.
5. OFFLINE scoring and provenance remain local after authority handover. Loss of cloud connectivity alone does not establish permissions, valid caches or control ownership. The LLM runs on the workstation and has no decision authority.

## 3. Proposed first runtime slice

**Selected direction following Jared's implementation go-ahead:** train a small Isolation Forest on the Mac, export a frozen artifact and normal-score reference, and perform only inference on the Pi. Pair the model with explicit baseline comparisons and a simple transition-frequency observation. The initial Web-01 profile now has 11 implemented features and a synthetic lab candidate. A motor profile, real-data curation and deployment artifact format remain separate decisions.

The numerical score measures joint unusualness. A factor such as `DESTINATION_UNSEEN` is an independently reproducible observation, not a claim that one feature caused a particular percentage of the model score. Do not implement SHAP, an embedding service, a language model, or a learned sequence network for this slice.

Novelty checks remain necessary even with Isolation Forest: a feature constant throughout normal training data is not guaranteed to become a useful learned split. In particular, a newly registered agent must remain visible to fusion even if the aggregate model score is low.

If Jared chooses deterministic checks first, retain the envelope and provenance contract but define a separately named scoring method and fixtures before emitting a numeric score. A heuristic must not be labeled as Isolation Forest output.

## 4. Input integration contract

### 4.1 Logical call boundary

The initial interface is a local call, conceptually:

```text
evaluate(normalized_request, trusted_snapshot, active_artifacts) -> AnomalyResult
```

An adapter in DCAMR binds identity, validates limits, supplies immutable inputs, supervises evaluation, and rejects results that do not match those inputs. The agent-facing API must not expose a way to submit a trusted feature vector or an already-approved anomaly result.

This is a future OFFLINE evaluator boundary. ONLINE synchronization must authenticate and bound external activity/cache inputs before they can support trusted local state; incomplete feeds cannot be labeled complete history. No live enterprise feed adapter, controlled handover or mode-based dispatch gate is implemented by the current schema/fixture slice.

| Consumed input | Required meaning and owner |
| --- | --- |
| Normalized request | DCAMR-assigned request ID; identity bound to the authenticated caller; mission ID; action; target; bounded parameters; evidence references. Agent claims remain claims. |
| Request digest | SHA-256 of the immutable normalized action body, including identity, mission, action, target, parameters, and original evidence references. Shared-schema owners must freeze canonical serialization before implementation; never hash Python `repr`. |
| Trusted snapshot | Immutable snapshot ID/digest, locally observed time, current trusted observations, their provenance/freshness, and bounded DCAMR history. Context-only evidence additions live in the snapshot rather than silently editing the original request. |
| Active baseline | Verified immutable package identity/version/digest, coverage, normal relationships/ranges, and transition counts. Metadata comes from DCAMR's package loader, never from an agent's `signature_valid` field. |
| Active model and reference | Model, feature order/version, runtime compatibility information, calibration reference, and severity profile bound to the baseline version/digest. |
| Evaluation context | Unique evaluation ID, prior evaluation ID if this is a re-evaluation, and the context attempt number. Attempt limits belong to fusion. |

The snapshot digest binds all feature-driving observations, the bounded history, and the context/evidence verification state. The adapter checks request digest, snapshot digest, and the immutable artifact identities captured at dispatch before accepting the result. Reusing a request ID with changed action parameters is a conflict; it cannot reuse an earlier score or approval.

Admission requires a valid normalized action body and a serializable, correlated snapshot. Malformed JSON, non-finite supplied JSON values, missing identity/correlation fields, or normalization failure before those digests exist is a **pre-admission validation error**: DCAMR rejects it without invoking the model or fabricating an anomaly envelope, timestamp, or digest. The shared API/audit owners define that error record. `INVALID_INPUT` inside an anomaly envelope covers validation failures after admission, such as a derived non-finite feature or a wrong feature type, while the bound input snapshot remains intact.

### 4.2 Feature profile: `cyber-behavior-v1`

The candidate table below records the original design discussion. The implemented 11-feature order and exact semantics are defined in [the feature-builder guide](../contracts/anomaly-features.md#fixed-feature-profile): `action_seen_for_profile` and `profile_target_seen` reflect cohort fallback; destination and sequence masks make inapplicability explicit; clock-window and host-metric features are excluded for this increment. Training and inference must use this same versioned order/types. Raw identifiers are lookup keys, not arbitrary integer encodings fed to the model.

| Candidate feature | Meaning/source |
| --- | --- |
| `agent_known` | Authenticated identity appears in the active baseline's agent registry. A new authenticated agent differs from an unauthenticated caller, which is handled before scoring. |
| `action_seen_for_agent` | Action membership in that agent's normal profile, with an explicit baseline-defined role/cohort fallback for new agents. |
| `target_known` | Target is represented by the applicable baseline profile. |
| `agent_target_seen` | Relationship has appeared in the baseline; lookup absence is only meaningful when profile coverage is complete. |
| `destination_seen` | For outbound actions, destination relationship appears in baseline. For other actions, use a separately versioned applicability mask/encoding; do not silently treat absent destination data as normal. |
| `action_frequency` | Relative frequency within a named baseline cohort/window, not a policy permission. |
| `recent_request_count_5m` | Distinct admitted action proposals in the prior 300 seconds, excluding this request and its retries/context rounds. |
| `recent_executed_state_changes_5m` | Confirmed executed changes in that interval, from enforcement records; a denied proposal is not an executed action. |
| `sequence_transition_probability` | Probability of previous distinct proposal action to current action within the same agent/mission session, from a fixed baseline transition table. |
| `outside_operating_window` | Derived using the baseline's explicit timezone and a trusted clock; not a free-form timestamp from the agent. |
| `host_state_deviation` | Optional later feature from a specific trusted metric, unit, range and freshness rule; excluded from the first scorer until its input source is selected. |

For the first profile, keep verified evidence sufficiency in DCAMR fusion rather than teaching the behavioral model that persuasive explanations make behavior normal. This narrows the chat's broader feature proposal while preserving the parent PRD's evidence-informed decision behavior.

The implemented increment uses unsmoothed transition frequencies from complete positive-support rows, explicit masks for an empty complete window, and the matching role/mission cohort fallback approved by Jared. An empty window is different from history lost on restart. Where a required feature cannot be constructed reliably, raise a typed feature failure for the future evaluator to map to a non-OK anomaly result; do not insert zero, drop a column, or select an arbitrary cohort. Fields excluded from the active profile are not required inputs.

### 4.3 Package and snapshot lifecycle

- Verify signatures, permitted issuer, content digests, compatibility, and validity before activating or deserializing artifacts. The model and its calibration/feature metadata must be authenticated together with their baseline binding.
- A replacement becomes active atomically. An in-flight evaluation keeps its original snapshot and captured artifact set; an incompatible replacement cannot mix a new baseline with an old model. Its result can be stored against that captured set for audit. If the active set changes before fusion completes, do not authorize using the old score: re-evaluate under the new valid set within the bounded admission/deadline, or remain blocked. A deterministic policy denial can still complete without a new anomaly score.
- Proposed failure behavior: reject a bad replacement and retain an independently valid active set. If no valid compatible active set remains, scoring is unavailable. The rejected candidate belongs in package/audit status; it must not be mislabeled as the baseline used to produce the score.
- An expired package, unknown validity because trusted time is unavailable, unsupported coverage, or incompatible model/reference produces an explicit unavailable reason. The team can later define a signed offline validity policy; silently extending validity is not part of this proposal.
- Do not dereference agent-provided URLs or filesystem paths to load evidence or model files. Source references in results are opaque provenance labels, not commands or fetch instructions.

Authority transfer is a separate integration boundary from artifact replacement. The same request and artifact digests do not prove that an old approval remains usable after changing control owners. Mode/authority-generation binding, remote proof and treatment of in-flight actions require an agreed trusted adapter/outer-record protocol. They are not fields in the current anomaly schema and must not be added to agent-supplied results without versioned contract work.

## 5. Anomaly result contract

### 5.1 Envelope and field definitions

For OFFLINE local decisions, the intended DCAMR integration embeds this object under `raw_decision.anomaly` and owns the outer record, including `decision.outcome`, evidence, context, packages, and audit metadata. ONLINE enterprise records must retain their actual authority and execution provenance; do not fabricate a Pi authorization around a synchronized event. The anomaly object never contains an execution permission, fused risk, or authorization confidence. These mode distinctions change system framing, not the nested fields below.

All listed fields are required; fields marked nullable must be present with null when unavailable. JSON numbers must be finite; strings are UTF-8. Object producers reject duplicate keys, unknown input fields, and invalid enum values. Array ordering is deterministic. Suggested bounds are defined in Section 9.

| Field | Type | Definition |
| --- | --- | --- |
| `schema_version` | string | Exact anomaly contract version, initially `1.0.0-draft.1`; independent of the outer decision schema version. |
| `evaluation_id` | string | DCAMR-assigned unique ID for this evaluation. |
| `previous_evaluation_id` | string or null | Prior evaluation when re-evaluating after context; null on the first evaluation. |
| `request_id` | string | Echo of normalized request ID. |
| `request_sha256` | string | Lowercase 64-character hex digest of the bound normalized action body. |
| `evaluated_at` | string or null | Trusted DCAMR UTC timestamp in RFC 3339 form; not an agent-supplied time. Null with `CLOCK_UNTRUSTED` when reliable UTC is unavailable. |
| `status` | enum | `OK`, `UNAVAILABLE`, `INVALID_INPUT`, `TIMEOUT`, `ERROR`, or `SKIPPED`. |
| `result` | enum | `LOW`, `ELEVATED`, `HIGH`, or `UNKNOWN`; a behavioral band, never a machine decision. |
| `score` | number or null | Finite relative anomaly score in `[0,1]`, higher means more unusual. Null unless `status=OK`. |
| `score_method` | string or null | `normal_tail_rank_v1` for the proposed Isolation Forest mapping; null if no score. |
| `raw_score` | object or null | `{method, value}`; proposed method `sklearn_isolation_forest.score_samples`, value finite with no assumed `[0,1]` range. Null if no score. |
| `source` | string or null | Stable baseline provenance label for handoff compatibility, e.g. `OPS_BASELINE:ops-web01/42`. Null if no baseline was accepted. |
| `baseline` | object or null | `{package_id, version, sha256}` for the verified baseline used. Null if none was accepted. This object never describes a rejected candidate as trusted. |
| `model` | object or null | `{name, version, sha256, feature_schema_version}` identifying the accepted model. Null when no model was accepted or scoring was skipped. |
| `calibration` | object or null | `{version, sha256, sample_count, threshold_profile, elevated_min, high_min}` identifying the accepted normal-score reference and severity settings. |
| `input_snapshot` | object | `{id, sha256, observed_at, history_window_seconds, context_attempt}`. SHA-256 binds observations/history/verification state. `observed_at` is trusted UTC or null with `CLOCK_UNTRUSTED`; null is included in the canonical snapshot, not replaced by a fabricated time. |
| `factors` | array | Zero to 16 structured observations, defined below. Sorted by `id`; no duplicate IDs. |
| `reason_codes` | array of strings | Sorted unique codes for novelty, unusual behavior, skip reason, or inability to score. At least one code. |
| `quality` | object | `{missing_fields, stale_fields, unsupported_fields}`: sorted unique bounded field paths; empty arrays when none. |
| `runtime` | object | `{duration_ms, execution_mode}`. Nonnegative finite duration for validation through result construction; mode `LIVE` or `FIXTURE`. Fixture duration is synthetic. |

For `OK`, `score`, `score_method`, `raw_score`, `source`, `baseline`, `model`, `calibration`, `evaluated_at`, and `input_snapshot.observed_at` must all be non-null; `result` must match the severity profile. For any other status, `score`, `score_method`, and `raw_score` are null and `result=UNKNOWN`. Accepted artifact metadata can remain for diagnosis on a non-OK result; it never makes that result usable as a successful score.

When present, `calibration.sample_count` is a positive integer and `0 <= elevated_min < high_min <= 1`. Snapshot `context_attempt` and `history_window_seconds` are nonnegative integers; the proposed cyber profile uses a 300-second window. If either UTC field is null, use non-OK status, record `CLOCK_UNTRUSTED`, and identify the missing time field in `quality`. Runtime duration uses a monotonic clock and does not require trusted UTC.

`SKIPPED` is adapter-generated only for `POLICY_DENY_SHORT_CIRCUIT` in this version; it may also contain `CLOCK_UNTRUSTED` when denial occurs without trusted UTC. `TIMEOUT` means the adapter's deadline expired. `INVALID_INPUT` covers malformed/non-finite input; `UNAVAILABLE` covers missing, stale or incompatible dependencies; `ERROR` covers a scorer/runtime failure. Error text must not expose arbitrary exception dumps or secrets in the decision record.

### 5.2 Factor schema

Each factor has all of these fields:

| Field | Type/meaning |
| --- | --- |
| `id` | Stable observation ID, e.g. `destination_seen`. |
| `state` | `EXPECTED`, `UNUSUAL`, `UNKNOWN`, or `NOT_APPLICABLE`. |
| `observed` | Bounded JSON scalar or null; never a whole log/history array. |
| `expected` | Bounded JSON scalar or null describing the comparison target. |
| `unit` | Short string such as `boolean`, `probability`, `count`, or `celsius`; numeric comparisons must use matching units. |
| `baseline_ref` | Opaque baseline record reference or null if unavailable. |
| `observation_ref` | Opaque snapshot/history observation reference or null if unavailable. |

`UNKNOWN` requires null observed or expected information plus an explanatory reason/quality path. A known absent destination yields `observed=false` only when the applicable trusted baseline list is complete. Truncated or unavailable data yields `UNKNOWN`, not `false`.

Factors explain comparisons the component actually performed. They do not add up to the model score, establish causation, or prove hostile intent. Labels and prose can be generated by the dashboard from stable IDs; free-form agent text is not an anomaly explanation.

### 5.3 Initial reason-code vocabulary

Successful observations: `WITHIN_BASELINE`, `AGENT_UNSEEN`, `TARGET_UNSEEN`, `DESTINATION_UNSEEN`, `SEQUENCE_UNUSUAL`, `REQUEST_RATE_UNUSUAL`, `OUTSIDE_OPERATING_WINDOW`, `HIGH_MODEL_ANOMALY`, `ELEVATED_MODEL_ANOMALY`.

Availability/validation: `BASELINE_MISSING`, `BASELINE_EXPIRED`, `BASELINE_UNTRUSTED`, `MODEL_MISSING`, `MODEL_BASELINE_MISMATCH`, `CALIBRATION_INVALID`, `FEATURE_SCHEMA_MISMATCH`, `REQUIRED_INPUT_MISSING`, `INPUT_STALE`, `INPUT_NONFINITE`, `INPUT_UNSUPPORTED`, `CLOCK_UNTRUSTED`, `HISTORY_INCOMPLETE`, `HISTORY_CAPACITY_EXCEEDED`.

Adapter/runtime: `POLICY_DENY_SHORT_CIRCUIT`, `INFERENCE_TIMEOUT`, `INFERENCE_ERROR`, `INPUT_LIMIT_EXCEEDED`, `CAPACITY_EXCEEDED`.

The DCAMR adapter additionally records `ANOMALY_RESULT_MISMATCH` or `ANOMALY_SCHEMA_UNSUPPORTED` when rejecting an incoming result. These are fusion/audit reasons, not codes that an untrusted result can use to validate itself. New reason codes require a contract-version update during the draft phase.

## 6. Score semantics and calibration

Preserve the handoff's machine scale: **`score` is 0–1**. A dashboard may show `100 * score` as an anomaly percentile, but must label it as relative unusualness rather than compromise probability. Do not duplicate it under `risk_score`, add an invented `confidence`, or equate it to `decision.risk`.

For the proposed Isolation Forest adapter, use `score_samples` consistently. Its lower values indicate more abnormal samples; do not interchange it with `decision_function`, which subtracts the fitted offset. This distinction and the configurable estimator/sample limits are documented by [scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).

Let `r` be the new raw score and `c[1..N]` the frozen raw scores of a separately held-out, trusted normal calibration set evaluated by the same model and feature profile:

```text
score = (count(c > r) + 0.5 * count(c == r)) / N
```

This defines direction and tie behavior. A value of `0.97` is a relative rank against this reference, not a 97% chance of compromise. The calibration reference must be finite, nonempty, non-degenerate, versioned, and compatible with the model. Proposed trained-model minimum is 1,000 held-out normal observations with multiple distinct scores; data adequacy beyond that minimum remains to be evaluated. Split at the scenario/session level to avoid leaking near-duplicates between training and validation.

**Provisional fixture severity profile `demo-tail-v1`:**

| Score interval | `result` |
| --- | --- |
| `0 <= score < 0.95` | `LOW` |
| `0.95 <= score < 0.99` | `ELEVATED` |
| `0.99 <= score <= 1` | `HIGH` |
| No valid score | `UNKNOWN` |

These are testable starting values, not measured detection thresholds. A percentile ranks normal data across the scale; the chat's 25/55 cutoffs would therefore escalate a large part of normal behavior. Do not copy those numbers onto this score. Tune thresholds using separate normal validation and synthetic attack scenarios, report false escalations/misses, and obtain a product decision about the tradeoff before operational use.

Keep the score unrounded for band assignment; any rounding is display-only. The fixture arithmetic and integer counts are exact; raw model values may require a recorded numeric tolerance across supported runtimes. A tolerance must never change a boundary rule or conceal a changed band. Store model, reference, feature and threshold versions together; scores from different versions are not automatically comparable.

## 7. DCAMR consumption, failure and re-evaluation

The following is a **proposed OFFLINE integration test profile**, after local authority/readiness is established, not an implementation of the team's fusion engine. Every blocked local outcome prevents execution. Anomaly unavailability cannot create an automatic allow path. This table does not impose an additional Pi gate on ONLINE enterprise execution.

| Conditions | Required/proposed DCAMR behavior |
| --- | --- |
| Policy `DENY`, any anomaly | Required: `DENY`; no context or human-approval bypass. Prefer skip to save Pi work. |
| Policy unavailable/invalid | Required: remain blocked under DCAMR's policy-failure behavior. A good anomaly score cannot compensate. |
| Otherwise eligible, anomaly non-OK or rejected | Proposed: `HOLD`, explicit reason, no execution. Deterministic denial still takes precedence. |
| Explicit mandatory technician approval | Required: remain blocked pending the exact-request human approval path, even with low anomaly and good evidence. |
| Policy permits, complete evidence, `LOW`, no novelty flags | Proposed fixture result: `ALLOW`. |
| Policy permits, `LOW` plus new authenticated agent, or `ELEVATED`, or missing required evidence; context remains | Proposed fixture result: `REQUEST_CONTEXT`. A low score cannot suppress a novelty/evidence rule. |
| Policy permits, `HIGH` | Proposed fixture result: `HOLD`; whether this should first request context is an open demo decision. |
| Final permitted context response still leaves a context requirement unresolved | Required by the bounded-loop design: `HOLD` rather than another challenge, unless deterministic policy requires `DENY`. Evaluate that final response first; a resolved request may proceed if all other conditions permit. |
| Independently verified contradiction | Proposed fixture behavior: `HOLD` for review unless deterministic policy requires `DENY`; the exact contradiction rules belong to fusion. |

The handoff's policy `REVIEW` is ambiguous about mandatory human approval versus a context-remediable review. This anomaly contract does not resolve that ambiguity by authorizing anything. Until the policy owner distinguishes them, the conservative fixture treats `REVIEW` as blocked pending review. The main context fixture uses explicit policy `ALLOW` with incomplete evidence.

On re-evaluation, preserve the original decision and anomaly result. Issue a new `evaluation_id`, link `previous_evaluation_id`, bind the same immutable action digest, and bind a new snapshot when trusted evidence changes. Changed action parameters require a new request. Same inputs/artifacts produce the same semantic score/factors; ID/time/duration may differ. Idempotent retries may reuse the stored result but cannot add history events.

Agent prose alone cannot lower the score. Independently verified evidence can change fusion's evidence sufficiency while the behavioral score stays unchanged. Evidence being locally present does not mean it is authentic, relevant, fresh, or verified. A context response cannot change observed destinations, execution history, or model/baseline content. Later cloud reconciliation appends findings and does not retroactively rewrite a decision.

On reconnection, the Pi synchronizes audit, retrieves available authenticated enterprise alerts and refreshes trusted caches directly. The Technician Mac is not a synchronization relay. Pending approvals and actions must follow the agreed control-transfer rule rather than silently resuming under a new authority; that rule is not implemented by current evaluation-ID/artifact binding alone.

The adapter must enforce deadlines and capacity limits. Measuring elapsed time after an unrestricted Python call is not a timeout mechanism. Before selecting the process layout, decide how to cancel/replace a stuck scorer and reject late results. Do not grow an unbounded queue or spawn one process per request.

## 8. Test fixtures consumed by DCAMR

The existing fixture inputs, numbers and expected assertions are unchanged. Their proposed execution outcomes assume the OFFLINE authority boundary above. In particular, A17's disconnected cloud flag tests local score independence; it does not test or implement the handover that makes local execution authority valid.

### 8.1 Fixture boundary and deterministic score reference

There are two distinct test layers:

1. **Contract/fusion fixtures:** inject known raw scorer outputs and baseline observations; test serialization, mapping, provenance, failure handling and DCAMR outcomes. These are not evidence of model detection quality.
2. **Model evaluation fixtures:** later replay frozen feature inputs through the real trained model, record artifact identities and measured outputs, and compare to held-out expectations. Never assert that a synthetic input must magically produce the numeric examples below.

The following complete JSON definition supplies the deterministic score-mapping fixtures. Expand each reference segment into `count` copies of `raw_score` before computing ranks. Use the profile in Section 6. `fixture_mode` marks these as mocks; live enforcement must reject fixture-mode results.

```json
{
  "fixture_format": "anomaly-score-cases-v1",
  "fixture_mode": true,
  "score_method": "normal_tail_rank_v1",
  "calibration_segments": [
    {"raw_score": -0.7, "count": 10},
    {"raw_score": -0.6, "count": 40},
    {"raw_score": -0.5, "count": 950}
  ],
  "thresholds": {"elevated_min": 0.95, "high_min": 0.99},
  "cases": [
    {"id": "normal", "raw_score": -0.5, "score": 0.475, "result": "LOW"},
    {"id": "elevated", "raw_score": -0.6, "score": 0.97, "result": "ELEVATED"},
    {"id": "high", "raw_score": -0.7, "score": 0.995, "result": "HIGH"},
    {"id": "elevated-boundary", "raw_score": -0.55, "score": 0.95, "result": "ELEVATED"},
    {"id": "high-boundary", "raw_score": -0.65, "score": 0.99, "result": "HIGH"},
    {"id": "lower-endpoint", "raw_score": -0.4, "score": 0.0, "result": "LOW"},
    {"id": "upper-endpoint", "raw_score": -0.8, "score": 1.0, "result": "HIGH"}
  ]
}
```

### 8.2 Complete scored-result fixture

Fixture request: authenticated `diagnostic-agent-04`, mission `INC-291`, action `allow_outbound`, target `Web-01`, destination `203.0.113.42`, port `443`, protocol `tcp`. The applicable trusted baseline contains expected destinations but not that destination. Inject the `elevated` raw score from Section 8.1. DCAMR's test policy permits the action and one required evidence item is unavailable, with zero context attempts used; expected fusion outcome is `REQUEST_CONTEXT`.

This is the **entire nested anomaly object**, not the entire raw-decision record. The repeated hex digests are inert fixture identifiers, not real signatures or hashes of production artifacts. The fixture harness supplies the same identifiers in its bound request/snapshot/artifact context. Replace them with computed hashes when generating real artifacts.

```json
{
  "schema_version": "1.0.0-draft.1",
  "evaluation_id": "eval-demo-002-0",
  "previous_evaluation_id": null,
  "request_id": "req-demo-002",
  "request_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "evaluated_at": "2026-09-05T15:42:18Z",
  "status": "OK",
  "result": "ELEVATED",
  "score": 0.97,
  "score_method": "normal_tail_rank_v1",
  "raw_score": {
    "method": "sklearn_isolation_forest.score_samples",
    "value": -0.6
  },
  "source": "OPS_BASELINE:ops-web01/42",
  "baseline": {
    "package_id": "ops-web01",
    "version": "42",
    "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "model": {
    "name": "IsolationForest",
    "version": "if-ops42-demo1",
    "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "feature_schema_version": "cyber-behavior-v1"
  },
  "calibration": {
    "version": "normal-reference-demo1",
    "sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "sample_count": 1000,
    "threshold_profile": "demo-tail-v1",
    "elevated_min": 0.95,
    "high_min": 0.99
  },
  "input_snapshot": {
    "id": "snapshot-demo-002-0",
    "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "observed_at": "2026-09-05T15:42:17Z",
    "history_window_seconds": 300,
    "context_attempt": 0
  },
  "factors": [
    {
      "id": "destination_seen",
      "state": "UNUSUAL",
      "observed": false,
      "expected": true,
      "unit": "boolean",
      "baseline_ref": "OPS_BASELINE:ops-web01/42#/hosts/Web-01/destinations",
      "observation_ref": "SNAPSHOT:snapshot-demo-002-0#/request/parameters/destination"
    }
  ],
  "reason_codes": ["DESTINATION_UNSEEN", "ELEVATED_MODEL_ANOMALY"],
  "quality": {"missing_fields": [], "stale_fields": [], "unsupported_fields": []},
  "runtime": {"duration_ms": 0.0, "execution_mode": "FIXTURE"}
}
```

The dashboard displays `97 / 100` as relative anomaly, the destination observation, and baseline/model versions. It displays the **outer DCAMR outcome** as `REQUEST_CONTEXT`. It must not infer an outcome from `ELEVATED` or from the number alone.

### 8.3 Complete unavailable-result fixture

Cold start with no accepted baseline or model. The same action remains blocked; under the proposed fusion profile, expected outcome is `HOLD`. There is no benign zero score for a UI to accidentally interpret as safe.

```json
{
  "schema_version": "1.0.0-draft.1",
  "evaluation_id": "eval-demo-003-0",
  "previous_evaluation_id": null,
  "request_id": "req-demo-003",
  "request_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "evaluated_at": "2026-09-05T15:43:00Z",
  "status": "UNAVAILABLE",
  "result": "UNKNOWN",
  "score": null,
  "score_method": null,
  "raw_score": null,
  "source": null,
  "baseline": null,
  "model": null,
  "calibration": null,
  "input_snapshot": {
    "id": "snapshot-demo-003-0",
    "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "observed_at": "2026-09-05T15:42:59Z",
    "history_window_seconds": 300,
    "context_attempt": 0
  },
  "factors": [],
  "reason_codes": ["BASELINE_MISSING", "MODEL_MISSING"],
  "quality": {
    "missing_fields": ["active_artifacts.baseline", "active_artifacts.model"],
    "stale_fields": [],
    "unsupported_fields": []
  },
  "runtime": {"duration_ms": 0.0, "execution_mode": "FIXTURE"}
}
```

### 8.4 Fixture manifest and expected assertions

When materialized in the next increment, each scenario contains `request`, `trusted_snapshot`, `artifact_context`, `scorer_stub` or `fault`, `expected_anomaly`, and `dcamr_context`/`expected_decision` for integration tests. Request and snapshot bodies have stable timestamps and hashes. Expected model outputs are supplied by the stub only in contract tests. The shared request-schema owner reviews the full input fixture before it becomes a canonical team artifact.

| ID | Inputs/change | Expected anomaly/assertion | Expected DCAMR assertion |
| --- | --- | --- | --- |
| A01 normal diagnostic | Known agent; `read_logs(Web-01)`; complete history; normal stub; sufficient evidence | `OK`, `LOW`, `0.475`, `WITHIN_BASELINE` | `ALLOW` only with permitting policy. |
| A02 new destination | Section 8.2 | `OK`, `ELEVATED`, `0.97`, `DESTINATION_UNSEEN` and source references | `REQUEST_CONTEXT`. |
| A03 high behavior | Novel destination and unusual proposal transition; high stub; evidence incomplete | `OK`, `HIGH`, `0.995`, destination/sequence observations and window provenance | `HOLD`; no execution. |
| A04 hard denial | `disable_edr(Web-01)` prohibited | Adapter returns `SKIPPED`, `UNKNOWN`, null score, `POLICY_DENY_SHORT_CIRCUIT`; model call count zero | `DENY`, no challenge or approval. Also reject attempted override using a low-score result. |
| A05 new authenticated agent | Baseline role/cohort valid, agent absent; deliberately use normal stub | `OK`, `LOW`, `0.475`, `AGENT_UNSEEN` factor | `REQUEST_CONTEXT` despite low aggregate score. |
| A06 mandatory approval | Policy requires technician approval; normal stub and complete evidence | Valid low anomaly | Remains blocked for exact-request review; cannot auto-allow. |
| A07 missing artifacts | Section 8.3 | `UNAVAILABLE`, `UNKNOWN`, null score; missing fields | `HOLD`. |
| A08 invalid replacement | Candidate signature invalid; active baseline/model still valid | A01 score/provenance still names the active version; no load of rejected candidate | Candidate rejection separately audited; normal valid active evaluation remains possible. |
| A09 invalid/expired active set | No valid active fallback; vary untrusted baseline, expiry, mismatched model, bad calibration or feature version; separately swap active set during inference | `UNAVAILABLE`, null score, matching explicit reason; old captured result remains correctly attributable but cannot authorize after replacement | `HOLD` or bounded fresh evaluation; no silent fallback to zero/old incompatible score. |
| A10 malformed numeric input | Missing required feature, NaN/infinity, wrong type, oversized input; separate cases | Pre-admission malformed JSON rejected without fabricated envelope; post-admission derived non-finite/wrong feature: `INVALID_INPUT`; missing dependency: `UNAVAILABLE`; null scores | Blocked; JSON never contains NaN/infinity; no invented digest to serialize an invalid body. |
| A11 unsupported domain | Physical-sensor action sent to a cyber-only model; no applicable profile | `UNAVAILABLE`, `INPUT_UNSUPPORTED` | `HOLD`; no arbitrary category encoding. |
| A12 stale/incomplete state | Trusted history lost, window truncated, required observation stale, or clock untrusted; then restore history/time | `UNAVAILABLE` with corresponding reason and quality path; untrusted UTC is null; complete trustworthy window required for recovery | `HOLD` until repaired; absence cannot count as normal. |
| A13 context: claims only | A02 action/behavior unchanged; agent adds prose or unverified evidence | New linked evaluation; same score and behavioral factors | No authority gain from persuasion. On exhausted context rounds, `HOLD`. |
| A14 context: verified evidence | A01 behavior with missing evidence first; verifier later independently confirms it | Same behavioral score; new linked snapshot/evaluation; old record unchanged | Under permitting policy, may move from `REQUEST_CONTEXT` to `ALLOW`; mandatory approval still blocks. |
| A15 context: trusted new behavior | New trusted observation justifies a changed feature snapshot | Re-score, new snapshot digest and linked evaluation; both retained | Outcome follows fresh policy/evidence/fusion, not prose. |
| A16 duplicate/mismatch | Retry same request; separately change port under reused ID or deliver old snapshot result | Retry stable and history counted once; mismatched digest/result rejected by adapter | Stale low score/approval never applies to altered action. |
| A17 DDIL | A01 inputs/artifacts unchanged; cloud flag offline | Identical semantic score/factors; no network call | Local `ALLOW` remains possible; separate missing cloud evidence may still block consequential actions. |
| A18 timeout/error/overload | Sleeping scorer, scorer exception, full queue, history overflow and recovery; separate cases | `TIMEOUT`/`ERROR`/`UNAVAILABLE`, null score, matching reason; history remains incomplete across the affected window | `HOLD`, no execution, late result rejected; worker/queue remain bounded; no early recovery from undercounted history. |
| A19 thresholds and ties | All Section 8.1 cases; values immediately below/at/above each band edge | Exact documented rank/tie/band behavior | No rounding-dependent decisions. |
| A20 unknown contract | Unsupported schema/enum, unknown required semantics, invalid field combination, duplicate JSON key | Consumer rejects payload; records adapter reason | Blocked; no best-effort allow. |
| A21 fixture isolation | `execution_mode=FIXTURE` reaches live enforcement | Rejected outside explicit lab fixture runner | No protected-device actuation from mock output. |
| A22 sequence/history semantics | Normal vs unusual transition; interleaved agents; denied proposals; repeated context; true session start | Scope separation; no duplicate proposal/execution counting; cold-start distinct from missing history | No manufactured normality or wrong-agent sequence. |

The high-anomaly narrative and the mandatory-review rules require fusion-owner agreement. The model workstream supplies fixtures and assertions; it does not silently change the team's decision policy to make a demo pass.

## 9. Raspberry Pi 4 resource guardrails

Jared confirmed **2 GB RAM** and Raspberry Pi OS Lite. The mentioned 64 GB may refer to storage; OS bitness, cooling and co-resident service footprint still need confirmation. The Pi 4 has a quad-core Cortex-A72 processor; measure this actual unit before sizing deployment. [Raspberry Pi specifications](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/)

All numbers below are **proposed acceptance budgets**, not measurements or performance promises. They apply to the anomaly slice and must be checked alongside policy, audit and API work on the Pi.

ONLINE synchronization must also bound trusted cache/feed work within the same 2 GB device allocation. Resource and readiness acceptance must cover both modes and handover; a passing local score benchmark does not validate enterprise connectors, cache completeness or single-authority control.

| Resource | Starting budget/proposal |
| --- | --- |
| Work placement | Train/calibrate on the Mac; one preloaded frozen model on Pi; no on-device fitting, online adaptation or LLM. |
| Model size/complexity | Start with 64 trees, at most 256 samples/tree, fixed seed, at most 16 numeric features including applicability masks. Adjust only after measuring quality and cost. |
| Parallelism | One scoring worker, one request in flight; explicitly limit numerical-library/inference threads to one. Do not use all-core execution or load a model per API worker. |
| Memory | Anomaly worker including Python/dependencies/model: target steady RSS <=256 MiB and load peak <=384 MiB. Record total DCAMR RSS and OS available memory too; passing the anomaly budget alone does not prove the Pi fits. |
| Artifact inputs | <=16 MiB uncompressed model; <=8 MiB baseline feature summaries/reference; preflight compressed and expanded sizes before loading. Large raw training history stays off Pi. |
| Request/result | <=16 KiB normalized request; <=16 KiB anomaly JSON result; <=16 factors, <=16 reason codes, <=16 entries per quality array; identifiers <=128 characters and source refs <=256. Scalar display strings <=256 characters. |
| Feature history | 300-second window; global maximum 1,024 distinct proposal records across at most 32 active agent/mission sessions. Prune only records outside the window; overflow within the window returns capacity/incomplete-state status rather than silently losing counts. |
| Normal inference | Target p95 <=100 ms at 1 request/second after warm-up, including feature construction and serialization. Model-only timing reported separately. |
| Admission/deadline | At most 8 queued requests; proposed 500 ms deadline from admission to result, including queue time. Full queue produces explicit capacity failure. Deadline enforcement must be implemented by the adapter/supervisor. |
| Startup | Target <=5 seconds to validate/load an already local artifact set; scorer stays unready until successful. DCAMR still serves policy denials, blocked/unavailable responses, audit and status paths. Package import timing reported separately. |

Reject oversized inputs before expensive parsing/inference where possible. Cap all arrays/strings and define nested parameter limits in the shared request schema. Cache immutable lookup tables; use compact numeric arrays; avoid pandas in the Pi request path, repeated filesystem reads, scanning full audit history, or a subprocess launch per score.

After history loss/overflow, track an incomplete-history horizon. Resume features that depend on the full window only after all omitted events have aged out of the 300-second window or trustworthy history has been restored. Expiring one old record or restarting a worker does not by itself restore completeness. Apply the horizon conservatively to all affected sessions, and keep its bookkeeping bounded.

The persistence format remains a decision. `joblib`/pickle model loading can execute code and requires trusted artifacts and compatible environments, as described in [scikit-learn's persistence guidance](https://scikit-learn.org/stable/model_persistence.html). Signed media alone is not a reason to deserialize arbitrary bytes. Evaluate a restricted model format or an explicitly trusted, verified artifact with pinned runtime versions before implementing the loader; do not add format-conversion dependencies until the team selects the path.

Pi acceptance run: record RAM/OS/runtime versions, model digest, power/cooling configuration and other running DCAMR services. Run 1,000 warmed requests at 1 request/second, a 10 request/second 60-second burst, and one hour at nominal rate. Record p50/p95/p99/max latency, queue wait, failures, throughput, worker/total RSS, CPU, temperature, throttling, swap and history growth. During bursts, bounded explicit holds are preferable to unbounded work; no drops masquerading as successful evaluation. Confirm package load/reload peaks and recovery after a stuck scorer. Mac measurements do not satisfy Pi acceptance.

## 10. Functional requirements and acceptance

- **FR-A1:** One bounded, schema-valid result for each admitted evaluation or an adapter-generated failure envelope. Result/input binding is validated before fusion.
- **FR-A2:** Preserve independent status, behavioral band, score, exact model/baseline/reference provenance, and traceable factors.
- **FR-A3:** Produce null scores for failed, skipped, unsupported or unavailable evaluations; never NaN, infinity, or a fallback zero.
- **FR-A4:** Keep policy prohibition, required approval, evidence verification and context limits outside model authority.
- **FR-A5:** Use trusted immutable state; stable retries do not change history, and re-evaluation/reconciliation preserve earlier records.
- **FR-A6:** Score without network access or training; bound memory, queueing, payloads, history and model work.
- **FR-A7:** Separate fixture behavior from measured model quality and reject fixture outputs on live enforcement paths.

Acceptance is incremental; unchecked items below are not claimed complete by this PRD:

- [ ] Jared and DCAMR/schema owners agree on status/null semantics, input binding and nested field names.
- [x] The materialized schema and Python validator validate the complete result examples and reject tested incompatible combinations and malformed payloads.
- [x] Score fixture arithmetic, tie behavior, monotonic direction and exact severity boundaries pass.
- [ ] A01–A22 replay with explicit expected inputs/results, policy precedence and zero unintended executions.
- [ ] Repeated identical behavioral inputs produce stable semantic results; context claims alone cannot lower scores.
- [ ] Frozen real-model tests report held-out normal false escalation rate and synthetic-scenario misses without calling mock outcomes detection evidence.
- [ ] Artifact integrity/compatibility failures, DDIL, overload and supervised timeout behavior have repeatable tests.
- [ ] Dashboard can render scored, unknown and skipped objects and reads decisions only from the outer authoritative record.
- [ ] Actual Pi measurements satisfy the agreed combined resource budget; unresolved limits are documented before hardware/demo integration.

## 11. Repository scope and delivery sequence

Use the existing skeleton rather than the attachments' alternative `shared/`, `demo/`, or `dcamr/anomaly/` layout.

| Path | Workstream role |
| --- | --- |
| `docs/prds/anomaly-model-prd.md` | Output contract, fixtures, decisions and acceptance. |
| `common/schemas/anomaly_result.json` | Implemented nested draft result schema; outer schema integration remains team-owned. |
| `tests/fixtures/anomaly/` | Implemented result/score fixtures and manifest; full request/state and end-to-end fixtures remain future work. |
| `tests/test_anomaly_engine.py`, `tests/test_anomaly_contract.py` | Implemented score-mapping, result-validation and binding tests. |
| `dcamr/anomaly_engine/contract.py`, `dcamr/anomaly_engine/scoring.py` | Implemented validation/binding and deterministic reference mapper; no model inference yet. |
| `scripts/lab/replay_anomaly_fixtures.py` | Implemented local mock replay; no policy/fusion or execution. |
| `scripts/lab/anomaly_training.py`, `scripts/lab/synthetic_anomaly_data.py`, `scripts/lab/train_anomaly_model.py` | Mac-only synthetic source generation, session splitting, candidate fitting and JSON evaluation reports. No deployable model export. |
| `scripts/lab/compare_anomaly_calibration.py` | Mac-only paired comparison of global/conditional references using the same forest and fresh source/evaluation pools; no live calibration change. |
| `dcamr/anomaly_engine/anomaly_engine.py` | Future evaluator and result adapter boundary. |
| `dcamr/anomaly_engine/baseline.py` | Implemented validated immutable baseline lookups and profile selection. |
| `dcamr/anomaly_engine/sequence.py` | Implemented bounded history/sequence feature calculations; persistent history owner remains external. |
| `dcamr/anomaly_engine/features.py`, `feature_types.py`, `feature_validation.py` | Implemented feature input validation and immutable feature batches. |
| `common/schemas/anomaly_baseline.json`, `anomaly_feature_input.json` | Implemented baseline and internal feature-input schemas. |
| `tests/fixtures/features/`, `tests/test_feature_builder.py`, `scripts/lab/replay_feature_fixtures.py` | Implemented feature fixtures, replay and positive/failure tests. |
| `packages/ops_baseline/` | Coordinate summaries/model binding with package-loader owner; do not replace others' formats unilaterally. |
| `dcamr/decision_model.py`, `common/schemas/decision_record.json` | DCAMR-owned fusion/shared record; review the anomaly embedding together. |
| `apps/desktop/`, `packages/contracts/` | Console consumer coordination; this anomaly slice does not implement its live assessment adapter. |

Suggested later branch name: `codex/ml-anomaly-contract`. The supplied documents propose basing work on `dev`, but only `main` was present in the inspected clone. Branch/integration-base selection is a separate team workflow decision; no branch, commit, push or PR is required by this document-only increment.

Delivery checkpoints:

1. **Completed:** drafted and discussed the first scope; selected Mac training/Pi inference and recorded 2 GB RAM.
2. **Implemented locally:** result schema, deterministic fixtures/validator and replay; 31 tests pass. Review the draft contract with DCAMR consumers before integrating it into the outer record.
3. **Implemented locally:** the agreed normal-behavior direction and cohort fallback are represented by synthetic examples and the fixed feature builder. The examples are not measured normal-operation data.
4. **Model increment in progress:** the Mac synthetic candidate and approved separate-calibration comparison are implemented and measured. Model format/runtime, operational acceptance and the new motor feature contract remain to be agreed.
5. **Pi increment:** measure resource use on the actual hardware, then connect the validated result to team-owned fusion and the demo.

Do not combine all five into one implementation pass. Each checkpoint should leave a small runnable or reviewable artifact and a specific decision for the next step.

## 12. Decisions for Jared and the integration team

### Immediate questions already raised with Jared

1. **First scorer:** The Mac-training/Pi-inference direction is accepted. The synthetic Mac candidate is now fitted and evaluated in memory; the live Pi scorer and model persistence remain unimplemented.
2. **Scenario direction:** Web-01 implements routine diagnostics plus occasional known-destination changes, with cohort novelty preserved. The newer conversation introduces motor commands and one USB. Motor-first versus dual-domain scope and absolute versus relative angle semantics are pending; baseline normality does not grant policy permission.
3. **Hardware:** 2 GB RAM confirmed; Raspberry Pi OS Lite reported. Confirm OS bitness and co-resident services with the hardware owner. Resource figures remain targets awaiting measurement.

### Next decisions, before the affected code is written

- **Authority transfer:** agree the trusted mode owner, single-authority readiness/handover protocol, cache validity, remote approval proof and handling of pending or dispatched actions across control generations. ONLINE enterprise direct execution is selected; the integration protocol remains unimplemented and is not part of the existing anomaly result fields.
- **Shared output:** accept canonical `score` 0–1, `status` separate from `result`, null failure scores, and independently versioned anomaly object? Dashboard/outer schema remain team-owned.
- **Fusion:** does high anomaly go directly to `HOLD` or receive a context round first? Does `REVIEW` always require a person, and how is context-remediable policy represented? Agree on the context-attempt limit and evidence requirements.
- **Feature/data design:** the implemented cyber profile documents cohort fallback, unsmoothed transitions, masks and history rules. Next agree on motor request/telemetry semantics and the normal/forbidden operating ranges; do not infer them from example angles.
- **Model packaging:** where does the authenticated model artifact live, what format can the runtime safely load, and how are baseline/model/reference versions bound and replaced together?
- **Offline time/failure behavior:** expiration/grace policy, valid-active-package fallback, timeout supervision and total Pi resource allocation.
- **Evaluation tradeoff:** acceptable normal-request escalation rate and required demo-scenario coverage before fixing thresholds.

No unresolved choice in this section should be represented to another workstream as a confirmed team decision.
