"""Signed fan-action client for the ALICE runtime boundary."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dcamr.audit.event_contract import canonical_bytes


class AliceFanClient:
    def __init__(self, url, agent_id, key_file):
        if url.rstrip('/') != 'http://192.168.50.20:8080':
            raise ValueError('fan demo client requires the fixed ALICE Pi origin')
        path = Path(key_file)
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError('agent key must be private mode 0600')
        self.url, self.agent_id = url.rstrip('/'), agent_id
        self.key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(path.read_text().strip()))
        self.opener = build_opener(ProxyHandler({}))

    def set_fan_speed(self, value):
        if type(value) is not int or not 0 <= value <= 100:
            raise ValueError('fan speed must be an integer from 0 through 100')
        request = {'schema_version': '1.0', 'request_id': str(uuid.uuid4()),
                   'agent_id': self.agent_id, 'action': 'set_fan_speed',
                   'target': 'SERVER-ROOM-FANS', 'parameters': {'value': value},
                   'issued_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}
        envelope = {'request': request, 'key_id': self.agent_id + '-k1',
                    'signature': base64.b64encode(self.key.sign(canonical_bytes(request))).decode()}
        raw = json.dumps(envelope).encode()
        try:
            response = self.opener.open(Request(self.url + '/request', data=raw,
                method='POST', headers={'Content-Type': 'application/json'}), timeout=15)
        except HTTPError as exc:
            response = exc
        with response:
            result = json.loads(response.read())
            return {'ok': response.code in (200, 202), 'http_status': response.code,
                    'request_id': request['request_id'], **result}
