"""Combined service workflow with deterministic test-only perception fixtures.

No camera, real participant, detector qualification or native grant is fabricated.
This proves route/session/coverage/staging integration, not biometric accuracy.
"""
import base64
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.live_contract import Control, Outcome, POSES
from app.main import create_app
from app.pose import PoseObservation, NeutralPose, FaceLandmarker
from app.storage import EnrollmentStore
from app.imaging import CaptureError
from test_identity import TOKEN
from test_live_biometrics import begin

@pytest.fixture
def live_client(tmp_path, monkeypatch):
    clock = [100.]
    monkeypatch.setattr('app.sessions.time.monotonic', lambda: clock[0])
    class Engine:
        ready, error = True, ''
        vector = np.array([1,0,0],np.float32)
        def observe_with_landmarks(self, image):
            return self.vector,np.array([100,100,400,400]),np.array([[200,150],[300,150],[250,200],[210,250],[290,250]])
    class Pose:
        region = 'CENTER'
        closed = 0
        def observe(self, image, elapsed):return PoseObservation(0,0,0,self.region)
        def close(self):self.closed += 1
    class PAD:
        result = Outcome.PASS
        def verify(self, image, box):return Control(result=self.result,model='test-pad',reason='TEST_ONLY',score=0.99)
    pose, pad = Pose(), PAD()
    monkeypatch.setattr('app.main.load_live_models',lambda _: (lambda:pose,pad,{'identity':'test-identity','pose':'test-pose','pad':'test-pad'}))
    settings = Settings(TOKEN,tmp_path/'store',tmp_path/'models')
    api = create_app(settings,Engine())
    with TestClient(api,headers={'Authorization':f'Bearer {TOKEN}'}) as client:
        yield client,pose,pad,clock,settings,api


def run_observations(client, pose, clock, request, *, enrollment, acquisition_detours=False, rejected_candidate=None, height=480):
    response = client.post('/live/begin',json=request.model_dump())
    assert response.status_code == 200, response.text
    epoch = response.json()['service_epoch']
    origin, sequence, elapsed = clock[0], 0, 0
    def observe(region):
        nonlocal sequence, elapsed
        sequence += 1; elapsed += 600
        clock[0] = origin + elapsed/1000
        pose.region = region
        image = np.full((height,640,3),sequence,np.uint8)
        ok,jpeg = cv2.imencode('.jpg',image);assert ok
        response=client.post('/live/observe',json={'session_id':request.session_id,'nonce':request.nonce,'service_epoch':epoch,
            'sequence':sequence,'elapsed_ms':elapsed,'jpeg':base64.b64encode(jpeg).decode()})
        assert response.status_code == 200,response.text
        return response.json()
    regions = [p for p in POSES for _ in range(2)] if enrollment else ['RIGHT']*3
    if enrollment:
        regions=['CENTER','CENTER','UP_RIGHT','UP_RIGHT','DOWN','DOWN','LEFT','LEFT','UP_LEFT','UP_LEFT','RIGHT','RIGHT','UP','UP']
    for index,region in enumerate(regions):
        if enrollment and acquisition_detours:
            previous=result['accepted_samples'] if 'result' in locals() else 0
            result=observe(None)
            assert not result['complete'] and result['accepted_samples']==previous
        if rejected_candidate is not None and (enrollment or index==0):
            rejected_candidate(True)
            previous=result['accepted_samples'] if 'result' in locals() else 0
            result=observe(region)
            assert not result['complete'] and result['accepted_samples']==previous
            rejected_candidate(False)
        result=observe(region)
        if not enrollment:
            assert result['prompt']=='VERIFYING_FACE'
    return result,{'session_id':request.session_id,'nonce':request.nonce,'service_epoch':epoch}


