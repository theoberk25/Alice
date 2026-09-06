"""Explicit local console-key creation; never contacts or configures a runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


def provision(output_dir, console_id, technician_ids):
    """Create a new private directory; refuse overwrite and repository storage."""
    if not IDENTIFIER.fullmatch(console_id):
        raise ValueError("Console ID must start with a letter/digit; use 1–128 ASCII letters, digits, _, ., : or -.")
    if (not 1 <= len(technician_ids) <= 64
            or len(set(technician_ids)) != len(technician_ids)
            or any(not IDENTIFIER.fullmatch(t) for t in technician_ids)):
        raise ValueError("Supply 1–64 distinct valid technician IDs.")
    output = Path(output_dir).expanduser().absolute()
    if not output.parent.is_dir() or output.parent.resolve() != output.parent:
        raise ValueError("Use an existing absolute parent directory without symlinks.")
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Private review keys must be stored outside the checkout.")
    # mkdir is the exclusive admission: a pre-existing directory or symlink fails.
    output.mkdir(mode=0o700)
    key = Ed25519PrivateKey.generate()
    seed = key.private_bytes(serialization.Encoding.Raw,
                             serialization.PrivateFormat.Raw,
                             serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw,
                                          serialization.PublicFormat.Raw)
    trust = {"schema_version": "alice-console-trust-v1", "consoles": [{
        "console_id": console_id, "public_key": public.hex(),
        "technician_ids": list(technician_ids),
    }]}
    for name, data in (("console.seed", seed), ("console-trust.candidate.json",
                       (json.dumps(trust, indent=2) + "\n").encode())):
        descriptor = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    directory = os.open(output, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {"console_id": console_id, "key_file": str(output / "console.seed"),
            "trust_candidate": str(output / "console-trust.candidate.json"),
            "public_key_sha256": hashlib.sha256(public).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New private directory outside the checkout; parent must exist")
    parser.add_argument("--console-id", required=True)
    parser.add_argument("--technician-id", action="append", required=True,
                        help="Exact enabled native technician ID; repeat for each trusted ID")
    args = parser.parse_args()
    try:
        result = provision(args.output_dir, args.console_id, args.technician_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Local provisioning stopped: {error}\nExisting files are preserved.\n")
    print(json.dumps(result, indent=2))
    print("Created locally only. No settings were changed and no runtime trust was installed.")


if __name__ == "__main__":
    main()
