"""Outbox bookkeeping never sends a command or proves execution."""
from contextlib import closing
import sqlite3
import unittest
from tests.test_audit_log import AuditFixture
from dcamr.audit import audit_log


class OutboxTests(AuditFixture, unittest.TestCase):
    # Inherit the real database fixture; only new tests are collected here.
    def test_unsigned_records_cannot_queue(self):
        self.ledger.append(self.event())
        with self.assertRaises(audit_log.LifecycleError):
            self.ledger.queue('event-1', 'enterprise')
        self.assertEqual(self.ledger.pending(), [])

    def test_lost_ack_and_restart_keep_identical_retryable_event(self):
        original = self.ledger.append(self.event()).event
        self.ledger.seal()
        self.ledger.queue('event-1', 'enterprise')
        self.ledger.record_attempt('event-1', retry_after_ms=1000, error_code=None)
        first = self.ledger.pending()[0]
        self.assertEqual((first['state'], first['attempts']), ('QUEUED', 1))
        self.reopen()
        self.assertEqual(self.ledger.pending()[0], first)
        self.assertEqual(self.ledger.read()[0], original)
        self.ledger.record_attempt('event-1', retry_after_ms=2000, error_code='ACK_LOST')
        self.assertEqual(self.ledger.pending()[0]['attempts'], 2)

    def test_ack_requires_exact_binding_and_matching_duplicate_is_idempotent(self):
        original = self.ledger.append(self.event()).event
        self.ledger.seal()
        self.ledger.queue('event-1', 'enterprise')
        args = dict(destination='enterprise', event_hash=original['event_hash'],
                    receipt_ref='receipt-1', receipt_sha256='a'*64)
        for change in ({'destination': 'other'}, {'event_hash': 'b'*64}):
            with self.assertRaises(audit_log.LifecycleError):
                self.ledger.acknowledge('event-1', **dict(args, **change))
        self.ledger.acknowledge('event-1', **args)
        count = self.ledger.validate().transition_count
        self.ledger.acknowledge('event-1', **args)
        self.assertEqual(self.ledger.validate().transition_count, count)
        with self.assertRaises(audit_log.LifecycleError):
            self.ledger.acknowledge('event-1', **dict(args, receipt_ref='different'))
        self.assertEqual(self.reopen().pending(), [])
        self.assertEqual(self.ledger.read()[0], original)

    def test_queue_destination_is_fixed_and_fifo_does_not_skip_ordinary_records(self):
        for i in range(1, 5):
            self.ledger.append(self.event(f'event-{i}'))
        self.ledger.seal()
        for i in reversed(range(1, 5)):
            self.ledger.queue(f'event-{i}', 'enterprise')
        self.ledger.queue('event-1', 'enterprise')
        with self.assertRaises(audit_log.LifecycleError):
            self.ledger.queue('event-1', 'other')
        self.assertEqual([row['event_id'] for row in self.ledger.pending(limit=2)], ['event-1', 'event-2'])
        self.assertEqual([row['event_id'] for row in self.ledger.pending(after=2)], ['event-3', 'event-4'])

    def test_reconciliation_requires_ack_and_linked_source_finding(self):
        original = self.ledger.append(self.event()).event
        finding = self.event('finding-1', 'RECONCILIATION_FINDING')
        finding['correlation'] = dict(original['correlation'], parent_event_id='event-1')
        finding['detail']['original_event_id'] = 'event-1'
        finding['detail']['original_event_hash'] = original['event_hash']
        self.ledger.append(finding)
        with self.assertRaises(audit_log.LifecycleError):
            self.ledger.reconcile('event-1', 'finding-1')
        self.ledger.seal()
        self.ledger.queue('event-1', 'enterprise')
        self.ledger.acknowledge('event-1', destination='enterprise', event_hash=original['event_hash'],
                               receipt_ref='receipt-1', receipt_sha256='a'*64)
        with self.assertRaises(audit_log.LifecycleError):
            self.ledger.reconcile('event-1', 'event-1')
        self.ledger.reconcile('event-1', 'finding-1')
        self.assertEqual(self.reopen().read()[0], original)
        self.assertEqual(len(self.ledger.read()), 2)

    def test_outbox_projection_disagreement_fails_closed_on_restart(self):
        self.ledger.append(self.event())
        self.ledger.close()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE outbox SET projection=x'7b7d'")
        with self.assertRaises(audit_log.IntegrityError):
            audit_log.AuditLog.open(self.path, **self.kwargs)

    def test_matching_ack_retry_does_not_need_more_reserve(self):
        from unittest.mock import patch
        original = self.ledger.append(self.event()).event
        self.ledger.seal()
        self.ledger.queue('event-1', 'enterprise')
        args = dict(destination='enterprise', event_hash=original['event_hash'],
                    receipt_ref='receipt-1', receipt_sha256='a'*64)
        self.ledger.acknowledge('event-1', **args)
        before = self.ledger.validate().transition_count
        with patch.object(self.ledger, '_set_page_limit', side_effect=audit_log.CapacityError('exhausted')):
            self.ledger.acknowledge('event-1', **args)
        self.assertEqual(self.ledger.validate().transition_count, before)

    def test_schema_valid_opaque_ids_work_across_delivery_api(self):
        original = self.ledger.append(self.event('source/event@1')).event
        self.ledger.seal()
        self.ledger.queue('source/event@1', 'enterprise/site@1')
        self.ledger.acknowledge('source/event@1', destination='enterprise/site@1', event_hash=original['event_hash'],
                               receipt_ref='receipt/source@1', receipt_sha256='a'*64)
        self.assertEqual(self.reopen().pending(), [])