def test_wrong_head_turns_recover_in_same_live_session(live_client):
    client,pose,pad,clock,settings,api=live_client
    request=begin()
    result,binding=run_observations(client,pose,clock,request,enrollment=True,acquisition_detours=True)
    assert result['complete'] and result['accepted_samples']==14
    assert api.state.live.active['request'].session_id==request.session_id
    assert pose.closed==0
    assert EnrollmentStore(settings.data_dir).generation('T1')=='none'
    assert client.post('/live/cancel',json=binding).status_code==200
    assert pose.closed==1


def test_enrollment_activation_restart_login_and_fresh_approval(live_client):
    client,pose,pad,clock,settings,api=live_client
    enrollment=begin()
    result,binding=run_observations(client,pose,clock,enrollment,enrollment=True)
    assert result['complete'] and result['accepted_samples']==14
    assert all(result['coverage'][p]==2 for p in POSES)
    assert set(result['controls']) == {'identity','quality','capture_integrity','pose','pad'}
    # A finished scan only stages; activation is a separate native-owned request.
    store=EnrollmentStore(settings.data_dir)
    assert store.generation('T1')=='none'
    commit={'technician_id':'T1','generation':enrollment.session_id,'previous_generation':'none'}
    assert client.post('/generation/activate',json=commit).status_code==200
    assert client.post('/generation/activate',json=commit).status_code==200
    assert client.post('/live/cancel',json=binding).status_code==200
    assert EnrollmentStore(settings.data_dir).generation('T1')==enrollment.session_id
    for purpose in ['LOGIN','APPROVAL']:
        request=begin(purpose).model_copy(update={'generation':enrollment.session_id})
        assert request.session_id != enrollment.session_id and request.nonce != enrollment.nonce
        result,binding=run_observations(client,pose,clock,request,enrollment=False)
        assert result['complete'] and result['accepted_samples']==3
        assert result['purpose']==purpose
        assert 'verification' not in result and 'technician' not in result
        assert client.post('/live/cancel',json=binding).status_code==200
    assert pose.closed==3


@pytest.mark.parametrize('kind',['pad','identity'])
def test_enrollment_rejected_candidates_do_not_fill_coverage_and_good_samples_resume(live_client,kind):
    client,pose,pad,clock,settings,api=live_client
    def candidate(reject):
        if kind=='pad':
            pad.result=Outcome.FAIL if reject else Outcome.PASS
        else:
            # First establish the enrollment's identity anchor, then introduce
            # a different face that must not contribute any representative.
            window=api.state.live.active['window']
            window.first=np.array([1.,0.,0.])
            api.state.live.engine.vector=np.array([0.,1.,0.]) if reject else np.array([1.,0.,0.])
    result,binding=run_observations(client,pose,clock,begin(),enrollment=True,rejected_candidate=candidate)
    assert result['complete'] and result['accepted_samples']==14 and pose.closed==0
    window=api.state.live.active['window']
    assert all(np.array_equal(v,[1.,0.,0.]) for v in window.templates)
    assert client.post('/live/cancel',json=binding).status_code==200


@pytest.mark.parametrize('kind,reason',[('pad','PRESENTATION_ATTACK_REJECTED'),('identity','CLAIMED_IDENTITY_MISMATCH')])
def test_authentication_negative_verdicts_remain_terminal(live_client,kind,reason):
    client,pose,pad,clock,settings,api=live_client
    enrollment=begin()
    result,binding=run_observations(client,pose,clock,enrollment,enrollment=True)
    assert client.post('/generation/activate',json={'technician_id':'T1','generation':enrollment.session_id,'previous_generation':'none'}).status_code==200
    assert client.post('/live/cancel',json=binding).status_code==200
    if kind=='pad':pad.result=Outcome.FAIL
    else:api.state.live.engine.vector=np.array([0.,1.,0.])
    login=begin('LOGIN').model_copy(update={'generation':enrollment.session_id})
    with pytest.raises(AssertionError, match=reason):
        run_observations(client,pose,clock,login,enrollment=False)
    assert api.state.live.active is None


