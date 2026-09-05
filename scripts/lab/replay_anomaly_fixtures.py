"""Replay contract examples locally. No model inference or actuator calls."""

import argparse
import json
from pathlib import Path
from common.repository_paths import repository_root
from typing import Any

from dcamr.anomaly_engine.contract import (
    ARTIFACT_FIELDS, ContractError, EvaluationBinding, parse_result, serialize_result,
)
from dcamr.anomaly_engine.scoring import CalibrationReference


FIXTURES = repository_root() / "tests/fixtures/anomaly"


def replay() -> list[dict[str, Any]]:
    """Validate committed result fixtures and their score mapping assertions."""
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    scores = json.loads((FIXTURES / "score-cases.json").read_text(encoding="utf-8"))
    if manifest["fixture_format"] != "anomaly-results-v1":
        raise ValueError("unsupported result fixture format")
    if scores["fixture_format"] != "anomaly-score-cases-v1" or not scores["fixture_mode"]:
        raise ValueError("score fixtures must be explicitly marked as mocks")
    reference = CalibrationReference(
        (segment["raw_score"] for segment in scores["calibration_segments"]
         for _ in range(segment["count"])),
        **scores["thresholds"],
    )
    for case in scores["cases"]:
        actual = reference.score(case["raw_score"])
        if (actual.score, actual.result) != (case["score"], case["result"]):
            raise ValueError(f"score fixture failed: {case['id']}")
    reports = []
    for case in manifest["cases"]:
        path = FIXTURES / case["result_file"]
        if path.resolve().parent != FIXTURES.resolve():
            raise ValueError("fixture path must remain in fixture directory")
        result = parse_result(path.read_bytes())
        actual = (result["status"], result["result"], result["score"])
        expected = (case["expected_status"], case["expected_result"], case["expected_score"])
        if actual != expected:
            raise ValueError(f"result fixture failed: {case['id']}")
        if result["runtime"]["execution_mode"] != "FIXTURE":
            raise ValueError("replay requires fixture-mode results")
        if result["status"] == "OK":
            mapped = reference.score(result["raw_score"]["value"])
            if (mapped.score, mapped.result) != (result["score"], result["result"]):
                raise ValueError(f"result score does not match reference: {case['id']}")
        # This self-binding checks fixture format only. Live callers must capture
        # metadata from trusted inputs BEFORE inference, never from its result.
        binding = EvaluationBinding.capture(result)
        artifacts = {key: result[key] for key in ARTIFACT_FIELDS}
        try:
            binding.check(result, active_artifacts=artifacts)
        except ContractError as exc:
            if "FIXTURE result" not in str(exc):
                raise
        else:
            raise ValueError("live guard accepted a fixture")
        binding.check(result, active_artifacts=artifacts, allow_fixtures=True)
        if parse_result(serialize_result(result)) != result:
            raise ValueError("result round trip changed the payload")
        reports.append({"id": case["id"], "status": result["status"],
                        "result": result["result"], "score": result["score"]})
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable summary")
    args = parser.parse_args()
    try:
        reports = replay()
    except (ContractError, ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Fixture replay failed: {exc}\n")
    if args.json:
        print(json.dumps({"execution_mode": "FIXTURE", "cases": reports}, allow_nan=False))
    else:
        for item in reports:
            score = "null" if item["score"] is None else str(item["score"])
            print(f"PASS {item['id']}: {item['status']} / {item['result']} / {score}")
        print(f"Verified {len(reports)} result fixtures and 7 score cases; no actions executed.")


if __name__ == "__main__":
    main()
