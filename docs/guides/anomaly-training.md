# Mac anomaly training lab

This slice prepares synthetic Web-01 sessions, trains one small Isolation Forest
in memory on the Mac, calibrates it against separate normal sessions, and exports
plain JSON reports. It does not save a deployable model or change the Pi runtime.
See the [implementation tracker](../implementation-tracker.md) for system work and
[updated data direction](../decisions/2026-09-05-data-direction.md) for the motor/USB changes.

A separate [general contextual model](../architecture/contextual-behavior-model.md) now fits and
scores supplied normal observations for exact contexts in separate PRE_ACTION
and POST_ACTION profiles. It does not alter the historical cyber experiments
below or invent an ESP baseline.

## System role and authority

The [canonical architecture](../architecture.md) assigns direct execution to enterprise
controls in **ONLINE** mode. The Pi synchronizes bounded trusted caches and
authenticated activity feeds and sends audit upstream; the lab model does not
make it a mandatory enterprise gateway. **OFFLINE**, the Pi governs local actions
only after controlled handover establishes a single ready authority. Behavioral
scores remain advisory to a separate permissions decision.

These experiments prepare an eventual OFFLINE behavioral component; their results
do not implement control transfer, authorize actions or establish cache/feed trust.
On reconnection the Pi synchronizes directly with enterprise systems, without
using the Technician Mac as a relay. Mode/authority-generation binding, remote
approval proof and in-flight action rules remain future integration requirements,
not fields added to the existing anomaly result or training artifacts. Existing
`policy` machine identifiers remain unchanged while product language uses permissions.

The [console integration handoff](../integration/technician-console.md) describes a
separate, reported Mac review/identity/explanation implementation. It is not a
deployed core integration, and its UI outcomes or facial login do not validate
these candidates. The experiments, numerical results and published historical
reports below retain their original cyber feature/calibration semantics.

## Run