@pytest.mark.parametrize('source,reason', [('engine','MULTIPLE_FACES_DETECTED'),
    ('engine','INVALID_FACE_BOUNDS'), ('pose','MULTIPLE_FACES_DETECTED'),
    ('pose','INVALID_POSE_MATRIX'), ('pose','NONFINITE_POSE'),
    ('pad','PAD_INVALID_BOUNDS'), ('pad','PAD_EMPTY_CROP')])
def test_enrollment_geometric_acquisition_errors_pause_without_progress(live_client,monkeypatch,source,reason):
    client,pose,pad,clock,settings,api=live_client
    target,name={'engine':(api.state.live.engine,'observe_with_landmarks'),
                 'pose':(pose,'observe'),'pad':(pad,'verify')}[source]
    original=getattr(target,name)
    reject=[False]
    def observe(*args):
        if reject[0]:raise CaptureError(reason)
        return original(*args)
    monkeypatch.setattr(target,name,observe)
    result,binding=run_observations(client,pose,clock,begin(),enrollment=True,
        rejected_candidate=lambda failed:reject.__setitem__(0,failed))
    assert result['complete'] and result['accepted_samples']==14 and pose.closed==0
    assert client.post('/live/cancel',json=binding).status_code==200


@pytest.mark.parametrize('purpose',['LOGIN','APPROVAL'])
@pytest.mark.parametrize('source,reason', [('engine','MULTIPLE_FACES_DETECTED'),
    ('pose','INVALID_POSE_MATRIX'), ('pad','PAD_INVALID_BOUNDS')])
def test_authentication_acquisition_ambiguity_pauses_and_valid_frames_resume(live_client,monkeypatch,purpose,source,reason):
    client,pose,pad,clock,settings,api=live_client
    enrollment=begin()
    _,binding=run_observations(client,pose,clock,enrollment,enrollment=True)
    assert client.post('/generation/activate',json={'technician_id':'T1','generation':enrollment.session_id,'previous_generation':'none'}).status_code==200
    assert client.post('/live/cancel',json=binding).status_code==200
    target,name={'engine':(api.state.live.engine,'observe_with_landmarks'),
                 'pose':(pose,'observe'),'pad':(pad,'verify')}[source]
    original=getattr(target,name)
    rejected=[False]
    def observe(*args):
        if rejected[0]:raise CaptureError(reason)
        return original(*args)
    monkeypatch.setattr(target,name,observe)
    request=begin(purpose).model_copy(update={'generation':enrollment.session_id})
    result,binding=run_observations(client,pose,clock,request,enrollment=False,
        rejected_candidate=lambda failed:rejected.__setitem__(0,failed))
    assert result['complete'] and result['accepted_samples']==3
    assert pose.closed==1 # Only prior enrollment was closed, not this auth session.
    assert client.post('/live/cancel',json=binding).status_code==200


def test_unknown_perception_failure_is_not_reclassified_as_recoverable(live_client,monkeypatch):
    client,pose,pad,clock,settings,api=live_client
    def failed(*args):raise CaptureError('UNEXPECTED_MODEL_CONTRACT')
    monkeypatch.setattr(api.state.live.engine,'observe_with_landmarks',failed)
    with pytest.raises(AssertionError,match='UNEXPECTED_MODEL_CONTRACT'):
        run_observations(client,pose,clock,begin(),enrollment=True)
    assert api.state.live.active is None


def test_invalid_bound_image_encoding_still_terminates_capture(live_client):
    client,pose,pad,clock,settings,api=live_client
    request=begin()
    epoch=client.post('/live/begin',json=request.model_dump()).json()['service_epoch']
    response=client.post('/live/observe',json={'session_id':request.session_id,'nonce':request.nonce,
        'service_epoch':epoch,'sequence':1,'elapsed_ms':1,'jpeg':'not-an-image'})
    assert response.status_code==422 and response.json()['detail']=='INVALID_IMAGE_ENCODING'
    assert api.state.live.active is None


