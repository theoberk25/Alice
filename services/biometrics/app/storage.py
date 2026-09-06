"""Encrypted embedding storage, private to the service user. No image persistence."""
from pathlib import Path
import json
import os
import sqlite3
from cryptography.fernet import Fernet
import numpy as np
from .live_contract import POLICY

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
            db.executescript("""
                CREATE TABLE IF NOT EXISTS face_generations (
                    technician_id TEXT NOT NULL, generation TEXT NOT NULL,
                    previous_generation TEXT NOT NULL, templates BLOB NOT NULL,
                    model TEXT NOT NULL, policy TEXT NOT NULL,
                    format TEXT NOT NULL CHECK(format='MULTI_POSE_V2'),
                    PRIMARY KEY(technician_id,generation));
                CREATE TABLE IF NOT EXISTS face_heads (
                    technician_id TEXT PRIMARY KEY, generation TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS face_removals (
                    removal_id TEXT PRIMARY KEY, technician_id TEXT NOT NULL,
                    expected_generations TEXT NOT NULL);
            """)
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
            db.execute("DELETE FROM face_heads WHERE technician_id=?", (technician_id,))
            db.execute("DELETE FROM face_generations WHERE technician_id=?", (technician_id,))

    def remove_guarded(self, technician_id: str, removal_id: str, expected_generations: list[str]):
        expected = json.dumps(sorted(expected_generations))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            receipt = db.execute("SELECT technician_id,expected_generations FROM face_removals WHERE removal_id=?",
                                 (removal_id,)).fetchone()
            if receipt:
                if receipt != (technician_id, expected):
                    raise ValueError('REMOVAL_BINDING_CHANGED')
                # A lost acknowledgment may be retried after another enrollment;
                # it acknowledges the original deletion without deleting again.
                return False
            head = db.execute("SELECT generation FROM face_heads WHERE technician_id=?", (technician_id,)).fetchone()
            legacy = db.execute("SELECT 1 FROM enrollments WHERE technician_id=?", (technician_id,)).fetchone()
            current = head[0] if head else 'legacy-v1' if legacy else 'none'
            if current not in expected_generations:
                raise ValueError('ENROLLMENT_GENERATION_CHANGED')
            db.execute("DELETE FROM enrollments WHERE technician_id=?", (technician_id,))
            db.execute("DELETE FROM face_heads WHERE technician_id=?", (technician_id,))
            db.execute("DELETE FROM face_generations WHERE technician_id=?", (technician_id,))
            db.execute("INSERT INTO face_removals VALUES(?,?,?)", (removal_id, technician_id, expected))
        return True

    def generation(self, technician_id: str) -> str:
        with self.connect() as db:
            row = db.execute("SELECT generation FROM face_heads WHERE technician_id=?", (technician_id,)).fetchone()
            if row:
                return row[0]
            legacy = db.execute("SELECT 1 FROM enrollments WHERE technician_id=?", (technician_id,)).fetchone()
        return "legacy-v1" if legacy else "none"

    def stage(self, technician_id: str, generation: str, previous: str,
              templates: list[np.ndarray], poses: list[str], model: str, policy: str):
        from .engine import unit, similarity
        from .live_contract import POSES
        if len(templates) != len(poses) or not 14 <= len(templates) <= 18:
            raise ValueError("INVALID_TEMPLATE_COUNT")
        if not all(poses.count(p) >= 2 for p in POSES):
            raise ValueError("INSUFFICIENT_POSE_COVERAGE")
        vectors = [unit(v) for v in templates]
        if any(similarity(a, b) < 0.5 for i, a in enumerate(vectors) for b in vectors[i + 1:]):
            raise ValueError("MIXED_ENROLLMENT_IDENTITY")
        payload = json.dumps({"templates": [v.tolist() for v in vectors], "poses": poses}, sort_keys=True).encode()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            head = db.execute("SELECT generation FROM face_heads WHERE technician_id=?", (technician_id,)).fetchone()
            legacy = db.execute("SELECT 1 FROM enrollments WHERE technician_id=?", (technician_id,)).fetchone()
            current = head[0] if head else "legacy-v1" if legacy else "none"
            if current != previous:
                raise ValueError("ENROLLMENT_GENERATION_CHANGED")
            prior = db.execute("SELECT templates,previous_generation,model,policy FROM face_generations WHERE technician_id=? AND generation=?", (technician_id, generation)).fetchone()
            if prior:
                if self.cipher.decrypt(prior[0]) != payload or tuple(prior[1:]) != (previous, model, policy):
                    raise ValueError("GENERATION_COLLISION")
                return
            db.execute("INSERT INTO face_generations VALUES(?,?,?,?,?,?,'MULTI_POSE_V2')",
                       (technician_id, generation, previous, self.cipher.encrypt(payload), model, policy))

    def activate(self, technician_id: str, generation: str, previous: str):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            staged = db.execute("SELECT previous_generation FROM face_generations WHERE technician_id=? AND generation=?", (technician_id, generation)).fetchone()
            if not staged or staged[0] != previous:
                raise ValueError("GENERATION_NOT_STAGED")
            head = db.execute("SELECT generation FROM face_heads WHERE technician_id=?", (technician_id,)).fetchone()
            legacy = db.execute("SELECT 1 FROM enrollments WHERE technician_id=?", (technician_id,)).fetchone()
            current = head[0] if head else "legacy-v1" if legacy else "none"
            if current == generation:
                return
            if current != previous:
                raise ValueError("ENROLLMENT_GENERATION_CHANGED")
            db.execute("INSERT INTO face_heads VALUES(?,?) ON CONFLICT(technician_id) DO UPDATE SET generation=excluded.generation", (technician_id, generation))

    def templates(self, technician_id: str, generation: str, model: str, policy: str = POLICY) -> list[np.ndarray]:
        if self.generation(technician_id) != generation:
            raise ValueError("ENROLLMENT_GENERATION_CHANGED")
        with self.connect() as db:
            row = db.execute("SELECT templates,model,policy FROM face_generations WHERE technician_id=? AND generation=?", (technician_id, generation)).fetchone()
        if row is None:
            raise ValueError("MULTI_POSE_V2_REQUIRED_REENROLL")
        if row[1] != model:
            raise ValueError("ENROLLMENT_MODEL_MISMATCH")
        # V2 continuous enrollment collected the same identity/PAD-checked pose
        # gallery as V3. Preserve it for passive V3 verification; older identity
        # or protected-policy material is not compatible by this exception.
        if policy != POLICY or row[2] not in ('alice.live-face.v2', 'alice.live-face.v3'):
            raise ValueError("ENROLLMENT_POLICY_MISMATCH")
        return [np.asarray(v, dtype=np.float32) for v in json.loads(self.cipher.decrypt(row[0]))["templates"]]
