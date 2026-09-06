import math
import uuid
import numpy as np
import pytest
from pydantic import ValidationError
from app.live_contract import Begin, Control, Outcome, POSES, all_pass
from app.sessions import EvidenceWindow
from app.imaging import CaptureError, check_face_quality
from app.pose import angles, pose_bin, mirrored_display_angles, NeutralPose, VERIFICATION_POSE_LIMITS
from app.pad import preprocess, bona_fide_probability
from app.storage import EnrollmentStore


def begin(purpose='ENROLLMENT'):
    return Begin(schema_version='2.0', session_id=str(uuid.uuid4()), nonce=str(uuid.uuid4()),
                 boot_epoch=str(uuid.uuid4()), helper_epoch=str(uuid.uuid4()), policy='alice.live-face.v3',
                 purpose=purpose, technician_id='T1', generation='none')


def test_contract_rejects_renderer_declared_outcomes_and_frames():
    for extra in ({'result':'PASS'}, {'frames':['image']}, {'policy':'identity-only'}, {'purpose':'UNKNOWN'}):
        with pytest.raises(ValidationError): Begin.model_validate(begin().model_dump() | extra)


@pytest.mark.parametrize('purpose,challenge', [('ENROLLMENT',['CENTER','LEFT','CENTER','RIGHT','CENTER']),
    ('LOGIN',[]), ('APPROVAL',[]), ('LOGIN',['CENTER','LEFT','CENTER','LEFT','CENTER']),
    ('LOGIN',['LEFT','CENTER','RIGHT','CENTER','UP'])])
def test_v3_rejects_all_retired_challenge_fields(purpose,challenge):
    with pytest.raises(ValidationError):
        Begin.model_validate(begin(purpose).model_dump() | {'challenge':challenge})


@pytest.mark.parametrize('policy',['alice.live-face.v1','alice.live-face.v2'])
def test_v3_rejects_previous_request_policy(policy):
    with pytest.raises(ValidationError):
        Begin.model_validate(begin().model_dump() | {'policy':policy})


@pytest.mark.parametrize('control', ['identity','quality','capture_integrity','pose','pad'])
@pytest.mark.parametrize('outcome', [Outcome.FAIL,Outcome.INCONCLUSIVE,Outcome.UNAVAILABLE,Outcome.NOT_CONFIGURED])
def test_required_control_never_fails_open(control,outcome):
    values={k:Control(result=Outcome.PASS,model='test',reason='test') for k in ['identity','quality','capture_integrity','pose','pad']}
    assert all_pass(values)
    values[control].result=outcome
    assert not all_pass(values)
    del values[control]
    assert not all_pass(values)


@pytest.mark.parametrize('yaw,pitch,roll,expected', [(0,0,0,'CENTER'),(20,0,0,'LEFT'),(-20,0,0,'RIGHT'),
    (0,15,0,'UP'),(0,-15,0,'DOWN'),(20,15,0,'UP_LEFT'),(-20,15,0,'UP_RIGHT'),
    (20,-15,0,'DOWN_LEFT'),(-20,-15,0,'DOWN_RIGHT'),(50,0,0,None),(0,40,0,None),(0,0,30,None)])
def test_defined_pose_regions(yaw,pitch,roll,expected):
    assert pose_bin(yaw,pitch,roll)==expected


@pytest.mark.parametrize('yaw,pitch,roll', [(20,0,0),(-20,0,0),(0,15,0),(0,-15,0),(0,0,12),(20,15,-10)])
def test_matrix_convention_and_display_mirror(yaw,pitch,roll):
    y,p,r=map(math.radians,(-yaw,-pitch,roll))
    rx=np.array([[1,0,0],[0,math.cos(p),-math.sin(p)],[0,math.sin(p),math.cos(p)]])
    ry=np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
    rz=np.array([[math.cos(r),-math.sin(r),0],[math.sin(r),math.cos(r),0],[0,0,1]])
    matrix=np.eye(4);matrix[:3,:3]=rz@ry@rx
    assert angles(matrix)==pytest.approx((yaw,pitch,roll))
    assert mirrored_display_angles(yaw,pitch,roll)==(-yaw,pitch,-roll)
    assert angles(matrix)==pytest.approx((yaw,pitch,roll))


