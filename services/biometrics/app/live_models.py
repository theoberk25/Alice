"""Pinned offline assets. No model downloads at service startup or authentication."""
import hashlib
import subprocess
import sys
from pathlib import Path
from .pad import MiniFASNet
from .pose import FaceLandmarker

ASSETS = {
    "pose": ("face_landmarker.task", "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
    "pad": ("MiniFASNetV2.onnx", "b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907"),
}

def verified_asset(root, name):
    filename, expected = ASSETS[name]
    path = root / "live" / filename
    if not path.is_file() or path.stat().st_size > 20_000_000:
        raise ValueError(f"{name.upper()}_MODEL_MISSING")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"{name.upper()}_MODEL_HASH_MISMATCH")
    return path

def load(config):
    models = {"identity": f"insightface-0.7.3/{config.model_name}",
              "pose": ASSETS["pose"][1], "pad": ASSETS["pad"][1]}
    pose_factory = pad = None
    try:
        pose_path = verified_asset(config.model_root, "pose")
        # Native MediaPipe can abort instead of raising when OS graphics services
        # are unavailable. Probe in a short-lived child so ArcFace stays bootable.
        code = "import sys;from app.pose import FaceLandmarker;p=FaceLandmarker(sys.argv[1]);p.close()"
        result = subprocess.run([sys.executable, "-c", code, str(pose_path.resolve())],
                                cwd=Path(__file__).resolve().parents[1], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=15, check=False)
        if result.returncode != 0:
            raise ValueError("POSE_NATIVE_RUNTIME_UNAVAILABLE")
        pose_factory = lambda: FaceLandmarker(pose_path)
    except (ImportError, ValueError, RuntimeError, OSError, subprocess.TimeoutExpired):
        pass
    try:
        pad = MiniFASNet(verified_asset(config.model_root, "pad"), models["pad"])
    except (ImportError, ValueError, RuntimeError, OSError):
        pass
    return pose_factory, pad, models
