"""Replay synthetic Web-01 features; no inference, fusion or device execution."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.features import build_features
from dcamr.anomaly_engine.feature_types import FeatureError


FIXTURES = Path(__file__).resolve().parents[1] / "tests/fixtures/features"


def replay() -> list[dict]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    if manifest["fixture_format"] != "anomaly-feature-cases-v1":
        raise ValueError("unsupported feature fixture format")
    data = _read_fixture(manifest["baseline_file"])
    # Synthetic local files only. Live callers use a verified package manifest,
    # not a digest just computed from untrusted incoming bytes.
    baseline = load_baseline(data, expected_sha256=sha256(data).hexdigest())
    reports = []
    for case in manifest["cases"]:
        data = _read_fixture(case["input_file"])
        result = build_features(data, baseline, expected_sha256=sha256(data).hexdigest())
        if list(result.values) != case["expected_values"]:
            raise ValueError(f"feature vector mismatch: {case['id']}")
        if result.selected_profile_id != case["expected_profile_id"]:
            raise ValueError(f"feature profile mismatch: {case['id']}")
        reports.append({"id": case["id"], "features": result.to_dict()})
    return reports


def _read_fixture(name: str) -> bytes:
    path = (FIXTURES / name).resolve()
    if path.parent != FIXTURES.resolve():
        raise ValueError("fixture path must remain inside fixture directory")
    return path.read_bytes()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print complete feature batches")
    args = parser.parse_args()
    try:
        reports = replay()
    except (FeatureError, ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"Feature fixture replay failed: {exc}\n")
    if args.json:
        print(json.dumps({"execution_mode": "FIXTURE", "cases": reports}, allow_nan=False))
    else:
        for report in reports:
            batch = report["features"]
            flags = ", ".join(batch["novelty_flags"]) or "no novelty flags"
            print(f"PASS {report['id']}: {batch['selected_profile_id']} / {flags}")
        print(f"Verified {len(reports)} feature vectors; no model scores or actions produced.")


if __name__ == "__main__":
    main()