@pytest.mark.parametrize('normal,expected', [
    ([0,0,1],'CENTER'), ([0.3,0,1],'RIGHT'), ([-0.3,0,1],'LEFT'),
    ([0,0.25,1],'UP'), ([0,-0.25,1],'DOWN'),
])
def test_pose_labels_follow_mediapipe_metric_face_normal(normal, expected):
    # Physical direction in the upstream right-handed camera space, independent
    # of the Euler decomposition. +Y is up; native operator feedback requires
    # the opposite horizontal label from the original matrix-yaw mapping.
    forward=np.asarray(normal,dtype=float);forward/=np.linalg.norm(forward)
    right=np.cross([0,1,0],forward);right/=np.linalg.norm(right)
    up=np.cross(forward,right)
    matrix=np.eye(4);matrix[:3,:3]=np.column_stack([right,up,forward])
    assert pose_bin(*angles(matrix))==expected


def test_invalid_pose_and_reflection_rejected():
    for matrix in (np.ones((3,3)),np.full((4,4),np.nan),np.diag([-1,1,1,1])):
        with pytest.raises(CaptureError):angles(matrix)
    with pytest.raises(CaptureError):pose_bin(float('nan'),0,0)


def test_neutral_calibration_removes_camera_bias_and_stays_fixed_during_scan():
    neutral=NeutralPose()
    assert not neutral.observe(6,-17,4,100).calibrated
    assert not neutral.observe(7,-16,5,350).calibrated
    center=neutral.observe(6,-17,4,600)
    assert center.calibrated and center.region=='CENTER'
    origin=neutral.center.copy()
    assert neutral.observe(18,-17,4,850).region=='LEFT'
    assert neutral.observe(14,-17,4,1100).region=='LEFT' # boundary wobble retained
    assert neutral.observe(12,-17,4,1350).region=='CENTER'
    assert neutral.observe(-6,-17,4,1600).region=='RIGHT'
    assert neutral.observe(6,-7,4,1850).region=='UP'
    assert np.array_equal(neutral.center,origin)


def test_passive_pose_covers_slight_movement_from_an_accepted_camera_bias():
    neutral=NeutralPose()
    for elapsed in (100,350,600):
        neutral.observe(15,-28,18,elapsed)
    raw=(23,-38,28) # Only8yaw/10pitch/10roll from the accepted neutral.
    assert neutral.observe(*raw,900).region=='DOWN'
    assert pose_bin(*raw) is None # Applying relative limits to raw pose was wrong.
    assert pose_bin(*raw,limits=VERIFICATION_POSE_LIMITS)=='DOWN_LEFT'


@pytest.mark.parametrize('axis,limit',list(enumerate((65,65,45))))
@pytest.mark.parametrize('sign',[-1,1])
def test_passive_pose_raw_envelope_is_bounded_without_changing_enrollment_limits(axis,limit,sign):
    raw=[0.,0.,0.]
    raw[axis]=sign*limit
    assert pose_bin(*raw,limits=VERIFICATION_POSE_LIMITS) is not None
    assert pose_bin(*raw) is None
    raw[axis]=sign*(limit+.01)
    assert pose_bin(*raw,limits=VERIFICATION_POSE_LIMITS) is None
    raw[axis]=float('nan')
    with pytest.raises(CaptureError,match='NONFINITE_POSE'):
        pose_bin(*raw,limits=VERIFICATION_POSE_LIMITS)


def test_neutral_requires_stable_bounded_observations_and_pause_clears_partial_calibration():
    neutral=NeutralPose()
    assert not neutral.observe(40,0,0,100).calibrated
    assert not neutral.observe(0,0,0,350).calibrated
    assert not neutral.observe(8,0,0,600).calibrated
    assert not neutral.observe(8,0,0,850).calibrated
    neutral.interrupt()
    assert not neutral.observe(8,0,0,1100).calibrated
    assert not neutral.observe(8,0,0,1350).calibrated
    assert neutral.observe(8,0,0,1600).calibrated
    with pytest.raises(CaptureError,match='STALE'):
        neutral.observe(8,0,0,1600)


