"""Rehearsal uses signed permission and existing mock controller, no native face bypass."""
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_rehearsal_starts_with_signed_holds_and_no_execution(tmp_path):
    directory = tmp_path.resolve() / "native rehearsal"
    child = subprocess.Popen(
        [sys.executable, "-m", "lab.first_light.native_review_demo", "--directory", str(directory),
         "--technician-id", "TEST-TECH"], cwd=ROOT, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # Child has no native app or biometric mock path. Readiness is emitted only
        # after two requests become HOLD via a genuinely signed test release.
        import select
        assert select.select([child.stdout], [], [], 20)[0], "Rehearsal startup timed out"
        line = child.stdout.readline()
        assert line, child.stderr.read()
        ready = json.loads(line)
        assert ready["ready"] and ready["mock_commands"] == 0
        assert ready["requests"][0].startswith("native-test-approve-")
        assert ready["requests"][1].startswith("native-test-reject-")
        session = json.loads((directory / "session.json").read_text())
        env = session["environment"]
        assert env["ALICE_TRANSPORT_MODE"] == "remote"
        assert env["ALICE_BIOMETRIC_MODE"] == "arcface"
        assert not any(k in env for k in ("ALICE_DATABASE_PATH", "ALICE_BIOMETRIC_TOKEN", "ALICE_BIOMETRIC_DATA_DIR"))
        req = urllib.request.Request(env["ALICE_FEED_URL"] + "/review/" + ready["requests"][0],
                                     headers={"Authorization": "Bearer " + env["ALICE_FEED_TOKEN"]})
        with urllib.request.urlopen(req, timeout=5) as response:
            snapshot = json.load(response)
        assert snapshot["eligible"] and snapshot["decision"] == "CHALLENGE"
        assert snapshot["execution_status"] == "NOT_EXECUTED"
        assert snapshot["request"]["parameters"] == {"state": "on"}
        assert os.stat(directory / "session.json").st_mode & 0o077 == 0
        assert session["runtime_url"].startswith("http://127.0.0.1:")
        # Public command submits through the existing runtime HTTP endpoint;
        # it adds a real signed permission HOLD without commanding the mock ESP.
        command = subprocess.run(
            [sys.executable, "-m", "lab.first_light.send_native_hold", "--session",
             str(directory / "session.json")], cwd=ROOT, capture_output=True, text=True, timeout=15)
        assert command.returncode == 0, command.stderr
        submitted = json.loads(command.stdout)
        assert set(submitted) == {"request_id", "decision", "execution"}
        assert submitted["request_id"].startswith("native-test-")
        assert submitted["request_id"] not in ready["requests"]
        assert submitted["decision"] == "CHALLENGE" and submitted["execution"] == "NOT_EXECUTED"
        assert env["ALICE_FEED_TOKEN"] not in command.stdout + command.stderr
        req = urllib.request.Request(env["ALICE_FEED_URL"] + "/review/" + submitted["request_id"],
                                     headers={"Authorization": "Bearer " + env["ALICE_FEED_TOKEN"]})
        with urllib.request.urlopen(req, timeout=5) as response:
            snapshot = json.load(response)
        assert snapshot["eligible"] and snapshot["decision"] == "CHALLENGE"
        assert snapshot["execution_status"] == "NOT_EXECUTED"
        child.stdin.write("status\nstop\n")
        child.stdin.flush()
        stdout, stderr = child.communicate(timeout=10)
        assert child.returncode == 0, stderr
        assert json.loads(stdout.splitlines()[0])["mock_commands"] == 0
    finally:
        if child.poll() is None:
            child.terminate()
            child.communicate(timeout=10)


@pytest.mark.parametrize("change", [
    {"source": "PHYSICAL PI"},
    {"runtime_url": "http://192.168.50.20:8080"},
    {"runtime_url": "https://127.0.0.1:8080"},
    {"runtime_url": "http://localhost:8080"},
    {"runtime_url": "http://127.0.0.1:8080/request"},
    {"runtime_url": "http://user:password@127.0.0.1:8080"},
    {"runtime_url": "http://127.0.0.1:8080?forward=remote"},
    {"directory": "/wrong/session"},
    {"extra": "unknown"},
])
def test_hold_command_refuses_nonlocal_or_nonrehearsal_without_network(tmp_path, change):
    from unittest.mock import patch
    from lab.first_light.send_native_hold import HoldTestError, send_hold
    from lab.first_light.native_review_demo import REHEARSAL_SOURCE
    directory = tmp_path.resolve() / "test-rehearsal"
    directory.mkdir(mode=0o700)
    value = {"source": REHEARSAL_SOURCE, "directory": str(directory),
             "runtime_url": "http://127.0.0.1:12345", "environment": {
                 "ALICE_TRANSPORT_MODE": "remote", "ALICE_BIOMETRIC_MODE": "arcface",
                 "ALICE_FEED_URL": "http://127.0.0.1:12346", "ALICE_FEED_TOKEN": "t" * 32}}
    value.update(change)
    session = directory / "session.json"
    session.write_text(json.dumps(value))
    session.chmod(0o600)
    with patch('lab.first_light.send_native_hold.build_opener') as network:
        with pytest.raises(HoldTestError, match='INVALID_LOCAL_REHEARSAL_SESSION'):
            send_hold(session)
    network.assert_not_called()


def test_hold_command_checks_session_privacy_and_package_alias(tmp_path):
    from unittest.mock import patch
    from lab.first_light.send_native_hold import HoldTestError, send_hold
    session = tmp_path / "session.json"
    session.write_text('{}')
    session.chmod(0o644)
    with patch('lab.first_light.send_native_hold.build_opener') as network:
        with pytest.raises(HoldTestError, match='INVALID_LOCAL_REHEARSAL_SESSION'):
            send_hold(session)
    network.assert_not_called()
    package = json.loads((ROOT / "package.json").read_text())
    assert package['scripts']['demo:hold'] == '.venv/bin/python -m lab.first_light.send_native_hold'


def test_hold_command_refuses_bridge_that_reports_physical_controller_before_post(tmp_path):
    from unittest.mock import MagicMock, patch
    from lab.first_light.send_native_hold import HoldTestError, send_hold
    from lab.first_light.native_review_demo import REHEARSAL_SOURCE
    directory = tmp_path.resolve() / 'private-rehearsal'
    directory.mkdir(mode=0o700)
    client = directory / 'bundle/client'
    client.mkdir(parents=True)
    key = client / 'term-agent-01-k1.seed'
    key.write_text(os.urandom(32).hex() + '\n')
    key.chmod(0o600)
    session = directory / 'session.json'
    session.write_text(json.dumps({
        'source': REHEARSAL_SOURCE, 'directory': str(directory),
        'runtime_url': 'http://127.0.0.1:12345', 'environment': {
            'ALICE_TRANSPORT_MODE': 'remote', 'ALICE_BIOMETRIC_MODE': 'arcface',
            'ALICE_FEED_URL': 'http://127.0.0.1:12346', 'ALICE_FEED_TOKEN': 't' * 32}}))
    session.chmod(0o600)
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps({
        'schema_version': 'alice-runtime-feed-v1',
        'source': {'connection': 'ssh-tunnel', 'controller': 'physical-serial'}, 'events': []}).encode()
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = response
    with patch('lab.first_light.send_native_hold.build_opener', return_value=opener):
        with pytest.raises(HoldTestError, match='LOCAL_MOCK_REHEARSAL_UNAVAILABLE'):
            send_hold(session)
    assert opener.open.call_count == 1
    assert opener.open.call_args.args[0].get_method() == 'GET'
