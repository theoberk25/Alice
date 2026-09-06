"""Cross-store deletion retries must never remove a replacement enrollment."""
import uuid
import numpy as np
import pytest
from pydantic import ValidationError
from app.live_contract import GenerationRemoval, POSES
from app.storage import EnrollmentStore
from test_live_biometrics import begin
from test_live_workflow import live_client


def stage(store, generation, previous):
    poses = [p for p in POSES for _ in range(2)]
    store.stage('T1', generation, previous, [np.array([1., 0., 0.])]*14,
                poses, 'buffalo_l', 'alice.live-face.v1')


def test_removal_lost_ack_retry_preserves_reenrollment_and_new_capture(live_client):
    client,pose,forged,clock,settings,api = live_client
    store = api.state.store
    original = str(uuid.uuid4())
    stage(store,original,'none')
    store.activate('T1',original,'none')
    removal = {'technician_id':'T1','removal_id':str(uuid.uuid4()),'expected_generations':[original]}
    result = client.post('/generation/remove',json=removal)
    assert result.status_code == 200
    assert result.json() == {'status':'REMOVED','technician_id':'T1','removal_id':removal['removal_id']}
    assert store.generation('T1') == 'none'
    replacement = str(uuid.uuid4())
    stage(store,replacement,'none')
    store.activate('T1',replacement,'none')
    new_session = begin().model_copy(update={'generation':replacement})
    assert client.post('/live/begin',json=new_session.model_dump()).status_code == 200
    # Simulate process restart plus replay of the exact lost acknowledgment.
    api.state.store = EnrollmentStore(settings.data_dir)
    assert client.post('/generation/remove',json=removal).json() == result.json()
    assert store.generation('T1') == replacement
    assert api.state.live.active['request'].session_id == new_session.session_id
    assert client.post('/generation/remove',json=removal | {'removal_id':str(uuid.uuid4())}).status_code == 422
    assert store.generation('T1') == replacement


def test_removal_binding_collision_and_transaction_failure_preserve_material(tmp_path):
    store = EnrollmentStore(tmp_path)
    store.put('T1',np.array([1.,0.,0.]),'buffalo_l',5)
    generation = str(uuid.uuid4())
    stage(store,generation,'legacy-v1')
    store.activate('T1',generation,'legacy-v1')
    token = str(uuid.uuid4())
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_removal BEFORE INSERT ON face_removals BEGIN SELECT RAISE(ABORT,'injected write failure'); END")
    with pytest.raises(Exception,match='injected write failure'):
        store.remove_guarded('T1',token,[generation])
    assert store.generation('T1') == generation
    np.testing.assert_array_equal(store.get('T1','buffalo_l'),[1.,0.,0.])
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM face_removals').fetchone()[0] == 0
        db.execute('DROP TRIGGER reject_removal')
    assert store.remove_guarded('T1',token,[generation])
    assert not store.remove_guarded('T1',token,[generation])
    with pytest.raises(ValueError,match='REMOVAL_BINDING_CHANGED'):
        store.remove_guarded('T1',token,['none'])
    with pytest.raises(ValueError,match='REMOVAL_BINDING_CHANGED'):
        store.remove_guarded('T2',token,[generation])


@pytest.mark.parametrize('generations',[[],['a','a'],['a','b','c'],[''],['x'*101]])
def test_removal_contract_bounds_snapshot(generations):
    with pytest.raises(ValidationError):
        GenerationRemoval(technician_id='T1',removal_id=str(uuid.uuid4()),expected_generations=generations)
