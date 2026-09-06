import json
from pathlib import Path
import pytest
from lab.first_light.build_release import build
from lab.first_light.terminal_client import build_envelope
from dcamr.packages.package_verifier import load_release
from services.enterprise_ingress import Gateway, IngressError, ReceiptSink, INDEX
from cloud.wazuh_audit import DeliveryError


@pytest.fixture
def setup(tmp_path):
    build(tmp_path)
    release=load_release(tmp_path/'release',bytes.fromhex((tmp_path/'trust/manifest_public.hex').read_text().strip()))
    seed=bytes.fromhex((tmp_path/'client/term-agent-01-k1.seed').read_text().strip())
    return release,seed


class Sink:
    def __init__(self,fail=False):self.calls=[];self.fail=fail
    def record(self,e):
        self.calls.append(e)
        if self.fail:raise DeliveryError('UNAVAILABLE')
        return {'verified':True}


def test_signed_forward_preserves_bytes_and_order(setup):
    release,seed=setup; sink=Sink(); forwarded=[]
    def forward(raw):
        assert sink.calls
        forwarded.append(raw);return 202,{'decision':'CHALLENGE'}
    g=Gateway(release,sink,forward)
    raw=json.dumps(build_envelope(seed,state='on'),indent=2).encode()
    status,result=g.submit(raw)
    assert status==202 and result['enterprise_receipt']['verified']
    assert forwarded==[raw]


def test_fail_closed_and_invalid_signatures(setup):
    release,seed=setup
    def no_forward(raw):raise AssertionError('Must not forward')
    sink=Sink(True);g=Gateway(release,sink,no_forward)
    e=build_envelope(seed,state='on')
    with pytest.raises(DeliveryError):g.submit(json.dumps(e).encode())
    sink.calls.clear();e['request']['parameters']['state']='off'
    with pytest.raises(IngressError):g.submit(json.dumps(e).encode())
    assert not sink.calls


def test_expired_and_duplicate_json(setup):
    from datetime import datetime,timezone,timedelta
    release,seed=setup;sink=Sink()
    e=build_envelope(seed,state='on')
    g=Gateway(release,sink,lambda _:None,now=lambda:datetime.now(timezone.utc)+timedelta(minutes=10))
    with pytest.raises(IngressError,match='EXPIRED'):g.submit(json.dumps(e).encode())
    with pytest.raises(IngressError):g.submit(b'{"key_id":"x","key_id":"y"}')
    assert not sink.calls


def test_receipt_replay_and_collision(setup):
    _,seed=setup
    class Client:
        docs={}
        def _request(self,method,path,body=None):
            key=path.split('/')[-1]
            if method=='PUT':
                if key in self.docs:return 409,{}
                self.docs[key]=body;return 201,{}
            return 200,{'found':True,'_id':key,'_index':INDEX,'_source':self.docs[key]}
    sink=ReceiptSink(Client());e=build_envelope(seed,state='on')
    assert sink.record(e)['replay'] is False
    assert sink.record(e)['replay'] is True
    e['request']['parameters']['state']='off'
    with pytest.raises(IngressError,match='CONFLICT'):sink.record(e)


def test_unknown_pi_outcome_keeps_receipt(setup):
    release,seed=setup
    def forward(_):raise TimeoutError()
    status,result=Gateway(release,Sink(),forward).submit(json.dumps(build_envelope(seed,state='on')).encode())
    assert status==502 and result['enterprise_receipt']['verified']
    assert result['error']=='PI_OUTCOME_UNKNOWN_CHECK_HISTORY'
