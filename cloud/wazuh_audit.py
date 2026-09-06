"""Bounded create-only delivery of canonical ledger events to Wazuh's indexer.

Owns no ledger/database. Call sync_once only from the single ledger owner, or
with the runtime stopped. Delivery acknowledgements do not imply execution or
semantic reconciliation. See docs/integration/wazuh-audit-sync.md.
"""
from dataclasses import dataclass
from hashlib import sha256
from http.client import HTTPException
import base64
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler

from dcamr.audit.audit_log import LifecycleError, MAX_ATTEMPTS
from dcamr.audit.event_contract import canonical_bytes, validate_event

MAX_RESPONSE = 128 * 1024
INDEX = 'alice-ledger-v1'
DESTINATION = 'wazuh-ledger-v1'


class DeliveryError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate key')
        out[key] = value
    return out


def document(event):
    validate_event(event)
    return {'schema_version': 'alice-ledger-delivery-v1',
            'ledger_id': event['ledger_id'], 'node_id': event['node_id'],
            'event_id': event['event_id'], 'event_hash': event['event_hash'],
            'sequence': event['sequence'], 'event_type': event['event_type'],
            'request_id': event['correlation']['request_id'], 'event': event}


def document_id(event):
    return sha256(canonical_bytes([event['node_id'], event['ledger_id'], event['event_id']])).hexdigest()


@dataclass(frozen=True)
class Receipt:
    event_hash: str
    receipt_ref: str
    receipt_sha256: str


