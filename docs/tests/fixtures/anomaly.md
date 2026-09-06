# Anomaly contract fixtures

Fixture files remain in `tests/fixtures/anomaly/` at the repository root.
Names below refer to that data directory, not this documentation folder.

These deterministic mock payloads let DCAMR and the dashboard validate the proposed
`1.0.0-draft.1` anomaly contract before a model or evaluator exists. Each result
file contains the complete object that DCAMR embeds at `raw_decision.anomaly`.
It is not a complete decision record. DCAMR owns the outer decision and all
authorization behavior; these fixtures contain no execution permissions or
expected authorization decisions.

All result files have `runtime.execution_mode: "FIXTURE"`. Consume them only
through an explicitly enabled lab fixture path. A live consumer must reject
fixture output. The repeated 64-character hexadecimal values are inert mock
identifiers, not computed input hashes, artifact signatures, or evidence of
verification. The fixed timestamps, durations, source references, and artifact
metadata are also synthetic. These files supply no model artifact or authority
to load one.

## Files and consumption

`manifest.json` uses `fixture_format: "anomaly-results-v1"`. Its ordered `cases`
list gives a unique `id`, a `result_file` relative to this directory, and the
expected anomaly `status`, `result`, and `score`. Load and validate the result
before comparing it with those expectations. Preserve null scores for all
non-OK results; never turn them into zero. Bands describe behavior only, and a
low score cannot suppress the independent `AGENT_UNSEEN` observation.

| Result file | Case | Expected anomaly |
| --- | --- | --- |
| `scored-low.json` | A01 normal diagnostic | `OK`, `LOW`, `0.475`; within-baseline observation |
| `scored-elevated.json` | A02 new destination | `OK`, `ELEVATED`, `0.97`; destination novelty |
| `scored-high.json` | A03 high behavior, result subset | `OK`, `HIGH`, `0.995`; destination novelty |
| `skipped-policy-deny.json` | A04 policy short circuit, result subset | `SKIPPED`, `UNKNOWN`, null score |
| `new-agent-low.json` | A05 new authenticated agent | `OK`, `LOW`, `0.475`; agent novelty remains explicit |
| `unavailable.json` | A07 missing artifacts | `UNAVAILABLE`, `UNKNOWN`, null score |
| `clock-untrusted.json` | A12 untrusted clock, result subset | `UNAVAILABLE`, `UNKNOWN`, null UTC fields and score |
| `timeout.json` | A18 timeout, result subset | `TIMEOUT`, `UNKNOWN`, null score |

`scored-elevated.json` and `unavailable.json` reproduce the nested payloads in
PRD Sections 8.2 and 8.3. `score-cases.json` reproduces Section 8.1 separately:
expand its calibration segments into the specified counts, then apply the
documented normal-tail rank mapping and thresholds. It exercises raw-score
ties, severity boundaries, and score endpoints without inference. The mock
calibration metadata in scored result files describes that same 1,000-score
reference and provisional `demo-tail-v1` severity profile.

The untrusted-clock example assumes that no artifacts could be accepted because
validity cannot be established. Its trusted UTC fields stay null, and the quality
paths identify both missing times. The timeout example retains captured artifact
metadata for diagnosis but has no usable score. A skipped result does not claim
that any baseline or model was loaded. All reasons and factors are sorted, and
all durations are synthetic zero values, not performance measurements.

## Scope of this increment

Replay validates result shape, invariants, deterministic rank arithmetic, and
consumer handling of known outputs. It does **not** demonstrate that a trained
Isolation Forest detects these scenarios, validate feature construction, or
measure Raspberry Pi resource use. No runtime parameters or thresholds have
been tuned on measured data.

The A01–A22 labels trace to the [PRD](../../prds/anomaly-model-prd.md);
they do not claim full integration-scenario coverage. This directory does not yet
contain the proposed request/snapshot bodies, computed binding hashes, artifact
packages, faults, scorer invocation checks, or DCAMR context. A03 has no sequence
feature because sequence encoding and smoothing are pending design. A04 does not
prove zero model calls; A18 does not implement or test a deadline. Broader tests
of policy precedence, evidence, context rounds, history, provenance binding,
artifact replacement, overload, DDIL, live enforcement isolation, and the other
A01–A22 assertions remain for their owning integration increments.
