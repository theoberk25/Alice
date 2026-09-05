"""Durability tests use real temporary SQLite files; no hardware acceptance."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import json
import os
from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dcamr.audit import audit_log


class AuditFixture:
    def setUp(self):
        self.assertTrue(hasattr(audit_log, 'AuditLog'), 'durable AuditLog is missing')
        from dcamr.audit.signing import Ed25519Signer, Ed25519Verifier, TrustStore
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from tests.audit_fixtures import event, clock
        self.event, self.clock = event, clock
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ledger.sqlite'
        self.signer = Ed25519Signer(bytes(range(32)), 'key-1')
        public = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.trust = TrustStore({('ed25519', 'key-1'): Ed25519Verifier(public)})
        self.kwargs = dict(signer=self.signer, trust=self.trust, clock=self.clock)
        self.ledger = audit_log.AuditLog.initialize(self.path, ledger_id='ledger-1', node_id='pi-1',
            quota_bytes=8*1024*1024, reserve_bytes=256*1024, **self.kwargs)
        self.addCleanup(lambda: self.ledger.close())

    def reopen(self, **kwargs):
        self.ledger.close()
        self.ledger = audit_log.AuditLog.open(self.path, **dict(self.kwargs, **kwargs))
        return self.ledger

class AuditLogTests(AuditFixture, unittest.TestCase):
    def test_append_is_durable_and_retry_recovers_original_bytes(self):
        payload = self.event()
        first = self.ledger.append(payload)
        self.assertTrue(first.persisted)
        self.assertEqual(first.covered_sequence, 0)
        self.assertEqual(first.event['sequence'], 1)
        self.assertEqual(first.event['previous_hash'], '0'*64)
        self.reopen()
        self.assertEqual(self.ledger.append(payload).event, first.event)
        self.assertEqual(len(self.ledger.read()), 1)
        self.assertEqual(self.ledger.append(self.event('event-2')).event['sequence'], 2)

    def test_caller_and_return_mutation_do_not_change_history(self):
        payload = self.event()
        original = self.ledger.append(payload).event
        payload['event_id'] = 'changed'
        original['attribution'].clear()
        self.assertEqual(self.ledger.read()[0]['event_id'], 'event-1')
        self.assertTrue(self.ledger.read()[0]['attribution'])

    def test_conflicting_retry_rejected_without_new_sequence(self):
        self.ledger.append(self.event())
        payload = self.event()
        payload['correlation']['correlation_id'] = 'different'
        with self.assertRaises(audit_log.IdempotencyConflict):
            self.ledger.append(payload)
        self.assertEqual(len(self.ledger.read()), 1)

    def test_explicit_initialize_never_replaces_and_open_never_creates(self):
        with self.assertRaises(audit_log.StorageError):
            audit_log.AuditLog.open(self.path.with_name('missing.sqlite'), **self.kwargs)
        with self.assertRaises(audit_log.StorageError):
            audit_log.AuditLog.initialize(self.path, ledger_id='other', node_id='pi-1',
                quota_bytes=1024*1024, reserve_bytes=128*1024, **self.kwargs)
        self.assertEqual(self.ledger.validate().event_count, 0)

    def test_unknown_and_backward_time_preserve_sequence(self):
        self.ledger.append(self.event())
        old = dict(self.clock(), recorded_at='2020-01-01T00:00:00Z', confidence='UNCERTAIN')
        self.reopen(clock=lambda: old)
        self.ledger.append(self.event('event-2'))
        absent = dict(old, recorded_at=None, confidence='UNAVAILABLE', boot_id='boot-2', monotonic_ns=0)
        self.reopen(clock=lambda: absent)
        self.ledger.append(self.event('event-3'))
        self.assertEqual([e['sequence'] for e in self.ledger.read()], [1, 2, 3])
        self.assertIsNone(self.ledger.read()[2]['time']['recorded_at'])

    def test_competing_connections_allocate_contiguous_sequences(self):
        def append(i):
            other = audit_log.AuditLog.open(self.path, **self.kwargs)
            try:
                return other.append(self.event(f'event-{i}')).event['sequence']
            finally:
                other.close()
        with ThreadPoolExecutor(max_workers=3) as pool:
            sequences = list(pool.map(append, range(1, 13)))
        self.assertEqual(sorted(sequences), list(range(1, 13)))
        self.assertEqual(self.reopen().validate().event_count, 12)

    def test_history_update_and_delete_are_rejected(self):
        self.ledger.append(self.event())
        with closing(sqlite3.connect(self.path)) as db, db:
            for sql in ('DELETE FROM events', "UPDATE events SET canonical=x'00'"):
                with self.assertRaises(sqlite3.DatabaseError):
                    db.execute(sql)
        self.assertEqual(self.reopen().validate().event_count, 1)

    def test_tamper_is_rejected_on_restart_without_repair(self):
        self.ledger.append(self.event())
        self.ledger.close()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER events_no_update')
            db.execute("UPDATE events SET canonical=x'7b7d'")
        before = self.path.read_bytes()
        with self.assertRaises(audit_log.IntegrityError):
            audit_log.AuditLog.open(self.path, **self.kwargs)
        self.assertEqual(self.path.read_bytes(), before)

    def test_periodic_and_explicit_sealing_coverage(self):
        for i in range(1, 65):
            result = self.ledger.append(self.event(f'event-{i}'))
        self.assertEqual(result.covered_sequence, 64)
        self.assertIsNone(result.sealing_error)
        self.assertEqual(self.reopen().validate().covered_sequence, 64)
        self.ledger.append(self.event('event-65'))
        checkpoint = self.ledger.seal()
        self.assertEqual(checkpoint['body']['covered_sequence'], 65)
        self.assertEqual(self.reopen(anchor=checkpoint).validate().covered_sequence, 65)

    def test_signing_failure_retains_committed_event_and_blocks_readiness(self):
        for i in range(1, 64):
            self.ledger.append(self.event(f'event-{i}'))
        class Broken:
            algorithm_id = 'ed25519'
            key_id = 'key-1'
            def sign(self, message):
                raise RuntimeError('private signer detail')
        self.reopen(signer=Broken())
        result = self.ledger.append(self.event('event-64'))
        self.assertTrue(result.persisted)
        self.assertEqual(result.covered_sequence, 0)
        self.assertEqual(result.sealing_error, 'SEALING_FAILED')
        self.assertFalse(self.ledger.readiness()['ready'])
        self.assertEqual(len(self.ledger.read()), 64)
        self.reopen()
        self.ledger.seal()
        self.assertTrue(self.ledger.readiness()['ready'])
        self.assertEqual(self.ledger.validate().covered_sequence, 64)

    def test_independent_anchor_detects_whole_store_rollback(self):
        self.ledger.append(self.event())
        self.ledger.seal()
        snapshot = self.path.read_bytes()
        self.ledger.append(self.event('event-2'))
        anchor = self.ledger.seal()
        self.ledger.close()
        self.path.write_bytes(snapshot)
        with self.assertRaises(audit_log.IntegrityError):
            audit_log.AuditLog.open(self.path, anchor=anchor, **self.kwargs)
        self.ledger = audit_log.AuditLog.open(self.path, **self.kwargs)
        self.assertEqual(self.ledger.validate().event_count, 1)

    def test_missing_storage_never_reports_durable_success(self):
        self.ledger.append(self.event())
        self.path.unlink()
        with self.assertRaises(audit_log.StorageError):
            self.ledger.append(self.event('event-2'))
        self.assertFalse(self.ledger.readiness()['ready'])
        self.assertFalse(self.path.exists())

    def test_usb_removal_does_not_remove_local_history(self):
        usb = Path(self.temp.name) / 'removable'
        usb.mkdir()
        (usb / 'cache').write_text('fixture')
        self.ledger.append(self.event())
        (usb / 'cache').unlink()
        usb.rmdir()
        self.assertEqual(self.reopen().validate().event_count, 1)
        self.assertTrue(self.ledger.append(self.event('event-2')).persisted)

    def test_quota_exhaustion_preserves_reserve_and_no_partial_event(self):
        self.ledger.close()
        self.path.unlink()
        self.ledger = audit_log.AuditLog.initialize(self.path, ledger_id='ledger-1', node_id='pi-1',
            quota_bytes=512*1024, reserve_bytes=128*1024, **self.kwargs)
        for i in range(1000):
            try:
                self.ledger.append(self.event(f'event-{i}'))
            except audit_log.CapacityError:
                break
        else:
            self.fail('quota never exhausted')
        count = self.ledger.validate().event_count
        with self.assertRaises(audit_log.CapacityError):
            self.ledger.append(self.event('beyond-quota'))
        self.assertEqual(self.ledger.validate().event_count, count)
        with self.assertRaises(audit_log.LedgerInputError):
            self.ledger.append(self.event('misuse'), recovery=True)
        result = self.ledger.append(self.event('failure', 'RECORDER_FAILURE'), recovery=True)
        self.assertTrue(result.persisted)
        for j in range(1000):
            try:
                self.ledger.append(self.event(f'failure-{j}', 'RECORDER_FAILURE'), recovery=True)
            except audit_log.CapacityError:
                break
        else:
            self.fail('reserve never exhausted')
        self.assertFalse(self.ledger.readiness()['ready'])

    def test_io_failure_rolls_back_event_and_outbox(self):
        with patch('dcamr.audit.audit_log.shutil.disk_usage', side_effect=OSError('private storage path')):
            with self.assertRaises(audit_log.StorageError):
                self.ledger.append(self.event())
        self.assertEqual(self.reopen().validate().event_count, 0)
        self.assertEqual(self.ledger.pending(), [])

    def test_batches_are_bounded(self):
        for limit in (0, 65, True, -1):
            with self.assertRaises(audit_log.LedgerInputError):
                self.ledger.read(limit=limit)

    def test_crash_after_committed_append_recovers_retry_identity(self):
        self.ledger.close()
        code = '''
import os, sys
from dcamr.audit.audit_log import AuditLog
from dcamr.audit.signing import Ed25519Signer, TrustStore
from tests.audit_fixtures import event, clock
ledger = AuditLog.open(sys.argv[1], signer=Ed25519Signer(bytes(range(32)), 'key-1'), trust=TrustStore({}), clock=clock)
ledger.append(event())
os._exit(23)
'''
        child = subprocess.run([sys.executable, '-c', code, str(self.path)], capture_output=True)
        self.assertEqual(child.returncode, 23, child.stderr.decode())
        self.ledger = audit_log.AuditLog.open(self.path, **self.kwargs)
        self.assertEqual(self.ledger.append(self.event()).event['sequence'], 1)
        self.assertEqual(self.ledger.validate().event_count, 1)

    def test_transaction_failure_never_leaves_an_orphan_event(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(audit_log.StorageError):
            self.ledger.append(self.event())
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM transitions').fetchone()[0], 0)
            db.execute('DROP TRIGGER fail_outbox')
        self.assertEqual(self.reopen().validate().event_count, 0)

    def test_failed_checkpoint_transaction_preserves_local_unsealed_event(self):
        self.ledger.append(self.event())
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER fail_checkpoint BEFORE INSERT ON checkpoints BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(audit_log.StorageError):
            self.ledger.seal()
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT count(*) FROM checkpoints').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT state FROM outbox').fetchone()[0], 'LOCAL')
            db.execute('DROP TRIGGER fail_checkpoint')
        self.assertEqual(self.reopen().validate().event_count, 1)
        self.assertEqual(self.ledger.seal()['body']['covered_sequence'], 1)

    def test_existing_checkpoint_rejects_unknown_historical_key(self):
        from dcamr.audit.signing import TrustStore
        self.ledger.append(self.event())
        self.ledger.seal()
        self.ledger.close()
        with self.assertRaises(audit_log.IntegrityError):
            audit_log.AuditLog.open(self.path, **dict(self.kwargs, trust=TrustStore({})))

    def test_restored_trigger_does_not_hide_changed_event_bytes(self):
        self.ledger.append(self.event())
        self.ledger.close()
        with closing(sqlite3.connect(self.path)) as db, db:
            trigger = db.execute("SELECT sql FROM sqlite_master WHERE name='events_no_update'").fetchone()[0]
            db.execute('DROP TRIGGER events_no_update')
            raw = db.execute('SELECT canonical FROM events').fetchone()[0]
            db.execute('UPDATE events SET canonical=?', (raw.replace(b'RECEIVED', b'ADMITTED'),))
            db.execute(trigger)
        with self.assertRaises(audit_log.IntegrityError):
            audit_log.AuditLog.open(self.path, **self.kwargs)

    def test_runtime_projection_tamper_prevents_idempotent_success(self):
        payload = self.event()
        self.ledger.append(payload)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE outbox SET projection=x'7b7d'")
        with self.assertRaises(audit_log.IntegrityError):
            self.ledger.append(payload)

    def test_crash_during_transaction_recovers_without_partial_row(self):
        self.ledger.close()
        code = '''
import os, sqlite3, sys
c=sqlite3.connect(sys.argv[1], isolation_level=None)
c.execute('PRAGMA synchronous=FULL')
c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO events VALUES (1,'partial',x'7b7d',x'7b7d')")
os._exit(24)
'''
        child = subprocess.run([sys.executable, '-c', code, str(self.path)], capture_output=True)
        self.assertEqual(child.returncode, 24, child.stderr.decode())
        self.ledger = audit_log.AuditLog.open(self.path, **self.kwargs)
        self.assertEqual(self.ledger.validate().event_count, 0)
        self.assertEqual(self.ledger.append(self.event()).event['sequence'], 1)

    def test_failed_partial_seal_remains_blocked_after_restart(self):
        class Broken:
            algorithm_id = 'ed25519'
            key_id = 'key-1'
            def sign(self, message):
                raise RuntimeError('signer unavailable')
        self.ledger.append(self.event())
        self.reopen(signer=Broken())
        with self.assertRaises(audit_log.SealingError):
            self.ledger.seal()
        self.reopen()
        self.assertFalse(self.ledger.readiness()['ready'])
        self.ledger.seal()
        self.assertTrue(self.ledger.readiness()['ready'])

    def test_full_filesystem_reports_blocked_readiness(self):
        from collections import namedtuple
        Usage = namedtuple('Usage', 'total used free')
        with patch('dcamr.audit.audit_log.shutil.disk_usage', return_value=Usage(100,100,0)):
            with self.assertRaises(audit_log.CapacityError):
                self.ledger.append(self.event())
            self.assertFalse(self.ledger.readiness()['ready'])
            self.assertFalse(self.ledger.readiness()['capacity_available'])
