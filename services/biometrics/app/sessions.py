"""Bounded inference windows owned by the native caller; raw frames are not stored."""
import hashlib
import logging
import time
import uuid
from collections import Counter
import numpy as np
from .engine import similarity
from .imaging import CaptureError, decode_frame
from .live_contract import Begin, Control, Outcome, POSES, all_pass, POLICY

logger = logging.getLogger('alice.biometrics')
ACQUISITION_ERRORS = frozenset({
    'LOW_QUALITY_FACE_TOO_SMALL', 'LOW_QUALITY_LIGHTING', 'LOW_QUALITY_BLUR',
    'NO_FACE_DETECTED', 'FACE_FEATURES_NOT_VISIBLE', 'FACE_POSE_INCONCLUSIVE',
    'MULTIPLE_FACES_DETECTED', 'INVALID_FACE_BOUNDS', 'INVALID_POSE_MATRIX', 'NONFINITE_POSE',
})
PAD_GEOMETRY_ERRORS = frozenset({'PAD_INVALID_BOUNDS', 'PAD_EMPTY_CROP'})
PAUSE_REASONS = ACQUISITION_ERRORS | PAD_GEOMETRY_ERRORS | {'CALIBRATING_CENTER', 'ENROLLMENT_SAMPLE_NOT_ACCEPTED'}

class EvidenceWindow:
    def __init__(self, request: Begin, references: list[np.ndarray], threshold: float):
        if request.purpose != 'ENROLLMENT' and len(references) < 3:
            raise CaptureError('INSUFFICIENT_ENROLLMENT_REFERENCES')
        self.request, self.references, self.threshold = request, references, threshold
        self.coverage = Counter()
        self.templates = []
        self.poses = []
        self.last_pose_sample = {}
        self.current_region = None
        self.accepted = 0
        self.first_accepted_ms = None
        self.last_accepted_ms = None
        self.last_sequence = 0
        self.last_elapsed = -1
        self.first = None
        self.min_similarity = 1.0
        self.min_pad = 1.0
        self.seen = set()

    def interrupt(self):
        self.current_region = None
        if self.request.purpose != 'ENROLLMENT':
            self.accepted = 0
            self.first_accepted_ms = self.last_accepted_ms = None

    def accept(self, vector, region, pad, sequence, elapsed_ms, digest, *, pose_ready=True):
        if sequence <= self.last_sequence or elapsed_ms <= self.last_elapsed or sequence > 360:
            raise CaptureError("STALE_OR_UNBOUNDED_OBSERVATION")
        self.last_sequence, self.last_elapsed = sequence, elapsed_ms
        if digest in self.seen:
            raise CaptureError("REPEATED_FRAME")
        self.seen.add(digest)
        if len(self.seen) > 360:
            raise CaptureError("SAMPLE_LIMIT_EXCEEDED")
        if pad.result != Outcome.PASS:
            raise CaptureError("PRESENTATION_ATTACK_REJECTED")
        first = self.first if self.first is not None else vector
        # A mismatch rejects this sample. Authentication treats it as terminal;
        # enrollment may continue selecting other mutually consistent samples.
        if similarity(vector, first) < max(0.5, self.threshold):
            raise CaptureError("MIXED_SEQUENCE_IDENTITY")
        if self.references:
            scores = sorted((similarity(vector, ref) for ref in self.references), reverse=True)
            if len(scores) < 3:
                raise CaptureError("INSUFFICIENT_ENROLLMENT_REFERENCES")
            # Two of the three nearest representatives must support the match.
            # A single best score cannot authorize a different identity.
            score = float(np.median(scores[:3]))
            self.min_similarity = min(self.min_similarity, score)
            if score < self.threshold:
                raise CaptureError("CLAIMED_IDENTITY_MISMATCH")
        elif any(similarity(vector, ref) < max(0.5, self.threshold) for ref in self.templates):
            raise CaptureError("MIXED_ENROLLMENT_IDENTITY")
        # Only a usable accepted sample may establish the identity anchor.
        # Every candidate still undergoes the claimed identity/PAD checks.
        self.min_pad = min(self.min_pad, pad.score if pad.score is not None else -1)
        if not pose_ready or region is None:
            self.interrupt()
            return
        if self.request.purpose == 'ENROLLMENT' and region in ('DOWN_LEFT', 'DOWN_RIGHT'):
            # The lower arc of a continuous circle still supplies actual
            # downward pitch, without a narrow straight-down stopping target.
            region = 'DOWN'
        self.current_region = region
        if self.request.purpose != "ENROLLMENT":
            if self.last_accepted_ms is not None and elapsed_ms - self.last_accepted_ms > 1500:
                self.interrupt()
            self.first = first
            if self.first_accepted_ms is None:
                self.first_accepted_ms = elapsed_ms
            self.last_accepted_ms = elapsed_ms
            self.accepted += 1
            return
        if region in POSES and self.coverage[region] < 2 and elapsed_ms - self.last_pose_sample.get(region, -1000) >= 500:
            self.first = first
            self.accepted += 1
            self.coverage[region] += 1
            self.last_pose_sample[region] = elapsed_ms
            self.templates.append(vector)
            self.poses.append(region)

    @property
    def enough(self):
        if self.request.purpose == "ENROLLMENT":
            return all(self.coverage[p] >= 2 for p in POSES)
        return self.accepted >= 3 and self.first_accepted_ms is not None and self.last_accepted_ms - self.first_accepted_ms >= 500

    @property
    def prompt(self):
        if self.request.purpose == 'ENROLLMENT':
            if self.coverage['CENTER'] < 2:
                return 'CENTER'
            remaining = [p for p in POSES if self.coverage[p] < 2]
            if len(remaining) == 1:
                target = remaining[0]
                return f'HOLD_{target}' if self.current_region == target else f'LOOK_{target}'
            return 'LOOK_AROUND'
        return 'VERIFYING_FACE'