def test_rejection_log_contains_only_bounded_error_code(live_client,monkeypatch,caplog):
    client,pose,pad,clock,settings,api=live_client
    def failed(*args):raise CaptureError('private-value: should never enter logs')
    monkeypatch.setattr(api.state.live.engine,'observe_with_landmarks',failed)
    with pytest.raises(AssertionError):
        run_observations(client,pose,clock,begin(),enrollment=True)
    records=[r.message for r in caplog.records if r.name=='alice.biometrics']
    assert records==['Live biometric operation rejected: LIVE_OPERATION_REJECTED']


def test_actual_clipped_face_box_pauses_before_pad_inference(live_client,monkeypatch):
    from app.imaging import check_face_quality
    from app.pad import preprocess
    client,pose,pad,clock,settings,api=live_client
    bbox=np.array([-4.,100.,240.,430.])
    def detected(image):
        check_face_quality(image,bbox,.99) # Existing quality crop permits clipping.
        return np.array([1.,0.,0.]),bbox,np.zeros((5,2))
    def presentation(image,box):
        preprocess(image,box) # Real pinned preprocessing rejects the same box.
        raise AssertionError('Clipped bounds must never reach PAD inference')
    monkeypatch.setattr(api.state.live.engine,'observe_with_landmarks',detected)
    monkeypatch.setattr(pad,'verify',presentation)
    request=begin()
    epoch=client.post('/live/begin',json=request.model_dump()).json()['service_epoch']
    clock[0]+=.6
    image=np.random.default_rng(42).integers(30,225,(480,640,3),dtype=np.uint8)
    ok,jpeg=cv2.imencode('.jpg',image);assert ok
    response=client.post('/live/observe',json={'session_id':request.session_id,'nonce':request.nonce,
        'service_epoch':epoch,'sequence':1,'elapsed_ms':600,'jpeg':base64.b64encode(jpeg).decode()})
    assert response.status_code==200
    result=response.json()
    assert not result['complete'] and result['accepted_samples']==0 and result['coverage']=={}
    assert result['controls']['pad']['reason']=='PAD_INVALID_BOUNDS'
    assert pose.closed==0 and api.state.live.active is not None


@pytest.mark.parametrize('height',[360,480])
def test_supported_native_aspect_ratio_completes_enrollment(live_client,height):
    client,pose,pad,clock,settings,api=live_client
    result,_=run_observations(client,pose,clock,begin(),enrollment=True,height=height)
    assert result['complete'] and result['accepted_samples']==14
    assert api.state.live.active['dimensions']==(height,640)


@pytest.mark.parametrize('first,second,reason', [((360,640),(480,640),'LIVE_FRAME_DIMENSIONS_CHANGED'),
    ((480,640),(360,640),'LIVE_FRAME_DIMENSIONS_CHANGED'),
    ((400,640),None,'LIVE_FRAME_DIMENSIONS'), ((360,641),None,'LIVE_FRAME_DIMENSIONS')])
def test_live_dimensions_are_exact_and_fixed_for_session(live_client,monkeypatch,first,second,reason):
    client,pose,pad,clock,settings,api=live_client
    request=begin()
    epoch=client.post('/live/begin',json=request.model_dump()).json()['service_epoch']
    if second:
        def blurred(image):raise CaptureError('LOW_QUALITY_BLUR')
        monkeypatch.setattr(api.state.live.engine,'observe_with_landmarks',blurred)
    origin=clock[0]
    dimensions=[first,second] if second else [first]
    for sequence,(height,width) in enumerate(dimensions,1):
        clock[0]=origin+sequence*.6
        ok,jpeg=cv2.imencode('.jpg',np.full((height,width,3),sequence,np.uint8));assert ok
        response=client.post('/live/observe',json={'session_id':request.session_id,'nonce':request.nonce,
            'service_epoch':epoch,'sequence':sequence,'elapsed_ms':sequence*600,'jpeg':base64.b64encode(jpeg).decode()})
        if sequence<len(dimensions):
            assert response.status_code==200 and response.json()['accepted_samples']==0
    assert response.status_code==422 and response.json()['detail']==reason
    assert api.state.live.active is None


