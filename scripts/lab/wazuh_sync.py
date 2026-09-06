"""One bounded Wazuh delivery pass with the Pi runtime stopped (single writer)."""
import argparse
import json
import time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cloud.wazuh_audit import WazuhAuditSink, sync_once
from dcamr.audit.audit_log import AuditLog
from dcamr.audit.signing import Ed25519Signer, Ed25519Verifier, TrustStore
from dcamr.main import LEDGER_KEY_ID, _utc_now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--ledger-key-file', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--runtime-stopped', action='store_true', required=True,
                        help='Operator confirms exclusive ledger ownership; never run beside the runtime')
    storage = parser.add_mutually_exclusive_group(required=True)
    storage.add_argument('--usb-root', type=Path)
    storage.add_argument('--local-test-storage', action='store_true')
    parser.add_argument('--after', type=int, default=0)
    parser.add_argument('--limit', type=int, default=16)
    args = parser.parse_args()
    guard = lambda: None
    if args.usb_root:
        from dcamr.usb_storage import UsbStorage
        guard = UsbStorage(args.usb_root, args.data_dir).check
    if args.usb_root and (args.ledger_key_file.resolve().is_relative_to(args.usb_root.resolve())
                         or args.config.resolve().is_relative_to(args.usb_root.resolve())):
        parser.error('Private key and sync credentials must stay outside USB')
    sink = WazuhAuditSink.from_config(args.config)
    seed = bytes.fromhex(args.ledger_key_file.read_text().strip())
    public = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    def clock():
        return {'recorded_at': _utc_now(), 'clock_source': 'pi-system-clock',
                'confidence': 'UNCERTAIN', 'boot_id': 'wazuh-sync-maintenance', 'monotonic_ns': time.monotonic_ns()}
    guard()
    ledger = AuditLog.open(args.data_dir/'ledger.sqlite', signer=Ed25519Signer(seed, LEDGER_KEY_ID),
                           trust=TrustStore({('ed25519', LEDGER_KEY_ID): Ed25519Verifier(public)}), clock=clock)
    try:
        result = sync_once(ledger, sink, after=args.after, limit=args.limit, check_storage=guard)
        print(json.dumps(result, sort_keys=True))
        return 1 if result['errors'] else 0
    finally:
        ledger.close()


if __name__ == '__main__':
    raise SystemExit(main())
