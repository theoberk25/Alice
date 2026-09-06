"""MiniFASNetV2 2.7 contextual-crop presentation-check adapter."""
import cv2
import numpy as np
from .imaging import CaptureError
from .live_contract import Control, Outcome

def preprocess(image: np.ndarray, bbox) -> np.ndarray:
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise CaptureError("PAD_EXPECTS_UINT8_BGR")
    values = np.asarray(bbox, dtype=float)
    if values.shape != (4,) or not np.isfinite(values).all():
        raise CaptureError("PAD_INVALID_BOUNDS")
    x1, y1, x2, y2 = values
    x, y, width, height = int(x1), int(y1), int(x2 - x1), int(y2 - y1)
    h, w = image.shape[:2]
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x2 > w or y2 > h:
        raise CaptureError("PAD_INVALID_BOUNDS")
    scale = min((h - 1) / height, (w - 1) / width, 2.7)
    cx, cy = x + width / 2, y + height / 2
    left, top = max(0, int(cx - width * scale / 2)), max(0, int(cy - height * scale / 2))
    right, bottom = min(w - 1, int(cx + width * scale / 2)), min(h - 1, int(cy + height * scale / 2))
    crop = image[top:bottom + 1, left:right + 1]
    if not crop.size:
        raise CaptureError("PAD_EMPTY_CROP")
    return np.ascontiguousarray(cv2.resize(crop, (80, 80)).astype(np.float32).transpose(2, 0, 1)[None])

def bona_fide_probability(logits: np.ndarray) -> float:
    logits = np.asarray(logits)
    if logits.shape != (1, 3) or not np.isfinite(logits).all():
        raise CaptureError("PAD_INVALID_OUTPUT")
    values = np.exp(logits.astype(np.float64) - np.max(logits))
    return float((values / values.sum())[0, 1])

class MiniFASNet:
    def __init__(self, path, model_id: str, threshold: float = 0.90):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        self.model_id, self.threshold = model_id, threshold
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        if len(inputs) != 1 or len(outputs) != 1 or inputs[0].shape[-3:] != [3, 80, 80] or inputs[0].type != "tensor(float)":
            raise CaptureError("PAD_MODEL_CONTRACT_MISMATCH")
        self.input_name, self.output_name = inputs[0].name, outputs[0].name

    def verify(self, image, bbox) -> Control:
        output = self.session.run([self.output_name], {self.input_name: preprocess(image, bbox)})[0]
        score = bona_fide_probability(output)
        return Control(result=Outcome.PASS if score >= self.threshold else Outcome.FAIL,
                       model=self.model_id, reason="BONA_FIDE_PROBABILITY", score=score)
