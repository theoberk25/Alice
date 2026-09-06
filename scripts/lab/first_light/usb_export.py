"""Verified USB export of one first-light request's ledger events (Pi side).

Uses AuditLog's delivery bookkeeping exactly as designed: queue each event to
the usb:<label> destination, write the events as NDJSON on the USB mount,
recompute each record's event_hash and the file sha256, then acknowledge with
the receipt. Failures use record_attempt. Acknowledgement never deletes
anything: the Pi-internal ledger stays the source of truth. The export file
contains LEDGER events (alice-audit-event-v1) only and is labelled so; the
enterprise-sim alice-audit.jsonl chain is a different format. Run after the
runtime is stopped (single trusted writer owns the ledger). Per AGENTS.md.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from dcamr.audit.audit_log import AuditLog
from dcamr.audit.event_contract import canonical_bytes, event_hash
from dcamr.audit.signing import Ed25519Signer, Ed25519Verifier, TrustStore
from dcamr.main import LEDGER_KEY_ID, _utc_now


class ExportError(RuntimeError):
    pass


def _events_for(ledger: AuditLog, request_id: str) -> list[dict]:
    events, after = [], 0
    while True:
        page = ledger.read(after=after, limit=64)
        if not page:
            return events
        events.extend(e for e in page if e["correlation"]["request_id"] == request_id)
        after = page[-1]["sequence"]


def export_request(ledger: AuditLog, request_id: str, usb_dir: Path,
                   label: str = "first-light") -> Path:
    """Queue, write, verify and acknowledge one request's events; return the file."""
    ledger.seal()
    events = _events_for(ledger, request_id)
    if not events:
        raise ExportError(f"no ledger events for request {request_id}")
    destination = f"usb:{label}"
    for event in events:
        ledger.queue(event["event_id"], destination)

    usb_dir = Path(usb_dir)
    usb_dir.mkdir(parents=True, exist_ok=True)
    out_path = usb_dir / f"first-light-{request_id}.ndjson"
    header = {"export_format": "alice-audit-event-v1-ndjson",
              "note": "ledger events only; not the enterprise-sim alice-audit.jsonl chain",
              "request_id": request_id}
    try:
        with out_path.open("wb") as output:
            output.write(canonical_bytes(header) + b"\n")
            for event in events:
                output.write(canonical_bytes(event) + b"\n")
        # Verify the copy by re-reading the USB file and matching each stored
        # event_hash against a recomputation from the copied record.
        lines = out_path.read_bytes().splitlines()
        copied = [json.loads(line) for line in lines[1:]]
        if len(copied) != len(events):
            raise ExportError("copied record count mismatch")
        for original, record in zip(events, copied):
            if (record["event_hash"] != original["event_hash"]
                    or event_hash(record) != record["event_hash"]):
                raise ExportError("copied event hash mismatch")
        file_sha256 = sha256(out_path.read_bytes()).hexdigest()
    except (OSError, ValueError, ExportError) as exc:
        for event in events:
            ledger.record_attempt(event["event_id"], retry_after_ms=60000,
                                  error_code="USB_WRITE_OR_VERIFY_FAILED")
        raise ExportError(f"usb export failed: {exc}") from exc

    for event in events:
        ledger.acknowledge(event["event_id"], destination=destination,
                           event_hash=event["event_hash"], receipt_ref=out_path.name,
                           receipt_sha256=file_sha256)
    return out_path


def open_ledger(data_dir: Path) -> AuditLog:
    seed = bytes.fromhex((data_dir / "ledger_key.seed").read_text().strip())
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    public = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw)

    def clock():
        import time
        return {"recorded_at": _utc_now(), "clock_source": "pi-system-clock",
                "confidence": "UNCERTAIN", "boot_id": "usb-export",
                "monotonic_ns": time.monotonic_ns()}

    return AuditLog.open(data_dir / "ledger.sqlite",
                         signer=Ed25519Signer(seed, LEDGER_KEY_ID),
                         trust=TrustStore({("ed25519", LEDGER_KEY_ID): Ed25519Verifier(public)}),
                         clock=clock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Pi-internal runtime data dir (ledger + key)")
    parser.add_argument("--usb-dir", type=Path, required=True, help="USB mount point")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--label", default="first-light")
    args = parser.parse_args()
    ledger = open_ledger(args.data_dir)
    try:
        path = export_request(ledger, args.request_id, args.usb_dir, args.label)
        print(f"exported and acknowledged: {path}")
    finally:
        ledger.close()


if __name__ == "__main__":
    main()
