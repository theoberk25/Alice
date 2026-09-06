"""Real ALICE decisions, Ed25519 review, durable execution and plant integration."""
import base64
from copy import deepcopy
import json
import time
import uuid
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from dcamr.audit.event_contract import canonical_bytes
from dcamr.technician_review import DOMAIN, BINDINGS
from services.thermal_demo.environment import Environment, DemoError
from services.thermal_demo.runtime import ThermalRuntime, load_agent_keys
from lab.thermal_demo.build_release import build


@pytest.fixture(scope='session')
def thermal_model_file(tmp_path_factory):
    import contextlib
    import io
    from lab.refine_fan_model import run
    root = tmp_path_factory.mktemp('thermal-model')
    demo = root / 'demo.jsonl'
    demo.write_text('')
    output = root / 'output'
    with contextlib.redirect_stdout(io.StringIO()):
        run(output, demo)
    return output / 'model.json'


@pytest.fixture
def integrated(tmp_path, thermal_model_file):
    bundle = tmp_path / 'bundle'
    release = build(bundle)
    console = Ed25519PrivateKey.generate()
    trust = tmp_path / 'console.json'
    trust.write_text(json.dumps({'schema_version': 'alice-console-trust-v1', 'consoles': [{
        'console_id': 'native-test', 'technician_ids': ['T1'],
        'public_key': console.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()}]}))
    now = [0.0]
    env = Environment(clock=lambda: now[0])
    args = dict(release_dir=release, trusted_manifest_key=bytes.fromhex((bundle/'manifest-public.hex').read_text()),
                data_dir=tmp_path/'ledger', console_trust_file=trust,
                agent_keys=load_agent_keys(bundle/'agent-keys.json'),
                fan_model_file=thermal_model_file)
    rt = ThermalRuntime(environment=env, **args)
    env.configure({'temperature_f': 100, 'fan_pct': 60, 'battery_pct': 60})
    env.control('start')
    def request(fan, agent='cooling-agent-01', rid=None):
        return env.request_fan({'run_id': env.run_id, 'request_id': rid or uuid.uuid4().hex,
                                'expected_revision': env.revision, 'fan_pct': fan}, agent)
    def proof(record, **changes):
        code, view = rt.review(request_id=record['audit_request_id'])
        assert code == 200
        stamp = int(time.time())
        value = {k: view[k] for k in BINDINGS}
        value.update(schema_version='alice-review-action-v1', console_id='native-test', technician_id='T1',
                     action_id=uuid.uuid4().hex, action='APPROVE_ONCE', biometric_session_id=uuid.uuid4().hex,
                     biometric_policy='alice.live-face.v3', issued_at=stamp, expires_at=stamp+60)
        value.update(changes)
        return {'proof': value, 'signature': base64.b64encode(console.sign(DOMAIN+canonical_bytes(value))).decode()}
    yield env, rt, now, request, proof, args
    rt.close()


def test_allow_ramp_energy_and_actual_display(integrated):
    from dcamr.display.led_patterns import map_patterns
    env, rt, now, request, _, _ = integrated
    record = request(70)
    assert record['decision'] == 'ALLOW' and record['application'] == 'APPLIED', record
    assert env.model.fan_actual_pct == 60 and env.model.fan_target_pct == 70
    for _ in range(150):
        now[0] += .1
        env.snapshot()
    state = env.snapshot()['values']
    assert state['fan_actual_pct'] > 69.9 and state['power_w'] > 430
    assert state['temperature_f'] > 100 and env.model.sim_seconds == pytest.approx(15)
    patterns = map_patterns({'temperature_f': state['temperature_f'], 'fan_pct': state['fan_actual_pct'],
                             'power_w': state['power_w'], 'battery_pct': state['battery_pct']})
    assert patterns[1].hz == pytest.approx(3.65, abs=.001)
    events = list(rt.iter_events())
    assert [e['event_type'] for e in events] == ['REQUEST','ASSESSMENT','DECISION','EXECUTION_ATTEMPT',
                                              'CONTROLLER_RECEIPT','EXECUTION_RESULT','OBSERVED_STATE']
    assert events[1]['detail']['kind'] == 'CONTEXTUAL_ML'
    assert events[1]['detail']['result'] == 'LOW' and events[1]['detail']['contextual'] is not None
    assert events[1]['provenance']['model']['sha256'] == rt.fan_model.sha256


def test_hold_live_then_signed_approval_exactly_once(integrated):
    env, rt, now, request, sign, _ = integrated
    record = request(0, 'power-agent-01')
    assert record['decision'] == 'CHALLENGE' and env.model.fan_target_pct == 60
    now[0] = 2
    assert env.snapshot()['values']['temperature_f'] > 100
    signed = sign(record)
    code, receipt = rt.review(envelope=signed)
    assert code == 200 and receipt['execution_status'] == 'COMPLETED', receipt
    env.reconcile()
    assert env.model.fan_target_pct == 0 and env.pending is None
    assert rt.review(envelope=signed)[1]['idempotent_replay']
    assert env.revision == 1
    assert [e['detail']['outcome'] for e in rt.iter_events() if e['event_type']=='DECISION'] == ['CHALLENGE']


