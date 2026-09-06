"""Immutable SQL packaging of the existing signed first-light input contract.

This is a read-only input artifact, never a replacement for the audit database.
No enterprise network fetch, general policy interpretation or hot activation.
Placement and preservation rules: AGENTS.md.
"""
import os
from pathlib import Path
import sqlite3
import tempfile

from dcamr.packages.package_verifier import (
    RELEASE_DOCUMENTS, ReleaseError, load_release_documents,
)

MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_BYTES = 1024 * 1024
APPLICATION_ID = 0x414C4943
VERSION = 1


def load_snapshot(path, trusted_manifest_key: bytes):
    """Read one consistent SQL transaction and reverify all signed documents."""
    path = Path(path).resolve()
    try:
        if not 0 < path.stat().st_size <= MAX_SNAPSHOT_BYTES:
            raise ReleaseError("snapshot size outside supported bounds")
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            try:
                db.execute("PRAGMA query_only=ON")
                db.execute("PRAGMA trusted_schema=OFF")
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_DOCUMENT_BYTES + 1024)
                db.set_progress_handler(lambda: 1, 100000)
                db.execute("BEGIN")
                if (db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                        or db.execute("PRAGMA user_version").fetchone()[0] != VERSION):
                    raise ReleaseError("unsupported release snapshot format")
                objects = db.execute("SELECT type, name FROM sqlite_master").fetchall()
                if sorted(objects) != [('index', 'sqlite_autoindex_documents_1'), ('table', 'documents')]:
                    raise ReleaseError("unexpected snapshot schema objects")
                rows = db.execute("SELECT name, content FROM documents LIMIT 6").fetchall()
                if len(rows) != len(RELEASE_DOCUMENTS):
                    raise ReleaseError("unexpected snapshot document count")
                documents = dict(rows)
                if any(type(raw) is not bytes or len(raw) > MAX_DOCUMENT_BYTES
                       for raw in documents.values()):
                    raise ReleaseError("invalid snapshot document")
                return load_release_documents(documents, trusted_manifest_key)
            finally:
                # sqlite's context manager commits/rolls back but does not close.
                db.rollback()
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ReleaseError("SQL release snapshot unavailable or invalid") from exc
    finally:
        if 'db' in locals():
            db.close()


def publish_snapshot(release_dir, output, trusted_manifest_key: bytes):
    """Validate captured source bytes, then atomically publish without overwrite.

    A changing source either forms a fully signed release or fails verification.
    The output parent must exist. Hard-link publication requires a filesystem
    supporting links and fsync; unsupported storage fails rather than overwrites.
    """
    output = Path(output).absolute()
    if os.path.lexists(output):
        raise FileExistsError(output)
    try:
        documents = {}
        for name in RELEASE_DOCUMENTS:
            with (Path(release_dir) / name).open('rb') as source:
                raw = source.read(MAX_DOCUMENT_BYTES + 1)
            if len(raw) > MAX_DOCUMENT_BYTES:
                raise ReleaseError("release document too large")
            documents[name] = raw
        release = load_release_documents(documents, trusted_manifest_key)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ReleaseError("source release unavailable or invalid") from exc
    fd, temporary = tempfile.mkstemp(prefix='.alice-snapshot-', dir=output.parent)
    os.close(fd)
    try:
        db = sqlite3.connect(temporary)
        try:
            with db:
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute(f"PRAGMA user_version={VERSION}")
                db.execute("CREATE TABLE documents (name TEXT PRIMARY KEY, content BLOB NOT NULL)")
                db.executemany("INSERT INTO documents VALUES (?, ?)", sorted(documents.items()))
        finally:
            db.close()
        load_snapshot(temporary, trusted_manifest_key)
        with open(temporary, 'rb') as stream:
            os.fsync(stream.fileno())
        os.link(temporary, output)  # Atomic create-if-absent, including racing publishers.
        parent_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        return release
    finally:
        os.unlink(temporary)
