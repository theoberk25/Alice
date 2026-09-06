import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from dcamr.audit.event_contract import canonical_bytes
from services.light_mcp.alice_client import AliceFanClient


class Response:
    code = 202

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b'{"decision":"CHALLENGE","reason_code":"ANOMALY_REVIEW_REQUIRED"}'


class CaptureOpener:
    def __init__(self):
        self.request = None

    def open(self, request, timeout):
        assert timeout == 15
        self.request = request
        return Response()


def test_fan_client_preserves_identity_and_signs_exact_request(tmp_path):
    key = Ed25519PrivateKey.generate()
    seed = tmp_path / 'cooling.seed'
    seed.write_text(key.private_bytes_raw().hex())
    seed.chmod(0o600)
    client = AliceFanClient('http://192.168.50.20:8080', 'cooling-agent-01', seed)
    capture = CaptureOpener()
    client.opener = capture

    result = client.set_fan_speed(40)
    envelope = json.loads(capture.request.data)
    request = envelope['request']
    assert capture.request.full_url == 'http://192.168.50.20:8080/request'
    assert request['agent_id'] == 'cooling-agent-01'
    assert request['action'] == 'set_fan_speed'
    assert request['target'] == 'SERVER-ROOM-FANS'
    assert request['parameters'] == {'value': 40}
    key.public_key().verify(base64.b64decode(envelope['signature']), canonical_bytes(request))
    assert result['http_status'] == 202
    assert result['request_id'] == request['request_id']


@pytest.mark.parametrize('value', [True, 1.5, -1, 101])
def test_fan_client_rejects_non_integer_or_out_of_range_values(tmp_path, value):
    key = Ed25519PrivateKey.generate()
    seed = tmp_path / 'agent.seed'
    seed.write_text(key.private_bytes_raw().hex())
    seed.chmod(0o600)
    client = AliceFanClient('http://192.168.50.20:8080', 'power-agent-01', seed)
    with pytest.raises(ValueError, match='integer'):
        client.set_fan_speed(value)
