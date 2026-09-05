"""Exercise real ArcFace through Rust commands with an isolated public-image identity."""
import base64
import json
import os
from pathlib import Path
from console_paths import REPOSITORY_ROOT, CONSOLE_ROOT
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import cv2
import numpy as np
from skimage import data

root = CONSOLE_ROOT

def jpeg(image, quality=90):
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    assert ok
    return base64.b64encode(encoded).decode()

with tempfile.TemporaryDirectory(prefix="alice-native-face-") as temporary:
    temp = Path(temporary)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    token = secrets.token_urlsafe(48)
    url = f"http://127.0.0.1:{port}"
    image = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    captures = temp / "captures.json"
    captures.write_text(json.dumps({
        "enrollment": [jpeg(image, quality) for quality in range(87, 92)],
        "face": [jpeg(image, 95)],
        "blank": [jpeg(np.zeros_like(image))],
    }))
    captures.chmod(0o600)
    env = {**os.environ, "ALICE_BIOMETRIC_TOKEN": token,
           "ALICE_BIOMETRIC_SERVICE_URL": url, "ALICE_BIOMETRIC_DATA_DIR": str(temp / "identity"),
           "ALICE_INSIGHTFACE_ROOT": str(root / "services/biometrics/models"),
           "ALICE_TEST_CAPTURE_FILE": str(captures), "NO_ALBUMENTATIONS_UPDATE": "1",
           "MPLCONFIGDIR": str(temp / "matplotlib")}
    with (temp / "service.log").open("w") as service_log:
        service = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                                   cwd=root / "services/biometrics", env=env, stdout=service_log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 55
            while True:
                if service.poll() is not None:
                    raise RuntimeError("Biometric service exited before readiness")
                try:
                    request = urllib.request.Request(url + "/health", headers={"Authorization": f"Bearer {token}"})
                    with urllib.request.urlopen(request, timeout=2) as response:
                        health = json.load(response)
                    assert health["status"] == "READY", health
                    assert health["liveness"] == "NOT_CONFIGURED", health
                    break
                except urllib.error.URLError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Biometric service readiness timed out")
                    time.sleep(0.25)
            try:
                urllib.request.urlopen(url + "/health", timeout=2)
                raise AssertionError("Unauthenticated service request was accepted")
            except urllib.error.HTTPError as error:
                assert error.code == 401
            subprocess.run(["node", str(REPOSITORY_ROOT / "scripts/console/rust.mjs"), "test", "real_identity_login_and_step_up", "--", "--ignored", "--nocapture"], cwd=root, env=env, check=True)
        finally:
            service.terminate()
            try:
                service.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service.kill()
                service.wait()
