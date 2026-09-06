"""ArcFace rejects unusable captures before running expensive recognition."""
from types import SimpleNamespace

import numpy as np
import pytest

from app.engine import ArcFaceEngine
from app.imaging import CaptureError


def engine_with_detection(bboxes, landmarks):
    calls=[]

    def detect(image, **options):
        calls.append(('detect', options))
        return np.asarray(bboxes,dtype=np.float32).reshape(-1,5), landmarks

    def recognize(image, face):
        calls.append(('recognize', face.kps.copy()))
        face.embedding=np.array([3.,4.,0.],dtype=np.float32)

    engine=ArcFaceEngine.__new__(ArcFaceEngine)
    engine.ready=True
    engine.app=SimpleNamespace(det_model=SimpleNamespace(detect=detect),
                               models={'recognition':SimpleNamespace(get=recognize)})
    return engine,calls


def textured_image():
    return np.random.default_rng(42).integers(40,215,(160,160,3),dtype=np.uint8)


@pytest.mark.parametrize('case,reason', [
    ('absent','NO_FACE_DETECTED'),
    ('multiple','MULTIPLE_FACES_DETECTED'),
    ('small','LOW_QUALITY_FACE_TOO_SMALL'),
    ('dark','LOW_QUALITY_LIGHTING'),
    ('blur','LOW_QUALITY_BLUR'),
    ('missing_landmarks','FACE_FEATURES_NOT_VISIBLE'),
    ('invalid_landmarks','FACE_FEATURES_NOT_VISIBLE'),
])
def test_bad_face_never_runs_recognition(case,reason):
    image=textured_image()
    bboxes=[[20,20,140,140,0.99]]
    landmarks=np.zeros((1,5,2),dtype=np.float32)
    if case=='absent': bboxes=[]
    if case=='multiple': bboxes*=2
    if case=='small': bboxes=[[20,20,40,40,0.99]]
    if case=='dark': image[:]=0
    if case=='blur': image[:]=128
    if case=='missing_landmarks': landmarks=None
    if case=='invalid_landmarks': landmarks[:]=np.nan
    engine,calls=engine_with_detection(bboxes,landmarks)
    with pytest.raises(CaptureError,match=reason):
        engine.observe_with_landmarks(image)
    assert calls==[('detect',{'max_num':0,'metric':'default'})]


def test_single_good_face_uses_same_detector_landmarks_for_alignment():
    landmarks=np.array([[[50,50],[100,50],[75,75],[55,100],[95,100]]],dtype=np.float32)
    engine,calls=engine_with_detection([[20,20,140,140,0.99]],landmarks)
    vector,bbox,observed_landmarks=engine.observe_with_landmarks(textured_image())
    assert vector==pytest.approx([0.6,0.8,0.])
    assert bbox.tolist()==[20,20,140,140]
    assert np.array_equal(observed_landmarks,landmarks[0])
    assert len(calls)==2 and calls[1][0]=='recognize'
    assert np.array_equal(calls[1][1],landmarks[0])
