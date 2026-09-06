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
            self.error = "MODEL_FILES_MISSING: run scripts/biometrics/setup_model.py"
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
        vector, _ = self.observe(image)
        return vector

    def observe(self, image: np.ndarray):
        vector, bbox, _ = self.observe_with_landmarks(image)
        return vector, bbox

    def observe_with_landmarks(self, image: np.ndarray):
        if not self.ready or self.app is None:
            raise CaptureError(self.error)
        # FaceAnalysis.get embeds every detected face before returning. Reject
        # missing/multiple/low-quality faces before paying for ArcFace, using
        # the same detector, full-image scan and upstream landmark alignment.
        bboxes, landmarks = self.app.det_model.detect(image, max_num=0, metric="default")
        if len(bboxes) == 0:
            raise CaptureError("NO_FACE_DETECTED")
        if len(bboxes) != 1:
            raise CaptureError("MULTIPLE_FACES_DETECTED")
        bbox, score = bboxes[0, :4], float(bboxes[0, 4])
        check_face_quality(image, bbox, score)
        if landmarks is None or np.asarray(landmarks).shape != (1, 5, 2) or not np.isfinite(landmarks).all():
            raise CaptureError("FACE_FEATURES_NOT_VISIBLE")
        from insightface.app.common import Face
        face = Face(bbox=bbox, kps=landmarks[0], det_score=score)
        # InsightFace recognition performs landmark alignment before ArcFace inference.
        self.app.models["recognition"].get(image, face)
        return unit(face.embedding), np.asarray(face.bbox), np.asarray(face.kps, dtype=np.float32)
