from copy import deepcopy
from http.client import BadStatusLine, IncompleteRead
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from cloud.wazuh_audit import (WazuhAuditSink, DeliveryError, INDEX, document, document_id,
                               sync_once)
from tests.test_audit_log import AuditFixture


class MemorySink(WazuhAuditSink):
    def __init__(self):
        self.docs = {}
        self.calls = []
        self.fail_get = False
        self.offline = False

    def probe(self):
        if self.offline:
            raise DeliveryError('TRANSPORT_UNAVAILABLE')

    def _request(self, method, path, body=None):
        self.calls.append((method, path))
        if self.offline:
            raise DeliveryError('TRANSPORT_UNAVAILABLE')
        identity = path.rsplit('/', 1)[1]
        if method == 'PUT':
            if identity in self.docs:
                return 409, {}
            self.docs[identity] = deepcopy(body)
            return 201, {'_id': identity, '_index': INDEX, 'result': 'created', '_shards': {'failed': 0}}
        if self.fail_get:
            raise DeliveryError('RECEIPT_UNAVAILABLE')
        return 200, {'found': True, '_id': identity, '_index': INDEX, '_source': deepcopy(self.docs[identity])}


class WazuhSyncTests(AuditFixture, unittest.TestCase):
    def prepare(self):
        event = self.ledger.append(self.event()).event
        self.ledger.seal()
        return event

    def test_exact_record_acknowledged_without_rewriting_event(self):
        event = self.prepare(); sink = MemorySink()
        report = sync_once(self.ledger, sink)
        self.assertEqual(report['acknowledged'], 1)
        self.assertEqual(self.ledger.pending(), [])
        self.assertEqual(self.ledger.read(), [event])
        self.assertEqual(sink.docs[document_id(event)]['event'], event)
        self.assertEqual(self.ledger.validate().event_count, 1)

    def test_retry_after_remote_commit_lost_receipt(self):
        event = self.prepare(); sink = MemorySink(); sink.fail_get = True
        self.assertEqual(sync_once(self.ledger, sink)['acknowledged'], 0)
        self.assertEqual(len(self.ledger.pending()), 1)
        self.reopen(); sink.fail_get = False
        self.assertEqual(sync_once(self.ledger, sink)['acknowledged'], 1)
        self.assertEqual(len(sink.docs), 1)
        self.assertEqual(self.ledger.read(), [event])

    def test_conflict_does_not_acknowledge_different_content(self):
        event = self.prepare(); sink = MemorySink()
        sink.docs[document_id(event)] = {'event': 'different'}
        report = sync_once(self.ledger, sink)
        self.assertEqual(report['errors'][0]['code'], 'REMOTE_CONTENT_CONFLICT')
        self.assertEqual(len(self.ledger.pending()), 1)
        self.assertEqual(sink.docs[document_id(event)], {'event': 'different'})

    def test_offline_preserves_retry_and_original(self):
        event = self.prepare(); sink = MemorySink(); sink.offline = True
        self.assertEqual(sync_once(self.ledger, sink)['acknowledged'], 0)
        self.reopen()
        self.assertEqual(self.ledger.pending()[0]['attempts'], 1)
        self.assertEqual(self.ledger.read(), [event])
        sink.offline = False
        self.assertEqual(sync_once(self.ledger, sink)['acknowledged'], 1)

    def test_outage_stops_batch_without_spending_other_attempts(self):
        for i in range(1, 4): self.ledger.append(self.event(f'event-{i}'))
        self.ledger.seal(); sink = MemorySink(); sink.offline = True
        report = sync_once(self.ledger, sink)
        self.assertEqual(report['scanned'], 1)
        self.assertEqual(len(sink.calls), 1)
        sink.offline = False
        self.assertEqual(sync_once(self.ledger, sink)['acknowledged'], 3)
        self.assertEqual(self.ledger.validate().event_count, 3)

    def test_acknowledged_replay_performs_no_network(self):
        self.prepare(); sink = MemorySink(); sync_once(self.ledger, sink)
        sink.calls.clear()
        self.assertEqual(sync_once(self.ledger, sink)['already_acknowledged'], 1)
        self.assertEqual(sink.calls, [])

    def test_unsealed_not_delivered(self):
        self.ledger.append(self.event()); sink = MemorySink()
        report = sync_once(self.ledger, sink)
        self.assertEqual(sink.calls, [])
        self.assertEqual(report['errors'][0]['code'], 'UNSEALED_OR_DESTINATION_CONFLICT')

    def test_existing_usb_destination_not_overwritten(self):
        self.prepare(); self.ledger.queue('event-1', 'usb:demo'); sink = MemorySink()
        self.assertEqual(sync_once(self.ledger, sink)['acknowledged'], 0)
        self.assertEqual(self.ledger.pending()[0]['destination'], 'usb:demo')
        self.assertEqual(sink.calls, [])

    def test_storage_loss_after_remote_write_does_not_ack(self):
        self.prepare(); sink = MemorySink(); calls = 0
        def guard():
            nonlocal calls
            calls += 1
            if calls == 3: raise OSError('removed')
        with self.assertRaises(OSError): sync_once(self.ledger, sink, check_storage=guard)
        self.assertEqual(len(sink.docs), 1)
        self.assertEqual(len(self.ledger.pending()), 1)

    def test_bounded_page_cursor(self):
        for i in range(1, 4): self.ledger.append(self.event(f'event-{i}'))
        self.ledger.seal(); sink = MemorySink()
        first = sync_once(self.ledger, sink, limit=2)
        second = sync_once(self.ledger, sink, after=first['next_after'], limit=2)
        self.assertEqual((first['scanned'],second['scanned']), (2,1))
        self.assertEqual(len(sink.docs), 3)

    def test_invalid_event_rejected_before_network(self):
        event = self.prepare(); event['event_hash'] = '0'*64; sink = MemorySink()
        with self.assertRaises(ValueError): sink.deliver(event)
        self.assertEqual(sink.calls, [])

    def test_document_identity_binds_node_ledger_and_event(self):
        event = self.prepare()
        for key in ('event_id', 'ledger_id', 'node_id'):
            changed = dict(event); changed[key] += '-different'
            self.assertNotEqual(document_id(event), document_id(changed))

    def test_config_rejects_plaintext_transport(self):
        with self.assertRaises(ValueError):
            WazuhAuditSink(url='http://localhost:9200',username='u',password='p',ca_file='unused')

    def test_config_rejects_public_credentials_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json';path.write_text('{}');path.chmod(0o644)
            with self.assertRaises(ValueError):WazuhAuditSink.from_config(path)

    def test_interrupted_http_exchange_is_retryable_delivery_error(self):
        # Fault injection below the real HTTP adapter: neither protocol setup
        # failure nor partial response body should escape into STOPPED_ERROR.
        sink = object.__new__(WazuhAuditSink)
        sink.url, sink.authorization, sink.timeout = 'https://example.test:9200', 'test-only', 1

        class InterruptedResponse:
            code = 201
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): raise IncompleteRead(b'{', 40)

        for fail_open in (False, True):
            with self.subTest(fail_open=fail_open):
                def open_response(*args, **kwargs):
                    if fail_open: raise BadStatusLine('interrupted')
                    return InterruptedResponse()
                sink.opener = SimpleNamespace(open=open_response)
                with self.assertRaises(DeliveryError) as caught:
                    sink._request('GET', '/test')
                self.assertEqual(caught.exception.code, 'TRANSPORT_UNAVAILABLE')

    def test_malformed_create_receipt_rejected_then_exact_replay_recovers(self):
        event = self.prepare()
        for shards in (None, [], 'invalid', {'failed': False}, {'failed': 0.0}):
            with self.subTest(shards=shards):
                sink = MemorySink()
                original = sink._request
                def malformed(method, path, body=None):
                    status, reply = original(method, path, body)
                    if method == 'PUT' and status == 201:
                        reply['_shards'] = shards
                    return status, reply
                sink._request = malformed
                with self.assertRaises(DeliveryError) as caught:
                    sink.deliver(event)
                self.assertEqual(caught.exception.code, 'INVALID_CREATE_RECEIPT')
                # A write may have committed before the invalid receipt. Retry
                # must verify the existing exact document, never create another.
                sink._request = original
                self.assertEqual(sink.deliver(event).event_hash, event['event_hash'])
                self.assertEqual(len(sink.docs), 1)
                self.assertEqual(self.ledger.read(), [event])