def test_deny_and_signed_rejection_never_change_plant(integrated):
    env, rt, _, request, sign, _ = integrated
    denied = request(90, 'observer-agent-01')
    assert denied['decision'] == 'DENY' and denied['application'] == 'NOT_APPLIED'
    held = request(0, 'power-agent-01')
    assert held['decision'] == 'CHALLENGE'
    code, receipt = rt.review(envelope=sign(held, action='REJECT'))
    assert code == 200 and receipt['review_state'] == 'REJECTED'
    env.reconcile()
    assert env.model.fan_target_pct == 60 and env.pending is None
    assert not any(e['event_type']=='EXECUTION_ATTEMPT' for e in rt.iter_events())


@pytest.mark.parametrize('operation', ['stop', 'pause', 'reset', 'exhaust', 'gap'])
def test_stale_review_cannot_apply(integrated, operation):
    env, rt, now, request, sign, _ = integrated
    held = request(0, 'power-agent-01')
    signed = sign(held)
    if operation == 'gap':
        now[0] = 11
    elif operation == 'exhaust':
        env.model.fan_actual_pct = 100
        env.model.battery_remaining_wh = 0
        now[0] = .1
    else:
        env.control('pause' if operation == 'pause' else 'stop')
        if operation == 'reset':
            env.configure({'temperature_f': 140, 'fan_pct': 60, 'battery_pct': 60})
            env.control('start')
    assert rt.review(envelope=signed)[0] == 409
    assert env.model.fan_target_pct == 60


def test_tamper_retry_unknown_and_restart(integrated):
    env, rt, _, request, sign, args = integrated
    record = request(0, 'power-agent-01', rid='same')
    forged = sign(record)
    forged['proof']['request_sha256'] = '0'*64
    assert rt.review(envelope=forged)[0] == 409
    with pytest.raises(DemoError):
        request(90, rid='same')
    signed = sign(record)
    with patch.object(rt, '_execute_request', side_effect=OSError('crash after review admission')):
        assert rt.review(envelope=signed)[0] == 503
    assert rt.review(envelope=signed)[1]['execution_status'] == 'UNKNOWN'
    assert env.model.fan_target_pct == 60
    rt.close()
    new = Environment(clock=lambda: 0)
    reopened = ThermalRuntime(environment=new, **args)
    try:
        assert reopened.review(envelope=signed)[1]['idempotent_replay']
        assert new.model is None
    finally:
        reopened.close()


def test_lost_response_reconciles_without_second_execution(integrated):
    env, rt, _, request, _, _ = integrated
    real = rt.submit
    def lost(action):
        real(action)
        raise OSError('lost response')
    with patch.object(rt, 'submit', side_effect=lost):
        record = request(70)
    assert record['application'] == 'RECONCILIATION_REQUIRED'
    env.reconcile()
    assert env.model.fan_target_pct == 70 and env.revision == 1
    assert sum(e['event_type']=='EXECUTION_ATTEMPT' for e in rt.iter_events()) == 1


def test_native_bridge_can_read_and_review_authenticated_demo(integrated):
    import threading
    from urllib.request import Request, urlopen
    from services.thermal_demo.server import make_server
    from services.runtime_feed import make_server as bridge_server
    env, rt, _, request, sign, _ = integrated
    upstream = make_server(env, 'operator-secret',
                           agents={'cooling-agent-01': 'agent-secret',
                                   'power-agent-01': 'power-secret'}, runtime=rt)
    bridge = bridge_server(upstream=f'http://127.0.0.1:{upstream.server_port}',
                           token='f'*32, source='local-runtime', controller='mock', port=0,
                           upstream_token='operator-secret')
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (upstream, bridge)]
    for thread in threads:
        thread.start()
    def get(path, body=None):
        req = Request(f'http://127.0.0.1:{bridge.server_port}' + path,
                      data=canonical_bytes(body) if body else None,
                      headers={'Authorization':'Bearer ' + 'f'*32})
        with urlopen(req, timeout=3) as response:
            return json.load(response)
    try:
        from services.thermal_demo.client import DemoClient
        client = DemoClient(f'http://127.0.0.1:{upstream.server_port}', 'agent-secret')
        power = DemoClient(f'http://127.0.0.1:{upstream.server_port}', 'power-secret')
        held = power.request_fan(power.state(), 0, 'http-fan')
        assert held['decision'] == 'CHALLENGE'
        assert get('/events?after=0')['events']
        assert get('/review/' + held['audit_request_id'])['eligible']
        assert get('/review', sign(held))['execution_status'] == 'COMPLETED'
        assert env.model.fan_target_pct == 0
    finally:
        for server in (upstream, bridge):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join()
