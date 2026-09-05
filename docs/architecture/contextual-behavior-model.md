# Contextual behavior model

This increment adds a general, context-conditioned Isolation Forest interface for **PRE_ACTION** and **POST_ACTION** assessment. It accepts a fixed numeric feature profile and supplied evidence; it does not yet know what normal ESP, light, or voltage behavior looks like. Real operating data and the device contract will be defined later.

The existing [cyber feature builder](../contracts/anomaly-features.md), [anomaly result contract](../contracts/anomaly-contract.md), and published training experiments remain unchanged. This new interface has its own `context-behavior-assessment-v1` output; a DCAMR adapter and dashboard agreement remain pending.

The [local model-to-ledger replay](decision-evidence-ledger.md#verification-scope)
checks supplied assessments through compact projection, durable recording, sealing
and restart. Run `.venv/bin/python -m lab.replay_contextual_ledger` with the audit
and training dependencies installed. It uses synthetic fixtures and temporary
evidence, and does not connect a live adapter or dashboard.

## What “context” means here

A profile defines an ordered list of numeric features with explicit units and freshness limits, plus one to four categorical context keys. Each exact context tuple gets its **own forest and held-out normal calibration reference**. For example, two operating modes can have different normal distributions for the same measurement. The model never silently uses a different context when it lacks support for the requested one.

Context values select a forest and reference; they are not numeric feature encodings or permission grants. Numeric requested parameters, state and history summaries are scored together within that context. Trusted adapters must establish context from authenticated requests and system state. Letting an agent freely claim a more favorable mode would undermine this comparison.

| Assessment | Question answered | Evidence boundary |
|---|---|---|
| `PRE_ACTION` | Is the requested action unusual given the available state and history? | Cutoff equals request time; no execution metadata or later sensor readings. |
| `POST_ACTION` | Is the observed result unusual for this action and context? | Separate execution ID and timestamp, followed by an observation cutoff. |

Use separate profiles and fitted models for the two phases. Each feature declares `timing`: `AT_OR_BEFORE_REQUEST` for request-time context or `AT_OR_AFTER_EXECUTION` for resulting observations. PRE_ACTION profiles allow only request-time features. POST_ACTION profiles must include at least one result feature and can also preserve request-time context. The parser checks the corresponding timestamp boundary and freshness; trusted timestamps alone cannot prove causality or that a light changed state.

Raw sensor parsing, sampling, voltage conversion, time-window aggregation, action-history summaries, expected-versus-actual feature calculations, and trusted identity/context enrichment remain adapter work. Supplied numeric features can represent measurements, requested parameters, or those summaries. Free-form agent explanations do not become numerical evidence automatically.

Possible later light/voltage features include requested output level, recent voltage statistics, action rate, time since the previous change, and post-action voltage change. These are candidate meanings, not chosen field names, windows, normal ranges or physical safety limits.

## Current modules

| Module | Responsibility |
|---|---|
| [`context_profile.py`](../../dcamr/anomaly_engine/context_profile.py) | Parse immutable profiles and observations; validate exact fields, units, phase, time, size and byte digests. |
| [`contextual_model.py`](../../dcamr/anomaly_engine/contextual_model.py) | Read-only assessment against an exact fitted context, or an explicit unavailable result. |
| [`contextual_training.py`](../../scripts/lab/contextual_training.py) | Fit independent forests and calibration references on a workstation from approved normal examples. |

Scoring performs no network calls, protected actions, data retention, permission evaluation, fitting or adaptation. ONLINE enterprise execution and OFFLINE local governance remain as defined in the [architecture](../prds/ALICE-DCAMR-Architecture.md). A low anomaly score does not authorize an action; a high score is evidence for decision fusion, not an automatic policy denial.

## Profile and observation contract

Profile schema version is `context-behavior-profile-v1`. Required fields are `schema_version`, `profile_id`, `version`, `phase`, `features`, and `context_keys`. Each feature contains exactly `name`, `unit`, `max_age_ms`, and `timing`. Feature names are unique; profile order determines vector order.

Observation schema version is `context-behavior-observation-v1`:

| Required field | Meaning |
|---|---|
| `schema_version`, `profile_sha256` | Contract version and digest of the exact profile bytes. |
| `observation_id`, `request_id`, `session_id` | Distinct observation, originating request, and complete collection-session identity. |
| `phase`, `request_at_ms`, `cutoff_at_ms` | Phase and integer millisecond timestamps on a consistent clock. |
| `execution_id`, `execution_at_ms` | Both null before execution; required after execution, with request time ≤ execution time ≤ cutoff. |
| `context` | Exactly the profile's context keys, with identifier-valued categories. |
| `measurements` | Exactly the profile's feature names, each containing `value`, `unit`, `observed_at_ms`, and `source_id`. |

Units must match exactly; there is no automatic unit conversion. Values must be finite numbers representable within the float32 range; booleans are not measurements. Each reading must respect its feature's timing boundary, remain at or before the cutoff, and be no older than that feature's freshness limit. A null value, timestamp, or source ID means unavailable telemetry. Omitted fields, unexpected fields, duplicate JSON keys, invalid units, and malformed bindings are rejected rather than repaired.

The limits are 16 KiB per profile, 32 KiB per observation, 32 numeric features, four context keys, and a maximum configured feature age of 24 hours. These are parser ceilings, not recommended sensor settings or guaranteed safe freshness periods. A caller must also enforce live clock trust, source authentication and processing deadlines.

Callers provide SHA-256 expectations for both profile and observation bytes. Digests bind the exact supplied bytes; they do not authenticate the sender or replace signed package verification. `source_id` identifies the originating evidence event or supplied summary, not just the device name. Its stable identity must survive reuse in overlapping windows.

## Minimal untrained example

This runnable example uses an arbitrary unitless engineering signal. Its values and timing exercise the interface; they are **not an ESP baseline or a selected operating range**. It needs only the standard library and repository code.

```python
from hashlib import sha256
from dcamr.anomaly_engine.context_profile import json_bytes, load_context_profile
from dcamr.anomaly_engine.contextual_model import ContextualModel

profile_bytes = json_bytes({
    "schema_version": "context-behavior-profile-v1",
    "profile_id": "example-signal", "version": "1.0.0",
    "phase": "PRE_ACTION", "context_keys": ["operating_mode"],
    "features": [{"name": "signal", "unit": "unitless", "max_age_ms": 1000,
                  "timing": "AT_OR_BEFORE_REQUEST"}],
})
profile_digest = sha256(profile_bytes).hexdigest()
profile = load_context_profile(profile_bytes, expected_sha256=profile_digest)
observation_bytes = json_bytes({
    "schema_version": "context-behavior-observation-v1",
    "profile_sha256": profile_digest,
    "observation_id": "observation-1", "request_id": "request-1",
    "session_id": "collection-session-1", "phase": "PRE_ACTION",
    "request_at_ms": 1000, "cutoff_at_ms": 1000,
    "execution_id": None, "execution_at_ms": None,
    "context": {"operating_mode": "example"},
    "measurements": {"signal": {
        "value": 0.5, "unit": "unitless", "observed_at_ms": 1000,
        "source_id": "measurement-1",
    }},
})
assessment = ContextualModel.untrained(profile).assess(
    observation_bytes, expected_sha256=sha256(observation_bytes).hexdigest(),
)
assert (assessment.status, assessment.result) == ("UNAVAILABLE", "UNKNOWN")
assert assessment.raw_score is None and assessment.score is None
print(assessment.to_dict())
```

## Collecting and fitting data later

1. Select the sensor, units, sampling rate, operating contexts, feature windows and phase-specific feature meanings. Version the resulting profiles before capture. Context selection should distinguish materially different normal operating conditions without making every request its own context.
2. Capture authenticated source evidence, requested actions, actual execution metadata and whole collection-session IDs. Preserve raw evidence in the collection system so that derived values can be reviewed. This module does not provide that collector.
3. Review and explicitly approve normal examples. Neither “the agent requested it,” “a technician approved it,” nor “no alert was logged” is sufficient to label a sample normal automatically. Keep anomalous challenges for evaluation.
4. Split complete collection sessions into training, calibration and independent evaluation sets **before** making overlapping windows. Use the same session assignments for both phase profiles. A session must not be split by context, request, or row merely to increase counts. Keep shared source evidence, request retries and execution lineage out of different splits.
5. Supply `NormalExample(input_bytes=..., input_sha256=..., label="NORMAL")` records to `fit_contextual_model(profile, training_examples, calibration_examples)`. Training and calibration must cover the same contexts, with at least **256 training examples and 1,000 held-out normal calibration examples per context**. These are minimum sample counts, not proof of sufficient independent coverage.
6. Evaluate the fitted model on untouched sessions, including normal transitions, challenging actions, missing/stale telemetry and resulting-state failures. The fitting function does not run this evaluation or decide deployment readiness.

The trainer rejects duplicate observation/request/execution rows and source or session lineage crossing collection sessions or training/calibration splits. A repeated source event must preserve the value and time of the same feature. Honest stable identifiers and trusted normal labels are prerequisites; checks cannot detect deliberately relabeled or republished evidence. Derived summaries do not carry a complete list of underlying raw readings in this interface: the collector must partition sessions before window construction and prevent hidden raw-evidence overlap. Validation of the separate evaluation collection remains the caller's responsibility.

Each context uses 64 trees, at most 256 training samples per tree, seed 1729 by default, float32 feature vectors, `n_jobs=1`, and a one-thread numerical limit. A fitting call supports at most eight contexts and 20,000 total training/calibration examples within 128 MiB of input bytes. Entirely constant training data and unusable calibration references are rejected. Some individually constant features are reported in metadata because their changes may be invisible to the forest.

A genuinely constant operating mode may need a deterministic baseline or another detector. Do not inject fake variation just to make a forest or percentile reference fit.

These are separate forests per **profile, phase and exact context**, not one global forest with only different score thresholds. The existing cyber calibration comparison remains a separate historical experiment.

## Reading an assessment

| Output | Interpretation |
|---|---|
| `status`, `result`, `reason_codes` | Processing outcome; `LOW`, `ELEVATED`, `HIGH`, or `UNKNOWN`, plus explicit evidence/failure reasons. |
| `raw_score`, `score` | Isolation Forest `score_samples` output and calibrated normal-tail rank from 0 to 1. Smaller raw scores indicate more unusual examples; larger calibrated ranks indicate more unusual examples. |
| `phase`, `observation_id`, `request_id`, `input_sha256`, `request_at_ms`, `cutoff_at_ms`, `execution_id`, `execution_at_ms` | Profile phase and observation bindings. Observation-derived fields are populated only after successful input parsing. |
| `profile_sha256`, `model_id`, `model_fingerprint`, `calibration_sha256`, `context` | Exact reference identity. The model fingerprint describes learned in-memory state; it is not a signed artifact. |
| `source_ids`, `factors` | Evidence references and per-feature value/unit comparisons with observed training minima/maxima, timing rule, source ID and observation timestamp. |

The calibrated rank uses `normal_tail_rank_v1` from the existing [scoring contract](../contracts/anomaly-contract.md): `LOW` below 0.95, `ELEVATED` from 0.95 to below 0.99, and `HIGH` at or above 0.99. It is not a probability of compromise, a safety guarantee, or an authorization level.

An untrained model, unseen context, or unavailable required telemetry produces `UNKNOWN` and null scores. Invalid input and scoring errors also produce `UNKNOWN` with a corresponding status/reason; malformed input is not presented as a trusted observation.

This is a synchronous internal API. On parse failure, observation-derived identity fields stay null. A future audit/dashboard adapter must retain its independently captured dispatch/request/input binding for failures; these objects cannot be forwarded as standalone authoritative decision events.

Factors report observed training ranges, **not policy limits, causal explanations or SHAP attribution**. Being inside every individual range does not imply that their combination is normal. Being outside a range does not automatically change the anomaly band. In particular, a feature constant during training may change while the forest still returns `LOW`; the separate range flag preserves that evidence for the eventual decision layer.

## Wazuh and the Pi boundary

Wazuh is a planned source integration for permissions-related context and some auditing. Its agent collects endpoint data and sends it to the Wazuh server. The agent-to-enterprise connection does not itself implement ALICE cache synchronization or DDIL reconciliation. [Wazuh agent documentation](https://documentation.wazuh.com/current/getting-started/components/wazuh-agent.html)

Wazuh RBAC governs access to Wazuh resources. We still need an explicit trusted export and mapping for permissions such as which local agent may change an ESP output; those are not automatically supplied by Wazuh RBAC. Permission checks remain outside this forest. [Wazuh RBAC documentation](https://documentation.wazuh.com/current/user-manual/user-administration/rbac.html)

The Pi has 2 GB RAM. A future Wazuh agent must share the total runtime budget with DCAMR and other services. Keep training, an LLM, and Wazuh manager/indexer workloads off this Pi. Eight contexts per profile is a software ceiling, not a proven Pi deployment budget; loading multiple profiles/phases multiplies model memory. The new code has no measured Pi latency/RAM acceptance, model persistence, signature verification, boot loader, bounded worker queue or process deadline supervisor.

Next work is to agree the actual device/action/context contract and collect representative sessions, then evaluate, package and benchmark a small selected model set. Live ESP ingestion, Wazuh adapters, raw audit export, decision fusion, execution control and post-execution response remain separate integration steps.
