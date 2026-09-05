"""Mac-only comparison of global versus action-family calibration; no deployment."""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.features import build_features
from dcamr.anomaly_engine.feature_types import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from dcamr.anomaly_engine.scoring import CalibrationReference, MIN_CALIBRATION_SAMPLES
from .anomaly_training import (
    DEFAULT_SEED, MAX_DATASET_BYTES, PreparedExample, json_bytes, prepare_dataset,
    train_and_evaluate,
)
from .synthetic_anomaly_data import generate_examples
from .train_anomaly_model import BASELINE_PATH, ROOT, SOURCE_FILES


COHORTS = ("diagnostic", "state_change")
REFERENCE_SIZE = MIN_CALIBRATION_SAMPLES
MAX_REFERENCE_BATCHES = 8
ROWS_PER_BATCH = 500 * 12
MAX_REFERENCE_ROWS = MAX_REFERENCE_BATCHES * ROWS_PER_BATCH
ROUTING_METHOD = "cyber-behavior-v1_destination-applicable_v1"


def route_batch(batch) -> str:
    """Route only this fixed cyber profile; absent/unknown routing never falls back."""
    if (batch.feature_schema_version != FEATURE_SCHEMA_VERSION
            or batch.names != FEATURE_NAMES or len(batch.values) != len(FEATURE_NAMES)):
        raise ValueError("unsupported feature profile for conditional calibration")
    flag = batch.values[FEATURE_NAMES.index("destination_applicable")]
    if type(flag) not in (int, float) or flag not in (0, 1):
        raise ValueError("invalid destination applicability for calibration routing")
    return COHORTS[int(flag)]


class LineageGuard:
    """Prevent reuse of sessions, source records, or snapshots across experiment sets."""

    def __init__(self):
        self.owners = {}
        self.current_requests = set()

    def observe(self, example, partition: str) -> None:
        if sha256(example.input_bytes).hexdigest() != example.input_sha256:
            raise ValueError("source digest mismatch in comparison lineage")
        payload = json.loads(example.input_bytes)
        request, snapshot = payload["request"], payload["snapshot"]
        key = (partition, request["request_id"])
        if key in self.current_requests:
            raise ValueError("duplicate current source request in comparison")
        self.current_requests.add(key)
        tokens = [("group", example.group_id), ("input", example.input_sha256),
                  ("snapshot_id", snapshot["id"]), ("snapshot_digest", snapshot["sha256"])]
        for record in (request, *snapshot["history"]["proposals"],
                       *snapshot["history"]["executions"]):
            tokens.extend((("session", (record["agent_id"], record["mission_id"])),
                           ("request_id", record["request_id"]),
                           ("request_digest", record["request_sha256"])))
        for token in tokens:
            if self.owners.setdefault(token, partition) != partition:
                raise ValueError("source lineage overlaps comparison partitions")


def _tracked(examples, guard, partition):
    for example in examples:
        # The downstream prepare_dataset validates exact bytes and baseline binding.
        guard.observe(example, partition)
        yield example


def collect_reference_sources(baseline, *, seed, guard, max_batches=MAX_REFERENCE_BATCHES,
                              generator=generate_examples):
    """Filter ordinary fresh normal requests; retain 1,000 actual sources per family.

    Source requests are unique, but requests within a session are correlated. The
    membership report preserves session counts rather than claiming independence.
    """
    if type(max_batches) is not int or not 1 <= max_batches <= MAX_REFERENCE_BATCHES:
        raise ValueError("reference batches must be in 1..8")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 102:
        raise ValueError("seed must leave room for disjoint reference/evaluation seeds")
    retained = {cohort: [] for cohort in COHORTS}
    examined = 0
    batches = []
    for offset in range(1, max_batches + 1):
        batch_seed = seed + offset
        count = byte_count = 0
        batch_report = {"seed": batch_seed, "examined_rows": 0,
                        "retained": {cohort: 0 for cohort in COHORTS}}
        batches.append(batch_report)
        for example in generator(baseline=baseline, seed=batch_seed, normal_sessions=500,
                                 requests_per_session=12, challenge_sessions_per_scenario=0):
            count += 1
            examined += 1
            byte_count += len(example.input_bytes)
            if count > ROWS_PER_BATCH or examined > MAX_REFERENCE_ROWS or byte_count > MAX_DATASET_BYTES:
                raise ValueError("conditional reference source budget exceeded")
            if example.label != "NORMAL" or example.baseline_sha256 != baseline.identity.sha256:
                raise ValueError("conditional references require normal sources bound to the same baseline")
            batch = build_features(example.input_bytes, baseline, expected_sha256=example.input_sha256)
            if batch.context_attempt != 0:
                raise ValueError("context retries cannot enter conditional references")
            guard.observe(example, "conditional_reference")
            cohort = route_batch(batch)
            batch_report["examined_rows"] = count
            if len(retained[cohort]) < REFERENCE_SIZE:
                retained[cohort].append(PreparedExample(example.group_id, example.scenario,
                                                       example.label, batch))
                batch_report["retained"][cohort] += 1
            if all(len(rows) == REFERENCE_SIZE for rows in retained.values()):
                return {key: tuple(value) for key, value in retained.items()}, {
                    "examined_rows": examined, "batches": batches,
                    "sampling": "first_1000_unique_normal_requests_per_family_in_generated_order",
                    "max_examined_rows": MAX_REFERENCE_ROWS,
                }
    sizes = {key: len(value) for key, value in retained.items()}
    raise ValueError(f"insufficient conditional references after bounded generation: {sizes}")


