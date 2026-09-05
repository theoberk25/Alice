"""Independent storage integrity cases; injected failures are not hardware tests."""

from contextlib import closing, contextmanager
from hashlib import sha256
import hmac
import json
import sqlite3
import unittest

from dcamr.audit import audit_log
from dcamr.audit.event_contract import canonical_bytes, parse_json, event_hash
from dcamr.audit.signing import TrustStore
from tests.test_audit_log import AuditFixture


class _TestOnlySigner:
    """Deliberately non-production stand-in proving storage protocol substitution."""

    algorithm_id = "test-only-digest-v1"
    key_id = "test-only-key"

    def sign(self, message):
        return sha256(b"not-a-production-signature\x00" + message).digest()


class _TestOnlyVerifier:
    def verify(self, signature, message):
        expected = sha256(b"not-a-production-signature\x00" + message).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid test-only signature")


@contextmanager
def _permit_history_update(db, table):
    """Simulate file-level tampering, restoring the exact protection trigger."""
    name = table + "_no_update"
    sql = db.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()[0]
    db.execute("DROP TRIGGER " + name)
    try:
        yield
    finally:
        db.execute(sql)


def _transition_digest(body):
    return sha256(b"ALICE-OUTBOX-v1\x00" + canonical_bytes(body)).hexdigest()


