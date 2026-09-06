"""Read-only acceptance of existing request history on the provisioned Pi.

Compare runtime events with mounted SQL and (optionally) exact Wazuh documents.
Never initializes a ledger, opens AuditLog as a writer, submits a command, changes
service/network configuration or uploads an event. Follow AGENTS.md and
docs/integration/esp-technician-handoff.md. Run on the Pi for physical USB checks.
"""
import argparse
from contextlib import closing
from http.client import HTTPException
import json
from pathlib import Path
import sqlite3
import time
from urllib.request import build_opener, ProxyHandler

from cloud.wazuh_audit import DeliveryError, WazuhAuditSink
from dcamr.audit.event_contract import canonical_bytes
from dcamr.usb_storage import UsbStorage
from services.runtime_feed import MAX_RESPONSE_BYTES, NoRedirect, loopback_url, unique_object, validate_page


class CheckError(RuntimeError):
    pass


def _get(url):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=5) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise CheckError('RUNTIME_RESPONSE_TOO_LARGE')
    return json.loads(raw, object_pairs_hook=unique_object)


def check_pipeline(*, url, request_id, data_dir, expected, usb_root=None, sink=None, wait_seconds=0):
    """Return narrowly scoped evidence; missing optional checks stay NOT_CHECKED."""
    url = loopback_url(url)
    if expected not in ('ALLOW', 'DENY', 'CHALLENGE') or not request_id or not 0 <= wait_seconds <= 300:
        raise CheckError('INVALID_CHECK_OPTIONS')
    storage = UsbStorage(usb_root, data_dir) if usb_root is not None else None
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            if storage:
                storage.check()
            page = _get(url + '/events?after=0')
            validate_page(page, 0)
            events = [e for e in page['events'] if e['correlation']['request_id'] == request_id]
            expected_chains = ([['REQUEST', 'ASSESSMENT', 'DECISION', 'EXECUTION_ATTEMPT',
                                 'CONTROLLER_RECEIPT', 'EXECUTION_RESULT', 'OBSERVED_STATE']]
                               if expected == 'ALLOW' else
                               ([['REQUEST', 'ASSESSMENT', 'DECISION']] if expected == 'CHALLENGE' else
                                [['REQUEST', 'REJECTION'], ['REQUEST', 'ASSESSMENT', 'DECISION']]))
            if [e['event_type'] for e in events] not in expected_chains:
                raise CheckError('REQUEST_CHAIN_NOT_COMPLETE_OR_EXPECTED')
            if len({e['correlation']['request_sha256'] for e in events}) != 1:
                raise CheckError('REQUEST_DIGEST_CONFLICT')
            if expected == 'DENY' and events[-1]['detail']['outcome'] != (
                    'REJECTED' if len(events) == 2 else 'DENY'):
                raise CheckError('EXPECTED_DENIAL_NOT_RECORDED')
            if expected == 'CHALLENGE' and events[-1]['detail']['outcome'] != 'CHALLENGE':
                raise CheckError('EXPECTED_CHALLENGE_NOT_RECORDED')
            if expected == 'ALLOW' and (
                    events[2]['detail']['outcome'] != 'ALLOW'
                    or events[4]['detail']['outcome'] != 'ACCEPTED'
                    or events[5]['detail']['outcome'] != 'COMPLETED'):
                raise CheckError('EXPECTED_EXECUTION_NOT_COMPLETED')
            ledger_path = (Path(data_dir) / 'ledger.sqlite').resolve()
            with closing(sqlite3.connect(ledger_path.as_uri() + '?mode=ro', uri=True)) as db:
                db.execute('PRAGMA query_only=ON')
                db.execute('BEGIN')
                for event in events:
                    row = db.execute('SELECT canonical FROM events WHERE event_id=?',
                                     (event['event_id'],)).fetchone()
                    if row is None or row[0] != canonical_bytes(event):
                        raise CheckError('RUNTIME_SQL_MISMATCH')
            if sink is not None:
                for event in events:
                    sink.verify_stored(event)
            if storage:
                storage.check()
            status = _get(url + '/sync-status')
            if type(status) is not dict or not isinstance(status.get('state'), str):
                raise CheckError('INVALID_SYNC_STATUS')
            return dict(request_id=request_id, expected=expected,
                        events_verified=len(events), runtime_sql='EXACT_MATCH',
                        storage='MOUNTED_USB' if storage else 'LOCAL_TEST',
                        wazuh='EXACT_MATCH' if sink is not None else 'NOT_CHECKED',
                        worker_state=status['state'], physical_effect='NOT_VERIFIED',
                        replay_execution_count='NOT_CHECKED', dashboard='NOT_CHECKED')
        except DeliveryError as exc:
            if exc.code != 'RECEIPT_UNAVAILABLE' or time.monotonic() >= deadline:
                raise CheckError(exc.code) from None
        except CheckError as exc:
            if str(exc) != 'REQUEST_CHAIN_NOT_COMPLETE_OR_EXPECTED' or time.monotonic() >= deadline:
                raise
        except (OSError, HTTPException, ValueError, sqlite3.Error) as exc:
            raise CheckError('INPUT_UNAVAILABLE_OR_INVALID') from exc
        time.sleep(min(1, max(0, deadline - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--expect', choices=('ALLOW', 'DENY', 'CHALLENGE'), required=True)
    parser.add_argument('--data-dir', type=Path, default=Path('/mnt/alice-usb/pi-data'))
    storage = parser.add_mutually_exclusive_group(required=True)
    storage.add_argument('--usb-root', type=Path)
    storage.add_argument('--local-test-storage', action='store_true')
    parser.add_argument('--wazuh-config', type=Path,
                        help='Existing private config; optional exact read-only Wazuh check')
    parser.add_argument('--wait-seconds', type=float, default=60,
                        help='Wait up to 300 seconds for request/remote documents; no uploads')
    args = parser.parse_args()
    try:
        if (args.usb_root and args.wazuh_config
                and args.wazuh_config.resolve().is_relative_to(args.usb_root.resolve())):
            raise CheckError('CREDENTIALS_MUST_STAY_OUTSIDE_USB')
        sink = WazuhAuditSink.from_config(args.wazuh_config) if args.wazuh_config else None
        report = check_pipeline(url=args.url, request_id=args.request_id, expected=args.expect,
                                data_dir=args.data_dir, usb_root=args.usb_root, sink=sink,
                                wait_seconds=args.wait_seconds)
        print(json.dumps(report, sort_keys=True))
    except Exception as exc:
        # Never emit config, credential content or an HTTP traceback to reports.
        print(json.dumps({'error': str(exc) if isinstance(exc, CheckError) else 'PIPELINE_CHECK_FAILED'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
