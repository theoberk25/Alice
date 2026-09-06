"""Immutable enterprise receipt cache, delivered through authenticated SSH.

Does not open or write the runtime ledger. See docs/integration/wazuh-audit-sync.md.
"""
import argparse
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile

from dcamr.audit.event_contract import canonical_bytes, parse_json
from dcamr.audit.signing import Ed25519Verifier
from dcamr.packages.package_verifier import load_release
from dcamr.usb_storage import UsbStorage

MAX_BYTES=16384


def validate(raw, release):
    if len(raw)>MAX_BYTES: raise ValueError('Receipt too large')
    body=parse_json(raw)
    if set(body)!={'envelope','enterprise_receipt'}:raise ValueError('Unexpected receipt fields')
    e=body['envelope'];r=body['enterprise_receipt']
    if set(e)!={'request','key_id','signature'}:raise ValueError('Invalid envelope')
    if set(r)!={'index','document_id','verified','received_at'}:raise ValueError('Invalid receipt')
    if r['index']!='alice-enterprise-ingress-v1' or r['verified'] is not True:raise ValueError('Unverified receipt')
    from datetime import datetime
    if datetime.fromisoformat(r['received_at']).tzinfo is None:raise ValueError('Missing receipt timezone')
    q=e['request'];rid=q['request_id']
    if type(rid) is not str or not 1<=len(rid)<=64:raise ValueError('Invalid request ID')
    identity=sha256(rid.encode()).hexdigest()
    if r['document_id']!=identity:raise ValueError('Receipt/request mismatch')
    key=release.terminal_keys[e['key_id']]
    Ed25519Verifier(key.public_key).verify(base64.b64decode(e['signature'],validate=True),canonical_bytes(q))
    if q['agent_id']!=key.agent_id:raise ValueError('Agent/key mismatch')
    return identity,canonical_bytes(body)


def store(directory, identity, data, check):
    """Create atomically without replacing existing evidence; exact retries only."""
    directory=Path(directory);check()
    if directory.is_symlink():raise ValueError('Cache redirects')
    directory.mkdir(mode=0o700,parents=False,exist_ok=True)
    check()
    target=directory/(identity+'.json')
    fd,name=tempfile.mkstemp(prefix='.receipt-',dir=directory)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        check()
        try:os.link(name,target)
        except FileExistsError:
            fd=os.open(target,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as f:
                if f.read(MAX_BYTES+1)!=data:raise ValueError('Existing receipt conflict')
        fd=os.open(directory,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        check()
        return {'stored':True,'request_document_id':identity,'sha256':sha256(data).hexdigest(),'path':str(target)}
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--usb-root',type=Path,required=True)
    p.add_argument('--release',type=Path,required=True)
    p.add_argument('--trust-key',type=Path,required=True)
    a=p.parse_args()
    directory=a.usb_root/'enterprise-cache'/'ingress-receipts'
    if (a.usb_root/'enterprise-cache').is_symlink():raise ValueError('Redirected cache root')
    guard=UsbStorage(a.usb_root,directory)
    # Parent is already managed by the existing permissions cache.
    if not directory.parent.is_dir():raise ValueError('Enterprise cache parent missing')
    release=load_release(a.release,bytes.fromhex(a.trust_key.read_text().strip()))
    identity,data=validate(sys.stdin.buffer.read(MAX_BYTES+1),release)
    print(json.dumps(store(directory,identity,data,guard.check)))

if __name__=='__main__':main()
