"""Real ephemeral Ed25519 keys; no private user files or remote services."""
import importlib.util
import json
from pathlib import Path
import stat

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "review_key_provisioning", ROOT / "scripts/console/provision_review_key.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_private_key_and_scoped_public_candidate_interoperate(tmp_path):
    output = tmp_path.resolve() / "private review"
    result = module.provision(output, "console-test", ["TECH-001", "TECH-002"])
    private = Path(result["key_file"]).read_bytes()
    trust = json.loads(Path(result["trust_candidate"]).read_text())
    assert len(private) == 32
    assert trust["consoles"][0]["technician_ids"] == ["TECH-001", "TECH-002"]
    public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(trust["consoles"][0]["public_key"]))
    body = b"ephemeral provisioning verification"
    public.verify(Ed25519PrivateKey.from_private_bytes(private).sign(body), body)
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in output.iterdir())
    assert private.hex() not in json.dumps(result)
    with pytest.raises(FileExistsError):
        module.provision(output, "console-test", ["TECH-001"])
    assert Path(result["key_file"]).read_bytes() == private


@pytest.mark.parametrize("console,technicians", [
    ("invalid/path", ["TECH-001"]), ("console", []),
    ("console", ["same", "same"]), ("console", ["invalid id"]),
])
def test_invalid_identity_creates_nothing(tmp_path, console, technicians):
    output = tmp_path.resolve() / "keys"
    with pytest.raises(ValueError):
        module.provision(output, console, technicians)
    assert not output.exists()


def test_symlinks_and_repository_storage_are_refused(tmp_path):
    parent = tmp_path.resolve()
    actual = parent / "actual"
    actual.mkdir()
    alias = parent / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError):
        module.provision(alias / "keys", "console", ["TECH-001"])
    with pytest.raises(ValueError):
        module.provision(ROOT / "private-test-keys", "console", ["TECH-001"])
    existing = parent / "existing"
    existing.symlink_to(actual, target_is_directory=True)
    with pytest.raises(FileExistsError):
        module.provision(existing, "console", ["TECH-001"])
    assert not list(actual.iterdir())