def test_failed_third_calibration_frame_cannot_commit_baseline(live_client,monkeypatch):
    from copy import deepcopy
    from types import MethodType
    client,pose,pad,clock,settings,api=live_client
    pose.neutral=NeutralPose()
    pose.pending_neutral=None
    def observe_pose(image,elapsed):
        pose.pending_neutral=deepcopy(pose.neutral)
        return pose.pending_neutral.observe(5,-12,3,elapsed)
    monkeypatch.setattr(pose,'observe',observe_pose)
    monkeypatch.setattr(pose,'accept',MethodType(FaceLandmarker.accept,pose),raising=False)
    monkeypatch.setattr(pose,'interrupt',MethodType(FaceLandmarker.interrupt,pose),raising=False)
    request=begin()
    epoch=client.post('/live/begin',json=request.model_dump()).json()['service_epoch']
    origin=clock[0]
    for sequence in range(1,7):
        elapsed=sequence*300
        clock[0]=origin+elapsed/1000
        pad.result=Outcome.FAIL if sequence==3 else Outcome.PASS
        ok,jpeg=cv2.imencode('.jpg',np.full((480,640,3),sequence,np.uint8));assert ok
        result=client.post('/live/observe',json={'session_id':request.session_id,'nonce':request.nonce,
            'service_epoch':epoch,'sequence':sequence,'elapsed_ms':elapsed,'jpeg':base64.b64encode(jpeg).decode()})
        assert result.status_code==200 and not result.json()['complete']
        if sequence<6:
            assert pose.neutral.center is None and result.json()['accepted_samples']==0
        else:
            assert pose.neutral.center.tolist()==[5,-12,3] and result.json()['accepted_samples']==1
    assert pose.closed==0


def test_standard_readiness_needs_no_forged_detector_and_rejects_old_policy(live_client):
    client,pose,pad,clock,settings,api=live_client
    ready=client.get('/live/readiness').json()
    assert ready['status']=='READY' and ready['policy']=='alice.live-face.v3'
    assert 'forged_media' not in ready and 'forged_media' not in ready['models']
    request=begin().model_dump()
    request['policy']='alice.full-protected.v1'
    assert client.post('/live/begin',json=request).status_code==422
    assert api.state.live.active is None


@pytest.mark.parametrize('policy',['alice.full-protected.v1','alice.live-face.v1'])
def test_prior_policy_enrollment_is_preserved_but_requires_reenrollment(live_client,policy):
    client,pose,pad,clock,settings,api=live_client
    request=begin()
    store=EnrollmentStore(settings.data_dir)
    store.stage('T1',request.session_id,'none',[np.array([1.,0.,0.])]*14,
                [p for p in POSES for _ in range(2)],settings.model_name,policy)
    store.activate('T1',request.session_id,'none')
    login=begin('LOGIN').model_copy(update={'generation':request.session_id})
    response=client.post('/live/begin',json=login.model_dump())
    assert response.status_code==422 and response.json()['detail']=='ENROLLMENT_POLICY_MISMATCH'
    assert store.generation('T1')==request.session_id


