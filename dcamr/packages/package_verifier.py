"""Minimal fail-closed release loader for the first-light test.

Verifies the workstation-signed permissions release (manifest Ed25519 signature
plus per-payload sha256 digests, mirroring lab.enterprise_sim.permissions'
canonical bytes) and parses grants and terminal keys into frozen structs. Any
mismatch raises and the runtime refuses to start. No staging, activation or
generation machinery lives here yet; that remains future runtime-plan work.
Placement and scope follow the repository working agreements in AGENTS.md.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from dcamr.audit.signing import Ed25519Verifier, TrustError


class ReleaseError(RuntimeError):
    """Release could not be verified; the runtime must refuse to start."""


def _canonical_bytes(value) -> bytes:
    # Must byte-match lab.enterprise_sim.permissions.canonical_bytes, which is
    # what sign_manifest and digest_of hash on the workstation.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class Grant:
    grant_id: str
    agents: tuple[str, ...]
    actions: tuple[str, ...]
    targets: tuple[str, ...]
    effect: str
    approval_required: bool
    parameter_bounds: dict


@dataclass(frozen=True)
class TerminalKey:
    key_id: str
    agent_id: str
    public_key: bytes


@dataclass(frozen=True)
class Release:
    bundle_id: str
    generation: int
    manifest_sha256: str
    grants: tuple[Grant, ...]
    terminal_keys: dict          # key_id -> TerminalKey
    subjects: dict               # agent_id -> responsible user_id


def _load_payload(documents: dict[str, bytes], name: str, expected_digest: str) -> dict:
    raw = documents[name]
    if sha256(raw).hexdigest() != expected_digest:
        raise ReleaseError(f"payload digest mismatch: {name}")
    payload = json.loads(raw)
    if _canonical_bytes(payload) != raw:
        raise ReleaseError(f"payload is not canonical JSON: {name}")
    return payload


def load_release(path, trusted_manifest_key: bytes) -> Release:
    """Verify and parse a release directory; raise ReleaseError on any doubt."""
    try:
        documents = {name: (Path(path) / name).read_bytes() for name in RELEASE_DOCUMENTS}
    except OSError as exc:
        raise ReleaseError("release documents unavailable") from exc
    return load_release_documents(documents, trusted_manifest_key)


RELEASE_DOCUMENTS = frozenset(("manifest.json", "manifest.sig", "grants.json",
                               "subjects.json", "terminal_keys.json"))


def load_release_documents(documents: dict[str, bytes], trusted_manifest_key: bytes) -> Release:
    """Verify exactly the same signed bytes from a directory or SQL snapshot."""
    if set(documents) != RELEASE_DOCUMENTS or any(type(v) is not bytes for v in documents.values()):
        raise ReleaseError("unexpected release documents")
    try:
        manifest_raw = documents["manifest.json"]
        signature = documents["manifest.sig"]
        manifest = json.loads(manifest_raw)
        unsigned = {key: value for key, value in manifest.items() if key != "signature"}
        Ed25519Verifier(trusted_manifest_key).verify(signature, _canonical_bytes(unsigned))
    except ReleaseError:
        raise
    except (OSError, ValueError, TrustError) as exc:
        raise ReleaseError("manifest unavailable or signature invalid") from exc

    digests = manifest.get("content_digests")
    if not isinstance(digests, dict):
        raise ReleaseError("manifest missing content digests")
    required = ("grants.json", "subjects.json", "terminal_keys.json")
    if set(digests) != set(required):
        raise ReleaseError("manifest digests do not cover the expected payloads")
    try:
        grants_doc = _load_payload(documents, "grants.json", digests["grants.json"])
        subjects_doc = _load_payload(documents, "subjects.json", digests["subjects.json"])
        keys_doc = _load_payload(documents, "terminal_keys.json", digests["terminal_keys.json"])
    except ReleaseError:
        raise
    except (OSError, ValueError) as exc:
        raise ReleaseError("release payload unavailable or malformed") from exc

    grants = []
    for entry in grants_doc.get("grants", ()):
        try:
            grants.append(Grant(
                grant_id=entry["grant_id"],
                agents=tuple(entry["agents"]),
                actions=tuple(entry["actions"]),
                targets=tuple(entry["targets"]),
                effect=entry["effect"],
                approval_required=bool(entry["approval_required"]),
                parameter_bounds=dict(entry.get("parameter_bounds", {})),
            ))
        except (KeyError, TypeError) as exc:
            raise ReleaseError("malformed grant entry") from exc

    terminal_keys = {}
    try:
        for key_id, entry in keys_doc["keys"].items():
            terminal_keys[key_id] = TerminalKey(
                key_id=key_id, agent_id=entry["agent_id"],
                public_key=bytes.fromhex(entry["ed25519_public_hex"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ReleaseError("malformed terminal key entry") from exc

    subjects = {}
    try:
        for agent_id, entry in subjects_doc["agents"].items():
            subjects[agent_id] = entry["responsible_user"]
    except (KeyError, TypeError) as exc:
        raise ReleaseError("malformed subject entry") from exc

    generation = manifest.get("generation")
    if type(generation) is not int or generation < 0:
        raise ReleaseError("manifest missing release generation")
    return Release(bundle_id=manifest.get("bundle_id", "unknown"),
                   generation=generation,
                   manifest_sha256=sha256(manifest_raw).hexdigest(),
                   grants=tuple(grants), terminal_keys=terminal_keys,
                   subjects=subjects)
