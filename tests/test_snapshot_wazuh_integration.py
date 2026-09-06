"""Merged runtime: SQL inputs, live HTTP feed and one owner-integrated uploader.

Controller and enterprise HTTP are explicitly simulated; runtime, SQL ledger,
worker, receipt validation and dashboard bridge projection are real components.
"""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from cloud.wazuh_audit import document_id
from cloud.wazuh_worker import WazuhWorker
from dcamr.main import FirstLightRuntime, make_server
from dcamr.packages.release_snapshot import publish_snapshot
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from services.runtime_feed import validate_page
from tests.test_wazuh_audit import MemorySink


class SnapshotWazuhIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='alice-snapshot-wazuh-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        release = build_release.build(root / 'bundle')
        trust = bytes.fromhex((root / 'bundle/trust/manifest_public.hex').read_text().strip())
        self.seed = bytes.fromhex((root / 'bundle/client/term-agent-01-k1.seed').read_text().strip())
        snapshot = root / 'inputs.sqlite'
        publish_snapshot(release, snapshot, trust)
        esp_server, self.esp = mock_esp.make_server()
        self.serve(esp_server)
        self.options = dict(release_dir=snapshot, release_snapshot=True,
                            trusted_manifest_key=trust, data_dir=root / 'runtime',
                            esp_base_url=f'http://127.0.0.1:{esp_server.server_port}')
        self.runtime = FirstLightRuntime(**self.options, initialize_ledger=True)
        self.addCleanup(lambda: self.runtime.close())

    def serve(self, server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def test_slow_upload_does_not_block_requests_or_live_feed_and_restart_skips_acks(self):
        first = build_envelope(self.seed, state='on')
        self.assertEqual(self.runtime.handle_request(first)[0], 200)
        original = list(self.runtime.iter_events())
        sink = MemorySink()
        entered, release_network = threading.Event(), threading.Event()
        deliver = sink.deliver

        def blocked_delivery(event):
            entered.set()
            if not release_network.wait(5):
                raise RuntimeError('test did not release simulated network')
            return deliver(event)

        sink.deliver = blocked_delivery
        self.addCleanup(release_network.set)
        with patch('cloud.wazuh_audit.WazuhAuditSink.from_config', return_value=sink):
            self.runtime.start_wazuh_sync('test-only-config')
        self.assertTrue(entered.wait(2))
        server = make_server(self.runtime, '127.0.0.1', 0)
        self.serve(server)
        base = f'http://127.0.0.1:{server.server_port}'
        request = Request(base + '/request', method='POST',
                          data=json.dumps(build_envelope(self.seed, state='off')).encode(),
                          headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=2) as response:
                self.assertEqual(json.load(response)['execution'], 'COMPLETED')
            with urlopen(base + '/events', timeout=2) as response:
                page = json.load(response)
            self.assertEqual(len(page['events']), 14)
            self.assertEqual(page['events'][:7], original)
            validate_page(page, 0)  # Same validation used by the dashboard bridge.
            with urlopen(base + '/sync-status', timeout=2) as response:
                self.assertEqual(json.load(response)['state'], 'DELIVERING')
        finally:
            release_network.set()
        deadline = time.monotonic() + 6
        while self.runtime.sync_worker.status()['delivered'] < 14 and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertEqual(self.runtime.sync_worker.status()['delivered'], 14)
        self.runtime.sync_worker.close()
        events = list(self.runtime.iter_events())
        self.assertEqual(self.runtime.ledger.pending(), [])
        for event in events:
            self.assertEqual(sink.docs[document_id(event)]['event'], event)
        self.runtime.close()
        self.runtime = FirstLightRuntime(**self.options)
        self.assertTrue(self.runtime.handle_request(first)[1]['idempotent_replay'])
        sink.calls.clear()
        WazuhWorker(self.runtime.ledger, sink, self.runtime._lock).step()
        self.assertEqual(sink.calls, [])
        self.assertEqual(list(self.runtime.iter_events()), events)
        self.assertEqual(self.esp.commands, 2)

    def test_wazuh_outage_keeps_new_sql_runtime_events_and_recovers_after_restart(self):
        first = build_envelope(self.seed, state='on')
        self.runtime.handle_request(first)
        sink = MemorySink()
        sink.offline = True
        worker = WazuhWorker(self.runtime.ledger, sink, self.runtime._lock)
        self.assertEqual(worker.step(), 60)
        self.assertEqual(self.runtime.ledger.pending()[0]['attempts'], 1)
        self.assertEqual(self.runtime.handle_request(build_envelope(self.seed, state='off'))[0], 200)
        before = list(self.runtime.iter_events())
        for _ in range(70):
            worker.step()
        self.assertEqual(self.runtime.ledger.pending()[0]['attempts'], 1)
        self.runtime.close()
        self.runtime = FirstLightRuntime(**self.options)
        sink.offline = False
        worker = WazuhWorker(self.runtime.ledger, sink, self.runtime._lock)
        for _ in before:
            worker.step()
        self.assertEqual(worker.status()['delivered'], 14)
        self.assertEqual(self.runtime.ledger.pending(), [])
        self.assertEqual(list(self.runtime.iter_events()), before)
        self.assertTrue(self.runtime.handle_request(first)[1]['idempotent_replay'])
        self.assertEqual(self.esp.commands, 2)

    def test_serial_selection_keeps_snapshot_feed_wazuh_and_restart_replay(self):
        from lab.first_light.mock_esp_serial import make_loopback
        from dcamr.enforcement.serial_light_controller import SerialLightController
        self.runtime.close()
        options = dict(self.options, esp_base_url=None, esp_serial='test-serial-port')
        self.runtime = FirstLightRuntime(**options)
        self.assertIsInstance(self.runtime.controller, SerialLightController)
        transport, serial_node = make_loopback()
        envelope = build_envelope(self.seed, state='on')
        with patch.object(self.runtime.controller, '_open', return_value=transport):
            self.assertEqual(self.runtime.handle_request(envelope)[1]['execution'], 'COMPLETED')
        events = list(self.runtime.iter_events())
        validate_page({'events': events}, 0)
        self.assertEqual(len(events), 7)
        self.assertTrue(all(e['provenance']['snapshot']['sha256'] for e in events))
        self.assertEqual(events[-1]['detail']['origin'], 'ACTUATOR_FEEDBACK')
        sink = MemorySink()
        worker = WazuhWorker(self.runtime.ledger, sink, self.runtime._lock)
        for _ in events: worker.step()
        self.assertEqual(self.runtime.ledger.pending(), [])
        for event in events:
            self.assertEqual(sink.docs[document_id(event)]['event'], event)
        self.runtime.close()
        self.runtime = FirstLightRuntime(**options)
        self.assertTrue(self.runtime.handle_request(envelope)[1]['idempotent_replay'])
        self.assertEqual(list(self.runtime.iter_events()), events)
        self.assertEqual(serial_node.commands, 1)
        self.assertEqual(self.esp.commands, 0)  # HTTP never substituted for serial.
