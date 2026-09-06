"""Verified enterprise permissions cache; does not activate first-light grants."""
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from dcamr.audit.signing import Ed25519Verifier
def canonical_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

from cloud.wazuh_audit import unique_object

FILES={'subjects.json','grants.json','prohibitions.json','revocations.json'}
ISSUER='sen.iam.permissions-authority'
KEY_ID=ISSUER+'.2026-09'


def public_bytes(raw):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
    if raw.startswith(b'-----BEGIN'):
        return load_pem_public_key(raw).public_bytes(Encoding.Raw,PublicFormat.Raw)
    return bytes.fromhex(raw.decode()) if len(raw)==64 else raw


def parse(raw):
    return json.loads(raw,object_pairs_hook=unique_object)


def verify(doc, public_key, now=None):
    now=now or datetime.now(timezone.utc)
    raw=base64.b64decode(doc['manifest_b64'],validate=True)
    sig=base64.b64decode(doc['signature_b64'],validate=True)
    m=parse(raw)
    if canonical_bytes(m)!=raw:raise ValueError('Noncanonical manifest')
    if m['issuer_id']!=ISSUER or m['site_id']!='SEN' or m['schema_version']!='alice-permissions-bundle-v1':
        raise ValueError('Wrong issuer/site/schema')
    if m['signature']['algorithm']!='Ed25519' or m['signature']['key_id']!=KEY_ID:
        raise ValueError('Wrong signing identity')
    Ed25519Verifier(public_key).verify(sig,canonical_bytes({k:v for k,v in m.items() if k!='signature'}))
    if type(m['generation']) is not int or m['generation']<0:raise ValueError('Invalid generation')
    if type(m['revocation_epoch']) is not int or m['revocation_epoch']<0:raise ValueError('Invalid epoch')
    start=datetime.fromisoformat(m['not_before'].replace('Z','+00:00'))
    end=datetime.fromisoformat(m['not_after'].replace('Z','+00:00'))
    if not start<=now<end:raise ValueError('Release outside validity interval')
    if doc['generation']!=m['generation'] or doc['manifest_sha256']!=sha256(raw).hexdigest():
        raise ValueError('Envelope mismatch')
    if set(m['content_digests'])!=FILES or set(doc['payload_b64'])!=FILES:raise ValueError('Incomplete release')
    payloads={'manifest.json':raw,'manifest.sig':sig}
    for name in FILES:
        data=base64.b64decode(doc['payload_b64'][name],validate=True)
        if sha256(data).hexdigest()!=m['content_digests'][name] or canonical_bytes(parse(data))!=data:
            raise ValueError('Invalid payload')
        payloads[name]=data
    return m,payloads


def durable(path,data):
    path=Path(path)
    fd,tmp=tempfile.mkstemp(prefix='.cache-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def sync(sink,root,anchor,public_key,guard,now=None):
    guard()
    code,result=sink._request('POST','/alice-permissions/_search',
        {'size':1,'sort':[{'generation':'desc'}],'query':{'term':{'status':'CURRENT'}}})
    if code!=200:raise ValueError('Enterprise release unavailable')
    hits=result['hits']['hits']
    if len(hits)!=1:raise ValueError('No current release')
    m,files=verify(hits[0]['_source'],public_key,now)
    state={'generation':m['generation'],'revocation_epoch':m['revocation_epoch'],
           'manifest_sha256':sha256(files['manifest.json']).hexdigest()}
    root=Path(root);anchor=Path(anchor)
    if anchor.exists():
        prev=parse(anchor.read_bytes())
        if state['generation']<prev['generation'] or state['revocation_epoch']<prev['revocation_epoch']:
            raise ValueError('Rollback rejected')
        if state['generation']==prev['generation'] and state!=prev:raise ValueError('Same-generation conflict')
    guard()
    if root.is_symlink():raise ValueError('Cache must not be a symlink')
    root.mkdir(parents=True,exist_ok=True)
    directory=root/f"{m['generation']:06d}"
    if directory.is_symlink():raise ValueError('Generation must not be a symlink')
    directory.mkdir(exist_ok=True)
    for name,data in files.items():
        guard();path=directory/name
        if path.is_symlink():raise ValueError('Payload symlink')
        if path.exists():
            if path.read_bytes()!=data:raise ValueError('Existing generation tampered')
        else:durable(path,data)
    guard()
    anchor.parent.mkdir(parents=True,exist_ok=True)
    durable(anchor,canonical_bytes(state))
    guard()
    durable(root/'current.json',canonical_bytes(dict(state,directory=directory.name,
        status='VERIFIED_CACHE_ONLY',runtime_activation='NOT_APPLIED',not_after=m['not_after'])))
    return dict(state,status='VERIFIED_CACHE_ONLY',runtime_activation='NOT_APPLIED')
