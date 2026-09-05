"""Stdlib mock of the ESP light node, used until the firmware contract lands.

Contract (open coordination item, see the first-light plan): POST /light with
{"state": "on"|"off"} sets the light; GET /light returns {"state": ...};
GET /stats returns {"commands": N} so tests can prove idempotent retries send
exactly one command. Placement per AGENTS.md (lab tooling in scripts/lab/).
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading


class MockEsp:
    def __init__(self):
        self._lock = threading.Lock()
        self.state = "off"
        self.commands = 0

    def set_state(self, state: str):
        with self._lock:
            self.state = state
            self.commands += 1


def make_server(host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, MockEsp]:
    esp = MockEsp()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/light":
                self._reply(200, {"state": esp.state})
            elif self.path == "/stats":
                self._reply(200, {"commands": esp.commands})
            else:
                self._reply(404, {"error": "unknown path"})

        def do_POST(self):
            if self.path != "/light":
                return self._reply(404, {"error": "unknown path"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                state = payload["state"]
                if state not in ("on", "off"):
                    raise ValueError
            except (ValueError, KeyError):
                return self._reply(400, {"error": "state must be on or off"})
            esp.set_state(state)
            self._reply(200, {"ok": True, "state": esp.state})

    return ThreadingHTTPServer((host, port), Handler), esp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    server, _ = make_server(args.host, args.port)
    print(f"mock ESP listening on {server.server_address}")
    server.serve_forever()


if __name__ == "__main__":
    main()
