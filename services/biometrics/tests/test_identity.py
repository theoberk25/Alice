import base64
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.imaging import decode_frame, CaptureError
from app.engine import unit, similarity

TOKEN = "test-only-token-" + "a" * 32

class FakeEngine:
    ready = True
    error = ""
    def embedding(self, value):
        if value == "no-face":
            raise CaptureError("NO_FACE_DETECTED")
        if value == "multiple-faces":
            raise CaptureError("MULTIPLE_FACES_DETECTED")
        return np.array([0,1,0], dtype=np.float32) if value == "other-person" else np.array([1,0,0], dtype=np.float32)

@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(TOKEN, tmp_path / "data", tmp_path / "models"), FakeEngine())
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        yield client

def enroll(client):
    return client.post("/enroll", json={"technician_id":"T1", "frames":["one","two","three","four","five"]})

def test_loopback_client_requires_service_token(client):
    assert client.get("/health", headers={"Authorization":"Bearer wrong"}).status_code == 401

def test_enrollment_requires_five_distinct_frames(client):
    assert client.post("/enroll", json={"technician_id":"T1","frames":["one"]}).status_code == 422
    assert client.post("/enroll", json={"technician_id":"T1","frames":["one"]*5}).status_code == 422

def test_claimed_identity_passes_and_other_identity_fails(client):
    assert enroll(client).status_code == 200
    good=client.post("/verify",json={"technician_id":"T1","frames":["same-person"]}).json()
    bad=client.post("/verify",json={"technician_id":"T1","frames":["other-person"]}).json()
    assert good["result"] == "PASS"
    assert bad["result"] == "FAIL"
    assert good["liveness"] == "NOT_CONFIGURED"
    assert "embedding" not in good

def test_does_not_guess_another_enrolled_identity(client):
    enroll(client)
    response=client.post("/verify",json={"technician_id":"T2","frames":["same-person"]})
    assert response.status_code == 422
    assert response.json()["detail"] == "IDENTITY_NOT_ENROLLED"

@pytest.mark.parametrize("frame",["no-face","multiple-faces"])
def test_bad_captures_fail_visibly(client,frame):
    enroll(client)
    assert client.post("/verify",json={"technician_id":"T1","frames":[frame]}).status_code == 422

def test_identity_inconsistent_enrollment_rejected(client):
    response=client.post("/enroll",json={"technician_id":"T1","frames":["one","two","three","four","other-person"]})
    assert response.status_code == 422

def test_remove_prevents_verification(client):
    enroll(client)
    assert client.post("/remove",json={"technician_id":"T1"}).status_code == 200
    assert client.post("/verify",json={"technician_id":"T1","frames":["one"]}).status_code == 422

def test_embedding_is_encrypted_and_files_private(client,tmp_path):
    enroll(client)
    import sqlite3
    path=tmp_path/"data"/"enrollments.sqlite3"
    with sqlite3.connect(path) as db:
        stored=db.execute("SELECT embedding FROM enrollments").fetchone()[0]
    assert not stored.startswith(b"[")
    assert path.stat().st_mode & 0o777 == 0o600

def test_image_decode_is_bounded():
    with pytest.raises(CaptureError): decode_frame("x"*2_000_001)
    with pytest.raises(CaptureError): decode_frame(base64.b64encode(b"not an image").decode())
    with pytest.raises(CaptureError): unit(np.array([np.nan,0]))
    assert similarity(np.array([1,0]),np.array([1,0])) == 1.0

def test_unavailable_model_keeps_service_bootable(tmp_path):
    engine=FakeEngine();engine.ready=False;engine.error="MODEL_FILES_MISSING"
    with TestClient(create_app(Settings(TOKEN,tmp_path/'data',tmp_path/'models'),engine),headers={"Authorization":f"Bearer {TOKEN}"}) as c:
        assert c.get('/health').json()['status']=='UNAVAILABLE'
        assert c.post('/verify',json={"technician_id":"T1","frames":["one"]}).status_code==503
