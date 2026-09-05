"""Prepare or train a synthetic Mac lab candidate, exporting plain JSON reports."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from common.repository_paths import repository_root
import sys

from dcamr.anomaly_engine.baseline import load_baseline
from .anomaly_training import (
    DEFAULT_SEED, json_bytes, prepare_dataset, train_and_evaluate, training_readiness,
)


ROOT = repository_root()
BASELINE_PATH = ROOT / "tests/fixtures/features/baseline.json"
SOURCE_FILES = (
    "dcamr/anomaly_engine/baseline.py", "dcamr/anomaly_engine/feature_types.py",
    "dcamr/anomaly_engine/feature_validation.py", "dcamr/anomaly_engine/features.py",
    "dcamr/anomaly_engine/sequence.py", "dcamr/anomaly_engine/scoring.py",
    "common/schemas/anomaly_baseline.json", "common/schemas/anomaly_feature_input.json",
    "scripts/lab/anomaly_training.py", "scripts/lab/synthetic_anomaly_data.py", "scripts/lab/train_anomaly_model.py",
    "requirements-anomaly.txt", "requirements-anomaly-training.txt",
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="new directory for lab JSON outputs")
    parser.add_argument("--prepare-only", action="store_true", help="validate/split without importing or fitting sklearn")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output directory already exists; select a new directory to preserve the previous run")

    from .synthetic_anomaly_data import generate_examples

    try:
        baseline_bytes = BASELINE_PATH.read_bytes()
        baseline = load_baseline(baseline_bytes, expected_sha256=sha256(baseline_bytes).hexdigest())
        source_hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}
        generator = {"version": "web01-synthetic-v1", "seed": args.seed,
                     "normal_sessions": 500, "requests_per_session": 12,
                     "challenge_sessions_per_scenario": 20}
        examples = generate_examples(baseline=baseline, **{key: value for key, value in generator.items() if key != "version"})
        if args.prepare_only:
            dataset = prepare_dataset(examples, baseline, seed=args.seed)
            manifest = dataset.manifest()
            report = {"schema_version": "lab-preparation-report-v1", "status": "PREPARED_ONLY",
                      "deployment_ready": False, "model_persisted": False,
                      "training_blockers": training_readiness(dataset)}
        else:
            run = train_and_evaluate(examples, baseline, seed=args.seed)
            report = run.report
            manifest = report.pop("dataset")
        manifest["generator"] = generator
        manifest["source_sha256"] = source_hashes
        manifest["source_set_sha256"] = sha256(json_bytes(source_hashes)).hexdigest()
        report["dataset_manifest_sha256"] = sha256(json_bytes(manifest)).hexdigest()
        outputs = {"dataset-manifest.json": manifest, "training-report.json": report}
        if not args.prepare_only:
            outputs["calibration-reference.json"] = report["calibration"].pop("reference")
        # Validate serialization before creating anything. Existing runs are never
        # overwritten. These files are inspection artifacts, not active packages.
        encoded = {name: json_bytes(value) for name, value in outputs.items()}
        args.output.mkdir(parents=True, exist_ok=False)
        for name, data in encoded.items():
            with (args.output / name).open("xb") as stream:
                stream.write(data)
        counts = {name: {key: split[key] for key in ("sample_count", "session_count")}
                  for name, split in manifest["splits"].items()}
        print(json.dumps({"status": report["status"], "splits": counts,
                          "output": str(args.output.resolve()),
                          **({"normal_evaluation": report["normal_evaluation"],
                              "constant_training_features": report["constant_training_features"]}
                             if not args.prepare_only else {"training_blockers": report["training_blockers"]})},
                         indent=2))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"Lab run failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