def compare_scores(rows, raw_scores, global_reference, conditional_references):
    """Map each single unchanged raw score both ways; preserve independent flags."""
    if set(conditional_references) != set(COHORTS):
        raise ValueError("both conditional references are required; no global fallback")
    thresholds = (global_reference.elevated_min, global_reference.high_min)
    if thresholds != (0.95, 0.99):
        raise ValueError("comparison holds the original 0.95/0.99 thresholds fixed")
    for reference in conditional_references.values():
        if (reference.elevated_min, reference.high_min) != thresholds:
            raise ValueError("conditional thresholds must match the fixed global thresholds")
    if len(rows) != len(raw_scores):
        raise ValueError("evaluation row/raw-score counts differ")
    measured = []
    for row, raw in zip(rows, raw_scores):
        cohort = route_batch(row.batch)
        global_score = global_reference.score(raw)
        conditional = conditional_references[cohort].score(raw)
        measured.append({
            "group_id": row.group_id, "scenario": row.scenario, "label": row.label,
            "request_id": row.batch.request_id, "input_sha256": row.batch.input_sha256,
            "baseline_sha256": row.batch.baseline.sha256, "cohort": cohort,
            "raw_score": raw, "novelty_flags": list(row.batch.novelty_flags),
            "global": {"score": global_score.score, "band": global_score.result},
            "conditional": {"score": conditional.score, "band": conditional.result},
        })
    return measured


def _summary(rows, method):
    bands = Counter(row[method]["band"] for row in rows)
    count = len(rows)
    return {"sample_count": count,
            "bands": {band: bands[band] for band in ("LOW", "ELEVATED", "HIGH")},
            "elevated_or_high_fraction": (bands["ELEVATED"] + bands["HIGH"]) / count if count else None}


def _member(row):
    batch = row.batch
    return {"group_id": row.group_id, "scenario": row.scenario, "label": row.label,
            "input_sha256": batch.input_sha256, "request_id": batch.request_id,
            "request_sha256": batch.request_sha256, "snapshot_id": batch.snapshot_id,
            "snapshot_sha256": batch.snapshot_sha256, "baseline_sha256": batch.baseline.sha256}


