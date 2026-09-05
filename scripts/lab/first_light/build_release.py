"""Build the signed first-light test release and terminal identity (Mac side).

Reuses lab.enterprise_sim.permissions for canonical bytes, manifest shape and
signing. All keys generated here are DEMONSTRATION TRUST ONLY: never provision
the manifest or terminal keys as production trust (see the enterprise_sim
warning and AGENTS.md working agreements). Output directory layout:

  release/                what the Pi loads (grants, subjects, terminal_keys,
                          manifest.json, manifest.sig)
  trust/manifest_public.hex   public key the Pi is provisioned to trust
  client/term-agent-01-k1.seed  terminal PRIVATE key seed (hex, local test only)
"""

import argparse
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from lab.enterprise_sim.permissions import (
    build_manifest, canonical_bytes, digest_of, sign_manifest,
)

AGENT_ID = "term-agent-01"
KEY_ID = "term-agent-01-k1"
USER_ID = "theo-test"
GRANT_ID = "G-LIGHT-ON"
GENERATION = 1


def build_grants_payload() -> dict:
    return {
        "schema_version": "alice-permissions-grants-v1",
        "site_id": "first-light-lab",
        "default_effect": "DENY",
        "grants": [{
            "grant_id": GRANT_ID,
            "agents": [AGENT_ID],
            "actions": ["set_light_state"],
            "targets": ["ESP-LIGHT-01"],
            "effect": "PERMIT",
            "approval_required": False,
            "parameter_bounds": {"state": {"one_of": ["on", "off"]}},
        }],
    }


def build_subjects_payload() -> dict:
    return {
        "schema_version": "alice-permissions-subjects-v1",
        "site_id": "first-light-lab",
        "users": {USER_ID: {"user_id": USER_ID, "display_name": "Theo (test)",
                            "role": "test-operator"}},
        "agents": {AGENT_ID: {"agent_id": AGENT_ID, "agent_type": "terminal",
                              "responsible_user": USER_ID, "delegator": USER_ID}},
    }


def build_terminal_keys_payload(public_hex: str) -> dict:
    return {
        "schema_version": "alice-terminal-keys-v1",
        "keys": {KEY_ID: {"agent_id": AGENT_ID, "ed25519_public_hex": public_hex}},
    }


def _public_hex(private: Ed25519PrivateKey) -> str:
    return private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def build(out_dir: Path) -> Path:
    release = out_dir / "release"
    trust = out_dir / "trust"
    client = out_dir / "client"
    for directory in (release, trust, client):
        directory.mkdir(parents=True, exist_ok=True)

    terminal_key = Ed25519PrivateKey.generate()
    seed = terminal_key.private_bytes_raw()
    (client / f"{KEY_ID}.seed").write_text(seed.hex() + "\n")

    payloads = {
        "grants.json": build_grants_payload(),
        "subjects.json": build_subjects_payload(),
        "terminal_keys.json": build_terminal_keys_payload(_public_hex(terminal_key)),
    }
    for name, payload in payloads.items():
        (release / name).write_bytes(canonical_bytes(payload))

    digests = {name: digest_of(payload) for name, payload in payloads.items()}
    manifest = build_manifest(digests, model_binding={"model_ids": []},
                              generation=GENERATION)
    manifest["bundle_id"] = f"first-light-{GENERATION:06d}"
    manifest["site_id"] = "first-light-lab"
    manifest["release_note"] = ("First-light test release: one PERMIT grant, "
                                "demonstration trust only.")

    manifest_key = Ed25519PrivateKey.generate()
    signed_bytes, signature = sign_manifest(manifest, manifest_key)
    (release / "manifest.json").write_bytes(signed_bytes)
    (release / "manifest.sig").write_bytes(signature)
    (trust / "manifest_public.hex").write_text(_public_hex(manifest_key) + "\n")
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    release = build(args.out_dir)
    print(f"release written: {release}")
    print("WARNING: demonstration trust only; do not provision these keys in production.")


if __name__ == "__main__":
    main()
