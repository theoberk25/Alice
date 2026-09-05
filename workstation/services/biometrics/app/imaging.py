"""Camera-independent decoding and quality checks. Raw frames stay in memory."""
import base64
import cv2
import numpy as np

class CaptureError(ValueError):
    pass

def decode_frame(encoded: str) -> np.ndarray:
    if not encoded or len(encoded) > 2_000_000:
        raise CaptureError("FRAME_TOO_LARGE_OR_EMPTY")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise CaptureError("INVALID_IMAGE_ENCODING") from exc
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3:
        raise CaptureError("INVALID_IMAGE")
    if min(image.shape[:2]) < 160 or max(image.shape[:2]) > 4096:
        raise CaptureError("UNSUPPORTED_IMAGE_DIMENSIONS")
    return image

def check_face_quality(image: np.ndarray, bbox: np.ndarray, score: float) -> None:
    x1, y1, x2, y2 = np.asarray(bbox, dtype=int)
    h, w = image.shape[:2]
    if score < 0.65 or x2 - x1 < 70 or y2 - y1 < 70:
        raise CaptureError("LOW_QUALITY_FACE_TOO_SMALL")
    crop = image[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
    if not crop.size:
        raise CaptureError("INVALID_FACE_BOUNDS")
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if not 25 < float(gray.mean()) < 235:
        raise CaptureError("LOW_QUALITY_LIGHTING")
    if float(cv2.Laplacian(gray, cv2.CV_64F).var()) < 25:
        raise CaptureError("LOW_QUALITY_BLUR")