From the repository root, create a Mac Python environment with
`requirements-anomaly-training.txt` (tested with Python 3.12.6). The Pi's
`requirements-anomaly.txt` remains separate.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-anomaly-training.txt
.venv/bin/python -m lab.train_anomaly_model --prepare-only --output artifacts/anomaly-lab/preparation-003
.venv/bin/python -m lab.train_anomaly_model --output artifacts/anomaly-lab/candidate-003
.venv/bin/python -m unittest discover -v
```

Select a new output directory for each run. Existing run directories are never
overwritten. `--prepare-only` performs source validation, session splitting and
readiness checks without importing NumPy/scikit-learn or fitting a model.
`--seed` defaults to `1729`; source generation and split membership are repeatable
with the recorded source/library versions. Timings are measurements and vary.

The default generator uses the fixed Web-01 fixture baseline and produces:

| Partition | Normal requests | Challenge requests | Original sessions |
| --- | ---: | ---: | ---: |
| Fit | 3,600 | 0 | 300 |
| Calibration | 1,200 | 0 | 100 |
| Evaluation | 1,200 | 100 | 200 |

The output directory contains:

- `dataset-manifest.json`: source input digests and session membership, generator
  settings, baseline binding, fixed feature order, source-code/schema/requirements
  digests and split method.
- `training-report.json`: fitted settings, actual library versions, normal and
  challenge results, independent novelty flags, constant columns, reference
  identity and limitations. Preparation mode produces a readiness report instead.
- `calibration-reference.json`: sorted held-out normal scores and fixed `.95/.99`
  boundaries, created only by a training run. This is lab data, not an activated
  signed reference package.

JSON digests cover the exact compact output bytes, without a trailing newline.
The report binds the dataset manifest and calibration file by SHA-256. No model
file exists: `model_persisted=false`, `model_sha256=null`, and
`deployment_ready=false` are deliberate. Generated runs under
`artifacts/anomaly-lab/` are local and ignored by Git. Selected measured outputs
are copied byte-for-byte into the tracked [experiment evidence](../reports/anomaly-lab/README.md)
so teammates can inspect the reports and verify their digest links after cloning.

## Source and split contract

`TrainingExample` carries a session group, scenario, `NORMAL`/`CHALLENGE` label,
immutable source input bytes, their expected digest and the generation baseline's
digest. The generator and trainer share the same captured baseline. The trainer
rejects a generation/training baseline mismatch before building features.

Every vector comes from the existing `build_features()` with exactly
`cyber-behavior-v1` and its 11 columns. There is no hand-authored vector shortcut,
silent row dropping, feature imputation or online learning. A malformed source
aborts the run.

Whole normal session groups are ordered by a seeded hash and split 60/20/20.
All challenge groups go to evaluation. Input order does not change membership.
Shared requests, request digests, snapshots, agent/mission sessions, or overlapping
history identities cannot cross groups. Duplicate current requests and context
retries are rejected in this dataset version. Equal numeric vectors from
independent sessions are valid for this small categorical feature profile.

The lab caps input at 10,000 examples and 128 MiB of source bytes, in addition to
the existing per-input limits. These are Mac dataset limits, not Pi request limits.
They do not constitute a whole-process RSS guarantee.

The synthetic generator uses normal action counts for the initial action and
positive baseline transition rows for subsequent actions, with 30–90 seconds
between normal requests. It creates occasional known-endpoint changes and
separately simulated execution confirmations. The baseline summaries remain fixed;
they are not estimated from any split. Generated action frequencies need not
exactly match the initial-action distribution.

Challenges use independent histories and represent a new agent, unseen endpoint,
unseen target, unseen action transition, or a 40-request burst. Their labels name
constructed scenarios; they do not promise that the forest must detect them.
Normal labels and history completeness are synthetic premises. A real-operations
importer will need trusted curation and lineage, not a renamed lab origin flag.

## Candidate and score semantics

The candidate uses 64 trees, 256 samples per tree, all 11 features, float32 input,
fixed seed, one fitting worker and numerical-library threads limited to one.
The implementation uses `score_samples`, whose lower values indicate greater
unusualness, then passes ordinary Python floats to the existing normal-tail rank
mapper. It does not use `predict`, `decision_function`, or contamination labels
as DCAMR bands. [Scikit-learn IsolationForest documentation](https://scikit-learn.org/1.5/modules/generated/sklearn.ensemble.IsolationForest.html)

At least 256 normal training rows and 1,000 distinct-source held-out normal
calibration rows are required. The reference must contain multiple distinct raw
scores. Those counts establish pipeline prerequisites, not statistical adequacy.

No hyperparameter search or threshold tuning uses the challenge set. The report
separates normal diagnostic and normal state-changing outcomes so that an
acceptable aggregate rate cannot conceal problems with legitimate changes.
Novelty flags remain separate from the forest, especially for columns that stay
constant during normal training. These observations are not learned attribution,
permissions, or full AnomalyResult envelopes.

## First experiment

The first local synthetic run used 1,200 held-out normal requests:

| Normal subgroup | Low | Elevated | High | Elevated or high |
| --- | ---: | ---: | ---: | ---: |
| Diagnostics (1,138) | 1,117 | 21 | 0 | 1.85% |
| Legitimate changes (62) | 35 | 14 | 13 | 43.55% |
| All normal (1,200) | 1,152 | 35 | 13 | 4.00% |

All 20 new-agent and 20 unseen-target challenges scored low; their independent
novelty flags were preserved. Only 4 of 20 bursts and 2 of 20 unseen endpoints
reached elevated/high. These are measured limitations of this synthetic candidate,
not detection-rate estimates for real attacks. The reference had 80 distinct raw
scores. Four training columns were constant: agent, action, target and
profile-target familiarity.

## Separate-reference experiment

Jared selected **try separate calibration references for diagnostics and
state-changing actions** after reviewing the legitimate-change rate. The separate
comparison command implements that experiment without changing the original
training command, the anomaly result contract, or any Pi runtime:

```sh
.venv/bin/python -m lab.compare_anomaly_calibration --output artifacts/anomaly-lab/calibration-comparison-002
```

The [first comparison report](../reports/anomaly-lab/calibration-comparison-001/comparison-report.json)
uses the same 64-tree forest and fixed `.95/.99` thresholds for both mappings.
It collected 1,000 distinct normal source requests per family by filtering
ordinary generated sessions from fresh seeds `1730..1732`: 15,628 requests were
examined, within a 48,000-request bound. The diagnostic reference covers 91
sessions and the change reference 749 sessions. Requests within a session can be
correlated; they are not claimed to be 1,000 statistically independent samples.

The original model's entire source pool, both conditional references, and a fresh
evaluation pool use disjoint lineage. Evaluation uses seed `1829` and contains
1,200 normal requests plus 100 challenges. Each raw score is calculated once and
mapped both ways; novelty flags remain identical. Missing/unsupported routing,
insufficient reference support, or degenerate references fail explicitly. There
is no fallback to a convenient global score.

The following are paired results on that **fresh evaluation set**, so its global
column differs from the first experiment above:

| Normal subgroup | Shared reference: elevated/high | Separate references: elevated/high |
| --- | ---: | ---: |
| Diagnostics (1,132) | 23 / 1,132 (2.03%) | 38 / 1,132 (3.36%) |
| Legitimate changes (68) | 32 / 68 (47.06%) | 2 / 68 (2.94%) |
| All normal (1,200) | 55 / 1,200 (4.58%) | 40 / 1,200 (3.33%) |

This improves the treatment of legitimate changes in these synthetic sessions,
but has tradeoffs. Elevated/high unseen-destination outcomes fell from 4/20 to
0/20; unusual-sequence outcomes fell from 6/20 to 1/20. Burst outcomes rose from
7/20 to 12/20. Independent endpoint/sequence/agent/target novelty remains visible
and must still reach future fusion; a low conditional rank cannot erase it.
These small constructed scenarios do not establish real-world detection quality
or justify activation of this candidate.

The command emits `comparison-report.json`, `comparison-references.json`, and
`comparison-membership.json`. Their digest links bind exact JSON bytes, source
code, runtime, baseline, cohort routing and all retained source/evaluation
memberships. The model remains in memory only. The routing method explicitly
supports the current five-action cyber profile; it is not a motor classifier.
All 103 current tests pass, and the generated artifact digests and 1,300 paired
score mappings were independently checked.

Once evaluation results inform a design choice, subsequent reuse of that set is
exploratory. Reserve fresh sessions and real curated data for final assessment.

The latest motor-control direction also needs its own feature/baseline contract.
It must not reuse cyber columns or claim that a Web-01 score describes servo
movement. Model persistence format, signed model/reference binding, the Pi loader,
live result adaptation and actual 2 GB Pi measurements remain separate checkpoints.
