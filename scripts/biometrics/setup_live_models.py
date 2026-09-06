"""Explicit, checksum-verified provisioning. Never invoked by an authentication flow."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
from console_paths import CONSOLE_ROOT

sys.path.insert(0, str(CONSOLE_ROOT / "services/biometrics"))
from app.live_models import ASSETS

URLS = {
    "pose": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "pad": "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx",
}

def provision():
    root = Path(os.environ.get("ALICE_INSIGHTFACE_ROOT") or CONSOLE_ROOT / "services/biometrics/models") / "live"
    root.mkdir(parents=True, exist_ok=True)
    for kind, (name, expected) in ASSETS.items():
        target = root / name
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"{name}: existing asset has an unexpected hash; preserved for inspection")
        else:
            with urllib.request.urlopen(URLS[kind], timeout=30) as response:
                content = response.read(20_000_001)
            if len(content) > 20_000_000 or hashlib.sha256(content).hexdigest() != expected:
                raise RuntimeError(f"{name}: download checksum mismatch")
            with tempfile.NamedTemporaryFile(dir=root, delete=False) as pending:
                pending.write(content)
                temporary = Path(pending.name)
            # Do not overwrite a concurrent operator's asset.
            try:
                os.link(temporary, target)
            finally:
                temporary.unlink()
        print(f"{kind}: {name} SHA256={expected}")
    print("Forged media: NONE_QUALIFIED. Full protected policy remains blocked.")

if __name__ == "__main__":
    provision()
