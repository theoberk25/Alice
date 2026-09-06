import json
from hashlib import sha256
import pytest
from lab.first_light.build_release import build
from lab.first_light.terminal_client import build_envelope
from dcamr.packages.package_verifier import load_release
from dcamr.enterprise_receipts import validate,store


def test_verified_immutable_cache(tmp_path):
    build(tmp_path/'release-build')
    b=tmp_path/'release-build'
    release=load_release(b/'release',bytes.fromhex((b/'trust/manifest_public.hex').read_text().strip()))
    e=build_envelope(bytes.fromhex((b/'client/term-agent-01-k1.seed').read_text().strip()),state='on')
    identity=sha256(e['request']['request_id'].encode()).hexdigest()
    body={'envelope':e,'enterprise_receipt':{'index':'alice-enterprise-ingress-v1','document_id':identity,'verified':True,'received_at':'2026-09-06T00:00:00+00:00'}}
    key,raw=validate(json.dumps(body).encode(),release)
    target=tmp_path/'cache';first=store(target,key,raw,lambda:None)
    assert store(target,key,raw,lambda:None)==first
    with pytest.raises(ValueError,match='conflict'):store(target,key,b'changed',lambda:None)
    body['envelope']['request']['parameters']['state']='off'
    with pytest.raises(Exception):validate(json.dumps(body).encode(),release)


def test_mount_guard_failure_no_write(tmp_path):
    def check():raise OSError('Unmounted')
    with pytest.raises(OSError):store(tmp_path/'cache','a'*64,b'{}',check)
    assert not (tmp_path/'cache').exists()