def run_comparison(baseline, *, seed=DEFAULT_SEED):
    """Fit the existing forest once, collect fresh references, evaluate fresh sessions."""
    if type(seed) is not int or not 0 <= seed <= 2**32 - 102:
        raise ValueError("seed must leave room for disjoint reference/evaluation seeds")
    guard = LineageGuard()
    run = train_and_evaluate(_tracked(generate_examples(baseline=baseline, seed=seed),
                                     guard, "original_pipeline"), baseline, seed=seed)
    sources, sampling = collect_reference_sources(baseline, seed=seed, guard=guard)
    fresh_seed = seed + 100
    fresh = prepare_dataset(_tracked(generate_examples(baseline=baseline, seed=fresh_seed),
                                      guard, "fresh_evaluation_pool"), baseline, seed=fresh_seed)
    evaluation = fresh.evaluation

    import numpy as np
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=1):
        references = {
            cohort: CalibrationReference(run.model.score_samples(
                np.asarray([row.batch.values for row in rows], dtype=np.float32)).tolist())
            for cohort, rows in sources.items()
        }
        raw = run.model.score_samples(np.asarray([row.batch.values for row in evaluation],
                                                 dtype=np.float32)).tolist()
    measured = compare_scores(evaluation, raw, run.calibration, references)
    reference_payload = {
        "schema_version": "lab-conditional-calibration-v1", "deployment_ready": False,
        "model_persisted": False, "model_sha256": None,
        "baseline": asdict(baseline.identity), "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "routing_method": ROUTING_METHOD, "score_method": "normal_tail_rank_v1",
        "raw_score_method": "sklearn_isolation_forest.score_samples",
        "elevated_min": 0.95, "high_min": 0.99,
        "references": {name: {"sample_count": len(ref.samples), "samples": list(ref.samples)}
                       for name, ref in {"global": run.calibration, **references}.items()},
    }
    membership = {
        "schema_version": "lab-calibration-comparison-membership-v1", "origin": "SYNTHETIC",
        "baseline": asdict(baseline.identity), "original_pipeline_seed": seed,
        "original_pipeline": run.report["dataset"], "conditional_sampling": sampling,
        "conditional_sources": {
            cohort: {"sample_count": len(rows), "session_count": len({r.group_id for r in rows}),
                     "members": [_member(row) for row in rows]}
            for cohort, rows in sources.items()
        },
        "fresh_evaluation_seed": fresh_seed, "fresh_pool": fresh.manifest(),
        "evaluated_members": [_member(row) for row in evaluation],
        "lineage_check": "No group, session, request identity/digest or snapshot overlaps across the three pools.",
    }
    normals = [row for row in measured if row["label"] == "NORMAL"]
    scenarios = sorted({row["scenario"] for row in measured if row["label"] == "CHALLENGE"})
    report = {
        "schema_version": "lab-calibration-comparison-v1", "status": "SYNTHETIC_COMPARISON",
        "deployment_ready": False, "model_persisted": False, "model_sha256": None,
        "baseline": asdict(baseline.identity), "model": run.report["model"],
        "runtime": run.report["runtime"], "routing_method": ROUTING_METHOD,
        "feature_schema_version": FEATURE_SCHEMA_VERSION, "feature_names": list(FEATURE_NAMES),
        "constant_training_features": run.report["constant_training_features"],
        "thresholds": {"elevated_min": 0.95, "high_min": 0.99},
        "normal_evaluation": {method: _summary(normals, method) for method in ("global", "conditional")},
        "normal_by_family": {
            cohort: {method: _summary([row for row in normals if row["cohort"] == cohort], method)
                     for method in ("global", "conditional")}
            for cohort in COHORTS
        },
        "challenge_scenarios": {
            scenario: {method: _summary([row for row in measured if row["label"] == "CHALLENGE"
                                         and row["scenario"] == scenario], method)
                       for method in ("global", "conditional")}
            for scenario in scenarios
        },
        "evaluation_samples": measured,
        "reference_statistics": {
            name: {"sample_count": ref["sample_count"], "distinct_raw_scores": len(set(ref["samples"])),
                   "sha256": sha256(json_bytes(ref)).hexdigest()}
            for name, ref in reference_payload["references"].items()
        },
        "limitations": [
            "Synthetic comparison only; independent source requests can share a correlated session.",
            "One unchanged fitted forest; only its raw-score reference distribution changes.",
            "The existing global reference has 1200 samples and each conditional reference has 1000.",
            "First-per-family sampling is bounded; family references can cover different generator seeds.",
            "Fresh evaluation sessions were excluded from both fitting and conditional calibration.",
            "A low conditional band cannot suppress novelty flags or authorize an action.",
            "No persisted model, active reference update, motor profile, or Pi deployment.",
        ],
    }
    return report, reference_payload, membership


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory for JSON comparison artifacts")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output directory exists; choose a new directory to preserve prior runs")
    try:
        data = BASELINE_PATH.read_bytes()
        baseline = load_baseline(data, expected_sha256=sha256(data).hexdigest())
        files = (*SOURCE_FILES, "lab/compare_anomaly_calibration.py")
        hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
        report, references, membership = run_comparison(baseline, seed=args.seed)
        membership["generator"] = {"version": "web01-synthetic-v1", "normal_sessions": 500,
                                   "requests_per_session": 12, "evaluation_challenge_sessions_per_scenario": 20}
        membership["source_sha256"] = hashes
        membership["source_set_sha256"] = sha256(json_bytes(hashes)).hexdigest()
        encoded_membership, encoded_references = json_bytes(membership), json_bytes(references)
        report["membership_sha256"] = sha256(encoded_membership).hexdigest()
        report["references_sha256"] = sha256(encoded_references).hexdigest()
        outputs = {"comparison-report.json": json_bytes(report),
                   "comparison-references.json": encoded_references,
                   "comparison-membership.json": encoded_membership}
        args.output.mkdir(parents=True, exist_ok=False)
        for name, payload in outputs.items():
            with (args.output / name).open("xb") as stream:
                stream.write(payload)
        print(json.dumps({"status": report["status"], "output": str(args.output.resolve()),
                          "normal_by_family": report["normal_by_family"],
                          "reference_statistics": report["reference_statistics"],
                          "sampling": membership["conditional_sampling"]}, indent=2))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"Calibration comparison failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
