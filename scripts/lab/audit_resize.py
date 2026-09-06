"""Offline quota-only ledger migration. Stop the runtime before invoking.

Copies the original database to a NEW backup, preserves all history bytes and
restores immutable-metadata guards in the same transaction. Does not prune data,
change identities, repair integrity, or clear delivery states.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def history_digest(db):
    digest = hashlib.sha256()
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if r[0] != 'metadata']
    for table in tables:
        if not table.replace('_', '').isalnum():
            raise ValueError('Unexpected table name')
        digest.update(table.encode())
        for row in db.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
            digest.update(repr(row).encode())
    return digest.hexdigest()


def resize(path, backup, quota):
    path, backup = Path(path), Path(backup)
    if path.is_symlink() or not path.is_file() or backup.exists():
        raise ValueError('Existing regular ledger and new backup path required')
    db = sqlite3.connect(path)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        metadata = json.loads(db.execute('SELECT canonical FROM metadata WHERE id=1').fetchone()[0])
        if type(quota) is not int or not metadata['quota_bytes'] < quota <= 1024**3:
            raise ValueError('Increase-only quota, at most 1 GiB')
        before = history_digest(db)
        with sqlite3.connect(backup) as copy:
            db.backup(copy)
        backup.chmod(0o600)
        trigger = db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='metadata_no_update'").fetchone()
        if trigger is None:
            raise ValueError('Missing metadata immutability guard')
        db.execute('BEGIN EXCLUSIVE')
        db.execute('DROP TRIGGER metadata_no_update')
        metadata['quota_bytes'] = quota
        raw = json.dumps(metadata,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        db.execute('UPDATE metadata SET canonical=? WHERE id=1',(raw,))
        db.execute(trigger[0])
        if history_digest(db) != before:
            raise ValueError('History changed')
        db.commit()
        print('Quota increased; all history tables unchanged. Backup:',backup)
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger',type=Path);p.add_argument('--backup',type=Path,required=True)
    p.add_argument('--quota-mib',type=int,required=True)
    p.add_argument('--runtime-stopped',action='store_true',required=True)
    a=p.parse_args();resize(a.ledger,a.backup,a.quota_mib*1024**2)
