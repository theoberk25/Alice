"""Synthetic source generation checks; no estimator is fitted by these tests."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.features import build_features
from lab.anomaly_training import json_bytes
from lab.synthetic_anomaly_data import BASELINE_PATH, CHALLENGE_SCENARIOS, generate_examples


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SyntheticAnomalyDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = BASELINE_PATH.read_bytes()
        cls.baseline = load_baseline(data, expected_sha256=sha256(data).hexdigest())
        cls.examples = list(generate_examples(normal_sessions=10, requests_per_session=12,
                                             challenge_sessions_per_scenario=2))

    def test_reproducible_sources_and_seed_variation(self):
        options = dict(normal_sessions=2, requests_per_session=3, challenge_sessions_per_scenario=1)
        first = list(generate_examples(**options))
        self.assertEqual(first, list(generate_examples(**options)))
        self.assertNotEqual(first, list(generate_examples(seed=1730, **options)))

    def test_exact_case_counts_and_single_scenario_per_group(self):
        counts = Counter((example.label, example.scenario) for example in self.examples)
        self.assertEqual(counts[("NORMAL", "routine_operations")], 120)
        for scenario in CHALLENGE_SCENARIOS:
            self.assertEqual(counts[("CHALLENGE", scenario)], 2)
        grouped = defaultdict(list)
        for example in self.examples:
            grouped[example.group_id].append(example)
        for rows in grouped.values():
            self.assertEqual(len({(row.label, row.scenario) for row in rows}), 1)
            self.assertEqual(len(rows), 12 if rows[0].label == "NORMAL" else 1)

    def test_every_source_uses_runtime_features_and_intended_challenges(self):
        confirmations = 0
        for example in self.examples:
            batch = build_features(example.input_bytes, self.baseline, expected_sha256=example.input_sha256)
            values = dict(zip(batch.names, batch.values))
            confirmations += values["recent_executed_state_changes_5m"]
            if example.label == "NORMAL":
                self.assertEqual(batch.novelty_flags, ())
                self.assertLessEqual(values["recent_request_count_5m"], 10)
            elif example.scenario == "new_agent":
                self.assertEqual(values["agent_known"], 0)
                self.assertEqual(batch.profile_source, "COHORT")
                self.assertIn("AGENT_UNSEEN", batch.novelty_flags)
            elif example.scenario == "unseen_destination":
                self.assertEqual(values["destination_applicable"], 1)
                self.assertEqual(values["destination_seen"], 0)
                self.assertEqual(batch.novelty_flags, ("DESTINATION_UNSEEN",))
            elif example.scenario == "unseen_target":
                self.assertEqual(values["target_known"], 0)
                self.assertEqual(values["destination_applicable"], 0)
                self.assertIn("TARGET_UNSEEN", batch.novelty_flags)
            elif example.scenario == "unusual_sequence":
                self.assertEqual(values["sequence_has_previous"], 1)
                self.assertEqual(values["sequence_transition_probability"], 0)
                self.assertEqual(batch.novelty_flags, ("SEQUENCE_UNUSUAL",))
            elif example.scenario == "request_burst":
                self.assertEqual(values["recent_request_count_5m"], 40)
                self.assertEqual(batch.novelty_flags, ())
        self.assertGreater(confirmations, 0)

    def test_actual_local_hashes_and_no_shared_source_lineage(self):
        owners = {}
        current_requests = set()
        for example in self.examples:
            self.assertEqual(example.baseline_sha256, self.baseline.identity.sha256)
            self.assertEqual(sha256(example.input_bytes).hexdigest(), example.input_sha256)
            payload = json.loads(example.input_bytes)
            request, snapshot = payload["request"], payload["snapshot"]
            for body, field in ((request, "request_sha256"), (snapshot, "sha256")):
                unhashed = {key: value for key, value in body.items() if key != field}
                self.assertEqual(sha256(json_bytes(unhashed)).hexdigest(), body[field])
            self.assertNotIn(request["request_id"], current_requests)
            current_requests.add(request["request_id"])
            for event in [request, *snapshot["history"]["proposals"], *snapshot["history"]["executions"]]:
                for identity in (("request", event["request_id"]),
                                 ("mission", event["agent_id"], event["mission_id"])):
                    owner = owners.setdefault(identity, example.group_id)
                    self.assertEqual(owner, example.group_id)

    def test_supplied_frozen_baseline_is_used_without_reopening_fixture(self):
        payload = json.loads(BASELINE_PATH.read_bytes())
        payload["version"] = "synthetic-custom-v1"
        # Give every initial action the same normal choice; all first requests
        # must honor this supplied distribution rather than the fixture file.
        for profile in payload["profiles"].values():
            profile["action_counts"] = {name: int(name == "query_network")
                                        for name in payload["action_catalog"]}
            profile["transitions"] = {"query_network": {"query_network": 1}}
        data = json_bytes(payload)
        supplied = load_baseline(data, expected_sha256=sha256(data).hexdigest())
        with patch("pathlib.Path.read_bytes", side_effect=AssertionError("fixture reopened")):
            examples = list(generate_examples(baseline=supplied, normal_sessions=3,
                                             requests_per_session=1,
                                             challenge_sessions_per_scenario=0))
        self.assertEqual(len(examples), 3)
        for example in examples:
            self.assertEqual(example.baseline_sha256, supplied.identity.sha256)
            self.assertEqual(json.loads(example.input_bytes)["request"]["action"], "query_network")
            build_features(example.input_bytes, supplied, expected_sha256=example.input_sha256)

    def test_complete_prior_windows_and_separate_execution_time(self):
        normal_times = defaultdict(list)
        for example in self.examples:
            payload = json.loads(example.input_bytes)
            request, snapshot = payload["request"], payload["snapshot"]
            end = _time(snapshot["observed_at"])
            start = end - timedelta(seconds=300)
            history = snapshot["history"]
            self.assertLessEqual(_time(history["complete_since"]), start)
            self.assertIsNone(history["incomplete_until"])
            self.assertEqual(snapshot["context_attempt"], 0)
            admissions = {}
            for event in history["proposals"]:
                at = _time(event["admitted_at"])
                self.assertLessEqual(start, at)
                self.assertLess(at, end)
                self.assertNotEqual(event["request_id"], request["request_id"])
                admissions[event["request_id"]] = at
            for event in history["executions"]:
                at = _time(event["executed_at"])
                self.assertLessEqual(start, at)
                self.assertLess(at, end)
                if event["request_id"] in admissions:
                    self.assertEqual(at - admissions[event["request_id"]], timedelta(seconds=1))
            if example.label == "NORMAL":
                normal_times[example.group_id].append(end)
        for times in normal_times.values():
            for previous, current in zip(times, times[1:]):
                self.assertGreaterEqual((current - previous).total_seconds(), 30)
                self.assertLessEqual((current - previous).total_seconds(), 90)

    def test_invalid_or_excessive_generation_arguments_are_rejected(self):
        for options in ({"seed": True}, {"seed": -1}, {"seed": 2**32},
                        {"normal_sessions": 0}, {"normal_sessions": 2001},
                        {"normal_sessions": 2000, "requests_per_session": 64},
                        {"requests_per_session": 0}, {"requests_per_session": 65},
                        {"challenge_sessions_per_scenario": -1},
                        {"challenge_sessions_per_scenario": 201}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                next(generate_examples(**options))


if __name__ == "__main__":
    unittest.main()
