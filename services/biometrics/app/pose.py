"""Unmirrored camera observations, not a liveness verdict.

MediaPipe matrix coordinates: x image-right, y up, z toward the viewer; its
virtual camera looks down -z and the canonical face looks toward +z. The image
landmarks have a different, y-down convention. Returned yaw follows the operator's
head-turn convention on ALICE's native Mac capture path: positive is LEFT. Live
operator feedback demonstrated the previous Euler-yaw direction was reversed;
that conversion is applied once here, independently of preview mirroring.
Returned pitch is positive UP and negates the matrix's X Euler angle.
Display mirroring must never be applied to authoritative input.

https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md#metric-3d-space
"""
from dataclasses import dataclass
from copy import deepcopy
import math
import cv2
import numpy as np
from .imaging import CaptureError

ENROLLMENT_POSE_LIMITS = (45, 35, 25)
NEUTRAL_POSE_LIMITS = (20, 30, 20)
# Enrollment applies limits after subtracting its accepted camera/resting bias.
# Existing galleries do not persist that bias. Passive verification must cover
# the same possible raw orientations, without requiring a new frontal scan.
VERIFICATION_POSE_LIMITS = tuple(a + b for a, b in zip(ENROLLMENT_POSE_LIMITS, NEUTRAL_POSE_LIMITS))

def angles(matrix: np.ndarray) -> tuple[float, float, float]:
    m = np.asarray(matrix, dtype=np.float64)
    if m.shape != (4, 4) or not np.isfinite(m).all():
        raise CaptureError("INVALID_POSE_MATRIX")
    rotation = m[:3, :3]
    # MediaPipe may include uniform scale. Reject shear/reflection/degeneracy.
    scales = np.linalg.norm(rotation, axis=0)
    if np.min(scales) < 1e-6:
        raise CaptureError("INVALID_POSE_MATRIX")
    rotation = rotation / scales
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=0.05) or np.linalg.det(rotation) < 0.9:
        raise CaptureError("INVALID_POSE_MATRIX")
    yaw = -math.asin(float(np.clip(-rotation[2, 0], -1, 1)))
    pitch = -math.atan2(rotation[2, 1], rotation[2, 2])
    roll = math.atan2(rotation[1, 0], rotation[0, 0])
    return tuple(math.degrees(v) for v in (yaw, pitch, roll))

def mirrored_display_angles(yaw: float, pitch: float, roll: float):
    return -yaw, pitch, -roll

def pose_bin(yaw: float, pitch: float, roll: float, *, limits=ENROLLMENT_POSE_LIMITS) -> str | None:
    if not all(math.isfinite(x) for x in (yaw, pitch, roll)):
        raise CaptureError("NONFINITE_POSE")
    if any(abs(value) > limit for value, limit in zip((yaw, pitch, roll), limits)):
        return None
    horizontal = "LEFT" if yaw >= 10 else "RIGHT" if yaw <= -10 else ""
    vertical = "UP" if pitch >= 8 else "DOWN" if pitch <= -8 else ""
    if horizontal and vertical:
        return f"{vertical}_{horizontal}"
    return vertical or horizontal or "CENTER"

@dataclass(frozen=True)
class PoseObservation:
    yaw: float
    pitch: float
    roll: float
    region: str | None
    calibrated: bool = True