class LiveInference:
    def __init__(self, config, engine, store, pose_factory, pad, models):
        self.config, self.engine, self.store = config, engine, store
        self.pose_factory, self.pad, self.models = pose_factory, pad, models
        self.policy = POLICY
        self.epoch = str(uuid.uuid4())
        self.active = None

    def readiness(self):
        ready = bool(self.engine.ready and self.pose_factory and self.pad)
        return {"schema_version": "2.0", "service_epoch": self.epoch,
                "policy": self.policy, "models": self.models,
                "identity": "PASS" if self.engine.ready else "UNAVAILABLE",
                "pose": "PASS" if self.pose_factory else "UNAVAILABLE",
                "pad": "PASS" if self.pad else "UNAVAILABLE",
                "status": "READY" if ready else "BLOCKED",
                "reason": "READY" if ready else "REQUIRED_MODELS_UNAVAILABLE"}

    def close(self):
        if self.active:
            active = self.active
            self.active = None
            if active['pauses']:
                # One aggregate entry per session: fixed reason codes/counts
                # only, never identifiers, images, embeddings or pose values.
                counts = ','.join(f'{reason}={count}' for reason, count in sorted(active['pauses'].items()))
                logger.warning('Live biometric pause counts: %s', counts)
            active["pose"].close()

    def expire(self):
        if self.active and time.monotonic() > self.active["deadline"]:
            self.close()

    def begin(self, request: Begin):
        self.expire()
        if request.policy != self.policy:
            raise CaptureError("BIOMETRIC_POLICY_MISMATCH")
        if self.active:
            raise CaptureError("CAMERA_SESSION_BUSY")
        if not self.engine.ready or not self.pose_factory or not self.pad:
            raise CaptureError("REQUIRED_MODELS_UNAVAILABLE")
        if self.store.generation(request.technician_id) != request.generation:
            raise CaptureError("ENROLLMENT_GENERATION_CHANGED")
        references = [] if request.purpose == "ENROLLMENT" else self.store.templates(request.technician_id, request.generation, self.config.model_name, self.policy)
        window = EvidenceWindow(request, references, self.config.threshold)
        pose = self.pose_factory()
        pose.calibrate_neutral = request.purpose == "ENROLLMENT"
        self.active = {"request": request, "window": window,
                       "last_sequence": 0, "last_elapsed": -1, "dimensions": None, "pauses": Counter(),
                       "pose": pose, "started": time.monotonic(),
                       "deadline": time.monotonic() + (90 if request.purpose == "ENROLLMENT" else 45)}
        return {"session_id": request.session_id, "service_epoch": self.epoch}

    def bound(self, request):
        self.expire()
        if not self.active or request.service_epoch != self.epoch or request.session_id != self.active["request"].session_id or request.nonce != self.active["request"].nonce:
            raise CaptureError("INVALID_OR_EXPIRED_INFERENCE_SESSION")
        return self.active

    def observe(self, request):
        active = self.bound(request)
        binding, window = active["request"], active["window"]
        if request.sequence <= active["last_sequence"] or request.elapsed_ms <= active["last_elapsed"]:
            raise CaptureError("STALE_OBSERVATION")
        active["last_sequence"], active["last_elapsed"] = request.sequence, request.elapsed_ms
        if self.store.generation(binding.technician_id) != binding.generation:
            self.close()
            raise CaptureError("ENROLLMENT_GENERATION_CHANGED")
        # Native monotonic timestamps and service arrival must agree within a
        # bounded queue/inference allowance. A timestamp alone is not provenance.
        if abs(request.elapsed_ms - (time.monotonic() - active["started"]) * 1000) > 3000:
            self.close()
            raise CaptureError("STALE_CAPTURE_WINDOW")
        image = decode_frame(request.jpeg)
        dimensions = image.shape[:2]
        # Native capture retains the supported camera aspect ratio without
        # artificial bars in PAD context. A session cannot switch its format.
        if dimensions not in ((480, 640), (360, 640)):
            raise CaptureError("LIVE_FRAME_DIMENSIONS")
        if active.get('dimensions') is None:
            active['dimensions'] = dimensions
        elif dimensions != active['dimensions']:
            raise CaptureError('LIVE_FRAME_DIMENSIONS_CHANGED')
        try:
            vector, bbox, _landmarks = self.engine.observe_with_landmarks(image)
            pose = active["pose"].observe(image, request.elapsed_ms)
        except CaptureError as error:
            # Ambiguous acquisition is no identity verdict. Multiple faces
            # produce no sample, and no face is silently selected. The current
            # operation pauses while its original session deadline keeps running.
            if str(error) not in ACQUISITION_ERRORS:
                raise
            return self.pause_observation(active, request, str(error))
        try:
            pad = self.pad.verify(image, bbox)
        except CaptureError as error:
            # Detection can return a box slightly beyond the camera boundary.
            # Do not clamp/change the pinned PAD crop or accept partial faces;
            # wait for a usable next frame. Actual PAD FAIL remains terminal
            # during authentication; invalid crop geometry is not a PAD result.
            if str(error) not in PAD_GEOMETRY_ERRORS:
                raise
            return self.pause_observation(active, request, str(error))
        pose_ready = getattr(pose, 'calibrated', True)
        try:
            window.accept(vector, pose.region, pad, request.sequence, request.elapsed_ms,
                          hashlib.sha256(image.tobytes()).digest(), pose_ready=pose_ready)
        except CaptureError as error:
            # Enrollment selects usable, mutually consistent representatives.
            # Rejected observations never enter its templates or fill the ring.
            # Authentication still rejects a mismatch/PAD failure immediately.
            candidate_errors = {'PRESENTATION_ATTACK_REJECTED', 'MIXED_SEQUENCE_IDENTITY', 'MIXED_ENROLLMENT_IDENTITY'}
            if binding.purpose != 'ENROLLMENT' or str(error) not in candidate_errors:
                raise
            window.interrupt()
            if hasattr(active['pose'], 'interrupt'):
                active['pose'].interrupt()
            controls = {name: Control(result=Outcome.INCONCLUSIVE, model=self.models.get(name, 'native-v1'), reason='ENROLLMENT_SAMPLE_NOT_ACCEPTED')
                        for name in ('identity', 'quality', 'capture_integrity', 'pose', 'pad')}
            controls['pad'] = pad
            if str(error).startswith('MIXED_'):
                controls['identity'] = Control(result=Outcome.FAIL, model=self.models.get('identity', 'unknown'), reason='ENROLLMENT_IDENTITY_NOT_MATCHED')
            return self.report(active, request, controls)
        if hasattr(active['pose'], 'accept'):
            active['pose'].accept()
        controls = {name: Control(result=Outcome.PASS, model=self.models.get(name, "native-v1"), reason="OBSERVED")
                    for name in ("identity", "quality", "capture_integrity", "pose", "pad")}
        # A valid arrival can expire while synchronous inference is running.
        # Recheck before returning completion or staging an enrollment; the
        # background reaper cannot acquire the inference mutex during this work.
        if time.monotonic() >= active["deadline"]:
            self.close()
            raise CaptureError("INFERENCE_SESSION_EXPIRED")
        if not window.enough or pose.region is None:
            controls["pose"].result = Outcome.INCONCLUSIVE
        if pose.region is None:
            controls["pose"].reason = "FACE_POSE_INCONCLUSIVE"
        if not pose_ready:
            controls['pose'].result = Outcome.INCONCLUSIVE
            controls['pose'].reason = 'CALIBRATING_CENTER'
        complete = all_pass(controls)
        if complete and binding.purpose == "ENROLLMENT":
            self.store.stage(binding.technician_id, binding.session_id, binding.generation,
                             window.templates, window.poses, self.config.model_name, binding.policy)
        return self.report(active, request, controls)

    def pause_observation(self, active, request, reason):
        # An unusable observation cannot advance enrollment or verification.
        active['window'].interrupt()
        if hasattr(active['pose'], 'interrupt'):
            active['pose'].interrupt()
        controls = {name: Control(result=Outcome.INCONCLUSIVE, model=self.models.get(name, 'native-v1'), reason=reason)
                    for name in ('identity', 'quality', 'capture_integrity', 'pose', 'pad')}
        return self.report(active, request, controls)

    def report(self, active, request, controls):
        binding, window = active["request"], active["window"]
        for reason in {control.reason for control in controls.values() if control.result != Outcome.PASS} & PAUSE_REASONS:
            active['pauses'][reason] += 1
        return {"schema_version": "2.0", "session_id": binding.session_id, "nonce": binding.nonce,
                "purpose": binding.purpose, "generation": binding.generation,
                "boot_epoch": binding.boot_epoch, "helper_epoch": binding.helper_epoch,
                "service_epoch": self.epoch, "sequence": request.sequence, "policy": binding.policy,
                "models": self.models, "controls": {k: v.model_dump() for k, v in controls.items()},
                "accepted_samples": window.accepted, "coverage": dict(window.coverage),
                "prompt": window.prompt,
                "complete": all_pass(controls)}
