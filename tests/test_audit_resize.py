import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from lab.audit_resize import resize


class QuotaMigrationTest(unittest.TestCase):
    def test_preserves_history_backup_and_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.sqlite'; backup=Path(tmp)/'backup.sqlite'
            with sqlite3.connect(p) as db:
                db.executescript("CREATE TABLE metadata(id INTEGER PRIMARY KEY, canonical BLOB); CREATE TABLE events(id INTEGER PRIMARY KEY, canonical BLOB); CREATE TRIGGER metadata_no_update BEFORE UPDATE ON metadata BEGIN SELECT RAISE(ABORT, 'immutable'); END;")
                db.execute('INSERT INTO metadata VALUES (1,?)',(json.dumps({'quota_bytes':8388608,'reserve_bytes':262144}).encode(),))
                db.execute('INSERT INTO events VALUES (1,?)',(b'original sealed bytes',))
            resize(p,backup,256*1024**2)
            with sqlite3.connect(p) as db, sqlite3.connect(backup) as old:
                self.assertEqual(db.execute('select * from events').fetchall(),old.execute('select * from events').fetchall())
                self.assertEqual(json.loads(old.execute('select canonical from metadata').fetchone()[0])['quota_bytes'],8388608)
                with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE metadata SET canonical=x'00'")
            with self.assertRaises(ValueError):resize(p,backup,512*1024**2)
