"""In-process ledger delivery; all SQL uses the runtime owner's lock.

Network I/O never holds that lock. One worker per owner, no second database
connection. Delivery reachability does not change execution authority.
"""
import threading
from dcamr.audit.audit_log import LifecycleError, MAX_ATTEMPTS
from cloud.wazuh_audit import DeliveryError


class WazuhWorker:
    def __init__(self, ledger, sink, lock, *, check_storage=lambda: None,
                 poll_seconds=5, retry_seconds=60):
        if poll_seconds <= 0 or retry_seconds <= 0:
            raise ValueError('Intervals must be positive')
        self.ledger, self.sink, self.lock = ledger, sink, lock
        self.check_storage = check_storage
        self.poll_seconds, self.retry_seconds = poll_seconds, retry_seconds
        self.cursor = 0
        self.failures = 0
        self._stop = threading.Event()
        self._thread = None
        self._status_lock = threading.Lock()
        self._status = dict(state='STARTING', delivered=0, last_event_id=None,
                            last_error=None, retry_in_seconds=0)

    def status(self):
        with self._status_lock:
            return dict(self._status)

    def _update(self, **fields):
        with self._status_lock:
            self._status.update(fields)

    def _prepare(self):
        with self.lock:
            self.check_storage()
            # Includes low-volume rejection events that have not reached a batch seal.
            self.ledger.seal()
            events = self.ledger.read(after=self.cursor, limit=64)
            if not events:
                self.cursor = 0
                return None, self.poll_seconds
            for event in events:
                self.cursor = event['sequence']
                try:
                    self.ledger.queue(event['event_id'], self.sink.destination)
                except LifecycleError:
                    self._update(last_error='UNSEALED_OR_DESTINATION_CONFLICT')
                    continue
                pending = self.ledger.pending(after=event['sequence']-1, limit=1)
                if not pending or pending[0]['event_id'] != event['event_id']:
                    continue
                if pending[0]['attempts'] >= MAX_ATTEMPTS:
                    self._update(last_error='ATTEMPT_BUDGET_EXHAUSTED')
                    continue
                self.ledger.record_attempt(event['event_id'], retry_after_ms=60000,
                                           error_code='DELIVERY_UNCONFIRMED')
                self.ledger.seal()
                return event, 0
            return None, 0.1  # Yield between bounded pages of already delivered records.

    def step(self):
        """Perform at most one upload. Return scheduler delay; useful for deterministic tests."""
        if self.failures:
            try:
                self.sink.probe()
            except DeliveryError as error:
                self.failures += 1
                delay = min(300, self.retry_seconds * 2 ** min(self.failures-1, 8))
                self._update(state='RETRYING', last_error=error.code, retry_in_seconds=delay)
                return delay
        event, delay = self._prepare()
        if event is None:
            self._update(state='IDLE', retry_in_seconds=delay)
            return delay
        self._update(state='DELIVERING', last_event_id=event['event_id'])
        try:
            receipt = self.sink.deliver(event)
        except DeliveryError as error:
            self.failures += 1
            delay = min(300, self.retry_seconds * 2 ** min(self.failures-1, 8))
            # Keep scanning after this event on retry so one conflict cannot starve
            # later records. At end of pass, restart from zero and revisit failures.
            self._update(state='RETRYING', last_error=error.code, retry_in_seconds=delay)
            return delay
        with self.lock:
            self.check_storage()
            self.ledger.acknowledge(event['event_id'], destination=self.sink.destination,
                                    event_hash=receipt.event_hash, receipt_ref=receipt.receipt_ref,
                                    receipt_sha256=receipt.receipt_sha256)
            self.ledger.seal()
        self.failures = 0
        self._update(state='DELIVERED', delivered=self.status()['delivered']+1,
                     last_error=None, retry_in_seconds=0)
        return 0.1

    def _run(self):
        while not self._stop.is_set():
            try:
                delay = self.step()
            except Exception:
                # Storage/signing/programming failures need operator inspection;
                # do not spin, leak exception contents, or acknowledge uncertain writes.
                self._update(state='STOPPED_ERROR', last_error='LOCAL_SYNC_FAILURE', retry_in_seconds=0)
                return
            if self._stop.wait(delay):
                break
        self._update(state='STOPPED', retry_in_seconds=0)

    def start(self):
        if self._thread is not None:
            raise RuntimeError('Worker already started')
        self._thread = threading.Thread(target=self._run, name='wazuh-ledger-sync', daemon=True)
        self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=25)
            if self._thread.is_alive():
                raise RuntimeError('Sync still running; do not close its ledger')
