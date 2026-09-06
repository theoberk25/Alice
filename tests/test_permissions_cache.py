import base64
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from cloud.permissions_cache import sync,verify,public_bytes
ROOT=Path(__file__).resolve().parents[1]/'artifacts/enterprise-sim'
class CacheTests(unittest.TestCase):
    def setUp(self):
        d=ROOT/'usb/permissions/generations/000042'
        b64=lambda p:base64.b64encode(p.read_bytes()).decode()
        self.doc={'manifest_b64':b64(d/'manifest.json'),'signature_b64':b64(d/'manifest.sig'),'generation':42,
                  'manifest_sha256':sha256((d/'manifest.json').read_bytes()).hexdigest(),
                  'payload_b64':{p.name:b64(p) for p in d.glob('*.json') if p.name!='manifest.json'}}
        raw=(ROOT/'keys/permissions-signing.ed25519.pk').read_bytes().strip()
        self.key=public_bytes(raw)
        self.now=datetime(2026,9,6,tzinfo=timezone.utc)
    def test_valid_and_tampered(self):
        self.assertEqual(verify(self.doc,self.key,self.now)[0]['generation'],42)
        self.doc['payload_b64']['grants.json']=base64.b64encode(b'{}').decode()
        with self.assertRaises(ValueError):verify(self.doc,self.key,self.now)
    def test_expiry(self):
        with self.assertRaises(ValueError):verify(self.doc,self.key,datetime(2027,1,1,tzinfo=timezone.utc))
    def test_install_idempotence_and_rollback(self):
        class Sink:
            def _request(_, *args):return 200,{'hits':{'hits':[{'_source':self.doc}]}}
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'usb';anchor=Path(t)/'anchor.json'
            a=sync(Sink(),root,anchor,self.key,lambda:None,self.now)
            self.assertEqual(a,sync(Sink(),root,anchor,self.key,lambda:None,self.now))
            prev=json.loads(anchor.read_text());prev['generation']=43;anchor.write_text(json.dumps(prev))
            with self.assertRaises(ValueError):sync(Sink(),root,anchor,self.key,lambda:None,self.now)
            self.assertEqual(json.loads((root/'current.json').read_text())['generation'],42)

    def test_offline_retains_verified_cache(self):
        class Sink:
            offline=False
            def _request(inner,*args):
                if inner.offline:raise OSError('offline')
                return 200,{'hits':{'hits':[{'_source':self.doc}]}}
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'usb';anchor=Path(t)/'anchor.json';sink=Sink()
            sync(sink,root,anchor,self.key,lambda:None,self.now)
            before=(root/'current.json').read_bytes();sink.offline=True
            with self.assertRaises(OSError):sync(sink,root,anchor,self.key,lambda:None,self.now)
            self.assertEqual((root/'current.json').read_bytes(),before)

    def test_wrong_trust_key_rejected(self):
        from dcamr.audit.signing import TrustError
        with self.assertRaises(TrustError):verify(self.doc,b'0'*32,self.now)
