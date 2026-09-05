from typing import Protocol
import numpy as np
from .imaging import decode_frame, check_face_quality, CaptureError
from .config import Settings

class IdentityEngine(Protocol):
    ready: bool
    error: str
    def embedding(self, encoded: str) -> np.ndarray: ...

def unit(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(vector)
    if vector.ndim != 1 or not np.isfinite(vector).all() or norm < 1e-8:
        raise CaptureError("INVALID_EMBEDDING")
    return vector / norm

def similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        raise CaptureError("EMBEDDING_MODEL_MISMATCH")
    return float(np.clip(np.dot(unit(a), unit(b)), -1, 1))

class ArcFaceEngine:
    def __init__(self, settings: Settings):
        self.ready = False
        self.error = "MODEL_NOT_LOADED"
        self.app = None
        model_dir = settings.model_root / "models" / settings.model_name
        if not model_dir.exists():
            self.error = "MODEL_FILES_MISSING: run scripts/setup-model.py"
            return
        try:
            from insightface.app import FaceAnalysis
            self.app = FaceAnalysis(name=settings.model_name, root=str(settings.model_root), allowed_modules=["detection", "recognition"], providers=["CPUExecutionProvider"])
            self.app.prepare(ctx_id=-1, det_size=(640, 640))
            self.ready = True
            self.error = ""
        except Exception as exc:
            self.error = f"MODEL_LOAD_FAILED: {type(exc).__name__}"

    def embedding(self, encoded: str) -> np.ndarray:
        if not self.ready or self.app is None:
            raise CaptureError(self.error)
        image = decode_frame(encoded)
        faces = self.app.get(image)
        if len(faces) == 0:
            raise CaptureError("NO_FACE_DETECTED")
        if len(faces) != 1:
            raise CaptureError("MULTIPLE_FACES_DETECTED")
        face = faces[0]
        check_face_quality(image, face.bbox, float(face.det_score))
        # InsightFace recognition performs landmark alignment before ArcFace inference.
        return unit(face.embedding)

class AuthenticityVerifier(Protocol):
    """Future anti-spoof adapter; never infer liveness from cosine similarity."""
    def verify_authenticity(self, frames: list[str]) -> str: ...