@pytest.mark.parametrize('camera_biased_angle',[False,True])
def test_saved_v2_gallery_supports_passive_v3_login_and_approval_without_reenrollment(live_client,monkeypatch,camera_biased_angle):
    client,pose,pad,clock,settings,api=live_client
    generation=begin().session_id
    store=EnrollmentStore(settings.data_dir)
    store.stage('T1',generation,'none',[np.array([1.,0.,0.])]*14,
                [p for p in POSES for _ in range(2)],settings.model_name,'alice.live-face.v2')
    store.activate('T1',generation,'none')
    def set_raw_pose(yaw,pitch,roll):
        from types import SimpleNamespace, MethodType
        # Exercise the actual matrix/visibility/pose adapter, with deterministic
        # perception output only. No real participant or accuracy claim.
        y,p,r=np.radians([-yaw,-pitch,roll])
        rx=np.array([[1,0,0],[0,np.cos(p),-np.sin(p)],[0,np.sin(p),np.cos(p)]])
        ry=np.array([[np.cos(y),0,np.sin(y)],[0,1,0],[-np.sin(y),0,np.cos(y)]])
        rz=np.array([[np.cos(r),-np.sin(r),0],[np.sin(r),np.cos(r),0],[0,0,1]])
        matrix=np.eye(4);matrix[:3,:3]=rz@ry@rx
        perception=SimpleNamespace(face_landmarks=[[SimpleNamespace(x=.5,y=.5)]*468],facial_transformation_matrixes=[matrix])
        pose.task=SimpleNamespace(detect_for_video=lambda *_:perception)
        pose.mp=SimpleNamespace(Image=lambda **kwargs:kwargs,ImageFormat=SimpleNamespace(SRGB=0))
        pose.neutral=NeutralPose()
        pose.pending_neutral=None
        pose.last_timestamp=-1
        monkeypatch.setattr(pose,'observe',MethodType(FaceLandmarker.observe,pose))
    if camera_biased_angle:
        set_raw_pose(23,-38,28)
    def stored_row():
        with EnrollmentStore(settings.data_dir).connect() as db:
            return db.execute('SELECT templates,policy FROM face_generations WHERE technician_id=? AND generation=?',('T1',generation)).fetchone()
    before=stored_row()
    for purpose in ['LOGIN','APPROVAL']:
        # The shared fixture object stands in for a fresh task per session.
        pose.last_timestamp=-1
        request=begin(purpose).model_copy(update={'generation':generation})
        result,binding=run_observations(client,pose,clock,request,enrollment=False)
        assert result['complete'] and result['accepted_samples']==3
        assert result['coverage']=={} and result['prompt']=='VERIFYING_FACE'
        assert not pose.calibrate_neutral
        assert client.post('/live/cancel',json=binding).status_code==200
    if camera_biased_angle:
        set_raw_pose(0,66,0)
        request=begin('LOGIN').model_copy(update={'generation':generation})
        result,binding=run_observations(client,pose,clock,request,enrollment=False)
        assert not result['complete'] and result['accepted_samples']==0
        assert result['controls']['pose']['reason']=='FACE_POSE_INCONCLUSIVE'
        assert client.post('/live/cancel',json=binding).status_code==200
        for bad_check,reason in [('identity','CLAIMED_IDENTITY_MISMATCH'),('pad','PRESENTATION_ATTACK_REJECTED')]:
            set_raw_pose(23,-38,28)
            api.state.live.engine.vector=np.array([0.,1.,0.]) if bad_check=='identity' else np.array([1.,0.,0.])
            pad.result=Outcome.FAIL if bad_check=='pad' else Outcome.PASS
            request=begin('LOGIN').model_copy(update={'generation':generation})
            with pytest.raises(AssertionError,match=reason):
                run_observations(client,pose,clock,request,enrollment=False)
            assert api.state.live.active is None
    assert stored_row()==before and before[1]=='alice.live-face.v2'
    assert EnrollmentStore(settings.data_dir).generation('T1')==generation


def test_recoverable_pause_log_is_one_aggregate_of_fixed_codes_without_private_context(live_client,monkeypatch,caplog):
    client,pose,pad,clock,settings,api=live_client
    def ambiguous(*args):raise CaptureError('MULTIPLE_FACES_DETECTED')
    monkeypatch.setattr(pose,'observe',ambiguous)
    request=begin()
    result,binding=run_observations(client,pose,clock,request,enrollment=True)
    assert not result['complete'] and result['accepted_samples']==0
    assert not [r for r in caplog.records if r.name=='alice.biometrics']
    assert client.post('/live/cancel',json=binding).status_code==200
    messages=[r.message for r in caplog.records if r.name=='alice.biometrics']
    assert messages==['Live biometric pause counts: MULTIPLE_FACES_DETECTED=14']
    assert all(value not in messages[0] for value in [request.session_id,request.nonce,request.technician_id,TOKEN])


