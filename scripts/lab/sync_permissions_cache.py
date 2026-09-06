"""One verified enterprise-to-USB cache pass; safe to schedule separately from ledger owner."""
import argparse
import json
from pathlib import Path
from cloud.permissions_cache import sync, public_bytes
from cloud.wazuh_audit import WazuhAuditSink
from dcamr.usb_storage import UsbStorage

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('config','usb-root','public-key','anchor'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); root=a.usb_root/'enterprise-cache'/'permissions'
    guard=UsbStorage(a.usb_root,root).check
    for path in (a.config,a.public_key,a.anchor):
        if path.resolve().is_relative_to(a.usb_root.resolve()):p.error('Trust/credentials/rollback anchor must stay off USB')
    raw=a.public_key.read_bytes().strip()
    key=public_bytes(raw)
    try:print(json.dumps(sync(WazuhAuditSink.from_config(a.config),root,a.anchor,key,guard),sort_keys=True))
    except Exception as exc:
        print(json.dumps({'status':'CACHE_SYNC_FAILED','error_type':type(exc).__name__}));return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
