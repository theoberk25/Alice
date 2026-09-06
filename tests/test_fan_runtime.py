import base64
from datetime import datetime, timezone
import json
import threading
import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dcamr.audit.event_contract import canonical_bytes
from dcamr.main import FirstLightRuntime
from dcamr.technician_review import BINDINGS, DOMAIN
from lab.first_light import build_release, mock_esp
from lab.first_light.extend_fan_release import extend


@pytest.fixture(scope='module')
def model_file(tmp_path_factory):
    import contextlib
    import io
    from lab.refine_fan_model import run
    root = tmp_path_factory.mktemp('fan-model')
    demo = root / 'demo.jsonl'; demo.write_text('')
    output = root / 'output'
    with contextlib.redirect_stdout(io.StringIO()):
        run(output, demo)
    return output / 'model.json'


def signed(seed, agent, value, request_id):
    request = {'schema_version': '1.0', 'request_id': request_id, 'agent_id': agent,
               'action': 'set_fan_speed', 'target': 'SERVER-ROOM-FANS',
               'parameters': {'value': value},
               'issued_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}
    key = Ed25519PrivateKey.from_private_bytes(seed)
    return {'request': request, 'key_id': agent + '-k1',
            'signature': base64.b64encode(key.sign(canonical_bytes(request))).decode()}


def test_anomalous_fan_hold_and_human_execution(tmp_path, model_file):
    manifest_key = Ed25519PrivateKey.generate()
    source = build_release.build(tmp_path / 'base', manifest_key=manifest_key)
    seed_file = tmp_path / 'manifest.seed'
    seed_file.write_text(manifest_key.private_bytes_raw().hex())
    trust_file = tmp_path / 'base/trust/manifest_public.hex'
    release = tmp_path / 'fan-release'
    clients = tmp_path / 'fan-clients'
    extend(source, release, clients, trust_file, seed_file)
    console_key = Ed25519PrivateKey.generate()
    trust = tmp_path / 'console.json'
    trust.write_text(json.dumps({'schema_version': 'alice-console-trust-v1', 'consoles': [{
        'console_id': 'console-test',
        'public_key': console_key.public_key().public_bytes_raw().hex(),
        'technician_ids': ['TECH-DEMO']}]}))
    state = tmp_path / 'machine-state.json'
    state.write_text(json.dumps({'fan_speed': 60, 'server_temperature': 36,
                                 'power_consumption': 475}))
    server, esp = mock_esp.make_server()
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    runtime = FirstLightRuntime(release_dir=release,
        trusted_manifest_key=bytes.fromhex(trust_file.read_text().strip()),
        data_dir=tmp_path / 'data', esp_base_url='http://%s:%s' % server.server_address,
        console_trust_file=trust, fan_model_file=model_file, machine_state_file=state)
    try:
        seed = bytes.fromhex((clients / 'power-agent-01-k1.seed').read_text().strip())
        envelope = signed(seed, 'power-agent-01', 0, 'fan-anomaly-001')
        code, response = runtime.handle_request(envelope)
        assert (code, response['decision'], response['reason_code']) == (
            202, 'CHALLENGE', 'ANOMALY_REVIEW_REQUIRED')
        assert json.loads(state.read_text())['fan_speed'] == 60
        code, view = runtime.review(request_id='fan-anomaly-001')
        assert code == 200 and view['eligible'] and view['assessment']['result'] == 'HIGH'
        assert view['assessment']['score_ppm'] == 1_000_000
        now = int(time.time())
        proof = {key: view[key] for key in BINDINGS}
        proof.update(schema_version='alice-review-action-v1', console_id='console-test',
            technician_id='TECH-DEMO', action_id=str(uuid.uuid4()), action='APPROVE_ONCE',
            biometric_session_id=str(uuid.uuid4()), biometric_policy='alice.live-face.v3',
            issued_at=now, expires_at=now + 60)
        review = {'proof': proof,
                  'signature': base64.b64encode(console_key.sign(DOMAIN + canonical_bytes(proof))).decode()}
        code, receipt = runtime.review(envelope=review)
        assert code == 200 and receipt['execution_status'] == 'COMPLETED'
        assert json.loads(state.read_text())['fan_speed'] == 0
        assert esp.commands == 0
    finally:
        runtime.close(); server.shutdown(); server.server_close()


def test_normal_fan_change_auto_allows(model_file):
    # Model-only regression: the staged +10 step must stay below review threshold.
    from dcamr.anomaly_engine.fan_model import FanModel
    model = FanModel(model_file)
    request = {'request_id': 'normal', 'agent_id': 'cooling-agent-01',
               'action': 'set_fan_speed', 'target': 'SERVER-ROOM-FANS',
               'parameters': {'value': 40}}
    raw, score = model.assess(request, {'fan_speed': 30, 'server_temperature': 35,
                                       'power_consumption': 400}, '0' * 64, 1)
    assert score['unusual'] is False and json.loads(raw)['result'] == 'LOW'
