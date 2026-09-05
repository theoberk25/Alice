"""Encrypted embedding storage, private to the service user. No image persistence."""
from pathlib import Path
import json
import os
import sqlite3
from cryptography.fernet import Fernet
import numpy as np

class EnrollmentStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        keyfile = directory / "enrollment.key"
        if not keyfile.exists():
            fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
        keyfile.chmod(0o600)
        self.cipher = Fernet(keyfile.read_bytes())
        self.path = directory / "enrollments.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS enrollments (technician_id TEXT PRIMARY KEY, embedding BLOB NOT NULL, model TEXT NOT NULL, samples INTEGER NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path)

    def put(self, technician_id: str, vector: np.ndarray, model: str, samples: int):
        encrypted = self.cipher.encrypt(json.dumps(vector.tolist()).encode())
        with self.connect() as db:
            db.execute("INSERT INTO enrollments (technician_id, embedding, model, samples) VALUES (?,?,?,?) ON CONFLICT(technician_id) DO UPDATE SET embedding=excluded.embedding, model=excluded.model, samples=excluded.samples, updated_at=CURRENT_TIMESTAMP", (technician_id, encrypted, model, samples))

    def get(self, technician_id: str, model: str) -> np.ndarray:
        with self.connect() as db:
            row = db.execute("SELECT embedding,model FROM enrollments WHERE technician_id=?", (technician_id,)).fetchone()
        if row is None:
            raise ValueError("IDENTITY_NOT_ENROLLED")
        if row[1] != model:
            raise ValueError("ENROLLMENT_MODEL_MISMATCH")
        return np.array(json.loads(self.cipher.decrypt(row[0])), dtype=np.float32)

    def remove(self, technician_id: str):
        with self.connect() as db:
            db.execute("DELETE FROM enrollments WHERE technician_id=?", (technician_id,))
