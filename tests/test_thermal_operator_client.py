"""Tests for the cloud operator lifecycle client (plant on/off).

Uses a tiny stub HTTP server that records requests, so we verify the client's
transitions and auth without standing up the full thermal runtime.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from cloud import thermal_operator_client as toc


def _make_stub(initial_status):
    recorded = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _state(self):
            return {"schema_version": "thermal-demo-v1", "status": self.server.status,
                    "run_id": "f" * 32, "revision": 0,
                    "values": {"temperature_f": 90, "fan_target_pct": 60, "fan_actual_pct": 60,
                               "power_w": 421.6, "battery_pct": 60}}

        def _reply(self, obj):
            body = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            recorded.append(("GET", self.path, None, self.headers.get("Authorization")))
            self._reply(self._state())

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n).decode()) if n else {}
            recorded.append(("POST", self.path, body, self.headers.get("Authorization")))
            if self.path == "/demo/configure":
                self.server.status = "READY"
            elif self.path in ("/demo/start", "/demo/resume"):
                self.server.status = "RUNNING"
            elif self.path == "/demo/stop":
                self.server.status = "STOPPED"
            self._reply(self._state())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.status = initial_status
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    return server, thread, url, recorded


def _token_file(tmp_path):
    f = tmp_path / "operator.token"
    f.write_text("operator-secret\n")
    return str(f)


def test_bring_online_from_off_configures_then_starts(tmp_path, monkeypatch):
    monkeypatch.setenv("ALICE_THERMAL_OPERATOR_TOKEN_FILE", _token_file(tmp_path))
    for k in ("ALICE_PLANT_TEMPERATURE_F", "ALICE_PLANT_FAN_PCT", "ALICE_PLANT_BATTERY_PCT"):
        monkeypatch.delenv(k, raising=False)
    server, thread, url, recorded = _make_stub("STOPPED")
    try:
        result = toc.bring_all_systems_online(base_url=url)
    finally:
        server.shutdown(); server.server_close(); thread.join()
    assert result["action"] == "configured_and_started"
    assert result["status"] == "RUNNING"
    paths = [(m, p) for m, p, _, _ in recorded]
    assert ("POST", "/demo/configure") in paths and ("POST", "/demo/start") in paths
    cfg = next(b for m, p, b, _ in recorded if p == "/demo/configure")
    assert cfg == {"temperature_f": 90, "fan_pct": 60, "battery_pct": 60}
    start_body = next(b for m, p, b, _ in recorded if p == "/demo/start")
    assert start_body == {}
    assert all(auth == "Bearer operator-secret" for _, _, _, auth in recorded)


def test_bring_online_already_running_is_noop(tmp_path, monkeypatch):
    monkeypatch.setenv("ALICE_THERMAL_OPERATOR_TOKEN_FILE", _token_file(tmp_path))
    server, thread, url, recorded = _make_stub("RUNNING")
    try:
        result = toc.bring_all_systems_online(base_url=url)
    finally:
        server.shutdown(); server.server_close(); thread.join()
    assert result["action"] == "already_online" and result["status"] == "RUNNING"
    assert not any(p == "/demo/configure" for _, p, _, _ in recorded)


def test_all_systems_off_stops_when_running(tmp_path, monkeypatch):
    monkeypatch.setenv("ALICE_THERMAL_OPERATOR_TOKEN_FILE", _token_file(tmp_path))
    server, thread, url, recorded = _make_stub("RUNNING")
    try:
        result = toc.all_systems_off(base_url=url)
    finally:
        server.shutdown(); server.server_close(); thread.join()
    assert result["action"] == "stopped" and result["status"] == "STOPPED"
    assert ("POST", "/demo/stop") in [(m, p) for m, p, _, _ in recorded]


def test_all_systems_off_noop_when_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setenv("ALICE_THERMAL_OPERATOR_TOKEN_FILE", _token_file(tmp_path))
    server, thread, url, recorded = _make_stub("UNCONFIGURED")
    try:
        result = toc.all_systems_off(base_url=url)
    finally:
        server.shutdown(); server.server_close(); thread.join()
    assert result["action"] == "already_off"
    assert not any(p == "/demo/stop" for _, p, _, _ in recorded)


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("ALICE_THERMAL_OPERATOR_TOKEN_FILE", raising=False)
    monkeypatch.delenv("ALICE_THERMAL_OPERATOR_TOKEN", raising=False)
    with pytest.raises(ValueError):
        toc.bring_all_systems_online(base_url="http://127.0.0.1:1")
