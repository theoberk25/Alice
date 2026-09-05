# Run the first anomaly contract slice

This slice implements the anomaly **output boundary**, deterministic score mapping, and local mock replay. It does not yet train or run Isolation Forest, build behavioral features, evaluate policy, enforce actions, verify packages, or supervise an inference worker. A validated result is not an authorization decision.

The subsequent [feature-builder slice](anomaly-features.md) implements model inputs separately, and the [Mac training lab](../guides/anomaly-training.md) fits a synthetic candidate in memory. This guide describes the output-contract boundary; a live model adapter, fusion and Pi deployment remain unimplemented.

The selected direction is Mac training and Pi inference, starting with Web-01 cyber requests. The target Pi has **2 GB RAM** and runs Raspberry Pi OS Lite; OS bitness still needs confirmation (`getconf LONG_BIT` on the Pi). The mentioned 64 GB may describe storage. There is no reason to change the OS for this slice.

## System authority and this contract

Under the [canonical architecture](../architecture.md), **ONLINE** enterprise controls execute directly. The Pi synchronizes bounded trusted caches and authenticated activity feeds and sends audit upstream; it is not a mandatory enterprise execution gateway. **OFFLINE**, the Pi governs local actions only after controlled handover establishes one ready authority. An anomaly score is advisory, with permissions evaluated separately. Reconnection synchronization is direct Pi-to-enterprise, not a Technician Mac relay.

The consumption example below describes the future OFFLINE decision path. The current nested result and binding helper do not implement mode selection, control transfer, authority-generation binding, remote approval proof or in-flight action handling. Matching request/artifact digests alone cannot carry an old approval across owners. Agree those protections in the trusted adapter/outer protocol without inventing fields in `1.0.0-draft.1`.

Use **permissions** in operator-facing explanations; existing `policy` keys and codes below retain their schema meanings pending a versioned adapter. The [separate console handoff](../integration/technician-console.md) reports Mac identity/review/explanation capabilities, not a connected or deployed core decision system. Its local grants and legacy risk display are not substitutes for this contract or remote authorization proof.

## Run locally

From the Alice repository root, using Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-anomaly.txt
.venv/bin/python -m unittest discover -v
.venv/bin/python -m lab.replay_anomaly_fixtures
.venv/bin/python -m lab.replay_anomaly_fixtures --json
```

Only `jsonschema` is declared as a direct dependency in `requirements-anomaly.txt`, pinned to the version used for local validation. Mac training has a separate requirements file; its real-estimator tests are skipped if training dependencies are absent. The contract replay uses the standard library for score mapping. It imports no NumPy/scikit-learn, runs no training, performs no network calls, and invokes no protected-system code. Provision dependencies before testing offline behavior. The schema uses local references only.

Local development was checked with Python 3.12.6 and jsonschema 4.26.0. A Pi run, its full dependency set and co-resident service memory remain separate acceptance work. These tests do not measure Pi latency or ML detection quality.

## Files and entry points

| File | Purpose |
| --- | --- |
| `common/schemas/anomaly_result.json` | Strict, versioned Draft 2020-12 nested anomaly schema. |
| `dcamr/anomaly_engine/contract.py` | Strict JSON parsing, serialization, semantic validation and immutable dispatch binding. |
| `dcamr/anomaly_engine/scoring.py` | Frozen normal-reference mapper with tie handling and threshold classification. |
| `tests/fixtures/anomaly/manifest.json` | Eight complete result fixtures and expected values. |
| `tests/fixtures/anomaly/score-cases.json` | Seven mock raw-score/reference cases. |
| `scripts/lab/replay_anomaly_fixtures.py` | Offline fixture validation/replay; emits a summary without authorizing anything. |
| `tests/test_anomaly_contract.py`, `tests/test_anomaly_engine.py` | Malformed inputs, fail states, boundary math, fixture isolation and stale/substituted bindings. |

The fixture README explains which parts of the PRD's broader 22 scenarios are covered. Most end-to-end scenarios require team-owned components that are still empty skeletons. A timeout fixture validates a timeout **record**; it does not implement cancellation. A policy-denial fixture validates a skipped **record**; it does not implement policy evaluation.

## Consume a result in DCAMR

This proposed call sequence applies when the Pi is the ready OFFLINE authority. ONLINE synchronization does not turn enterprise-executed activity into a request awaiting Pi approval. No live handover or authenticated transport is implied by this example.

```python
from dcamr.anomaly_engine.contract import EvaluationBinding, parse_result

# BEFORE dispatch: supplied by trusted DCAMR components, never by the agent
# or copied from an arriving result. All fields are required, including nulls.
binding = EvaluationBinding.capture({
    "evaluation_id": evaluation_id,
    "previous_evaluation_id": previous_evaluation_id,
    "request_id": normalized_request_id,
    "request_sha256": normalized_request_digest,
    "input_snapshot": immutable_snapshot_metadata,
    "baseline": accepted_baseline_metadata,
    "model": accepted_model_metadata,
    "calibration": accepted_calibration_metadata,
})

