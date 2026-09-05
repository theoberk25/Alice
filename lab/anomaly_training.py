"""Mac-only candidate training. No model persistence, activation, or decisions."""

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import islice
import json
import platform
import re
from time import perf_counter

from dcamr.anomaly_engine.baseline import OperationalBaseline
from dcamr.anomaly_engine.features import build_features
from dcamr.anomaly_engine.feature_types import (
    FEATURE_NAMES, FEATURE_SCHEMA_VERSION, BaselineIdentity, FeatureBatch,
)
from dcamr.anomaly_engine.feature_validation import MAX_FEATURE_INPUT_BYTES
from dcamr.anomaly_engine.scoring import CalibrationReference, MIN_CALIBRATION_SAMPLES


MAX_EXAMPLES = 10_000
MAX_DATASET_BYTES = 128 * 1024 * 1024
ESTIMATORS = 64
TREE_SAMPLES = 256
DEFAULT_SEED = 1729
_LABELS = {"NORMAL", "CHALLENGE"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


def json_bytes(value: object) -> bytes:
    """Deterministic lab serialization, not DCAMR's shared signing protocol."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class TrainingExample:
    group_id: str
    scenario: str
    label: str
    input_bytes: bytes
    input_sha256: str
    baseline_sha256: str


@dataclass(frozen=True, slots=True)
class PreparedExample:
    group_id: str
    scenario: str
    label: str
    batch: FeatureBatch


@dataclass(frozen=True, slots=True)
class PreparedDataset:
    train: tuple[PreparedExample, ...]
    calibration: tuple[PreparedExample, ...]
    evaluation: tuple[PreparedExample, ...]
    seed: int
    baseline: BaselineIdentity

    def manifest(self) -> dict:
        splits = {}
        for name in ("train", "calibration", "evaluation"):
            rows = getattr(self, name)
            members = [{"group_id": r.group_id, "scenario": r.scenario,
                        "label": r.label, "input_sha256": r.batch.input_sha256}
                       for r in rows]
            splits[name] = {
                "sample_count": len(rows),
                "session_count": len({r.group_id for r in rows}),
                "labels": dict(sorted(Counter(r.label for r in rows).items())),
                "scenarios": dict(sorted(Counter(r.scenario for r in rows).items())),
                "membership_sha256": sha256(json_bytes(members)).hexdigest(),
                "members": members,
            }
        return {
            "schema_version": "lab-training-dataset-v1",
            "origin": "SYNTHETIC", "seed": self.seed,
            "baseline": asdict(self.baseline),
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "feature_names": list(FEATURE_NAMES),
            "split_method": "session_hash_order_60_20_20_challenges_evaluation_only_v1",
            "splits": splits,
            "authentication": "Local synthetic inputs; digests establish reproducibility only.",
        }


def _check_seed(seed: int) -> None:
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be an integer in 0..2^32-1")


def prepare_dataset(examples, baseline: OperationalBaseline, *, seed: int = DEFAULT_SEED) -> PreparedDataset:
    """Validate every source, enforce lineage isolation, then split whole sessions.

    This entry point is for generated synthetic lab inputs. A real-operations
    importer must establish trusted normal labels and source lineage separately.
    Invalid rows stop the run; they are never silently dropped or imputed.
    """
    _check_seed(seed)
    groups = {}
    group_types = {}
    owners = {}
    current_requests = set()
    input_digests = set()
    total_bytes = 0

    def claim(kind, identity, group_id):
        key = (kind, identity)
        owner = owners.setdefault(key, group_id)
        if owner != group_id:
            raise ValueError(f"source lineage crosses session groups: {kind}")

    for index, example in enumerate(islice(examples, MAX_EXAMPLES + 1)):
        if index == MAX_EXAMPLES:
            raise ValueError("dataset exceeds example limit")
        if not isinstance(example, TrainingExample):
            raise ValueError("dataset requires TrainingExample sources, not numeric vectors")
        if any(type(v) is not str or not _ID.fullmatch(v)
               for v in (example.group_id, example.scenario)) or type(example.label) is not str or example.label not in _LABELS:
            raise ValueError("invalid dataset group, scenario, or label")
        if type(example.input_bytes) is not bytes or len(example.input_bytes) > MAX_FEATURE_INPUT_BYTES:
            raise ValueError("invalid or oversized source input")
        if example.baseline_sha256 != baseline.identity.sha256:
            raise ValueError("source baseline binding does not match training baseline")
        total_bytes += len(example.input_bytes)
        if total_bytes > MAX_DATASET_BYTES:
            raise ValueError("dataset exceeds byte limit")
        batch = build_features(example.input_bytes, baseline, expected_sha256=example.input_sha256)
        if batch.context_attempt != 0:
            raise ValueError("context retries are excluded from this training dataset version")
        if batch.input_sha256 in input_digests or batch.request_id in current_requests:
            raise ValueError("duplicate current request or source input")
        input_digests.add(batch.input_sha256)
        current_requests.add(batch.request_id)
        group_type = (example.label, example.scenario)
        if group_types.setdefault(example.group_id, group_type) != group_type:
            raise ValueError("a session group must have one classification and scenario")
        # build_features already strictly validated these exact bytes. Inspect
        # source identity here only to catch cross-group history/context leakage.
        payload = json.loads(example.input_bytes)
        request, snapshot = payload["request"], payload["snapshot"]
        claim("session", (request["agent_id"], request["mission_id"]), example.group_id)
        claim("snapshot_id", snapshot["id"], example.group_id)
        claim("snapshot_sha256", snapshot["sha256"], example.group_id)
        records = [request, *snapshot["history"]["proposals"], *snapshot["history"]["executions"]]
        for record in records:
            claim("session", (record["agent_id"], record["mission_id"]), example.group_id)
            claim("request_id", record["request_id"], example.group_id)
            claim("request_sha256", record["request_sha256"], example.group_id)
        groups.setdefault(example.group_id, []).append(
            PreparedExample(example.group_id, example.scenario, example.label, batch))

    normal = [group for group, (label, _) in group_types.items() if label == "NORMAL"]
    if len(normal) < 5:
        raise ValueError("at least five independent normal session groups are required")
    # Membership is independent of input ordering and numeric values. Equal
    # vectors from distinct sessions are valid for these categorical features.
    normal.sort(key=lambda group: (sha256(f"{seed}:{group}".encode()).hexdigest(), group))
    train_end, calibration_end = 3 * len(normal) // 5, 4 * len(normal) // 5
    assigned = {group: "train" for group in normal[:train_end]}
    assigned.update({group: "calibration" for group in normal[train_end:calibration_end]})
    partitions = {name: [] for name in ("train", "calibration", "evaluation")}
    for group in sorted(groups):
        partitions[assigned.get(group, "evaluation")].extend(
            sorted(groups[group], key=lambda row: row.batch.request_id))
    return PreparedDataset(*(tuple(partitions[name]) for name in partitions), seed, baseline.identity)


def training_readiness(dataset: PreparedDataset) -> list[str]:
    reasons = []
    if len(dataset.train) < TREE_SAMPLES:
        reasons.append(f"need at least {TREE_SAMPLES} normal training rows")
    if len(dataset.calibration) < MIN_CALIBRATION_SAMPLES:
        reasons.append(f"need at least {MIN_CALIBRATION_SAMPLES} held-out normal calibration rows")
    if not any(row.label == "NORMAL" for row in dataset.evaluation):
        reasons.append("need held-out normal evaluation rows")
    return reasons


@dataclass(frozen=True, slots=True)
class TrainingRun:
    model: object  # In-memory Mac estimator only; never serialized by this module.
    calibration: CalibrationReference
    report: dict


def train_and_evaluate(examples, baseline: OperationalBaseline, *, seed: int = DEFAULT_SEED) -> TrainingRun:
    """Fit once on normal training sessions and evaluate untouched held-out rows.

    Always goes through source validation and build_features. No alternate
    vector-only path, hyperparameter search, or challenge-driven threshold fit.
    """
    dataset = prepare_dataset(examples, baseline, seed=seed)
    reasons = training_readiness(dataset)
    if reasons:
        raise ValueError("; ".join(reasons))
    # Heavy dependencies live only in this lab function, not the Pi import path.
    import numpy as np
    import sklearn
    import scipy
    import joblib
    import threadpoolctl
    from sklearn.ensemble import IsolationForest
    from threadpoolctl import threadpool_limits

    parameters = dict(n_estimators=ESTIMATORS, max_samples=TREE_SAMPLES,
                      max_features=1.0, contamination="auto", bootstrap=False,
                      random_state=seed, n_jobs=1, warm_start=False)

    def matrix(rows):
        return np.asarray([row.batch.values for row in rows], dtype=np.float32)

    train = matrix(dataset.train)
    started = perf_counter()
    with threadpool_limits(limits=1):
        model = IsolationForest(**parameters).fit(train)
        fit_seconds = perf_counter() - started
        reference = CalibrationReference(model.score_samples(matrix(dataset.calibration)).tolist())
        raw_scores = model.score_samples(matrix(dataset.evaluation)).tolist()
    measured = []
    counts = {}
    for row, raw in zip(dataset.evaluation, raw_scores):
        scored = reference.score(raw)
        key = f"{row.label}:{row.scenario}"
        bands = counts.setdefault(key, Counter())
        bands[scored.result] += 1
        measured.append({"group_id": row.group_id, "scenario": row.scenario,
                         "label": row.label, "request_id": row.batch.request_id,
                         "input_sha256": row.batch.input_sha256,
                         "raw_score": scored.raw_score, "score": scored.score,
                         "band": scored.result, "novelty_flags": list(row.batch.novelty_flags),
                         "action_frequency": row.batch.values[6],
                         "destination_applicable": bool(row.batch.values[4])})

    def summary(rows):
        bands = Counter(row["band"] for row in rows)
        count = len(rows)
        return {"sample_count": count,
                "bands": {band: bands[band] for band in ("LOW", "ELEVATED", "HIGH")},
                "elevated_or_high_fraction": (bands["ELEVATED"] + bands["HIGH"]) / count if count else None}

    normals = [row for row in measured if row["label"] == "NORMAL"]
    calibration_payload = {
        "schema_version": "lab-calibration-v1", "deployment_ready": False,
        "raw_score_method": "sklearn_isolation_forest.score_samples",
        "score_method": "normal_tail_rank_v1",
        "elevated_min": reference.elevated_min, "high_min": reference.high_min,
        "samples": list(reference.samples),
    }
    report = {
        "schema_version": "lab-training-report-v1", "status": "SYNTHETIC_CANDIDATE",
        "deployment_ready": False, "model_persisted": False, "model_sha256": None,
        "dataset": dataset.manifest(),
        "runtime": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                    "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__,
                    "threadpoolctl": threadpoolctl.__version__,
                    "system": platform.system(), "machine": platform.machine(),
                    "numeric_threads": 1, "dtype": "float32"},
        "model": {"algorithm": "IsolationForest", "parameters": parameters,
                  "fitted_max_samples": int(model.max_samples_),
                  "tree_count": len(model.estimators_),
                  "total_tree_nodes": sum(int(tree.tree_.node_count) for tree in model.estimators_),
                  "fit_seconds": fit_seconds},
        "calibration": {"sha256": sha256(json_bytes(calibration_payload)).hexdigest(),
                        "sample_count": len(reference.samples),
                        "distinct_raw_scores": len(set(reference.samples)),
                        "raw_min": reference.samples[0], "raw_max": reference.samples[-1],
                        "reference": calibration_payload},
        "constant_training_features": [name for index, name in enumerate(FEATURE_NAMES)
                                       if np.all(train[:, index] == train[0, index])],
        "normal_evaluation": summary(normals),
        "normal_diagnostics": summary([row for row in normals if not row["destination_applicable"]]),
        "normal_changes": summary([row for row in normals if row["destination_applicable"]]),
        "scenario_bands": {key: {band: value[band] for band in ("LOW", "ELEVATED", "HIGH")}
                           for key, value in sorted(counts.items())},
        "evaluation_samples": measured,
        "limitations": [
            "Synthetic scenarios test the pipeline, not real-world detection accuracy.",
            "Baseline summaries are fixed synthetic inputs, not fitted from this corpus.",
            "Constant novelty columns may be ignored by the forest; retain independent flags.",
            "Bands are behavioral ranks, not permissions or compromise probabilities.",
            "Calibration thresholds are provisional and were not tuned against evaluation scenarios.",
            "No saved model, signature verification, Pi performance measurement, or deployment.",
        ],
    }
    return TrainingRun(model, reference, report)
