"""Real inference smoke test using scikit-image's public astronaut sample, not a live user."""
import base64
from pathlib import Path
from console_paths import CONSOLE_ROOT
import sys
import tempfile
import cv2
import numpy as np
from skimage import data
from fastapi.testclient import TestClient
sys.path.insert(0, str(CONSOLE_ROOT / "services/biometrics"))
from app.config import Settings
from app.engine import ArcFaceEngine
from app.main import create_app

root = CONSOLE_ROOT
token = "isolated-test-token-" + "x" * 32
def jpeg(image, quality=90):
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    assert ok
    return base64.b64encode(encoded).decode()

with tempfile.TemporaryDirectory(prefix="alice-arcface-") as temp:
    settings = Settings(token, Path(temp), root / "services/biometrics/models")
    engine = ArcFaceEngine(settings)
    assert engine.ready, engine.error
    image = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    with TestClient(create_app(settings, engine), headers={"Authorization": f"Bearer {token}"}) as client:
        response = client.post("/enroll", json={"technician_id":"PUBLIC-TEST-IMAGE", "frames":[jpeg(image, q) for q in range(87, 92)]})
        assert response.status_code == 200, response.text
        response = client.post("/verify", json={"technician_id":"PUBLIC-TEST-IMAGE", "frames":[jpeg(image, 95)]})
        assert response.status_code == 200 and response.json()["result"] == "PASS", response.text
        assert response.json()["liveness"] == "NOT_CONFIGURED"
        print("REAL_ARCFACE_ENROLLMENT: PASS (5 distinct encodings of a public test image)")
        print("REAL_ARCFACE_IDENTITY_MATCH: PASS")
        blank = np.zeros_like(image)
        response = client.post("/verify", json={"technician_id":"PUBLIC-TEST-IMAGE", "frames":[jpeg(blank)]})
        assert response.status_code == 422 and response.json()["detail"] == "NO_FACE_DETECTED", response.text
        doubled = np.concatenate([image,image],axis=1)
        response = client.post("/verify", json={"technician_id":"PUBLIC-TEST-IMAGE", "frames":[jpeg(doubled)]})
        assert response.status_code == 422 and response.json()["detail"] == "MULTIPLE_FACES_DETECTED", response.text
        print("REAL_ARCFACE_NO_FACE_AND_MULTIPLE_FACES: BLOCKED")
        print("LIVENESS: NOT CONFIGURED; live camera enrollment requires a technician")
