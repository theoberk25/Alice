"""Fit the Sentinel voltage models on the generated data and score challenges.

    .venv/bin/python -m lab.enterprise_sim.fit

This is a Mac-only experiment. It fits in memory, keeps no model on disk, and
does not produce a deployable artifact. The scores it reports are normal-tail
ranks against a held-out normal reference: a percentile, not a probability of
compromise and not a permission.

Evaluation rows are a third disjoint collection; challenge rows are labelled
abnormal by construction and were never in training or calibration.
"""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from common.repository_paths import repository_root

from dcamr.anomaly_engine.context_profile import load_context_profile
from lab.contextual_training import NormalExample, fit_contextual_model

from .contextual import json_bytes

ROOT = repository_root()
OUT = ROOT / "artifacts" / "enterprise-sim"


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _examples(rows: list[dict]) -> list[NormalExample]:
    examples = []
    for row in rows:
        payload = json_bytes(row["observation"])
        examples.append(NormalExample(input_bytes=payload,
                                      input_sha256=sha256(payload).hexdigest()))
    return examples


def run_phase(phase_tag: str) -> dict:
    profile_path = (OUT / "usb" / "normal_behavior" / "contextual"
                    / f"sen-feeder-voltage-{phase_tag}.json")
    profile_bytes = profile_path.read_bytes()
    profile = load_context_profile(profile_bytes,
                                   expected_sha256=sha256(profile_bytes).hexdigest())

    data = OUT / "datasets" / "contextual" / phase_tag
    training = _examples(_load(data / "train.jsonl"))
    calibration = _examples(_load(data / "calibration.jsonl"))

    model = fit_contextual_model(
        profile, training, calibration,
        model_id=f"sen-voltage-{phase_tag}-001", seed=1729)

    # --- held-out normal evaluation ---------------------------------------
    bands = defaultdict(Counter)
    for row in _load(data / "evaluation.jsonl"):
        payload = json_bytes(row["observation"])
        assessment = model.assess(payload, expected_sha256=sha256(payload).hexdigest())
        context = "/".join(row["observation"]["context"][key]
                           for key in ("feeder_id", "operating_mode"))
        bands[context][assessment.result if assessment.status == "OK"
                       else assessment.status] += 1

    # --- labelled challenges ----------------------------------------------
    challenges = []
    for row in _load(data / "challenges.jsonl"):
        payload = json_bytes(row["observation"])
        assessment = model.assess(payload, expected_sha256=sha256(payload).hexdigest())
        outside = [factor.name for factor in assessment.factors
                   if factor.outside_training_range]
        challenges.append({
            "scenario": row["scenario"],
            "expected": row["expected"],
            "context": "/".join(row["observation"]["context"][key]
                                for key in ("feeder_id", "operating_mode")),
            "status": assessment.status,
            "band": assessment.result,
            "score": None if assessment.score is None else round(assessment.score, 4),
            "reason_codes": list(assessment.reason_codes),
            "outside_training_range": outside,
            "note": row["note"],
        })

    metadata = model.metadata
    return {
        "phase": profile.phase,
        "profile_id": profile.profile_id,
        "model_id": metadata["model_id"],
        "model_fingerprint": metadata["model_fingerprint"][:16] + "...",
        "scikit_learn": metadata["scikit_learn"],
        "context_count": metadata["context_count"],
        "contexts": [
            {"context": dict(detail["context"]) if isinstance(detail["context"], dict)
             else {pair[0]: pair[1] for pair in detail["context"]},
             "training_rows": detail["training_count"],
             "calibration_rows": detail["calibration_count"],
             "training_sessions": detail["training_sessions"],
             "calibration_sessions": detail["calibration_sessions"],
             "tree_nodes": detail["total_tree_nodes"]}
            for detail in metadata["contexts"]
        ],
        "held_out_normal_bands": {context: dict(counter)
                                  for context, counter in sorted(bands.items())},
        "challenges": challenges,
        "model_persisted": metadata["model_persisted"],
        "deployment_ready": metadata["deployment_ready"],
    }


def main() -> int:
    report = {"note": "Mac-only in-memory experiment. No model is saved, none "
                      "boots on the Pi, and no Pi acceptance has run.",
              "phases": {}}
    for phase_tag in ("pre", "post"):
        report["phases"][phase_tag] = run_phase(phase_tag)

    path = OUT / "reports" / "voltage-model-experiment.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for phase_tag, result in report["phases"].items():
        print(f"\n=== {result['phase']} ({result['profile_id']}) ===")
        print(f"contexts fitted: {result['context_count']}  "
              f"sklearn {result['scikit_learn']}")
        for context in result["contexts"]:
            label = "/".join(context["context"].values())
            print(f"  {label:<28} train={context['training_rows']:>4} "
                  f"cal={context['calibration_rows']:>5} "
                  f"nodes={context['tree_nodes']:>6}")
        print("  held-out normal bands:")
        for context, counts in result["held_out_normal_bands"].items():
            print(f"    {context:<28} {dict(counts)}")
        print("  challenges:")
        for challenge in result["challenges"]:
            score = "null" if challenge["score"] is None else f"{challenge['score']:.4f}"
            print(f"    {challenge['scenario']:<24} {challenge['status']:<10} "
                  f"{challenge['band']:<9} score={score:<8} "
                  f"outside={challenge['outside_training_range']}")
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
