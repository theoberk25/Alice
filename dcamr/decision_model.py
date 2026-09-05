"""Pi assessment boundary for technician-application decision making.

Trusted in-process callers supply authenticated bindings and a permission outcome
from a resolver. This module neither resolves permissions nor accepts agent-made
permission claims. It performs no transport, logging, execution or LLM calls.
"""
from dataclasses import asdict, dataclass
import math
import re
from typing import Protocol

from .anomaly_engine.context_profile import MAX_OBSERVATION_BYTES
from .anomaly_engine.contextual_model import ContextAssessment
from .anomaly_engine.scoring import severity_band


SCHEMA_VERSION = 'alice-decision-assessment-v1'
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_HASH = re.compile(r'[a-f0-9]{64}\Z')


def _check(value, pattern):
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError('invalid assessment binding')


@dataclass(frozen=True, slots=True)
class AssessmentBinding:
    evaluation_id: str
    request_id: str
    request_sha256: str
    observation_sha256: str
    phase: str
    execution_id: str | None = None

    def __post_init__(self):
        for value in (self.evaluation_id, self.request_id):
            _check(value, _ID)
        for value in (self.request_sha256, self.observation_sha256):
            _check(value, _HASH)
        if self.phase not in ('PRE_ACTION', 'POST_ACTION'):
            raise ValueError('invalid assessment phase')
        if self.phase == 'PRE_ACTION' and self.execution_id is not None:
            raise ValueError('unexpected execution binding')
        if self.phase == 'POST_ACTION':
            _check(self.execution_id, _ID)


@dataclass(frozen=True, slots=True)
class PermissionFinding:
    """Trusted resolver output, bound to the exact normalized action digest.

    NOT_READY covers missing/untrusted/expired snapshots according to the agreed
    activation policy. Validity and signature verification are upstream work.
    No numeric permission score: permission is categorical, not probabilistic.
    """
    request_sha256: str
    outcome: str
    package_generation: int | None
    package_sha256: str | None
    rule_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self):
        _check(self.request_sha256, _HASH)
        if self.outcome not in ('PERMITTED', 'PROHIBITED', 'REVIEW_REQUIRED',
                                'UNRESOLVED', 'NOT_READY'):
            raise ValueError('invalid permission outcome')
        if self.package_generation is not None and (
                type(self.package_generation) is not int or
                not 0 <= self.package_generation <= 2**53 - 1):
            raise ValueError('invalid permission generation')
        if self.package_sha256 is not None:
            _check(self.package_sha256, _HASH)
        if (self.package_generation is None) != (self.package_sha256 is None):
            raise ValueError('incomplete permission provenance')
        if self.outcome in ('PERMITTED', 'PROHIBITED', 'REVIEW_REQUIRED') and self.package_sha256 is None:
            raise ValueError('permission provenance required')
        for values in (self.rule_ids, self.reason_codes):
            if type(values) is not tuple or len(values) > 32:
                raise ValueError('invalid permission evidence')
            for value in values:
                _check(value, _ID)
        if not self.reason_codes:
            raise ValueError('permission reason required')


class Scorer(Protocol):
    def assess(self, input_bytes: bytes, *, expected_sha256: str) -> ContextAssessment: ...


def assess_for_technician(binding: AssessmentBinding, permission: PermissionFinding,
                          observation_bytes: bytes, scorer: Scorer) -> dict:
    """Produce JSON-ready evidence, never an approval or execution token.

    The coordinator must authenticate identity, construct the normalized request
    hash and bind measurements/context to that request. The scorer validates the
    observation digest, profile, measurement timing and freshness. Live ownership,
    clock trust, durable audit and execution checks remain outside this function.
    """
    if type(binding) is not AssessmentBinding or type(permission) is not PermissionFinding:
        raise ValueError('trusted typed inputs required')
    if permission.request_sha256 != binding.request_sha256:
        raise ValueError('permission request binding mismatch')
    blockers = []
    signals = []
    anomaly = None
    status = 'SKIPPED'
    reasons = ['POLICY_DENY_SHORT_CIRCUIT']
    if permission.outcome == 'PROHIBITED':
        blockers.append('HARD_PROHIBITION')
    if not (permission.outcome == 'PROHIBITED' and binding.phase == 'PRE_ACTION'):
        if permission.outcome not in ('PERMITTED', 'PROHIBITED'):
            blockers.append('PERMISSION_' + permission.outcome)
        if type(observation_bytes) is not bytes or len(observation_bytes) > MAX_OBSERVATION_BYTES:
            status, reasons = 'INVALID_INPUT', ['OBSERVATION_LIMIT_OR_TYPE_INVALID']
        else:
            try:
                result = scorer.assess(observation_bytes, expected_sha256=binding.observation_sha256)
                if type(result) is not ContextAssessment:
                    raise ValueError('invalid scorer result')
                if result.phase != binding.phase:
                    raise ValueError('phase mismatch')
                # Failed parsing legitimately lacks inner IDs; outer binding is retained.
                for actual, expected in ((result.request_id, binding.request_id),
                                         (result.input_sha256, binding.observation_sha256),
                                         (result.execution_id, binding.execution_id)):
                    if actual is not None and actual != expected:
                        raise ValueError('result binding mismatch')
                if result.status == 'OK':
                    if (result.request_id != binding.request_id or
                        result.input_sha256 != binding.observation_sha256 or
                        result.execution_id != binding.execution_id):
                        raise ValueError('missing result binding')
                    if (type(result.score) not in (int, float) or not math.isfinite(result.score)
                            or not 0 <= result.score <= 1 or
                            type(result.raw_score) not in (int, float) or not math.isfinite(result.raw_score)
                            or result.result != severity_band(result.score, 0.95, 0.99)):
                        raise ValueError('invalid score')
                elif (result.status not in ('UNAVAILABLE', 'INVALID_INPUT', 'ERROR', 'TIMEOUT')
                      or result.score is not None or result.raw_score is not None or result.result != 'UNKNOWN'):
                    raise ValueError('invalid failure result')
                anomaly = result.to_dict()
                status, reasons = result.status, list(result.reason_codes)
            except Exception:
                # Never forward exception text, request prose or a stale partial result.
                status, reasons = 'ERROR', ['SCORER_FAILURE_OR_BINDING_MISMATCH']
                anomaly = None
        if status != 'OK':
            blockers.append('ANOMALY_UNAVAILABLE')
        elif anomaly['result'] in ('ELEVATED', 'HIGH'):
            signals.append('ANOMALY_' + anomaly['result'])
        if anomaly and any(factor['outside_training_range'] for factor in anomaly['factors']):
            signals.append('OUTSIDE_TRAINING_RANGE')
    human_approval_required = (binding.phase == 'PRE_ACTION' and
                               permission.outcome != 'PROHIBITED' and
                               (permission.outcome == 'REVIEW_REQUIRED' or bool(signals)))
    if human_approval_required:
        blockers.append('HUMAN_APPROVAL_REQUIRED')
    return {
        'schema_version': SCHEMA_VERSION,
        'binding': asdict(binding),
        'permission': asdict(permission),
        'anomaly_status': status,
        'anomaly_reason_codes': reasons,
        'anomaly': anomaly,
        'approval_blockers': blockers,
        'review_signals': signals,
        'human_approval_required': human_approval_required,
        'decision_owner': 'TECHNICIAN_APPLICATION',
        'decision': None,
        'explanation': None,
        'execution_authorized': False,
        'score_semantics': 'NORMAL_TAIL_RANK_NOT_PROBABILITY',
    }
