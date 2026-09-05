"""Decision evidence boundary: permission/ML failures never create authority."""
from dataclasses import replace
from hashlib import sha256
import json
import importlib.util
import unittest
from unittest.mock import Mock

from dcamr.anomaly_engine.context_profile import json_bytes, load_context_profile
from dcamr.anomaly_engine.contextual_model import ContextualModel, NumericComparison
from dcamr.decision_model import AssessmentBinding, PermissionFinding, assess_for_technician


class DecisionAssessmentTests(unittest.TestCase):
    def setUp(self):
        data = json_bytes({'schema_version': 'context-behavior-profile-v1',
                          'profile_id': 'unitless', 'version': '1', 'phase': 'PRE_ACTION',
                          'features': [{'name': 'signal', 'unit': 'unitless', 'max_age_ms': 1000,
                                        'timing': 'AT_OR_BEFORE_REQUEST'}],
                          'context_keys': ['action']})
        profile = load_context_profile(data, expected_sha256=sha256(data).hexdigest())
        self.data = json_bytes({'schema_version': 'context-behavior-observation-v1',
                               'profile_sha256': profile.sha256, 'observation_id': 'o-1',
                               'request_id': 'r-1', 'session_id': 's-1', 'phase': 'PRE_ACTION',
                               'request_at_ms': 1000, 'cutoff_at_ms': 1000,
                               'execution_id': None, 'execution_at_ms': None,
                               'context': {'action': 'read'},
                               'measurements': {'signal': {'value': 1, 'unit': 'unitless',
                                                           'observed_at_ms': 1000, 'source_id': 'e-1'}}})
        self.binding = AssessmentBinding('eval-1', 'r-1', 'a'*64, sha256(self.data).hexdigest(), 'PRE_ACTION')
        self.permission = PermissionFinding('a'*64, 'PERMITTED', 42, 'b'*64, ('G-READ',), ('GRANT_MATCHED',))
        self.model = ContextualModel.untrained(profile)
        unavailable = self.model.assess(self.data, expected_sha256=self.binding.observation_sha256)
        self.ok = replace(unavailable, status='OK', result='LOW', raw_score=-0.4,
                          score=0.5, model_id='model-1', model_fingerprint='c'*64,
                          calibration_sha256='d'*64, reason_codes=('WITHIN_TRAINING_RANGES',))

    def run_packet(self, result=None, permission=None, binding=None, data=None):
        return assess_for_technician(binding or self.binding, permission or self.permission,
                                     self.data if data is None else data,
                                     Mock(assess=Mock(return_value=result or self.ok)))

    def test_normal_is_evidence_not_authorization(self):
        packet = self.run_packet()
        self.assertEqual(packet['approval_blockers'], [])
        self.assertIsNone(packet['decision'])
        self.assertIsNone(packet['explanation'])
        self.assertFalse(packet['execution_authorized'])
        self.assertFalse(packet['human_approval_required'])
        json.dumps(packet, allow_nan=False)

    def test_hard_prohibition_never_invokes_scorer(self):
        scorer = Mock()
        packet = assess_for_technician(self.binding, replace(self.permission, outcome='PROHIBITED'), b'bad', scorer)
        scorer.assess.assert_not_called()
        self.assertEqual(packet['anomaly_status'], 'SKIPPED')
        self.assertEqual(packet['approval_blockers'], ['HARD_PROHIBITION'])
        self.assertIsNone(packet['anomaly'])

    def test_elevated_and_high_require_human(self):
        for band, score in [('ELEVATED', .95), ('HIGH', .99)]:
            with self.subTest(band=band):
                packet = self.run_packet(replace(self.ok, result=band, score=score))
                self.assertTrue(packet['human_approval_required'])
                self.assertIn('HUMAN_APPROVAL_REQUIRED', packet['approval_blockers'])

    def test_low_score_does_not_hide_training_range_evidence(self):
        factor = NumericComparison('signal', 'unitless', 5, 0, 1, True, 'AT_OR_BEFORE_REQUEST', 'e-1', 1000)
        packet = self.run_packet(replace(self.ok, factors=(factor,)))
        self.assertEqual(packet['review_signals'], ['OUTSIDE_TRAINING_RANGE'])
        self.assertTrue(packet['human_approval_required'])

    def test_permission_review_is_not_cleared_by_low_score(self):
        packet = self.run_packet(permission=replace(self.permission, outcome='REVIEW_REQUIRED'))
        self.assertTrue(packet['human_approval_required'])
        self.assertIn('PERMISSION_REVIEW_REQUIRED', packet['approval_blockers'])

    def test_unresolved_permissions_block_even_with_low_score(self):
        for outcome in ('UNRESOLVED', 'NOT_READY'):
            packet = self.run_packet(permission=replace(self.permission, outcome=outcome))
            self.assertIn('PERMISSION_' + outcome, packet['approval_blockers'])

    def test_real_untrained_model_retains_unknown(self):
        packet = assess_for_technician(self.binding, self.permission, self.data, self.model)
        self.assertEqual(packet['anomaly_status'], 'UNAVAILABLE')
        self.assertIsNone(packet['anomaly']['score'])
        self.assertIn('ANOMALY_UNAVAILABLE', packet['approval_blockers'])

    def test_scorer_failures_are_redacted_and_blocked(self):
        packet = assess_for_technician(self.binding, self.permission, self.data,
                                      Mock(assess=Mock(side_effect=RuntimeError('SECRET'))))
        self.assertNotIn('SECRET', json.dumps(packet))
        self.assertEqual(packet['anomaly_status'], 'ERROR')
        self.assertIn('ANOMALY_UNAVAILABLE', packet['approval_blockers'])

    def test_mismatched_request_or_execution_results_are_blocked(self):
        for result in (replace(self.ok, request_id='other'), replace(self.ok, execution_id='other'),
                       replace(self.ok, input_sha256='f'*64), replace(self.ok, phase='POST_ACTION')):
            self.assertEqual(self.run_packet(result)['anomaly_status'], 'ERROR')

    def test_invalid_score_or_failure_cannot_become_normal(self):
        for result in (replace(self.ok, score=float('nan')), replace(self.ok, score=True),
                       replace(self.ok, score=.99), replace(self.ok, status='ERROR'),
                       replace(self.ok, raw_score=float('inf'))):
            self.assertEqual(self.run_packet(result)['anomaly_status'], 'ERROR')

    def test_permission_binding_mismatch_rejected_before_scoring(self):
        with self.assertRaises(ValueError):
            self.run_packet(permission=replace(self.permission, request_sha256='f'*64))

    def test_failed_parse_keeps_outer_binding(self):
        bad = b'{}'
        binding = replace(self.binding, observation_sha256=sha256(bad).hexdigest())
        packet = assess_for_technician(binding, self.permission, bad, self.model)
        self.assertEqual(packet['binding']['request_id'], 'r-1')
        self.assertIsNone(packet['anomaly']['request_id'])
        self.assertIn('ANOMALY_UNAVAILABLE', packet['approval_blockers'])

    def test_oversized_input_does_not_call_scorer(self):
        scorer = Mock()
        packet = assess_for_technician(self.binding, self.permission, b'x'*32769, scorer)
        scorer.assess.assert_not_called()
        self.assertEqual(packet['anomaly_status'], 'INVALID_INPUT')

    def test_post_action_is_followup_not_retroactive_approval(self):
        binding = replace(self.binding, phase='POST_ACTION', execution_id='exec-1')
        result = replace(self.ok, phase='POST_ACTION', execution_id='exec-1', result='HIGH', score=.999)
        packet = self.run_packet(result, binding=binding)
        self.assertEqual(packet['review_signals'], ['ANOMALY_HIGH'])
        self.assertFalse(packet['human_approval_required'])
        self.assertFalse(packet['execution_authorized'])

    def test_permission_provenance_and_reason_are_required(self):
        for updates in ({'package_sha256': None}, {'reason_codes': ()}, {'rule_ids': ['mutable']},
                        {'package_generation': True}):
            with self.assertRaises(ValueError):
                replace(self.permission, **updates)

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in
                             ('numpy', 'sklearn', 'threadpoolctl')), 'training dependencies absent')
    def test_real_fitted_contextual_model_integration(self):
        from tests.test_contextual_model import profile, normal_examples, observation, json_bytes
        from lab.contextual_training import fit_contextual_model
        model_profile, digest = profile()
        rows = normal_examples(digest)
        model = fit_contextual_model(model_profile, *rows)
        data = json_bytes(observation(digest))
        payload = json.loads(data)
        binding = replace(self.binding, request_id=payload['request_id'],
                          observation_sha256=sha256(data).hexdigest())
        expected = model.assess(data, expected_sha256=binding.observation_sha256)
        packet = assess_for_technician(binding, self.permission, data, model)
        self.assertEqual(packet['anomaly_status'], 'OK')
        self.assertEqual(packet['anomaly'], expected.to_dict())
        self.assertIsNone(packet['decision'])
        self.assertFalse(packet['execution_authorized'])

    def test_post_action_still_scores_an_observed_prohibited_execution(self):
        binding = replace(self.binding, phase='POST_ACTION', execution_id='exec-1')
        result = replace(self.ok, phase='POST_ACTION', execution_id='exec-1', result='HIGH', score=.999)
        packet = self.run_packet(result, binding=binding,
                                 permission=replace(self.permission, outcome='PROHIBITED'))
        self.assertEqual(packet['anomaly_status'], 'OK')
        self.assertIn('HARD_PROHIBITION', packet['approval_blockers'])
        self.assertIn('ANOMALY_HIGH', packet['review_signals'])
        self.assertFalse(packet['execution_authorized'])
