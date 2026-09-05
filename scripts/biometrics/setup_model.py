"""Explicitly provision the InsightFace research model; never downloads at app login."""
from pathlib import Path
from console_paths import CONSOLE_ROOT
import os
from insightface.app import FaceAnalysis
root = Path(os.environ.get("ALICE_INSIGHTFACE_ROOT") or CONSOLE_ROOT / "services/biometrics/models")
model = FaceAnalysis(name="buffalo_l", root=str(root), allowed_modules=["detection", "recognition"], providers=["CPUExecutionProvider"])
model.prepare(ctx_id=-1, det_size=(640, 640))
print(f"ArcFace detection and recognition ready at {root}. Liveness: NOT CONFIGURED.")
