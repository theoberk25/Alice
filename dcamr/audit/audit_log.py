"""Local tamper-evident recorder, not an admission gate or execution authority.

One trusted writer service owns the file, parent directory and trust configuration.
SQLite FULL synchronization assumes the storage stack honors fsync. An independent
checkpoint anchor is needed to detect whole-store rollback. No network or retention
worker runs here; accepting supplied evidence does not authenticate its source.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import sqlite3
import threading

from .event_contract import (LedgerInputError, canonical_bytes, parse_json,
                             validate_input, validate_event, event_hash, validate_time)

GENESIS = '0' * 64
CHECKPOINT_INTERVAL = 64
MAX_ATTEMPTS = 64
JOURNAL_MARGIN = 65536
RECOVERY_TYPES = {'CONTROLLER_RECEIPT', 'EXECUTION_RESULT', 'OBSERVED_STATE', 'RECORDER_FAILURE'}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,127}\Z')
_HASH = re.compile(r'[a-f0-9]{64}\Z')


class StorageError(RuntimeError):
    """No durable success; caller must resolve storage before consequential work."""


class CapacityError(StorageError):
    """Normal budget or recovery reserve exhausted; history was not pruned."""


class IntegrityError(StorageError):
    """History, checkpoint or projection validation failed; never repaired here."""


class SealingError(RuntimeError):
    """Sealing failed; previously committed events remain persisted."""


class IdempotencyConflict(ValueError):
    """Event ID already belongs to different caller content."""


class LifecycleError(ValueError):
    """Invalid delivery transition or receipt/finding binding."""


@dataclass(frozen=True)
class AppendResult:
    event: dict
    persisted: bool
    covered_sequence: int
    sealing_error: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    event_count: int
    covered_sequence: int
    transition_count: int
    covered_transition_sequence: int
    anchor_checked: bool


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise LedgerInputError('invalid identifier')
    return value


def _integer(value, minimum=0, maximum=2**63-1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise LedgerInputError('invalid integer')
    return value


def _digest(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise LedgerInputError('invalid digest')
    return value


def _hash(domain, body):
    return sha256(domain + canonical_bytes(body)).hexdigest()


_SCHEMA = '''
CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), canonical BLOB NOT NULL);
CREATE TABLE events (sequence INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
 canonical BLOB NOT NULL, caller BLOB NOT NULL);
CREATE TABLE transitions (sequence INTEGER PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(event_id),
 canonical BLOB NOT NULL, transition_hash TEXT UNIQUE NOT NULL);
CREATE INDEX transitions_event ON transitions(event_id, sequence);
CREATE TABLE outbox (event_id TEXT PRIMARY KEY REFERENCES events(event_id),
 event_sequence INTEGER UNIQUE NOT NULL REFERENCES events(sequence), state TEXT NOT NULL,
 projection BLOB NOT NULL);
CREATE INDEX outbox_state ON outbox(state, event_sequence);
CREATE TABLE checkpoints (sequence INTEGER PRIMARY KEY, canonical BLOB NOT NULL,
 digest TEXT UNIQUE NOT NULL);
'''
_IMMUTABLE = ('metadata', 'events', 'transitions', 'checkpoints')


def _trigger(table, operation):
    return (f'CREATE TRIGGER {table}_no_{operation} BEFORE {operation.upper()} ON {table} '
            "BEGIN SELECT RAISE(ABORT, 'append-only history'); END")


class AuditLog:
    """Explicit initialize/open lifecycle; bounded reads and serialized writes.

    Paths must be provisioned on non-removable local storage by deployment. This
    module cannot reliably infer mount/removability or authenticate caller claims.
    Quota covers conservative database+journal allocation, not other directory
    contents. Recovery is a restricted recorder API, not reserved admission credit.
    """
    @classmethod
    def initialize(cls, path, *, ledger_id, node_id, quota_bytes, reserve_bytes,
                   signer, trust, clock):
        _id(ledger_id)
        _id(node_id)
        _integer(quota_bytes, 256 * 1024)
        _integer(reserve_bytes, 64 * 1024, quota_bytes - 128 * 1024)
        path = Path(path).absolute()
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except OSError:
            raise StorageError('ledger initialization unavailable') from None
        db = None
        try:
            db = cls._connect(path)
            db.executescript(_SCHEMA)
            db.execute('BEGIN IMMEDIATE')
            metadata = dict(version='alice-ledger-store-v1', ledger_id=ledger_id, node_id=node_id,
                            quota_bytes=quota_bytes, reserve_bytes=reserve_bytes)
            db.execute('INSERT INTO metadata VALUES (1,?)', (canonical_bytes(metadata),))
            for table in _IMMUTABLE:
                for operation in ('update', 'delete'):
                    db.execute(_trigger(table, operation))
            db.commit()
            # Persist the initial directory entry; a failed initialization is not
            # silently removed/retried because it may require operator inspection.
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except (sqlite3.Error, OSError):
            raise StorageError('ledger initialization failed; inspect storage') from None
        finally:
            if db is not None:
                db.close()
        return cls.open(path, signer=signer, trust=trust, clock=clock)

    @staticmethod
    def _connect(path):
        db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, isolation_level=None,
                             timeout=10, check_same_thread=False)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA journal_mode=DELETE')
        db.execute('PRAGMA cache_size=-2048')
        db.execute('PRAGMA temp_store=FILE')
        return db

    @classmethod
    def open(cls, path, *, signer, trust, clock, anchor=None):
        self = cls.__new__(cls)
        self.path = Path(path).absolute()
        self.signer, self.trust, self.clock = signer, trust, clock
        self._lock = threading.RLock()
        self._unavailable = self._integrity_failed = self._sealing_failed = False
        self._closed = False
        self._db = None
        try:
            stat = self.path.stat()
            if self.path.is_symlink() or not self.path.is_file():
                raise StorageError('ledger must be a local regular file')
            self._identity = (stat.st_dev, stat.st_ino)
            self._db = cls._connect(self.path)
            with self._snapshot():
                row = self._db.execute('SELECT canonical FROM metadata WHERE id=1').fetchone()
                if row is None:
                    raise IntegrityError('missing ledger identity')
                self._metadata = parse_json(row[0])
                m = self._metadata
                if set(m) != {'version', 'ledger_id', 'node_id', 'quota_bytes', 'reserve_bytes'} or m['version'] != 'alice-ledger-store-v1':
                    raise IntegrityError('unsupported ledger identity')
                _id(m['ledger_id']); _id(m['node_id'])
                _integer(m['quota_bytes'], 256*1024)
                _integer(m['reserve_bytes'], 64*1024, m['quota_bytes']-128*1024)
                if canonical_bytes(m) != row[0]:
                    raise IntegrityError('noncanonical ledger identity')
                self._validate(anchor)
                self._data_version = self._db.execute('PRAGMA data_version').fetchone()[0]
            return self
        except (sqlite3.Error, OSError):
            self.close()
            if not self.path.exists():
                raise StorageError('existing ledger unavailable') from None
            raise IntegrityError('cannot open or validate existing ledger') from None
        except (LedgerInputError, ValueError, KeyError, TypeError):
            self.close()
            raise IntegrityError('invalid stored ledger') from None
        except Exception:
            self.close()
            raise

    def close(self):
        if self._db is not None and not self._closed:
            self._db.close()
        self._closed = True

    def _check_file(self):
        if self._closed or self._unavailable:
            raise StorageError('writer unavailable')
        if self._integrity_failed:
            raise IntegrityError('writer blocked by integrity failure')
        try:
            stat = self.path.stat()
            if self.path.is_symlink() or (stat.st_dev, stat.st_ino) != self._identity:
                raise OSError()
        except OSError:
            self._unavailable = True
            raise StorageError('ledger storage lost or replaced') from None

    @contextmanager
    def _snapshot(self):
        with self._lock:
            self._check_file()
            self._db.execute('BEGIN')
            try:
                if hasattr(self, '_data_version'):
                    version = self._db.execute('PRAGMA data_version').fetchone()[0]
                    if version != self._data_version:
                        self._validate(None)
                        self._data_version = version
                yield
            finally:
                self._db.rollback()

    def _allocation(self):
        pages = self._db.execute('PRAGMA page_count').fetchone()[0]
        size = self._db.execute('PRAGMA page_size').fetchone()[0]
        # One journal copy of every page plus per-page journal framing, rounded
        # up by a fixed header/filesystem allowance. Deliberately conservative.
        return pages * (2 * size + 8) + JOURNAL_MARGIN

    def _set_page_limit(self, recovery):
        size = self._db.execute('PRAGMA page_size').fetchone()[0]
        budget = self._metadata['quota_bytes'] - (0 if recovery else self._metadata['reserve_bytes'])
        limit = (budget - JOURNAL_MARGIN) // (2 * size + 8)
        current = self._db.execute('PRAGMA page_count').fetchone()[0]
        if current >= limit:
            raise CapacityError('audit capacity exhausted')
        self._db.execute(f'PRAGMA max_page_count={limit}')
        return budget

    @contextmanager
    def _write(self, recovery=False):
        with self._lock:
            self._check_file()
            try:
                budget = self._set_page_limit(recovery)
                # Free-space check is advisory. SQLite commit/full errors remain
                # authoritative; this is not an admission reservation.
                if shutil.disk_usage(self.path.parent).free < self.path.stat().st_size + JOURNAL_MARGIN:
                    raise CapacityError('audit filesystem capacity exhausted')
                self._db.execute('BEGIN IMMEDIATE')
                version = self._db.execute('PRAGMA data_version').fetchone()[0]
                if version != self._data_version:
                    self._validate(None)
                    self._data_version = version
                yield
                if self._allocation() > budget:
                    raise CapacityError('audit quota exhausted')
                self._check_file()
                self._db.commit()
            except sqlite3.Error as exc:
                self._db.rollback()
                if getattr(exc, 'sqlite_errorcode', 0) == sqlite3.SQLITE_FULL:
                    raise CapacityError('audit quota or disk exhausted') from None
                self._unavailable = True
                raise StorageError('audit transaction failed') from None
            except OSError:
                self._db.rollback()
                self._unavailable = True
                raise StorageError('audit storage unavailable') from None
            except Exception:
                self._db.rollback()
                raise

    def _head(self):
        row = self._db.execute('SELECT sequence,canonical FROM events ORDER BY sequence DESC LIMIT 1').fetchone()
        return (row[0], parse_json(row[1])['event_hash']) if row else (0, GENESIS)

    def _checkpoint(self):
        row = self._db.execute('SELECT canonical FROM checkpoints ORDER BY sequence DESC LIMIT 1').fetchone()
        return parse_json(row[0]) if row else None

    def _coverage(self):
        cp = self._checkpoint()
        return cp['body']['covered_sequence'] if cp else 0

    def _event(self, event_id):
        row = self._db.execute('SELECT canonical FROM events WHERE event_id=?', (event_id,)).fetchone()
        if row is None:
            raise LifecycleError('unknown event')
        return parse_json(row[0])

    def _projection(self, event_id):
        row = self._db.execute('SELECT projection FROM outbox WHERE event_id=?', (event_id,)).fetchone()
        if row is None:
            raise LifecycleError('unknown outbox entry')
        return parse_json(row[0])

    def _transition(self, projection, operation, event_sequence):
        row = self._db.execute('SELECT sequence,transition_hash FROM transitions ORDER BY sequence DESC LIMIT 1').fetchone()
        body = dict(version='alice-outbox-transition-v1', sequence=row[0]+1 if row else 1,
                    previous_hash=row[1] if row else GENESIS, operation=operation,
                    event_sequence=event_sequence, time=self.clock(), projection=projection)
        validate_time(body['time'])
        digest = _hash(b'ALICE-OUTBOX-v1\0', body)
        self._db.execute('INSERT INTO transitions VALUES (?,?,?,?)',
                         (body['sequence'], projection['event_id'], canonical_bytes(body), digest))
        self._db.execute('INSERT INTO outbox VALUES (?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET state=excluded.state,projection=excluded.projection',
                         (projection['event_id'], event_sequence, projection['state'], canonical_bytes(projection)))

    def _check_link(self, event):
        parent_id = event['correlation']['parent_event_id']
        if parent_id is None:
            return
        parent = self._event(parent_id)
        if event['event_type'] == 'RECONCILIATION_FINDING':
            if event['detail']['original_event_id'] != parent_id or event['detail']['original_event_hash'] != parent['event_hash']:
                raise LedgerInputError('finding binding mismatch')
        for key in ('request_id', 'request_sha256', 'action_id', 'execution_id'):
            value = event['correlation'][key]
            if value is not None and parent['correlation'][key] is not None and value != parent['correlation'][key]:
                raise LedgerInputError('parent correlation mismatch')

    def append(self, value, *, recovery=False):
        validate_input(value)
        caller = canonical_bytes(value)
        value = parse_json(caller)
        if type(recovery) is not bool or (recovery and value['event_type'] not in RECOVERY_TYPES):
            raise LedgerInputError('event not eligible for recovery reserve')
        # Return an existing committed identity even when the normal budget is full.
        with self._snapshot():
            row = self._db.execute('SELECT canonical,caller FROM events WHERE event_id=?', (value['event_id'],)).fetchone()
            if row:
                if row[1] != caller:
                    raise IdempotencyConflict('event content conflict')
                return AppendResult(parse_json(row[0]), True, self._coverage(),
                                    'SEALING_FAILED' if self._sealing_failed else None)
        with self._write(recovery=recovery):
            # Recheck under serialized lock for a concurrent retry.
            row = self._db.execute('SELECT canonical,caller FROM events WHERE event_id=?', (value['event_id'],)).fetchone()
            if row:
                if row[1] != caller:
                    raise IdempotencyConflict('event content conflict')
                return AppendResult(parse_json(row[0]), True, self._coverage())
            sequence, previous = self._head()
            if (sequence-self._coverage() >= CHECKPOINT_INTERVAL or self._seal_pending()) and not recovery:
                raise SealingError('unsealed interval full; seal before new work')
            self._check_link(value)
            event = dict(value, schema_version='alice-audit-event-v1', canonicalization_version='alice-json-v1',
                         ledger_id=self._metadata['ledger_id'], node_id=self._metadata['node_id'],
                         sequence=sequence+1, time=self.clock(), previous_hash=previous,
                         event_hash=GENESIS, outbox_id=value['event_id'], initial_state='LOCAL')
            event['event_hash'] = event_hash(event)
            validate_event(event)
            self._db.execute('INSERT INTO events VALUES (?,?,?,?)',
                             (sequence+1, event['event_id'], canonical_bytes(event), caller))
            projection = dict(event_id=event['event_id'], event_hash=event['event_hash'], state='LOCAL',
                              destination=None, attempts=0, retry_after_ms=0, last_error=None,
                              receipt_ref=None, receipt_sha256=None, finding_event_id=None)
            self._transition(projection, 'LOCAL', sequence+1)
            coverage = self._coverage()
        error = None
        if sequence+1-coverage >= CHECKPOINT_INTERVAL:
            try:
                self.seal()
            except (SealingError, StorageError):
                self._sealing_failed = True
                error = 'SEALING_FAILED'
            else:
                coverage = self._coverage()
        return AppendResult(event, True, coverage, error)

    def read(self, *, after=0, limit=64):
        _integer(after); _integer(limit, 1, 64)
        with self._snapshot():
            return [parse_json(row[0]) for row in self._db.execute(
                'SELECT canonical FROM events WHERE sequence>? ORDER BY sequence LIMIT ?', (after, limit))]

    def _seal_pending(self):
        checkpoint = self._checkpoint()
        covered = checkpoint['body']['transition_sequence'] if checkpoint else 0
        for (raw,) in self._db.execute('SELECT canonical FROM transitions WHERE sequence>? ORDER BY sequence', (covered,)):
            if parse_json(raw)['operation'] == 'SEAL_REQUESTED':
                return True
        return False

    def seal(self):
        try:
            # Persist intent before calling an external signer so a failed partial
            # seal remains blocked after restart. It is local lifecycle history,
            # not another deliverable event or a recursively queued receipt.
            with self._write(recovery=True):
                head, _ = self._head()
                if head and not self._seal_pending():
                    checkpoint = self._checkpoint()
                    latest = self._db.execute('SELECT max(sequence) FROM transitions').fetchone()[0]
                    if not checkpoint or head > checkpoint['body']['covered_sequence'] or latest > checkpoint['body']['transition_sequence']:
                        event = parse_json(self._db.execute('SELECT canonical FROM events WHERE sequence=?', (head,)).fetchone()[0])
                        self._transition(self._projection(event['event_id']), 'SEAL_REQUESTED', head)
            with self._write(recovery=True):
                previous = self._checkpoint()
                coverage = previous['body']['covered_sequence'] if previous else 0
                head_sequence, _ = self._head()
                end = min(head_sequence, coverage + CHECKPOINT_INTERVAL)
                rows = self._db.execute('SELECT event_id FROM events WHERE sequence>? AND sequence<=? ORDER BY sequence', (coverage, end)).fetchall()
                for row in rows:
                    p = self._projection(row[0])
                    if p['state'] != 'LOCAL':
                        raise IntegrityError('unsealed event has invalid delivery state')
                    p['state'] = 'SEALED'
                    self._transition(p, 'SEALED', self._event(row[0])['sequence'])
                transition = self._db.execute('SELECT sequence,transition_hash FROM transitions ORDER BY sequence DESC LIMIT 1').fetchone()
                trans_sequence, trans_hash = transition if transition else (0, GENESIS)
                if previous and end == coverage and trans_sequence == previous['body']['transition_sequence']:
                    self._sealing_failed = False
                    return previous
                head = self._db.execute('SELECT canonical FROM events WHERE sequence=?', (end,)).fetchone()
                body = dict(version='alice-checkpoint-v1', sequence=previous['body']['sequence']+1 if previous else 1,
                            ledger_id=self._metadata['ledger_id'], node_id=self._metadata['node_id'],
                            covered_sequence=end, head_event_hash=parse_json(head[0])['event_hash'] if head else GENESIS,
                            transition_sequence=trans_sequence, transition_hash=trans_hash,
                            previous_checkpoint_digest=previous['digest'] if previous else GENESIS,
                            algorithm_id=self.signer.algorithm_id, key_id=self.signer.key_id, time=self.clock())
                _id(body['algorithm_id']); _id(body['key_id'])
                validate_time(body['time'])
                message = b'ALICE-CHECKPOINT-v1\0' + canonical_bytes(body)
                signature = self.signer.sign(message)
                if type(signature) is not bytes or not 1 <= len(signature) <= 1024:
                    raise SealingError('invalid signer response')
                self.trust.verify(body['algorithm_id'], body['key_id'], message, signature)
                envelope = dict(body=body, signature=signature.hex())
                envelope['digest'] = _hash(b'ALICE-CHECKPOINT-DIGEST-v1\0', envelope)
                self._db.execute('INSERT INTO checkpoints VALUES (?,?,?)',
                                 (body['sequence'], canonical_bytes(envelope), envelope['digest']))
            self._sealing_failed = False
            return envelope
        except StorageError:
            self._sealing_failed = True
            raise
        except Exception:
            self._sealing_failed = True
            raise SealingError('checkpoint sealing failed') from None

    def queue(self, event_id, destination):
        _id(event_id); _id(destination)
        with self._write():
            event, p = self._event(event_id), self._projection(event_id)
            if p['state'] in ('QUEUED', 'ACKNOWLEDGED', 'RECONCILED') and p['destination'] == destination:
                return
            if p['state'] != 'SEALED' or event['sequence'] > self._coverage():
                raise LifecycleError('event not sealed or destination conflict')
            p.update(state='QUEUED', destination=destination)
            self._transition(p, 'QUEUED', event['sequence'])

    def pending(self, *, after=0, limit=64):
        _integer(after); _integer(limit, 1, 64)
        with self._snapshot():
            return [dict(parse_json(row[0]), sequence=row[1]) for row in self._db.execute(
                "SELECT projection,event_sequence FROM outbox WHERE state='QUEUED' AND event_sequence>? ORDER BY event_sequence LIMIT ?", (after, limit))]

    def record_attempt(self, event_id, *, retry_after_ms, error_code):
        _id(event_id); _integer(retry_after_ms, 0, 86400000)
        if error_code is not None:
            _id(error_code)
        with self._write():
            p = self._projection(event_id)
            if p['state'] != 'QUEUED':
                raise LifecycleError('event not queued')
            if p['attempts'] >= MAX_ATTEMPTS:
                raise LifecycleError('delivery attempt budget exhausted; remains queued')
            p.update(attempts=p['attempts']+1, retry_after_ms=retry_after_ms, last_error=error_code)
            self._transition(p, 'ATTEMPT', self._event(event_id)['sequence'])

    def acknowledge(self, event_id, *, destination, event_hash, receipt_ref, receipt_sha256):
        """Record a supplied authenticated-adapter receipt; no authentication here."""
        _id(event_id); _id(destination); _id(receipt_ref); _digest(event_hash); _digest(receipt_sha256)
        with self._snapshot():
            p = self._projection(event_id)
            if p['state'] in ('ACKNOWLEDGED', 'RECONCILED'):
                if (p['destination'], p['event_hash'], p['receipt_ref'], p['receipt_sha256']) == (destination, event_hash, receipt_ref, receipt_sha256):
                    return
                raise LifecycleError('receipt conflict')
        with self._write(recovery=True):
            p = self._projection(event_id)
            if p['destination'] != destination or p['event_hash'] != event_hash:
                raise LifecycleError('receipt binding mismatch')
            if p['state'] in ('ACKNOWLEDGED', 'RECONCILED'):
                if (p['receipt_ref'], p['receipt_sha256']) == (receipt_ref, receipt_sha256):
                    return
                raise LifecycleError('receipt conflict')
            if p['state'] != 'QUEUED':
                raise LifecycleError('event not queued')
            p.update(state='ACKNOWLEDGED', receipt_ref=receipt_ref, receipt_sha256=receipt_sha256)
            self._transition(p, 'ACKNOWLEDGED', self._event(event_id)['sequence'])

    def reconcile(self, event_id, finding_event_id):
        _id(event_id); _id(finding_event_id)
        with self._write():
            p = self._projection(event_id)
            finding = self._event(finding_event_id)
            if p['state'] not in ('ACKNOWLEDGED', 'RECONCILED'):
                raise LifecycleError('reconciliation requires acknowledgement')
            if finding['event_type'] != 'RECONCILIATION_FINDING' or finding['detail']['original_event_id'] != event_id or finding['detail']['original_event_hash'] != p['event_hash']:
                raise LifecycleError('unrelated reconciliation finding')
            if p['state'] == 'RECONCILED':
                # Additional findings are append-only events; the completion
                # marker remains bound to its first finding without extra churn.
                return
            p.update(state='RECONCILED', finding_event_id=finding_event_id)
            self._transition(p, 'RECONCILED', self._event(event_id)['sequence'])

    def readiness(self):
        try:
            with self._snapshot():
                allocation = self._allocation()
                sequence, _ = self._head()
                covered = self._coverage()
                capacity = (allocation + 32768 < self._metadata['quota_bytes']-self._metadata['reserve_bytes']
                            and shutil.disk_usage(self.path.parent).free >= self.path.stat().st_size + JOURNAL_MARGIN)
                ready = capacity and not self._sealing_failed and not self._seal_pending() and sequence-covered < CHECKPOINT_INTERVAL
                return dict(ready=ready, storage_available=True, capacity_available=capacity,
                            allocated_budget_bytes=allocation, covered_sequence=covered,
                            unsealed_events=sequence-covered, admission_reserved=False)
        except (StorageError, sqlite3.Error, OSError):
            return dict(ready=False, storage_available=False, capacity_available=False,
                        covered_sequence=None, admission_reserved=False)

    def validate(self, *, anchor=None):
        with self._snapshot():
            return self._validate(anchor)

    def _validate(self, anchor):
        # Keep this implementation separate from mutation logic so checking does
        # not replay writes or trust the mutable projection as its authority.
        from .validation import validate_store
        try:
            return validate_store(self._db, self._metadata, self.trust, anchor)
        except Exception:
            self._integrity_failed = True
            raise IntegrityError('ledger integrity validation failed') from None
