import json
from pathlib import Path
import pytest
from lab.first_light.build_release import build
from lab.first_light.terminal_client import build_envelope
from dcamr.packages.package_verifier import load_release
from services.enterprise_ingress import Gateway, IngressError, ReceiptSink, INDEX, lan_host, pi_forwarder
from cloud.wazuh_audit import DeliveryError
from cloud.thermal_governed_client import build_wire_request, sign_envelope
from lab.thermal_demo.build_release import build as build_thermal_release


@pytest.fixture
def setup(tmp_path):
    build(tmp_path)
    release=load_release(tmp_path/'release',bytes.fromhex((tmp_path/'trust/manifest_public.hex').read_text().strip()))
    seed=bytes.fromhex((tmp_path/'client/term-agent-01-k1.seed').read_text().strip())
    return release,seed


@pytest.fixture
def thermal_setup(tmp_path):
    bundle=tmp_path/'thermal'
    build_thermal_release(bundle)
    release=load_release(bundle/'release',bytes.fromhex((bundle/'manifest-public.hex').read_text().strip()))
    seed=bytes.fromhex((bundle/'cooling-agent-01-k1.seed').read_text().strip())
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


def test_thermal_envelope_is_receipted_then_forwarded_unchanged(thermal_setup):
    release,seed=thermal_setup; sink=Sink(); forwarded=[]
    request=build_wire_request(fan_pct=70,run_id='a'*32,expected_revision=4,
                               agent_id='cooling-agent-01',client_request_id='cloud-thermal-1')
    envelope=sign_envelope(seed,request,key_id='cooling-agent-01-k1')
    raw=json.dumps(envelope,indent=2).encode()
    def forward(value):
        assert sink.calls
        forwarded.append(value)
        return 200,{'decision':'ALLOW','demo_application':'APPLIED'}
    status,result=Gateway(release,sink,forward,request_schema='thermal').submit(raw)
    assert status==200
    assert result['enterprise_receipt']['verified'] is True
    assert result['pi']['decision']=='ALLOW'
    assert forwarded==[raw]


def test_thermal_schema_rejects_light_envelope(setup):
    release,seed=setup; sink=Sink()
    with pytest.raises(IngressError):
        Gateway(release,sink,lambda _:None,request_schema='thermal').submit(
            json.dumps(build_envelope(seed,state='on')).encode())
    assert not sink.calls


def test_pi_forwarder_accepts_only_demo_lan_or_ssh_tunnel():
    assert callable(pi_forwarder('http://127.0.0.1:18080'))
    assert callable(pi_forwarder('http://192.168.50.20:8080'))
    with pytest.raises(ValueError):
        pi_forwarder('http://0.0.0.0:8080')


def test_ingress_listener_accepts_isolated_lan_without_wildcard():
    assert lan_host('127.0.0.1')=='127.0.0.1'
    assert lan_host('192.168.50.150')=='192.168.50.150'
    with pytest.raises(Exception):
        lan_host('0.0.0.0')
    with pytest.raises(Exception):
        lan_host('192.168.11.214')
