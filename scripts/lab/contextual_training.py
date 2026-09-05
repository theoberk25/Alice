"""General context-conditioned Isolation Forest fitting on a workstation.

Training and calibration sources must already be approved normal examples, split
by complete collection session. This module validates source lineage and refuses
insufficient support; it never guesses normal labels or invents ESP operating data.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import islice
import re

from dcamr.anomaly_engine.context_profile import (
    ContextProfile, json_bytes, parse_context_observation,
)
from dcamr.anomaly_engine.contextual_model import ContextualModel, _ContextState
from dcamr.anomaly_engine.scoring import CalibrationReference, MIN_CALIBRATION_SAMPLES


MAX_CONTEXTS = 8
MAX_EXAMPLES = 20_000
MAX_DATASET_BYTES = 128 * 1024 * 1024
ESTIMATORS = 64
TREE_SAMPLES = 256
DEFAULT_SEED = 1729
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class NormalExample:
    input_bytes: bytes
    input_sha256: str
    label: str = "NORMAL"


def fit_contextual_model(
    profile: ContextProfile, training_examples, calibration_examples, *,
    model_id: str = "contextual-candidate", seed: int = DEFAULT_SEED,
) -> ContextualModel:
    """Fit up to eight exact contexts, each with an independent normal reference.

    This is not a data splitter or an evaluation benchmark. Supply complete
    session-disjoint training/calibration collections and keep a third collection
    untouched for evaluation. Caller authentication and trusted normal labels are
    prerequisites. Identifiers/digests detect reuse, not a dishonest data publisher.
    """
    if type(model_id) is not str or not _ID.fullmatch(model_id):
        raise ValueError("invalid model_id")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be an integer in 0..2^32-1")
    grouped = {"train": defaultdict(list), "calibration": defaultdict(list)}
    lineage = {}
    observations, requests = set(), set()
    executions, source_values = set(), {}
    total_bytes = total_rows = 0

    def claim(kind, identifier, split, session_id):
        owner = (split, session_id)
        if lineage.setdefault((kind, identifier), owner) != owner:
            raise ValueError(f"source lineage crosses sessions or splits: {kind}")

    for split, sources in (("train", training_examples), ("calibration", calibration_examples)):
        for row in islice(sources, MAX_EXAMPLES + 1):
            total_rows += 1
            if total_rows > MAX_EXAMPLES:
                raise ValueError("dataset exceeds example limit")
            if not isinstance(row, NormalExample) or row.label != "NORMAL":
                raise ValueError("fitting and calibration require approved NORMAL examples")
            if type(row.input_bytes) is not bytes:
                raise ValueError("normal example requires bounded bytes")
            total_bytes += len(row.input_bytes)
            if total_bytes > MAX_DATASET_BYTES:
                raise ValueError("dataset exceeds byte limit")
            observation = parse_context_observation(
                row.input_bytes, profile, expected_sha256=row.input_sha256)
            if observation.observation_id in observations or observation.request_id in requests:
                raise ValueError("duplicate observation or request; retries are not training rows")
            observations.add(observation.observation_id)
            requests.add(observation.request_id)
            claim("session", observation.session_id, split, observation.session_id)
            claim("input", observation.input_sha256, split, observation.session_id)
            if observation.execution_id is not None:
                if observation.execution_id in executions:
                    raise ValueError("duplicate execution; each outcome requires its own execution")
                executions.add(observation.execution_id)
                claim("execution", observation.execution_id, split, observation.session_id)
            for feature, source, value, observed_at in zip(
                profile.features, observation.source_ids, observation.values,
                observation.observed_at_ms,
            ):
                claim("source", source, split, observation.session_id)
                key = (source, feature.name)
                evidence = (value, feature.unit, observed_at, feature.timing)
                if source_values.setdefault(key, evidence) != evidence:
                    raise ValueError("source feature changed value or observation time")
            grouped[split][observation.context].append(observation)
            if len(grouped[split]) > MAX_CONTEXTS:
                raise ValueError("dataset exceeds supported context limit")
    if not grouped["train"] or grouped["train"].keys() != grouped["calibration"].keys():
        raise ValueError("training and calibration must cover the same nonempty contexts")
    for context in grouped["train"]:
        if len(grouped["train"][context]) < TREE_SAMPLES:
            raise ValueError(f"each context needs at least {TREE_SAMPLES} normal training rows")
        if len(grouped["calibration"][context]) < MIN_CALIBRATION_SAMPLES:
            raise ValueError(f"each context needs at least {MIN_CALIBRATION_SAMPLES} held-out normal calibration rows")
        for split in grouped:
            grouped[split][context].sort(key=lambda row: row.observation_id)

    # Importing the interface alone does not load the training stack on the Pi.
    import numpy as np
    import sklearn
    from sklearn.ensemble import IsolationForest
    from threadpoolctl import threadpool_limits

    parameters = dict(n_estimators=ESTIMATORS, max_samples=TREE_SAMPLES,
                      max_features=1.0, contamination="auto", bootstrap=False,
                      random_state=seed, n_jobs=1, warm_start=False)
    states, details = {}, []
    state_digest = sha256()
    state_digest.update(json_bytes({"profile_sha256": profile.sha256,
                                   "parameters": parameters, "sklearn": sklearn.__version__}))
    for context in sorted(grouped["train"]):
        training = grouped["train"][context]
        calibration = grouped["calibration"][context]
        matrix = np.asarray([row.values for row in training], dtype=np.float32)
        calibration_matrix = np.asarray([row.values for row in calibration], dtype=np.float32)
        if not np.isfinite(matrix).all() or not np.isfinite(calibration_matrix).all():
            raise ValueError("features exceed finite float32 range")
        if np.all(matrix == matrix[0]):
            raise ValueError("all training features are constant; model is not ready")
        with threadpool_limits(limits=1):
            estimator = IsolationForest(**parameters).fit(matrix)
            reference = CalibrationReference(estimator.score_samples(calibration_matrix).tolist())
        # The fingerprint binds learned in-memory state, not a signed deployable
        # artifact. Include dtype/shape with array bytes, plus context/reference.
        context_state_digest = sha256(json_bytes({"context": context, "parameters": parameters}))
        for tree in estimator.estimators_:
            for array in (tree.tree_.children_left, tree.tree_.children_right,
                          tree.tree_.feature, tree.tree_.threshold, tree.tree_.n_node_samples):
                context_state_digest.update(json_bytes({"dtype": array.dtype.str, "shape": array.shape}))
                context_state_digest.update(array.tobytes(order="C"))
        reference_payload = {"context": context, "profile_sha256": profile.sha256,
                             "estimator_fingerprint": context_state_digest.hexdigest(),
                             "score_method": "normal_tail_rank_v1",
                             "elevated_min": reference.elevated_min, "high_min": reference.high_min,
                             "samples": reference.samples}
        calibration_sha256 = sha256(json_bytes(reference_payload)).hexdigest()
        # Retain source precision for observations, not just float32 extrema.
        minima = tuple(min(row.values[i] for row in training) for i in range(len(profile.features)))
        maxima = tuple(max(row.values[i] for row in training) for i in range(len(profile.features)))
        states[context] = _ContextState(estimator, reference, calibration_sha256, minima, maxima)
        memberships = {
            split: [{"observation_id": row.observation_id, "request_id": row.request_id,
                     "session_id": row.session_id, "input_sha256": row.input_sha256}
                    for row in grouped[split][context]]
            for split in grouped
        }
        detail = {
            "context": [list(pair) for pair in context],
            "training_count": len(training), "calibration_count": len(calibration),
            "training_sessions": len({row.session_id for row in training}),
            "calibration_sessions": len({row.session_id for row in calibration}),
            "training_membership_sha256": sha256(json_bytes(memberships["train"])).hexdigest(),
            "calibration_membership_sha256": sha256(json_bytes(memberships["calibration"])).hexdigest(),
            "calibration_sha256": calibration_sha256,
            "estimator_fingerprint": context_state_digest.hexdigest(),
            "constant_features": [f.name for i, f in enumerate(profile.features)
                                  if np.all(matrix[:, i] == matrix[0, i])],
            "numeric_ranges": [{"name": f.name, "unit": f.unit,
                                "training_min": low, "training_max": high}
                               for f, low, high in zip(profile.features, minima, maxima)],
            "total_tree_nodes": sum(tree.tree_.node_count for tree in estimator.estimators_),
        }
        state_digest.update(json_bytes(detail))
        details.append(detail)
    fingerprint = state_digest.hexdigest()
    metadata = {
        "schema_version": "context-behavior-model-metadata-v1",
        "algorithm": "IsolationForest", "parameters": parameters,
        "numeric_threads": 1, "dtype": "float32", "scikit_learn": sklearn.__version__,
        "profile_sha256": profile.sha256, "profile_id": profile.profile_id,
        "profile_version": profile.version, "phase": profile.phase,
        "feature_names": [f.name for f in profile.features],
        "features": [asdict(f) for f in profile.features],
        "routing": "exact_context_tuple_v1", "context_count": len(states),
        "contexts": details, "model_id": model_id, "model_fingerprint": fingerprint,
        "model_persisted": False, "deployment_ready": False,
        "evaluation_performed": False,
        "limitations": [
            "Normal labels and trusted source identities are caller prerequisites.",
            "Training/calibration are disjoint; independent evaluation remains required.",
            "Unknown contexts or missing required telemetry cannot be scored.",
            "Training ranges are observations, not policy bounds or causal feature importance.",
            "No model persistence, signature verification, live adapter or Pi acceptance.",
        ],
    }
    return ContextualModel(profile, model_id=model_id, model_fingerprint=fingerprint,
                           contexts=states, metadata=metadata)
