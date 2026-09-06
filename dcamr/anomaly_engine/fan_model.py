"""Bounded data-only scorer for the synthetic fan demo candidate."""
from bisect import bisect_right
from hashlib import sha256
import heapq
import json
import math
from pathlib import Path
import struct

from dcamr.audit.event_contract import canonical_bytes

MAX_MODEL_BYTES = 4 * 1024 * 1024
FEATURES = ('fan_before', 'fan_after', 'delta', 'absolute_delta',
            'temperature', 'power')
AGENT_PROFILE = {'cooling-agent-01': 'cooling-agent',
                 'power-agent-01': 'power-agent'}


def _correction(n):
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    return 2 * (math.log(n - 1) + 0.5772156649015329) - 2 * (n - 1) / n


def _forest_score(model, vector):
    values = [struct.unpack('f', struct.pack('f', value))[0] for value in vector]
    depth = 0.0
    trees = model['trees']
    for tree in trees:
        node = length = 0
        while tree['left'][node] != -1:
            feature = tree['feature'][node]
            node = (tree['left'][node] if values[feature] <= tree['threshold'][node]
                    else tree['right'][node])
            length += 1
        depth += length + _correction(tree['samples'][node])
    return -(2 ** (-depth / (len(trees) * _correction(model['max_samples']))))


def _rank(reference, value):
    return bisect_right(reference, value) / len(reference)


class FanModel:
    def __init__(self, path):
        path = Path(path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MODEL_BYTES:
            raise ValueError('fan model unavailable')
        raw = path.read_bytes()
        value = json.loads(raw)
        if (value.get('schema_version') != 'alice-fan-hybrid-experiment-v1'
                or tuple(value.get('features', ())) != FEATURES
                or set(value.get('models', {})) != {'cooling-agent', 'power-agent'}):
            raise ValueError('unsupported fan model')
        self.value = value
        self.sha256 = sha256(raw).hexdigest()
        self.model_id = 'fan-hybrid-synthetic-v2'
        calibration = json.dumps({key: item['distance_reference'] for key, item in value['models'].items()},
                                 sort_keys=True, separators=(',', ':')).encode()
        self.calibration_sha256 = sha256(calibration).hexdigest()
        # Exercise every array through one bounded score at startup.
        for profile in value['models']:
            self.score(profile, [50, 50, 0, 0, 25, 350])

    def score(self, profile, vector):
        if (profile not in self.value['models'] or len(vector) != len(FEATURES)
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)):
            raise ValueError('invalid fan model input')
        model = self.value['models'][profile]
        raw = _forest_score(model['forest'], vector)
        score = _rank(model['forest_reference'], -raw)
        normalized = [(v - mean) / scale for v, mean, scale
                      in zip(vector, model['mean'], model['scale'])]
        nearest = heapq.nsmallest(model['neighbors'],
                                  (math.dist(normalized, p) for p in model['prototypes']))
        distance = sum(nearest) / len(nearest)
        score = max(score, _rank(model['distance_reference'], distance))
        return {'raw_score': raw, 'score': score,
                'result': 'HIGH' if score >= 0.99 else ('ELEVATED' if score >= 0.95 else 'LOW'),
                'threshold': model['threshold'], 'distance': distance,
                'unusual': score > model['threshold']}

    def assess(self, request, snapshot, request_sha256, request_at_ms,
               source_id='machine-state-file'):
        profile = AGENT_PROFILE.get(request['agent_id'])
        if profile is None:
            raise ValueError('unknown fan agent profile')
        before = snapshot['fan_speed']
        after = request['parameters']['value']
        delta = after - before
        vector = [before, after, delta, abs(delta),
                  snapshot['server_temperature'], snapshot['power_consumption']]
        scored = self.score(profile, vector)
        # The candidate's threshold is calibrated from the combined forest and
        # contextual-distance score.  Keep the decision band aligned with that
        # selected threshold instead of applying a second, lower cutoff.
        result = 'HIGH' if scored['unusual'] else 'LOW'
        assessment = {
            'schema_version': 'context-behavior-assessment-v1', 'status': 'OK',
            'result': result, 'raw_score': scored['raw_score'], 'score': scored['score'],
            'reason_codes': ['OUTSIDE_NORMAL_SUPPORT'] if scored['unusual'] else [],
            'phase': 'PRE_ACTION', 'observation_id': request['request_id'] + '.fan-obs',
            'request_id': request['request_id'], 'input_sha256': request_sha256,
            'profile_sha256': sha256(canonical_bytes({'features': list(FEATURES)})).hexdigest(),
            'model_id': self.model_id, 'model_fingerprint': self.sha256,
            'calibration_sha256': self.calibration_sha256,
            'context': {'action': request.get('action', 'set_fan_speed'), 'agent_profile': profile,
                        'target': request['target']},
            'request_at_ms': request_at_ms, 'cutoff_at_ms': request_at_ms,
            'execution_id': None, 'execution_at_ms': None,
            'source_ids': [source_id],
            'factors': [{'name': name,
                         'unit': ('percent' if 'fan' in name or 'delta' in name
                                  else ('degrees_C' if name == 'temperature' else 'W')),
                         'observed': value, 'training_min': value, 'training_max': value,
                         'outside_training_range': False, 'timing': 'PRE_ACTION',
                         'source_id': source_id, 'observed_at_ms': request_at_ms}
                        for name, value in zip(FEATURES, vector)],
        }
        return json.dumps(assessment, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode(), scored