# AFTER evaluation: parse and compare to the independently captured context.
anomaly = parse_result(result_bytes)
binding.check(anomaly, active_artifacts={
    "baseline": current_baseline_metadata,
    "model": current_model_metadata,
    "calibration": current_calibration_metadata,
})

# DCAMR then applies its own policy/evidence/context logic. A successful check
# returns None; it never returns ALLOW or an execution token.
```

`ContractError` means the payload must not be used as a successful result. In the OFFLINE authorization path, DCAMR must record an appropriate rejection and remain blocked, preserving any deterministic denial. Schema validation alone is insufficient: binding, package trust, evidence verification, freshness, current policy and enforcement remain necessary. Handle late results and active artifact changes through bounded re-evaluation or a blocked outcome in the future adapter. Authority changes also require an agreed invalidate/revalidate rule; this helper does not supply it.

For a policy-denial short circuit, build a separate skipped context before model dispatch, with `model=None`; do not compare a skipped envelope against a binding that promised a model evaluation. A clock failure may add `CLOCK_UNTRUSTED` alongside `POLICY_DENY_SHORT_CIRCUIT`, preserving denial with nullable timestamps. This helper does not generate either envelope automatically.

`EvaluationBinding.capture` stores copies of metadata as immutable strings so later mutation of a caller dictionary cannot change the comparison. Its serialization is an internal equality representation, **not** the team's shared canonical request/snapshot hashing protocol. The caller must supply previously computed, trusted digests. Input-hashing and package-verification formats remain to be agreed with the integration team.

Mock results use `runtime.execution_mode="FIXTURE"`. `binding.check` rejects them by default. `allow_fixtures=True` is for an isolated test harness only; never wire an agent parameter to it. The mode is a marker, not an authentication mechanism: restricting who can produce results is a separate DCAMR trust boundary.

The outer raw-decision schema remains team-owned. Embed the validated nested result in `raw_decision.anomaly`; read the machine outcome from DCAMR's outer decision. Do not derive a decision from the score or overwrite the outer record in a dashboard.

## Contract details enforced by Python

The JSON schema describes fields, allowed statuses, nullability, enums and bounds. The Python boundary also checks properties that schema consumers must not overlook:

- At most 16 KiB UTF-8 JSON; duplicate keys, non-finite values, malformed Unicode and excessive nesting are rejected. Object/list limits are checked before schema traversal.
- Actual valid UTC calendar timestamps, ending in `Z` or `+00:00`. This draft excludes leap-second notation, matching Python's datetime parser. Null time requires `CLOCK_UNTRUSTED` and the corresponding `quality.missing_fields` path: `evaluated_at` or `input_snapshot.observed_at`.
- Sorted unique reasons, quality paths and factor IDs; unknown observations need matching quality paths and explanatory availability/input reasons.
- Status/reason consistency: failures must carry a matching failure code; OK contains only behavioral reasons. Elevated/high bands carry the corresponding model reason. `WITHIN_BASELINE` cannot coexist with unusual/unknown factors.
- Threshold order and unrounded band consistency; successful scoring requires at least 1,000 normal calibration observations. OK must not report missing/stale/unsupported feature inputs.
- `source` identifies the exact accepted baseline using `OPS_BASELINE:{package_id}/{version}`.
- Separate dispatch checks bind evaluation/request/snapshot/artifact metadata and reject an OK result when the active artifact set has changed.

`CalibrationReference` accepts 1,000–100,000 finite normal raw scores with more than one distinct value, freezes a sorted copy once, and uses binary search for each score. The upper limit bounds this mapper's input allocation; it is a new implementation limit within the proposed Pi artifact budget. This function does not authenticate or statistically validate the reference, and an evaluator must not skip those checks simply because construction succeeded.

The replay intentionally uses inert digest strings and injected raw scores from the PRD. It checks contract math and transport invariants; it cannot prove model calibration or reconstruct real artifact hashes. Cross-field structure validation cannot independently recompute a score without the separately authenticated calibration data.

## Feature-builder increment

Jared selected **routine diagnostics plus occasional changes to known destinations** and approved same-role/mission cohort fallback for new authenticated agents with an explicit novelty flag. The [implemented feature profile and runnable fixtures](anomaly-features.md) cover these choices. This describes usual behavior, not policy permission. The separate Mac lab uses these inputs; model format and Pi measurements remain future checkpoints. The [motor/USB data update](../decisions/2026-09-05-data-direction.md) requires a separately versioned motor profile.

The 2 GB Pi constraint remains: one scoring worker, no Pi training or LLM, bounded history/queue/payloads and measured memory. The PRD's 256 MiB worker RSS and 384 MiB load-peak targets are still unmeasured budgets; timeout, queue and history enforcement are not implemented by this output-contract slice.
