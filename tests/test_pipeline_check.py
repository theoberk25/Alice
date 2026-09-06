"""Acceptance helper proves selected runtime records match SQL and Wazuh."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from cloud.wazuh_audit import document_id
from cloud.wazuh_worker import WazuhWorker
from dcamr.main import FirstLightRuntime, make_server
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from tests.test_wazuh_audit import MemorySink


class PipelineCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='alice-pipeline-check-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        release = build_release.build(root / 'bundle')
        trusted = bytes.fromhex((root / 'bundle/trust/manifest_public.hex').read_text().strip())
        self.seed = bytes.fromhex((root / 'bundle/client/term-agent-01-k1.seed').read_text().strip())
        server, self.esp = mock_esp.make_server()
        self.serve(server)
        self.data = root / 'runtime'
        self.runtime = FirstLightRuntime(release_dir=release, trusted_manifest_key=trusted,
                                        data_dir=self.data,
                                        esp_base_url=f'http://127.0.0.1:{server.server_port}')
        self.addCleanup(self.runtime.close)
        server = make_server(self.runtime, '127.0.0.1', 0)
        self.serve(server)
        self.url = f'http://127.0.0.1:{server.server_port}'
        envelope = build_envelope(self.seed, state='on', request_id='operator-check')
        self.runtime.handle_request(envelope)
        self.sink = MemorySink()
        worker = WazuhWorker(self.runtime.ledger, self.sink, self.runtime._lock)
        for _ in range(7): worker.step()

    def serve(self, server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def check(self, **kwargs):
        from lab.first_light.check_pipeline import check_pipeline
        return check_pipeline(url=self.url, request_id='operator-check',
                              data_dir=self.data, sink=self.sink, expected='ALLOW', **kwargs)

    def test_read_only_check_matches_all_three_stores_without_submission_or_delivery(self):
        before = list(self.runtime.iter_events())
        self.sink.calls.clear()
        report = self.check()
        self.assertEqual(report['events_verified'], 7)
        self.assertEqual(report['wazuh'], 'EXACT_MATCH')
        self.assertEqual(report['storage'], 'LOCAL_TEST')
        self.assertEqual(self.esp.commands, 1)
        self.assertEqual(list(self.runtime.iter_events()), before)
        self.assertTrue(all(method == 'GET' for method, _ in self.sink.calls))

    def test_remote_conflict_is_not_reported_as_success(self):
        from lab.first_light.check_pipeline import CheckError
        event = list(self.runtime.iter_events())[0]
        self.sink.docs[document_id(event)] = {'conflict': True}
        with self.assertRaises(CheckError): self.check()

    def test_missing_sql_record_is_not_reported_as_success(self):
        from lab.first_light.check_pipeline import CheckError
        import sqlite3
        # Separate test input, never modify the running ledger to simulate loss.
        other = Path(self.tmp.name) / 'other-data'
        other.mkdir()
        db = sqlite3.connect(other / 'ledger.sqlite')
        db.execute('CREATE TABLE events(event_id TEXT, canonical BLOB)')
        db.close()
        from lab.first_light.check_pipeline import check_pipeline
        with self.assertRaises(CheckError):
            check_pipeline(url=self.url, request_id='operator-check', data_dir=other,
                           sink=self.sink, expected='ALLOW')

    def test_cli_read_only_without_wazuh_is_explicitly_not_checked(self):
        result = subprocess.run([sys.executable, '-m', 'lab.first_light.check_pipeline',
                                 '--url', self.url, '--request-id', 'operator-check',
                                 '--data-dir', str(self.data), '--local-test-storage',
                                 '--expect', 'ALLOW'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['wazuh'], 'NOT_CHECKED')
        self.assertEqual(report['events_verified'], 7)
        self.assertEqual(self.esp.commands, 1)

    def test_denied_request_has_no_execution_and_is_verified_separately(self):
        from dataclasses import replace
        from lab.first_light.check_pipeline import check_pipeline
        self.runtime.release = replace(self.runtime.release, grants=())
        envelope = build_envelope(self.seed, state='off', request_id='denied-check')
        self.assertEqual(self.runtime.handle_request(envelope)[0], 403)
        worker = WazuhWorker(self.runtime.ledger, self.sink, self.runtime._lock)
        worker.step()
        worker.step()
        report = check_pipeline(url=self.url, request_id='denied-check', data_dir=self.data,
                                sink=self.sink, expected='DENY')
        self.assertEqual(report['events_verified'], 2)
        self.assertEqual(report['wazuh'], 'EXACT_MATCH')
        self.assertEqual(self.esp.commands, 1)

    def test_denial_after_assessment_is_also_a_valid_nonexecuting_chain(self):
        from dataclasses import replace
        from lab.first_light.check_pipeline import check_pipeline
        grant = replace(self.runtime.release.grants[0], approval_required=True)
        self.runtime.release = replace(self.runtime.release, grants=(grant,))
        code, response = self.runtime.handle_request(
            build_envelope(self.seed, state='off', request_id='review-required'))
        self.assertEqual((code, response['decision']), (403, 'DENY'))
        worker = WazuhWorker(self.runtime.ledger, self.sink, self.runtime._lock)
        for _ in range(3): worker.step()
        report = check_pipeline(url=self.url, request_id='review-required', data_dir=self.data,
                                sink=self.sink, expected='DENY')
        self.assertEqual(report['events_verified'], 3)
        self.assertEqual(self.esp.commands, 1)