def test_duplicate_pose_does_not_inflate_coverage_and_mixed_identity_aborts():
    w=EvidenceWindow(begin(),[],0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    vector=np.array([1.,0.,0.])
    for i in range(1,20):w.accept(vector,'CENTER',pad,i,i*500,bytes([i]))
    assert w.coverage['CENTER']==2 and len(w.templates)==2 and w.accepted==2 and not w.enough
    with pytest.raises(CaptureError,match='MIXED'):w.accept(np.array([0.,1.,0.]),'LEFT',pad,20,10000,b'new')


def test_complete_coverage_requires_every_pose_twice():
    w=EvidenceWindow(begin(),[],0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    for i,region in enumerate([r for r in POSES for _ in range(2)],1):
        w.accept(np.array([1.,0.,0.]),region,pad,i,i*500,bytes([i]))
        assert w.enough==(i==14)


def test_enrollment_collects_any_order_without_challenge_timeout_and_never_counts_bad_candidates():
    w=EvidenceWindow(begin(),[],0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    vector=np.array([1.,0.,0.])
    regions=['CENTER','CENTER','UP_RIGHT','UP_RIGHT','DOWN','DOWN','LEFT','LEFT','UP_LEFT','UP_LEFT','RIGHT','RIGHT','UP','UP']
    for i,region in enumerate(regions,1):
        # Beyond the removed40s ordered-challenge limit, still inside90s session.
        w.accept(vector,region,pad,i,42000+i*600,bytes([i]))
        assert w.enough==(i==14)
    assert w.prompt=='LOOK_AROUND' and w.accepted==14


def test_enrollment_uncalibrated_or_off_axis_frames_cannot_anchor_empty_enrollment():
    w=EvidenceWindow(begin(),[],0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    w.accept(np.array([1.,0.,0.]),None,pad,1,100,b'initial',pose_ready=False)
    w.accept(np.array([1.,0.,0.]),None,pad,2,700,b'outside')
    assert w.first is None and w.accepted==0
    w.accept(np.array([0.,1.,0.]),'CENTER',pad,3,1300,b'usable')
    assert np.array_equal(w.first,[0.,1.,0.]) and w.accepted==1


def test_lower_circle_arc_counts_actual_downward_pose():
    w=EvidenceWindow(begin(),[],0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    for i,region in enumerate(['DOWN_LEFT','DOWN_RIGHT'],1):
        w.accept(np.array([1.,0.,0.]),region,pad,i,i*600,bytes([i]))
    assert w.coverage=={'DOWN':2} and w.poses==['DOWN','DOWN'] and not w.enough


def test_verification_cannot_average_away_wrong_frames():
    w=EvidenceWindow(begin('LOGIN'),[np.array([1.,0.,0.])]*14,0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    w.accept(np.array([1.,0.,0.]),'CENTER',pad,1,100,b'1')
    with pytest.raises(CaptureError):w.accept(np.array([0.,1.,0.]),'CENTER',pad,2,600,b'2')


@pytest.mark.parametrize('purpose',['LOGIN','APPROVAL'])
def test_passive_verification_requires_three_distinct_samples_over_half_second_without_center(purpose):
    vector=np.array([1.,0.,0.])
    w=EvidenceWindow(begin(purpose),[vector]*14,0.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    for i,elapsed in enumerate([100,350,600],1):
        w.accept(vector,'UP_RIGHT',pad,i,elapsed,bytes([i]))
        assert w.enough==(i==3)
    assert w.prompt=='VERIFYING_FACE' and w.coverage=={} and w.templates==[]


def test_passive_verification_cannot_use_three_near_simultaneous_or_repeated_images():
    vector=np.array([1.,0.,0.])
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    w=EvidenceWindow(begin('LOGIN'),[vector]*14,.45)
    for i,elapsed in enumerate([100,200,300],1):
        w.accept(vector,'LEFT',pad,i,elapsed,bytes([i]))
    assert w.accepted==3 and not w.enough
    with pytest.raises(CaptureError,match='REPEATED_FRAME'):
        w.accept(vector,'LEFT',pad,4,600,bytes([1]))


@pytest.mark.parametrize('interruption',['acquisition','pose','gap'])
def test_passive_verification_requires_a_fresh_window_after_interruption(interruption):
    vector=np.array([1.,0.,0.])
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=.99)
    w=EvidenceWindow(begin('LOGIN'),[vector]*14,.45)
    w.accept(vector,'RIGHT',pad,1,100,b'one')
    w.accept(vector,'RIGHT',pad,2,350,b'two')
    if interruption=='pose':
        w.accept(vector,None,pad,3,600,b'unusable')
    elif interruption=='acquisition':
        w.interrupt()
    if interruption!='gap':
        assert w.accepted==0 and not w.enough
    for sequence,elapsed in enumerate([2000,2250,2500],4):
        w.accept(vector,'RIGHT',pad,sequence,elapsed,bytes([sequence]))
        assert w.accepted==sequence-3 and w.enough==(sequence==6)
    assert np.array_equal(w.first,vector)
    with pytest.raises(CaptureError,match='REPEATED_FRAME'):
        w.accept(vector,'RIGHT',pad,7,2750,b'one')


def test_enrollment_interruption_preserves_accepted_coverage():
    vector=np.array([1.,0.,0.])
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=.99)
    w=EvidenceWindow(begin(),[],.45)
    w.accept(vector,'CENTER',pad,1,100,b'one')
    w.interrupt()
    assert w.accepted==1 and w.coverage=={'CENTER':1}
    assert np.array_equal(w.first,vector) and len(w.templates)==1


def test_unusable_initial_authentication_pose_cannot_anchor_unaccepted_identity():
    def vector(degrees):
        return np.array([math.cos(math.radians(degrees)),math.sin(math.radians(degrees)),0.])
    references=[vector(0)]*7+[vector(50)]*7
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=.99)
    w=EvidenceWindow(begin('LOGIN'),references,.45)
    w.accept(vector(65),None,pad,1,100,b'unusable')
    assert w.accepted==0 and w.first is None
    w.accept(vector(-25),'RIGHT',pad,2,350,b'usable')
    assert w.accepted==1 and np.array_equal(w.first,vector(-25))


@pytest.mark.parametrize('supporting,passed',[(2,True),(1,False)])
def test_gallery_requires_two_nearby_representatives_not_single_best_or_all_angle_median(supporting,passed):
    def vector(degrees):
        return np.array([math.cos(math.radians(degrees)),math.sin(math.radians(degrees)),0.])
    # Every enrollment representative remains pairwise consistent (cos50>.5).
    # A valid off-axis query is close to its two matching-pose representatives.
    references=[vector(0)]*supporting+[vector(50)]*(14-supporting)
    w=EvidenceWindow(begin('LOGIN'),references,.45)
    pad=Control(result=Outcome.PASS,model='test',reason='test',score=0.99)
    if passed:
        w.accept(vector(-25),'RIGHT',pad,1,100,b'one')
        assert w.min_similarity==pytest.approx(math.cos(math.radians(25)))
    else:
        with pytest.raises(CaptureError,match='CLAIMED_IDENTITY_MISMATCH'):
            w.accept(vector(-25),'RIGHT',pad,1,100,b'one')


@pytest.mark.parametrize('count',[0,1,2])
def test_passive_verification_cannot_fall_back_when_gallery_is_missing(count):
    with pytest.raises(CaptureError,match='INSUFFICIENT_ENROLLMENT_REFERENCES'):
        EvidenceWindow(begin('LOGIN'),[np.array([1.,0.,0.])]*count,.45)


@pytest.mark.parametrize('kind',['blur','dark','bright','small','bounds'])
def test_quality_rejections(kind):
    image=np.full((200,200,3),128,dtype=np.uint8);bbox=np.array([20,20,180,180])
    if kind=='dark':image[:]=0
    if kind=='bright':image[:]=255
    if kind=='small':bbox=np.array([20,20,40,40])
    if kind=='bounds':bbox=np.array([300,300,400,400])
    with pytest.raises(CaptureError):check_face_quality(image,bbox,0.9)


def test_pad_channels_shape_dtype_range_and_semantics():
    image=np.zeros((120,120,3),np.uint8);image[:]=[12,101,230]
    tensor=preprocess(image,[20,20,100,100])
    assert tensor.shape==(1,3,80,80) and tensor.dtype==np.float32
    assert tensor[0,:,40,40].tolist()==[12,101,230]
    assert tensor.max()==230 # BGR, no division by 255.
    assert bona_fide_probability(np.array([[0,10,0]]))>0.99
    assert bona_fide_probability(np.array([[10,0,0]]))<0.01
    assert bona_fide_probability(np.array([[0,0,10]]))<0.01


@pytest.mark.parametrize('bbox',[[0,0,80,80],[40,40,120,120],[1,1,119,119]])
def test_pad_edge_crops_are_bounded(bbox):
    assert preprocess(np.zeros((120,120,3),np.uint8),bbox).shape==(1,3,80,80)


@pytest.mark.parametrize('output',[np.array([[np.nan,0,0]]),np.array([[np.inf,0,0]]),np.zeros((3,)),np.zeros((1,2))])
def test_pad_invalid_outputs(output):
    with pytest.raises(CaptureError):bona_fide_probability(output)


def stage(store,generation,previous='legacy-v1'):
    poses=[r for r in POSES for _ in range(2)]
    store.stage('T1',generation,previous,[np.array([1.,0.,0.])]*14,poses,'buffalo_l','alice.live-face.v2')


def test_generation_stage_activation_restart_and_ciphertext_preservation(tmp_path):
    store=EnrollmentStore(tmp_path);store.put('T1',np.array([1.,0.,0.]),'buffalo_l',5)
    with store.connect() as db:original=db.execute('SELECT embedding FROM enrollments').fetchone()[0]
    assert store.generation('T1')=='legacy-v1'
    g=str(uuid.uuid4());stage(store,g)
    assert store.generation('T1')=='legacy-v1'
    restarted=EnrollmentStore(tmp_path)
    with pytest.raises(ValueError):restarted.templates('T1',g,'buffalo_l')
    restarted.activate('T1',g,'legacy-v1');restarted.activate('T1',g,'legacy-v1')
    assert len(restarted.templates('T1',g,'buffalo_l'))==14
    with restarted.connect() as db:
        assert db.execute('SELECT embedding FROM enrollments').fetchone()[0]==original
        assert not db.execute('SELECT templates FROM face_generations').fetchone()[0].startswith(b'{')
    with pytest.raises(ValueError):restarted.templates('T1',g,'different-model')


def test_concurrent_activation_cannot_overwrite_committed_generation(tmp_path):
    store=EnrollmentStore(tmp_path);store.put('T1',np.array([1.,0.,0.]),'buffalo_l',5)
    a,b=str(uuid.uuid4()),str(uuid.uuid4());stage(store,a);stage(store,b)
    store.activate('T1',a,'legacy-v1')
    with pytest.raises(ValueError):store.activate('T1',b,'legacy-v1')
    assert store.generation('T1')==a
    with pytest.raises(ValueError):stage(store,str(uuid.uuid4()))
    store.remove('T1')
    with pytest.raises(ValueError):store.activate('T1',a,'legacy-v1')


def test_incomplete_enrollment_never_replaces_prior(tmp_path):
    store=EnrollmentStore(tmp_path);store.put('T1',np.array([1.,0.,0.]),'buffalo_l',5)
    with pytest.raises(ValueError):store.stage('T1',str(uuid.uuid4()),'legacy-v1',[np.array([1.,0.,0.])]*14,['CENTER']*14,'buffalo_l','policy')
    assert store.generation('T1')=='legacy-v1'


def test_exact_upstream_preprocessing_golden_and_selected_model():
    import hashlib, json
    from pathlib import Path
    from app.live_models import verified_asset
    from app.pad import MiniFASNet
    fixture=json.loads((Path(__file__).parent/'fixtures/minifasnet-v2-golden.json').read_text())
    y,x=np.indices((120,160))
    image=np.stack([(x*7+y*3)%256,(y*11)%256,(x*5)%256],axis=2).astype(np.uint8)
    for case in fixture['cases']:
        assert hashlib.sha256(preprocess(image,case['bbox']).tobytes()).hexdigest()==case['tensor_sha256']
    root=Path(__file__).resolve().parents[1]/'models'
    if not (root/'live/MiniFASNetV2.onnx').exists():
        pytest.skip('Exact model not provisioned; tensor golden checks above passed')
    model=MiniFASNet(verified_asset(root,'pad'),fixture['model_sha256'])
    for case in fixture['cases']:
        tensor=preprocess(image,case['bbox'])
        output=model.session.run([model.output_name],{model.input_name:tensor})[0]
        assert output==pytest.approx(np.array(case['logits']),abs=2e-5)
        assert model.verify(image,case['bbox']).score==pytest.approx(bona_fide_probability(np.array(case['logits'])),abs=1e-6)


def test_service_live_api_cannot_treat_model_absence_as_identity_pass(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import Settings
    from test_identity import FakeEngine, TOKEN
    with TestClient(create_app(Settings(TOKEN,tmp_path/'data',tmp_path/'models'),FakeEngine()),headers={'Authorization':f'Bearer {TOKEN}'}) as client:
        ready=client.get('/live/readiness').json()
        assert ready['identity']=='PASS' and ready['pose']=='UNAVAILABLE' and ready['pad']=='UNAVAILABLE' and ready['status']=='BLOCKED'
        assert client.post('/live/begin',json=begin().model_dump()).status_code==422
        assert client.post('/live/observe',json={'session_id':str(uuid.uuid4()),'nonce':str(uuid.uuid4()),'service_epoch':ready['service_epoch'],'sequence':1,'elapsed_ms':1,'jpeg':'injected'}).status_code==422
        assert client.get('/live/readiness',headers={'Authorization':'Bearer wrong'}).status_code==401


def test_low_quality_is_not_enrollment_progress_and_repeated_observation_is_rejected(tmp_path, monkeypatch):
    from collections import Counter
    import time
    from app.sessions import LiveInference
    from app.config import Settings
    from app.live_contract import Observation
    class Engine:
        ready=True
        def observe_with_landmarks(self,image):raise CaptureError('LOW_QUALITY_BLUR')
    class Pose:
        def close(self):pass
    request=begin('LOGIN');store=EnrollmentStore(tmp_path)
    live=LiveInference(Settings('test',tmp_path,tmp_path),Engine(),store,None,None,{})
    # Test-only internal fixture; no production service endpoint can configure this.
    live.active={'request':request,'window':EvidenceWindow(request,[np.array([1.,0.,0.])]*14,0.45),'pose':Pose(),
                 'last_sequence':0,'last_elapsed':-1,'pauses':Counter(),
                 'started':time.monotonic(),'deadline':time.monotonic()+10}
    monkeypatch.setattr('app.sessions.decode_frame',lambda _:np.zeros((480,640,3),np.uint8))
    sample=Observation(session_id=request.session_id,nonce=request.nonce,service_epoch=live.epoch,
                       sequence=1,elapsed_ms=1,jpeg='test-only')
    result=live.observe(sample)
    assert not result['complete'] and result['accepted_samples']==0 and result['coverage']=={}
    assert result['controls']['quality']['result']==Outcome.INCONCLUSIVE
    assert live.active is not None
    with pytest.raises(CaptureError,match='STALE'):live.observe(sample)
    live.close()
