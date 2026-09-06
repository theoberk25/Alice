"""Demo fan adapter using ALICE's signed requests, policy, ledger and review."""
import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from jsonschema import Draft202012Validator

from dcamr.audit.event_contract import canonical_bytes
from dcamr.main import FirstLightRuntime
from dcamr.enforcement.serial_light_controller import SerialLightController
from .environment import DemoError, GatewayUnavailable


class ThermalRuntime(FirstLightRuntime):
    """One process owns the plant, signed ALICE authority and optional serial port.

    Agent bearer identities are configured by the operator and mapped to private
    request keys. Neither an agent nor an operator can submit decision outcomes.
    The frontend review endpoint still requires the existing native signed proof.
    """
    def __init__(self, *, environment, agent_keys, **options):
        self.environment = environment
        self.agent_keys = agent_keys
        super().__init__(**options)
        self._lock = environment.lock
        try:
            for agent, (key_id, key) in agent_keys.items():
                trusted = self.release.terminal_keys.get(key_id)
                public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                if trusted is None or trusted.agent_id != agent or trusted.public_key != public:
                    raise ValueError('Agent signing key does not match signed release')
            environment.gateway = self
        except Exception:
            self.close()
            raise

    @staticmethod
    def request_validator():
        schema = json.loads(Path(__file__).with_name('fan-request.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema)

    @staticmethod
    def make_controller(esp_base_url, esp_serial, serial_baud, serial_timeout):
        if esp_base_url:
            raise ValueError('Demo indicators require serial; HTTP actuator is unsupported')
        return SerialLightController(esp_serial, baud=serial_baud, timeout=serial_timeout) if esp_serial else None

    @staticmethod
    def wire(action):
        return {**deepcopy(action), 'schema_version': 'alice-demo-fan-v1',
                'request_id': sha256((action['run_id'] + '.' + action['request_id']).encode()).hexdigest(),
                'client_request_id': action['request_id'],
                'parameters': {'fan_basis_points': round(action['parameters']['fan_pct'] * 100)}}

    @staticmethod
    def action(request):
        value = deepcopy(request)
        value.pop('schema_version')
        value['parameters'] = {'fan_pct': value['parameters']['fan_basis_points'] / 100}
        value['request_id'] = value.pop('client_request_id')
        return value

    def request_is_current(self, request):
        return self.environment.current(self.action(request))

    def submit(self, action):
        with self._lock:
            credentials = self.agent_keys.get(action['agent_id'])
            if credentials is None:
                raise GatewayUnavailable('Agent signing identity is not configured')
            key_id, key = credentials
            request = self.wire(action)
            code, _ = self.handle_request({'request': request, 'key_id': key_id,
                'signature': base64.b64encode(key.sign(canonical_bytes(request))).decode()})
            if code >= 500:
                raise GatewayUnavailable('ALICE outcome requires reconciliation')
            return self.result(action)

    def result(self, action):
        with self._lock:
            wire = self.wire(action)
            rid = wire['request_id']
            recorded = self._outcomes.get(rid)
            if recorded is None or recorded['request_sha256'] != sha256(canonical_bytes(wire)).hexdigest():
                raise GatewayUnavailable('No exact durable outcome')
            response = recorded['response']
            view = self.reviews.view(rid)
            return {'action': deepcopy(action), 'audit_request_id': rid,
                    'decision': response['decision'], 'execution': response['execution'],
                    'review_state': view['review_state']}

    def assess_request(self, request, request_sha256, correlation, attribution):
        current = self.request_is_current(request)
        # Real deterministic policy assessment, explicitly no anomaly/model score.
        detail = {'kind': 'POLICY', 'status': 'OK' if current else 'UNAVAILABLE',
                  'result': 'PASS' if current else 'UNKNOWN', 'contextual': None,
                  'reason_codes': ['DEMO_RUN_CURRENT' if current else 'DEMO_RUN_STALE']}
        correlation = dict(correlation, assessment_id=request['request_id'] + '.a1')
        state = self.environment.snapshot()
        observation = json.dumps({k: state[k] for k in ('run_id', 'revision', 'elapsed_seconds', 'values', 'metadata')},
                                 sort_keys=True, allow_nan=False).encode()
        rid = request['request_id']
        self._write_evidence(self._evidence_dir / f'{rid}.environment.json', observation)
        self._append(rid + '.assessment', 'ASSESSMENT', correlation=correlation,
                     attribution=attribution, detail=detail,
                     evidence=[{'ref': rid + '.environment', 'sha256': sha256(observation).hexdigest(),
                                'source': self._source('thermal-demo', rid + '.observation')}])
        return detail, correlation

    def _execute_request(self, request, request_sha256, response, correlation, attribution):
        rid = request['request_id']
        action = self.action(request)
        correlation = dict(correlation, action_id=correlation.get('action_id') or rid + '.action',
                           execution_id=rid + '.exec')
        self._append(rid + '.attempt', 'EXECUTION_ATTEMPT', correlation=correlation,
                     attribution=attribution, detail={'command_ref': rid + '.command',
                     'command_sha256': sha256(canonical_bytes(request)).hexdigest(),
                     'outcome': 'ATTEMPTED', 'reason_codes': []})
        self._owner.check()
        if self.storage:
            self.storage.check()
        try:
            self.environment.apply_authorized(action)
            accepted = True
        except DemoError:
            accepted = False
        source = self._source('DEMO-SERVER-01', rid + '.simulation')
        for suffix, kind, outcome in (
            ('receipt', 'CONTROLLER_RECEIPT', 'ACCEPTED' if accepted else 'REJECTED'),
            ('result', 'EXECUTION_RESULT', 'COMPLETED' if accepted else 'FAILED')):
            self._append(rid + '.' + suffix, kind, correlation=correlation, attribution=attribution,
                         detail={'outcome': outcome, 'source': source,
                                 'reason_codes': [] if accepted else ['DEMO_RUN_STALE']})
        values = self.environment.snapshot()['values']
        raw = json.dumps({'simulation': True, 'values': values}, sort_keys=True, allow_nan=False).encode()
        self._write_evidence(self._evidence_dir / f'{rid}.observed.json', raw)
        ref = rid + '.observed-evidence'
        self._append(rid + '.observed', 'OBSERVED_STATE', correlation=correlation,
            attribution=attribution, detail={'asset_id': 'DEMO-SERVER-01',
                'sensor_id': 'demo-fan-target-readback', 'origin': 'ACTUATOR_FEEDBACK',
                'property': 'simulated_fan_target', 'value': str(values['fan_target_pct']),
                'unit': 'percent', 'quality': 'GOOD', 'correlation_absence_reason': None,
                'source': source, 'evidence_ref': ref},
            evidence=[{'ref': ref, 'sha256': sha256(raw).hexdigest(), 'source': source}])
        response.update(execution='COMPLETED' if accepted else 'FAILED',
                        observed_state=values['fan_target_pct'])
        self._record_outcome(rid, request_sha256, response)
        self.ledger.seal()
        return 200, response


def load_agent_keys(config):
    """Private file: agent id -> key id and seed file. Never returned in state."""
    path = Path(config)
    value = json.loads(path.read_text())
    result = {}
    for agent, entry in value.items():
        seed = (path.parent / entry['seed_file']).read_text().strip()
        result[agent] = (entry['key_id'], Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed)))
    return result
