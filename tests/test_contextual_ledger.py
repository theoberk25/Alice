"""Real model-to-ledger component replay; no live sensor or execution claims."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tests.test_contextual_model import HAS_TRAINING_DEPS


@unittest.skipUnless(HAS_TRAINING_DEPS, 'install requirements-anomaly-training.txt for replay')
class ContextualLedgerTests(unittest.TestCase):
    def test_assessments_survive_sealing_restart_and_retry_with_exact_evidence(self):
        from lab.replay_contextual_ledger import replay

        with tempfile.TemporaryDirectory() as directory:
            report = replay(Path(directory))
            self.assertEqual(report['cases'], {
                'pre-ok': 'OK', 'post-ok': 'OK', 'untrained': 'UNAVAILABLE',
                'unseen-context': 'UNAVAILABLE', 'missing-telemetry': 'UNAVAILABLE',
                'invalid-input': 'INVALID_INPUT',
            })
            with closing(sqlite3.connect(Path(directory) / 'ledger.sqlite')) as db:
                rows = db.execute('SELECT canonical FROM events ORDER BY sequence').fetchall()
                self.assertEqual(len(rows), 6)
                self.assertEqual(db.execute('SELECT count(*) FROM checkpoints').fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM outbox WHERE state='QUEUED'").fetchone()[0], 6)
                for (raw,) in rows:
                    recorded = json.loads(raw)
                    case = recorded['event_id']
                    original = (Path(directory) / f'{case}.assessment.json').read_bytes()
                    assessment = json.loads(original)
                    detail = recorded['detail']
                    compact = detail['contextual']
                    self.assertEqual(detail['status'], report['cases'][case])
                    self.assertEqual(detail['result'], assessment['result'])
                    self.assertEqual(compact['assessment_evidence']['sha256'], sha256(original).hexdigest())
                    self.assertEqual(recorded['provenance']['evidence'][0]['sha256'], sha256(original).hexdigest())
                    self.assertEqual(compact['dispatch']['request_id'], recorded['correlation']['request_id'])
                    self.assertEqual(compact['dispatch']['input_sha256'], sha256(
                        (Path(directory) / f'{case}.input.json').read_bytes()).hexdigest())
                    self.assertEqual(recorded['correlation']['request_sha256'], sha256(
                        (Path(directory) / f'{case}.request.json').read_bytes()).hexdigest())
                    for key in ('raw_score', 'score', 'factors'):
                        self.assertNotIn(key, detail)
                        self.assertNotIn(key, compact)
                    if detail['status'] == 'OK':
                        self.assertIsInstance(assessment['score'], float)
                        self.assertTrue(assessment['factors'])
                        self.assertEqual(compact['model_fingerprint'], assessment['model_fingerprint'])
                    else:
                        self.assertEqual(detail['result'], 'UNKNOWN')
                        self.assertIsNone(assessment['score'])
                    if case in ('invalid-input', 'missing-telemetry'):
                        self.assertIsNone(compact['parsed']['request_id'])
                        self.assertTrue(compact['dispatch']['request_id'])
                    self.assertEqual(recorded['authority']['execution_owner'], 'UNKNOWN')
                    self.assertIsNone(recorded['provenance']['model']['sha256'])
