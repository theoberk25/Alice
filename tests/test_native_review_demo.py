"""Rehearsal uses signed permission and existing mock controller, no native face bypass."""
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

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
        child.stdin.write("status\nstop\n")
        child.stdin.flush()
        stdout, stderr = child.communicate(timeout=10)
        assert child.returncode == 0, stderr
        assert json.loads(stdout.splitlines()[0])["mock_commands"] == 0
    finally:
        if child.poll() is None:
            child.terminate()
            child.communicate(timeout=10)