@pytest.mark.parametrize('purpose',['LOGIN','APPROVAL'])
def test_auth_acquisition_pause_discards_partial_window_without_closing_session(live_client,monkeypatch,purpose):
    client,pose,pad,clock,settings,api=live_client
    enrollment=begin()
    _,binding=run_observations(client,pose,clock,enrollment,enrollment=True)
    assert client.post('/generation/activate',json={'technician_id':'T1','generation':enrollment.session_id,'previous_generation':'none'}).status_code==200
    assert client.post('/live/cancel',json=binding).status_code==200
    request=begin(purpose).model_copy(update={'generation':enrollment.session_id})
    epoch=client.post('/live/begin',json=request.model_dump()).json()['service_epoch']
    original=pose.observe
    origin=clock[0]
    for sequence in range(1,7):
        clock[0]=origin+sequence*.3
        def observed(image,elapsed):
            if sequence==3:raise CaptureError('MULTIPLE_FACES_DETECTED')
            return original(image,elapsed)
        monkeypatch.setattr(pose,'observe',observed)
        ok,jpeg=cv2.imencode('.jpg',np.full((480,640,3),sequence,np.uint8));assert ok
        response=client.post('/live/observe',json={'session_id':request.session_id,'nonce':request.nonce,
            'service_epoch':epoch,'sequence':sequence,'elapsed_ms':sequence*300,'jpeg':base64.b64encode(jpeg).decode()})
        assert response.status_code==200,response.text
        result=response.json()
        assert result['complete']==(sequence==6)
        assert result['accepted_samples']==([1,2,0,1,2,3][sequence-1])
        if sequence==3:
            assert all(control['result']=='INCONCLUSIVE' for control in result['controls'].values())
            assert api.state.live.active is not None and pose.closed==1


def test_old_cancel_and_busy_begin_do_not_kill_new_session(live_client):
    client,pose,pad,clock,settings,api=live_client
    old=begin();new=begin()
    epoch=client.post('/live/begin',json=old.model_dump()).json()['service_epoch']
    cancel={'session_id':old.session_id,'nonce':old.nonce,'service_epoch':epoch}
    assert client.post('/live/cancel',json=cancel).status_code==200
    assert client.post('/live/begin',json=new.model_dump()).status_code==200
    assert client.post('/live/cancel',json=cancel).status_code==422
    assert api.state.live.active['request'].session_id==new.session_id
    assert client.post('/live/begin',json=begin().model_dump()).status_code==422
    assert api.state.live.active['request'].session_id==new.session_id


def test_inference_expiry_cannot_stage_completed_enrollment(live_client, monkeypatch):
    client,pose,pad,clock,settings,api=live_client
    original = pad.verify

    def slow_final_window(image, bbox):
        result = original(image, bbox)
        if api.state.live.active['window'].accepted == 13:
            clock[0] += 91
        return result

    monkeypatch.setattr(pad, 'verify', slow_final_window)
    # The normal workflow reaches completion only in the final model call.
    # Expiry during that call must fail before writing a staged generation.
    with pytest.raises(AssertionError, match='INFERENCE_SESSION_EXPIRED'):
        run_observations(client,pose,clock,begin(),enrollment=True)
    assert api.state.live.active is None
    assert pose.closed == 1
    with EnrollmentStore(settings.data_dir).connect() as db:
        assert db.execute('SELECT COUNT(*) FROM face_generations').fetchone()[0] == 0


def test_pose_close_error_still_releases_session(live_client, monkeypatch):
    client,pose,pad,clock,settings,api=live_client
    request=begin()
    client.post('/live/begin',json=request.model_dump())
    def broken_close():
        raise RuntimeError('native pose shutdown error')
    monkeypatch.setattr(pose,'close',broken_close)
    with pytest.raises(RuntimeError,match='native pose shutdown error'):
        api.state.live.close()
    assert api.state.live.active is None