class WazuhAuditSink:
    destination = DESTINATION

    def __init__(self, *, url, username, password, ca_file, timeout=5):
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or not parsed.port
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/')):
            raise ValueError('Explicit HTTPS indexer origin required')
        if not username or ':' in username or not password or any(c in username+password for c in '\r\n'):
            raise ValueError('Invalid indexer credentials')
        if type(timeout) not in (int, float) or not 0 < timeout <= 10:
            raise ValueError('Timeout must be at most ten seconds')
        self.url, self.timeout = url.rstrip('/'), timeout
        self.authorization = 'Basic ' + base64.b64encode((username+':'+password).encode()).decode()
        context = ssl.create_default_context(cafile=str(ca_file))
        self.opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=context))

    @classmethod
    def from_config(cls, path):
        path = Path(path)
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError('Sync credential file must be private (0600) and not a symlink')
        if path.stat().st_size > 8192:
            raise ValueError('Sync configuration too large')
        config = json.loads(path.read_text(), object_pairs_hook=unique_object)
        if set(config) != {'url', 'username', 'password', 'ca_file'}:
            raise ValueError('Unsupported sync configuration')
        if not Path(config['ca_file']).is_absolute():
            raise ValueError('CA file must be an absolute path')
        return cls(**config)

    def _request(self, method, path, body=None):
        request = Request(self.url + path, data=canonical_bytes(body) if body is not None else None,
                          method=method, headers={'Authorization': self.authorization,
                                                  'Content-Type': 'application/json'})
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except HTTPError as error:
            response = error
        except (URLError, TimeoutError, OSError, HTTPException):
            raise DeliveryError('TRANSPORT_UNAVAILABLE') from None
        try:
            with response:
                raw = response.read(MAX_RESPONSE + 1)
                status = response.code
            if len(raw) > MAX_RESPONSE:
                raise ValueError
            payload = json.loads(raw, object_pairs_hook=unique_object,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if type(payload) is not dict:
                raise ValueError
            return status, payload
        except (OSError, HTTPException):
            raise DeliveryError('TRANSPORT_UNAVAILABLE') from None
        except ValueError:
            raise DeliveryError('INVALID_INDEXER_RESPONSE') from None

    def probe(self):
        """Authenticated TLS reachability without spending a ledger delivery attempt."""
        status, _ = self._request('GET', f'/{INDEX}/_doc/alice-sync-connectivity-check')
        if status not in (200, 404):
            raise DeliveryError('INDEXER_AUTHORIZATION' if status in (401, 403) else 'INDEXER_UNAVAILABLE')

    def deliver(self, event):
        body = document(event)
        identity = document_id(event)
        status, created = self._request('PUT', f'/{INDEX}/_create/{identity}', body)
        if status not in (201, 409):
            raise DeliveryError('INDEXER_AUTHORIZATION' if status in (401, 403) else 'INDEXER_WRITE_FAILED')
        shards = created.get('_shards')
        if status == 201 and (created.get('_id') != identity or created.get('_index') != INDEX
                              or created.get('result') != 'created' or type(shards) is not dict
                              or type(shards.get('failed')) is not int or shards['failed'] != 0):
            raise DeliveryError('INVALID_CREATE_RECEIPT')
        return self.verify_stored(event)

    def verify_stored(self, event):
        """Read-only exact-content verification; never uploads or acknowledges."""
        body = document(event)
        identity = document_id(event)
        # 409 can mean a conflicting document, never unconditional success.
        # GET is real-time; do not depend on search refresh to verify storage.
        status, stored = self._request('GET', f'/{INDEX}/_doc/{identity}')
        if (status != 200 or stored.get('found') is not True or stored.get('_id') != identity
                or stored.get('_index') != INDEX):
            raise DeliveryError('RECEIPT_UNAVAILABLE')
        try:
            matches = canonical_bytes(stored.get('_source')) == canonical_bytes(body)
        except ValueError:
            matches = False
        if not matches:
            raise DeliveryError('REMOTE_CONTENT_CONFLICT')
        receipt = {'destination': self.destination, 'index': INDEX, 'document_id': identity,
                   'event_hash': event['event_hash'], 'document_sha256': sha256(canonical_bytes(body)).hexdigest()}
        return Receipt(event['event_hash'], 'wazuh-'+identity, sha256(canonical_bytes(receipt)).hexdigest())


def sync_once(ledger, sink, *, after=0, limit=16, check_storage=lambda: None):
    """Scan at most 64 events, queue sealed ones and deliver a bounded batch.

    One owner, one destination per existing outbox event. Caller supplies a USB
    guard on physical storage. Restart from zero to revisit any failed deliveries;
    the returned cursor only supports draining a single pass, not durable ack.
    No automatic retries: caller schedules/backoffs between passes. Failure leaves
    exact events queued; attempt exhaustion or destination conflicts are surfaced.
    """
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError('Batch limit must be 1..64')
    result = {'scanned': 0, 'acknowledged': 0, 'already_acknowledged': 0,
              'errors': [], 'next_after': after}
    check_storage()
    events = ledger.read(after=after, limit=limit)
    for event in events:
        check_storage()
        result['scanned'] += 1
        result['next_after'] = event['sequence']
        try:
            ledger.queue(event['event_id'], sink.destination)
        except LifecycleError:
            result['errors'].append({'event_id': event['event_id'], 'code': 'UNSEALED_OR_DESTINATION_CONFLICT'})
            continue
        pending = ledger.pending(after=event['sequence']-1, limit=1)
        if not pending or pending[0]['event_id'] != event['event_id']:
            result['already_acknowledged'] += 1
            continue
        if pending[0]['attempts'] >= MAX_ATTEMPTS:
            result['errors'].append({'event_id': event['event_id'], 'code': 'ATTEMPT_BUDGET_EXHAUSTED'})
            continue
        # Persist the attempt before network I/O, including crash/lost-response cases.
        ledger.record_attempt(event['event_id'], retry_after_ms=60000, error_code='DELIVERY_UNCONFIRMED')
        try:
            receipt = sink.deliver(event)
        except DeliveryError as error:
            result['errors'].append({'event_id': event['event_id'], 'code': error.code})
            if error.code in ('TRANSPORT_UNAVAILABLE', 'INDEXER_AUTHORIZATION', 'INDEXER_WRITE_FAILED'):
                break  # Global outage/configuration failure: do not exhaust a whole batch.
            continue
        check_storage()
        ledger.acknowledge(event['event_id'], destination=sink.destination,
                           event_hash=receipt.event_hash, receipt_ref=receipt.receipt_ref,
                           receipt_sha256=receipt.receipt_sha256)
        result['acknowledged'] += 1
    # Cover delivery transitions with the existing checkpoint signer; no event edits.
    if events:
        check_storage()
        ledger.seal()
    return result
