import threading
import unittest
from cloud.wazuh_worker import WazuhWorker
from tests.test_audit_log import AuditFixture
from tests.test_wazuh_audit import MemorySink


class WorkerTests(AuditFixture, unittest.TestCase):
    def worker(self, sink=None, **kw):
        return WazuhWorker(self.ledger, sink or MemorySink(), threading.Lock(), **kw)

    def append(self, name='event-1'):
        return self.ledger.append(self.event(name)).event

    def test_low_volume_events_sealed_and_delivered(self):
        original = self.append()
        worker = self.worker()
        worker.step()
        self.assertEqual(self.ledger.pending(), [])
        self.assertEqual(worker.status()['delivered'], 1)
        self.assertEqual(self.ledger.read(), [original])
        self.assertEqual(self.ledger.validate().event_count, 1)

    def test_offline_recovery_automatic_loop_and_restart_cursor(self):
        self.append(); sink = MemorySink(); sink.offline = True
        worker = self.worker(sink)
        self.assertEqual(worker.step(), 60)
        self.assertEqual(self.ledger.pending()[0]['attempts'], 1)
        for _ in range(70): worker.step()
        self.assertEqual(self.ledger.pending()[0]['attempts'], 1)
        self.reopen()
        sink.offline = False
        worker = self.worker(sink)
        worker.step()
        self.assertEqual(len(sink.docs), 1)
        self.assertEqual(self.ledger.pending(), [])

    def test_network_does_not_hold_owner_lock(self):
        self.append(); sink = MemorySink(); worker = self.worker(sink)
        original = sink.deliver
        def deliver(event):
            acquired = worker.lock.acquire(blocking=False)
            self.assertTrue(acquired)
            if acquired: worker.lock.release()
            return original(event)
        sink.deliver = deliver
        worker.step()

    def test_storage_loss_between_delivery_and_ack_stays_pending(self):
        self.append(); checks = []
        def guard():
            checks.append(1)
            if len(checks) > 1: raise OSError('removed')
        worker = self.worker(check_storage=guard)
        with self.assertRaises(OSError): worker.step()
        self.assertEqual(len(self.ledger.pending()), 1)

    def test_conflict_does_not_starve_later_event(self):
        from cloud.wazuh_audit import document_id
        first = self.append(); self.append('event-2'); sink = MemorySink()
        sink.docs[document_id(first)] = {'conflict': True}
        worker = self.worker(sink)
        self.assertEqual(worker.step(), 60)
        worker.step()
        self.assertEqual(worker.status()['delivered'], 1)
        self.assertEqual(len(self.ledger.pending()), 1)

    def test_thread_delivers_new_event_and_stops(self):
        self.append(); sink = MemorySink(); worker = self.worker(sink, poll_seconds=.01)
        delivered = threading.Event(); original = sink.deliver
        def deliver(event):
            result = original(event); delivered.set(); return result
        sink.deliver = deliver
        worker.start()
        self.assertTrue(delivered.wait(2))
        worker.close()
        self.assertEqual(worker.status()['state'], 'STOPPED')
        self.assertEqual(self.ledger.pending(), [])

    def test_exhausted_event_does_not_drop_or_block_next(self):
        from dcamr.audit.audit_log import MAX_ATTEMPTS
        self.append(); self.append('event-2'); self.ledger.seal()
        sink = MemorySink(); self.ledger.queue('event-1', sink.destination)
        for _ in range(MAX_ATTEMPTS):
            self.ledger.record_attempt('event-1', retry_after_ms=60000, error_code='FAILED')
        worker = self.worker(sink); worker.step()
        self.assertEqual(worker.status()['delivered'], 1)
        self.assertEqual(self.ledger.pending()[0]['event_id'], 'event-1')