class AuditIntegrityTests(AuditFixture, unittest.TestCase):
    def assert_restart_rejects_without_repair(self):
        before = self.path.read_bytes()
        with self.assertRaises(audit_log.IntegrityError):
            audit_log.AuditLog.open(self.path, **self.kwargs)
        self.assertEqual(self.path.read_bytes(), before)

    def test_changed_signature_with_recomputed_envelope_digest_is_rejected(self):
        self.ledger.append(self.event())
        checkpoint = self.ledger.seal()
        self.ledger.close()
        changed = dict(checkpoint)
        signature = bytearray.fromhex(changed["signature"])
        signature[0] ^= 1
        changed["signature"] = bytes(signature).hex()
        envelope = {"body": changed["body"], "signature": changed["signature"]}
        changed["digest"] = sha256(b"ALICE-CHECKPOINT-DIGEST-v1\x00" + canonical_bytes(envelope)).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            with _permit_history_update(db, "checkpoints"):
                db.execute("UPDATE checkpoints SET canonical=?,digest=?", (canonical_bytes(changed), changed["digest"]))
        self.assert_restart_rejects_without_repair()

    def test_rehashed_lifecycle_and_matching_projection_conflict_with_signed_head(self):
        self.ledger.append(self.event())
        first_checkpoint = self.ledger.seal()
        self.ledger.queue("event-1", "enterprise")
        self.ledger.record_attempt("event-1", retry_after_ms=1000, error_code="ACK_LOST")
        checkpoint = self.ledger.seal()
        self.ledger.close()
        with closing(sqlite3.connect(self.path)) as db, db:
            previous = first_checkpoint["body"]["transition_hash"]
            with _permit_history_update(db, "transitions"):
                rows = db.execute("SELECT sequence,canonical FROM transitions WHERE sequence>? ORDER BY sequence",
                                  (first_checkpoint["body"]["transition_sequence"],)).fetchall()
                for sequence, raw in rows:
                    transition = parse_json(raw)
                    transition["previous_hash"] = previous
                    transition["projection"]["destination"] = "substituted-destination"
                    previous = _transition_digest(transition)
                    db.execute("UPDATE transitions SET canonical=?,transition_hash=? WHERE sequence=?",
                               (canonical_bytes(transition), previous, sequence))
            db.execute("UPDATE outbox SET projection=?", (canonical_bytes(transition["projection"]),))
            self.assertNotEqual(previous, checkpoint["body"]["transition_hash"])
        # Legal lifecycle, consistent mutable projection, and recomputed hash
        # links are insufficient to forge the previously signed lifecycle head.
        self.assert_restart_rejects_without_repair()

    def test_storage_seal_and_restart_accept_explicit_substituted_signer(self):
        signer = _TestOnlySigner()
        trust = TrustStore({(signer.algorithm_id, signer.key_id): _TestOnlyVerifier()})
        self.reopen(signer=signer, trust=trust)
        original = self.ledger.append(self.event()).event
        checkpoint = self.ledger.seal()
        self.assertEqual(checkpoint["body"]["algorithm_id"], "test-only-digest-v1")
        self.assertEqual(checkpoint["body"]["key_id"], "test-only-key")
        self.ledger.queue("event-1", "enterprise")
        self.reopen(signer=signer, trust=trust, anchor=checkpoint)
        self.assertEqual(self.ledger.validate(anchor=checkpoint).covered_sequence, 1)
        self.assertEqual(self.ledger.pending()[0]["state"], "QUEUED")
        self.assertEqual(self.ledger.read()[0], original)

    def test_untrusted_new_signer_cannot_create_coverage_or_queue_records(self):
        self.ledger.append(self.event())
        self.reopen(signer=_TestOnlySigner())
        with self.assertRaises(audit_log.SealingError):
            self.ledger.seal()
        self.assertEqual(self.ledger.validate().covered_sequence, 0)
        self.assertFalse(self.ledger.readiness()["ready"])
        with self.assertRaises(audit_log.LifecycleError):
            self.ledger.queue("event-1", "enterprise")
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM checkpoints").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT state FROM outbox").fetchone()[0], "LOCAL")
        self.reopen()
        self.assertEqual(self.ledger.read()[0]["event_id"], "event-1")
        self.assertEqual(self.ledger.seal()["body"]["covered_sequence"], 1)

    def test_read_only_sqlite_connection_never_reports_durable_append(self):
        before = self.path.read_bytes()
        self.ledger._db.close()
        # A real read-only SQLite handle deterministically exercises SQLITE_READONLY
        # even when running as a user whose filesystem permissions are privileged.
        self.ledger._db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True,
                                         isolation_level=None, check_same_thread=False)
        with self.assertRaises(audit_log.StorageError):
            self.ledger.append(self.event())
        self.assertFalse(self.ledger.readiness()["ready"])
        self.assertEqual(self.path.read_bytes(), before)
        self.reopen()
        self.assertEqual(self.ledger.validate().event_count, 0)
        self.assertEqual(self.ledger.validate().transition_count, 0)
        self.assertEqual(self.ledger.pending(), [])
        self.assertTrue(self.ledger.append(self.event()).persisted)

    def test_sqlite_insert_authorizer_denial_rolls_back_without_success(self):
        def deny_event_insert(operation, table, column, database, trigger):
            return sqlite3.SQLITE_DENY if operation == sqlite3.SQLITE_INSERT and table == "events" else sqlite3.SQLITE_OK

        self.ledger._db.set_authorizer(deny_event_insert)
        with self.assertRaises(audit_log.StorageError):
            self.ledger.append(self.event())
        self.assertFalse(self.ledger.readiness()["ready"])
        self.reopen()
        report = self.ledger.validate()
        self.assertEqual((report.event_count, report.transition_count), (0, 0))
        self.assertEqual(self.ledger.pending(), [])

    def test_noncanonical_but_semantically_identical_event_bytes_are_rejected(self):
        event = self.ledger.append(self.event()).event
        self.ledger.close()
        noncanonical = json.dumps(event, sort_keys=True, indent=1).encode()
        self.assertEqual(parse_json(noncanonical), event)
        with closing(sqlite3.connect(self.path)) as db, db:
            with _permit_history_update(db, "events"):
                db.execute("UPDATE events SET canonical=?", (noncanonical,))
        self.assert_restart_rejects_without_repair()

    def test_rehashed_event_sequence_gap_cannot_be_hidden_by_matching_indices(self):
        self.ledger.append(self.event())
        second = self.ledger.append(self.event("event-2")).event
        self.ledger.close()
        second["sequence"] = 3
        second["event_hash"] = event_hash(second)
        with closing(sqlite3.connect(self.path)) as db, db:
            with _permit_history_update(db, "events"):
                db.execute("UPDATE events SET sequence=3,canonical=? WHERE event_id='event-2'", (canonical_bytes(second),))
            with _permit_history_update(db, "transitions"):
                raw = db.execute("SELECT canonical FROM transitions WHERE event_id='event-2'").fetchone()[0]
                transition = parse_json(raw)
                transition["event_sequence"] = 3
                transition["projection"]["event_hash"] = second["event_hash"]
                db.execute("UPDATE transitions SET canonical=?,transition_hash=? WHERE event_id='event-2'",
                           (canonical_bytes(transition), _transition_digest(transition)))
            db.execute("UPDATE outbox SET event_sequence=3,projection=? WHERE event_id='event-2'",
                       (canonical_bytes(transition["projection"]),))
        self.assert_restart_rejects_without_repair()


if __name__ == "__main__":
    unittest.main()