class NeutralPose:
    """Session-local neutral pose; never updated while the operator scans."""
    def __init__(self):
        self.samples = []
        self.center = None
        self.previous = None
        self.last_ms = -1

    def interrupt(self):
        self.samples.clear()
        self.previous = None

    def observe(self, yaw, pitch, roll, elapsed_ms):
        values = np.asarray([yaw, pitch, roll], dtype=float)
        if not np.isfinite(values).all():
            raise CaptureError('NONFINITE_POSE')
        if elapsed_ms <= self.last_ms:
            raise CaptureError('STALE_POSE_OBSERVATION')
        if self.last_ms >= 0 and elapsed_ms - self.last_ms > 1500:
            self.interrupt()
        self.last_ms = elapsed_ms
        if self.center is None:
            # A near-front stable pose tolerates laptop/camera mounting bias.
            # Three observations spanning >=400ms are required; a moving or
            # strongly off-axis head cannot become the neutral reference.
            if np.any(np.abs(values) > NEUTRAL_POSE_LIMITS):
                self.samples.clear()
                return PoseObservation(yaw, pitch, roll, None, False)
            self.samples.append((elapsed_ms, values))
            self.samples = self.samples[-3:]
            recent = np.stack([v for _, v in self.samples])
            if np.any(np.ptp(recent, axis=0) > 3):
                self.samples = [(elapsed_ms, values)]
            if len(self.samples) < 3 or elapsed_ms - self.samples[0][0] < 400:
                return PoseObservation(yaw, pitch, roll, None, False)
            self.center = np.median(recent, axis=0)
        relative = values - self.center
        region = pose_bin(*relative)
        if region == 'CENTER':
            # Retain small boundary wobble only near neutral. Extending a diagonal
            # into an already valid cardinal view narrows that sector on a circle
            # and can skip its second sample at the native 4 Hz evidence cadence.
            old = self.previous or ''
            horizontal = ('LEFT' if relative[0] >= 10 or ('LEFT' in old and relative[0] >= 7)
                          else 'RIGHT' if relative[0] <= -10 or ('RIGHT' in old and relative[0] <= -7) else '')
            vertical = ('UP' if relative[1] >= 8 or ('UP' in old and relative[1] >= 5)
                        else 'DOWN' if relative[1] <= -8 or ('DOWN' in old and relative[1] <= -5) else '')
            region = f'{vertical}_{horizontal}' if horizontal and vertical else vertical or horizontal or 'CENTER'
        self.previous = region
        return PoseObservation(*map(float, relative), region)

class FaceLandmarker:
    def __init__(self, path):
        import mediapipe as mp
        self.mp = mp
        self.task = mp.tasks.vision.FaceLandmarker.create_from_options(
            mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(path), delegate=mp.tasks.BaseOptions.Delegate.CPU),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_faces=2, min_face_detection_confidence=0.7,
                min_face_presence_confidence=0.7, min_tracking_confidence=0.7,
                output_facial_transformation_matrixes=True,
            )
        )
        self.last_timestamp = -1
        self.neutral = NeutralPose()
        self.pending_neutral = None
        self.calibrate_neutral = True

    def observe(self, image: np.ndarray, timestamp: int) -> PoseObservation:
        if timestamp <= self.last_timestamp:
            raise CaptureError("STALE_POSE_OBSERVATION")
        self.last_timestamp = timestamp
        result = self.task.detect_for_video(self.mp.Image(
            image_format=self.mp.ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB)), timestamp)
        if len(result.face_landmarks) == 0:
            raise CaptureError("NO_FACE_DETECTED")
        if len(result.face_landmarks) > 1:
            raise CaptureError("MULTIPLE_FACES_DETECTED")
        if len(result.facial_transformation_matrixes) != 1:
            raise CaptureError("FACE_POSE_INCONCLUSIVE")
        # Require the main facial features inside the input bounds. This is a
        # conservative visibility proxy, not a trained occlusion classifier.
        points = result.face_landmarks[0]
        if len(points) < 468 or any(not (0.02 <= points[i].x <= 0.98 and 0.02 <= points[i].y <= 0.98)
                                   for i in (1, 33, 263, 61, 291, 152)):
            raise CaptureError("FACE_FEATURES_NOT_VISIBLE")
        yaw, pitch, roll = angles(result.facial_transformation_matrixes[0])
        if not self.calibrate_neutral:
            # Login/approval accepts any usable view in the saved pose gallery;
            # there is no frontal calibration or head-turn request.
            return PoseObservation(yaw, pitch, roll, pose_bin(yaw, pitch, roll, limits=VERIFICATION_POSE_LIMITS))
        # Geometry is only a candidate until identity and PAD also pass.
        # Keep calibration transactional so a rejected third frame cannot lock
        # the baseline used by the remaining enrollment.
        self.pending_neutral = deepcopy(self.neutral)
        return self.pending_neutral.observe(yaw, pitch, roll, timestamp)

    def accept(self):
        if self.pending_neutral is not None:
            self.neutral = self.pending_neutral
            self.pending_neutral = None

    def interrupt(self):
        self.pending_neutral = None
        self.neutral.interrupt()

    def close(self):
        self.task.close()
