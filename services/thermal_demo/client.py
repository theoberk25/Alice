"""Small agent-facing observation/proposal client. No decision or approval API."""
import json
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.parse import urlsplit


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class DemoClient:
    def __init__(self, base_url, token):
        parsed = urlsplit(base_url)
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/')):
            raise ValueError('Use the loopback demo URL or a local SSH tunnel')
        self.url, self.token = base_url.rstrip('/'), token
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _call(self, path, body=None):
        req = Request(self.url + path, data=None if body is None else json.dumps(body, allow_nan=False).encode(),
                      headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        # No automatic retry: uncertain requests must be reconciled by request ID.
        with self.opener.open(req, timeout=5) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('Demo response exceeds limit')
        return json.loads(raw)

    def state(self):
        return self._call('/demo/state')

    def request_fan(self, snapshot, fan_pct, request_id):
        return self._call('/demo/fan-requests', {'run_id': snapshot['run_id'],
                          'expected_revision': snapshot['revision'],
                          'fan_pct': fan_pct, 'request_id': request_id})
