"""Feature correctness and failure cases, independent of any trained model."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.feature_types import FEATURE_NAMES, FeatureError
from dcamr.anomaly_engine.feature_validation import MAX_BASELINE_BYTES, MAX_FEATURE_INPUT_BYTES
from dcamr.anomaly_engine.features import build_features
from lab.replay_feature_fixtures import replay


FIXTURES = Path(__file__).parent / "fixtures/features"


def read(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def encode(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()


def load(payload):
    data = encode(payload)
    return load_baseline(data, expected_sha256=sha256(data).hexdigest())


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.payload = read("baseline.json")
        self.baseline = load(self.payload)
        self.input = read("input-normal.json")

    def build(self, value=None, baseline=None):
        data = encode(self.input if value is None else value)
        return build_features(data, self.baseline if baseline is None else baseline,
                              expected_sha256=sha256(data).hexdigest())

    def value(self, batch, name):
        return batch.values[batch.names.index(name)]

    def assert_failure(self, value=None, baseline=None, code=None):
        with self.assertRaises(FeatureError) as caught:
            self.build(value, baseline)
        if code:
            self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_committed_replay_offline(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")):
            self.assertEqual(len(replay()), 5)

    def test_feature_order_and_each_source_match(self):
        batch = self.build()
        self.assertEqual(batch.names, FEATURE_NAMES)
        self.assertEqual(tuple(s.feature for s in batch.sources), FEATURE_NAMES)
        self.assertEqual(len(batch.values), 11)
        self.assertTrue(all(isinstance(value, float) for value in batch.values))
        self.assertNotIn("score", batch.to_dict())
        self.assertNotIn("decision", batch.to_dict())
        for factor in batch.factors:
            for ref in (factor.baseline_ref, factor.observation_ref):
                self.assertTrue(ref is None or len(ref) <= 256)

    def test_routine_and_occasional_actions_have_different_positive_frequency(self):
        normal = self.build()
        changed = self.build(read("input-known-change.json"))
        self.assertEqual(self.value(normal, "action_frequency"), .2)
        self.assertEqual(self.value(changed, "action_frequency"), .02)
        self.assertFalse(normal.novelty_flags)
        self.assertFalse(changed.novelty_flags)

    def test_destination_mask_differs_from_missing_required_destination(self):
        batch = self.build()
        self.assertEqual((self.value(batch, "destination_applicable"),
                          self.value(batch, "destination_seen")), (0, 0))
        factor = next(f for f in batch.factors if f.id == "destination_seen")
        self.assertEqual(factor.state, "NOT_APPLICABLE")
        outbound = read("input-known-change.json")
        del outbound["request"]["parameters"]["destination"]
        self.assertEqual(self.assert_failure(outbound).status, "INVALID_INPUT")

    def test_destination_includes_port_and_protocol(self):
        for field, value in (("destination", "203.0.113.42"), ("port", 8443), ("protocol", "udp")):
            outbound = read("input-known-change.json")
            outbound["request"]["parameters"][field] = value
            with self.subTest(field=field):
                batch = self.build(outbound)
                self.assertEqual(self.value(batch, "destination_seen"), 0)
                self.assertIn("DESTINATION_UNSEEN", batch.novelty_flags)

    def test_host_comparison_is_normalized_without_dns(self):
        self.payload["targets"]["Web-01"]["destinations"][0]["host"] = "DB.EXAMPLE."
        outbound = read("input-known-change.json")
        outbound["request"]["parameters"]["destination"] = "db.example"
        batch = self.build(outbound, load(self.payload))
        self.assertEqual(self.value(batch, "destination_seen"), 1)
        self.payload["targets"]["Web-01"]["destinations"][0]["host"] = "2001:db8::1"
        outbound["request"]["parameters"]["destination"] = "2001:0db8:0:0:0:0:0:1"
        self.assertEqual(self.value(self.build(outbound, load(self.payload)), "destination_seen"), 1)

    def test_destination_urls_paths_and_ambiguous_ip_are_invalid(self):
        for host in ("https://db.example", "db.example/path", "010.0.0.10", "bad host"):
            outbound = read("input-known-change.json")
            outbound["request"]["parameters"]["destination"] = host
            with self.subTest(host=host):
                self.assertEqual(self.assert_failure(outbound).status, "INVALID_INPUT")

    def test_new_agent_uses_exact_cohort_and_keeps_flag(self):
        batch = self.build(read("input-new-agent.json"))
        self.assertEqual(batch.profile_source, "COHORT")
        self.assertEqual(batch.selected_profile_id, "diagnostic-cohort")
        self.assertEqual(self.value(batch, "agent_known"), 0)
        self.assertIn("AGENT_UNSEEN", batch.novelty_flags)

    def test_no_cohort_or_scope_mismatch_never_uses_arbitrary_profile(self):
        for mutation in ("no_cohort", "other_role", "other_mission"):
            value = read("input-new-agent.json")
            payload = deepcopy(self.payload)
            if mutation == "no_cohort":
                payload["cohorts"] = []
            elif mutation == "other_role":
                value["snapshot"]["subject"]["role"] = "operator"
            else:
                value["snapshot"]["subject"]["mission_type"] = "cooling"
            with self.subTest(mutation=mutation):
                self.assert_failure(value, load(payload), "INPUT_UNSUPPORTED")

    def test_subject_binding_and_known_agent_scope_are_enforced(self):
        for field in ("agent_id", "mission_id", "role", "mission_type"):
            value = deepcopy(self.input)
            value["snapshot"]["subject"][field] = "unrelated"
            with self.subTest(field=field):
                self.assert_failure(value, code="INPUT_UNSUPPORTED")

    def test_unknown_target_is_novel_within_supported_mission(self):
        self.input["request"]["target"] = "Web-02"
        batch = self.build()
        self.assertIn("TARGET_UNSEEN", batch.novelty_flags)
        self.assertIn("PROFILE_TARGET_UNSEEN", batch.novelty_flags)

    def test_unsupported_actions_and_diagnostic_outbound_parameters_fail(self):
        for action in ("disable_edr", "read_temperature"):
            value = deepcopy(self.input)
            value["request"]["action"] = action
            self.assert_failure(value, code="INPUT_UNSUPPORTED")
        self.input["request"]["parameters"] = {"destination": "10.0.0.10"}
        self.assert_failure(code="INPUT_UNSUPPORTED")

    def test_empty_complete_window_is_not_missing_history(self):
        value = read("input-session-start.json")
        batch = self.build(value)
        self.assertEqual(self.value(batch, "sequence_has_previous"), 0)
        self.assertEqual(self.value(batch, "sequence_transition_probability"), 0)
        for complete_since in (None, "2026-09-05T15:00:01Z"):
            value["snapshot"]["history"]["complete_since"] = complete_since
            self.assert_failure(value, code="HISTORY_INCOMPLETE")

    def test_exact_duplicate_proposals_do_not_change_features(self):
        original = self.build()
        self.input["snapshot"]["history"]["proposals"] *= 2
        batch = self.build()
        self.assertEqual(original.values, batch.values)
        self.assertNotEqual(original.input_sha256, batch.input_sha256)

    def test_conflicting_retry_digest_or_action_is_rejected(self):
        for field, value in (("request_sha256", "f" * 64), ("action", "read_logs")):
            payload = deepcopy(self.input)
            retry = deepcopy(payload["snapshot"]["history"]["proposals"][-1])
            retry[field] = value
            payload["snapshot"]["history"]["proposals"].append(retry)
            self.assert_failure(payload, code="INPUT_UNSUPPORTED")

    def test_current_proposal_and_context_round_are_not_extra_history(self):
        before = self.build()
        current = self.input["request"]
        event = {key: current[key] for key in ("request_id", "request_sha256", "agent_id", "mission_id", "action", "target")}
        event.update(admitted_at="2026-09-05T15:04:30Z", ordinal=3)
        self.input["snapshot"]["history"]["proposals"].append(event)
        self.input["snapshot"]["context_attempt"] = 1
        after = self.build()
        self.assertEqual(before.values, after.values)
        self.assertEqual(after.context_attempt, 1)
        event["request_sha256"] = "f" * 64
        self.assert_failure(code="INPUT_UNSUPPORTED")

    def test_interleaved_sessions_do_not_change_counts_or_sequence(self):
        before = self.build()
        event = deepcopy(self.input["snapshot"]["history"]["proposals"][-1])
        event.update(request_id="req-other", agent_id="other-agent", action="modify_firewall")
        self.input["snapshot"]["history"]["proposals"].append(event)
        self.assertEqual(before.values, self.build().values)

    def test_retry_cannot_use_later_proposals_as_its_original_predecessor(self):
        request = self.input["request"]
        event = {key: request[key] for key in ("request_id", "request_sha256", "agent_id", "mission_id", "action", "target")}
        event.update(admitted_at="2026-09-05T15:02:00Z", ordinal=2)
        events = self.input["snapshot"]["history"]["proposals"]
        events[-1]["ordinal"] = 3
        events.append(event)
        failure = self.assert_failure(code="INPUT_UNSUPPORTED")
        self.assertEqual(failure.field, "snapshot.history.after_current_request")

    def test_window_lower_edge_is_inclusive_and_upper_edge_invalid(self):
        history = self.input["snapshot"]["history"]
        history["proposals"][0]["admitted_at"] = "2026-09-05T15:00:00Z"
        self.assertEqual(self.value(self.build(), "recent_request_count_5m"), 2)
        history["proposals"][0]["admitted_at"] = "2026-09-05T14:59:59Z"
        self.assertEqual(self.value(self.build(), "recent_request_count_5m"), 1)
        for when in ("2026-09-05T15:05:00Z", "2026-09-05T15:05:01Z"):
            history["proposals"][-1]["admitted_at"] = when
            self.assert_failure(code="INPUT_UNSUPPORTED")

    def test_same_time_requires_authoritative_ordinals_not_array_order(self):
        events = self.input["snapshot"]["history"]["proposals"]
        for event in events:
            event["admitted_at"] = "2026-09-05T15:04:00Z"
        before = self.build()
        events.reverse()
        self.assertEqual(before.values, self.build().values)
        events[0]["ordinal"] = events[1]["ordinal"]
        self.assert_failure(code="INPUT_UNSUPPORTED")

    def test_order_conflicting_with_time_is_invalid(self):
        events = self.input["snapshot"]["history"]["proposals"]
        events[0]["ordinal"], events[1]["ordinal"] = events[1]["ordinal"], events[0]["ordinal"]
        self.assert_failure(code="INPUT_UNSUPPORTED")

    def execution(self, **overrides):
        result = {"execution_id": "exec-1", "request_id": "req-prior-change", "request_sha256": "1" * 64,
                  "agent_id": self.input["request"]["agent_id"], "mission_id": "INC-291",
                  "action": "allow_outbound", "target": "Web-01", "executed_at": "2026-09-05T15:02:00Z"}
        result.update(overrides)
        return result

    def test_executions_use_their_own_clock_and_duplicate_deliveries_count_once(self):
        history = self.input["snapshot"]["history"]
        event = self.execution()
        proposal = {key: event[key] for key in ("request_id", "request_sha256", "agent_id", "mission_id", "action", "target")}
        proposal.update(admitted_at="2026-09-05T14:58:00Z", ordinal=0)
        history["proposals"].insert(0, proposal)
        history["executions"] = [event, deepcopy(event)]
        batch = self.build()
        self.assertEqual(self.value(batch, "recent_request_count_5m"), 2)
        self.assertEqual(self.value(batch, "recent_executed_state_changes_5m"), 1)

    def test_unexecuted_change_proposal_does_not_count_as_executed(self):
        events = self.input["snapshot"]["history"]["proposals"]
        events[-1]["action"] = "modify_firewall"
        batch = self.build()
        self.assertEqual(self.value(batch, "recent_request_count_5m"), 2)
        self.assertEqual(self.value(batch, "recent_executed_state_changes_5m"), 0)

    def test_execution_cannot_precede_matching_admission(self):
        event = deepcopy(self.input["snapshot"]["history"]["proposals"][-1])
        event.pop("ordinal")
        event.pop("admitted_at")
        event.update(execution_id="exec-invalid", executed_at="2026-09-05T15:00:30Z")
        self.input["snapshot"]["history"]["executions"] = [event]
        self.assert_failure(code="INPUT_UNSUPPORTED")

    def test_execution_conflicts_future_events_and_already_executed_request_fail(self):
        for case in ("future", "multiple", "current", "cross_stream"):
            value = deepcopy(self.input)
            event = self.execution()
            value["snapshot"]["history"]["executions"] = [event]
            if case == "future":
                event["executed_at"] = "2026-09-05T15:06:00Z"
            elif case == "multiple":
                second = deepcopy(event)
                second["execution_id"] = "exec-2"
                value["snapshot"]["history"]["executions"].append(second)
            elif case == "current":
                event.update({key: value["request"][key] for key in ("request_id", "request_sha256", "action")})
            else:
                event["request_id"] = value["snapshot"]["history"]["proposals"][0]["request_id"]
            with self.subTest(case=case):
                self.assert_failure(value, code="INPUT_UNSUPPORTED")

    def test_overflow_horizon_blocks_until_omitted_events_have_aged_out(self):
        self.input["snapshot"]["history"]["incomplete_until"] = "2026-09-05T15:05:00Z"
        self.assert_failure(code="HISTORY_INCOMPLETE")
        self.input["snapshot"]["observed_at"] = "2026-09-05T15:05:00.000001Z"
        self.build()  # The omitted lower-edge event is now outside the window.

    def test_clock_and_calendar_fail_without_fabricated_features(self):
        for value in (None, "2026-02-30T15:05:00Z", "2026-09-05T15:05:00-04:00",
                      "0001-01-01T00:00:00Z"):
            self.input["snapshot"]["observed_at"] = value
            self.assert_failure()

    def test_missing_transition_row_is_not_a_zero_probability(self):
        profile = self.payload["profiles"]["diagnostic-agent-04"]
        del profile["transitions"]["query_status"]
        self.assert_failure(baseline=load(self.payload), code="REQUIRED_INPUT_MISSING")

    def test_unseen_transition_in_complete_row_is_zero_with_flag(self):
        self.input["request"]["action"] = "query_status"
        batch = self.build()
        self.assertEqual(self.value(batch, "sequence_transition_probability"), 0)
        self.assertIn("SEQUENCE_UNUSUAL", batch.novelty_flags)

    def test_explicit_zero_action_count_is_novel_not_missing(self):
        profile = self.payload["profiles"]["diagnostic-agent-04"]
        profile["action_counts"]["modify_firewall"] = 0
        del profile["transitions"]["modify_firewall"]
        del profile["transitions"]["query_network"]["modify_firewall"]
        outbound = read("input-known-change.json")
        outbound["request"]["action"] = "modify_firewall"
        batch = self.build(outbound, load(self.payload))
        self.assertEqual(self.value(batch, "action_frequency"), 0)
        self.assertIn("ACTION_UNSEEN", batch.novelty_flags)

    def test_baseline_cross_references_counts_and_cohort_ambiguity_fail(self):
        for mutation in ("target", "profile", "count_missing", "zero", "negative", "bool", "row_zero", "duplicate_cohort"):
            payload = deepcopy(self.payload)
            profile = payload["profiles"]["diagnostic-agent-04"]
            if mutation == "target":
                profile["targets"] = ["missing"]
            elif mutation == "profile":
                payload["agents"]["diagnostic-agent-04"]["profile_id"] = "missing"
            elif mutation == "count_missing":
                del profile["action_counts"]["read_logs"]
            elif mutation == "zero":
                profile["action_counts"] = dict.fromkeys(profile["action_counts"], 0)
            elif mutation == "negative":
                profile["action_counts"]["read_logs"] = -1
            elif mutation == "bool":
                profile["action_counts"]["read_logs"] = True
            elif mutation == "row_zero":
                profile["transitions"]["query_status"] = {"read_logs": 0}
            else:
                payload["cohorts"].append(deepcopy(payload["cohorts"][0]))
            with self.subTest(mutation=mutation), self.assertRaises(FeatureError):
                load(payload)

    def test_baseline_cannot_relabel_state_changing_action_as_read_only(self):
        self.payload["action_catalog"]["allow_outbound"]["state_changing"] = False
        with self.assertRaises(FeatureError) as caught:
            load(self.payload)
        self.assertEqual(caught.exception.code, "FEATURE_SCHEMA_MISMATCH")

    def test_actual_byte_digest_binding_and_new_input_digest(self):
        original = self.build()
        data = encode(self.input)
        with self.assertRaises(FeatureError):
            build_features(data + b" ", self.baseline, expected_sha256=sha256(data).hexdigest())
        self.input["request"]["target"] = "Web-02"
        changed = self.build()
        self.assertNotEqual(original.input_sha256, changed.input_sha256)
        baseline_bytes = encode(self.payload)
        with self.assertRaises(FeatureError) as caught:
            load_baseline(baseline_bytes + b" ", expected_sha256=sha256(baseline_bytes).hexdigest())
        self.assertEqual(caught.exception.code, "BASELINE_UNTRUSTED")

    def test_bounded_payloads_histories_and_sessions(self):
        for data, limit, baseline_mode in ((b" " * (MAX_FEATURE_INPUT_BYTES + 1), MAX_FEATURE_INPUT_BYTES, False),
                                            (b" " * (MAX_BASELINE_BYTES + 1), MAX_BASELINE_BYTES, True)):
            with self.subTest(limit=limit), self.assertRaises(FeatureError):
                if baseline_mode:
                    load_baseline(data, expected_sha256=sha256(data).hexdigest())
                else:
                    build_features(data, self.baseline, expected_sha256=sha256(data).hexdigest())
        value = deepcopy(self.input)
        value["snapshot"]["history"]["proposals"] *= 513
        self.assert_failure(value, code="INPUT_LIMIT_EXCEEDED")
        value = deepcopy(self.input)
        for index in range(32):
            event = deepcopy(value["snapshot"]["history"]["proposals"][0])
            event.update(request_id=f"req-extra-{index}", agent_id=f"agent-{index}")
            value["snapshot"]["history"]["proposals"].append(event)
        self.assert_failure(value, code="HISTORY_CAPACITY_EXCEEDED")

    def test_duplicate_keys_nonfinite_unknown_fields_and_version_fail(self):
        for raw in (b'{"schema_version":"1.0.0","schema_version":"1.0.0"}',
                    b'{"value":NaN}', b'{"value":1e999}'):
            with self.assertRaises(FeatureError):
                build_features(raw, self.baseline, expected_sha256=sha256(raw).hexdigest())
        self.input["snapshot"]["verified"] = True
        self.assert_failure()
        del self.input["snapshot"]["verified"]
        self.input["schema_version"] = "2.0.0"
        self.assert_failure()

    def test_freezing_and_defensive_export_prevent_mutation(self):
        batch = self.build()
        with self.assertRaises(TypeError):
            self.baseline.profiles["diagnostic-agent-04"]["action_counts"]["read_logs"] = 0
        with self.assertRaises(FrozenInstanceError):
            batch.values = (0.0,) * 11
        exported = batch.to_dict()
        exported["values"][0] = 0.0
        exported["factors"][0]["observed"] = False
        self.assertEqual(batch.values[0], 1.0)
        self.assertTrue(batch.factors[0].observed)
        self.payload["profiles"]["diagnostic-agent-04"]["action_counts"]["read_logs"] = 0
        self.assertEqual(batch.values, self.build().values)


if __name__ == "__main__":
    unittest.main()
