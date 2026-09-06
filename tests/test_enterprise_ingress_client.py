"""Cloud-agent enterprise-ingress path: envelope contract + end-to-end over the
local mock ingress (loopback only; no .50 host, no Pi, no ESP).

Covers:
- the signed envelope matches the shared contract (3 keys; signature over
  ``canonical_bytes(request)``; verifies with the agent's public key);
- ``dry_run`` builds but does not send;
- a verified request yields ``enterprise_receipt.verified: true`` and a
  CHALLENGE decision, and is recorded in the receipts stand-in;
- an unknown key / bad signature is rejected (401) and NOT forwarded.
"""
from __future__ import annotations

import base64
import json
import threading
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from dcamr.audit.event_contract import canonical_bytes

import cloud.enterprise_ingress_client as client
from lab.enterprise_ingress.mock_ingress import MockIngress, build_server, _load_public_keys

AGENT_ID = "elec-agent-01"
KEY_ID = f"{AGENT_ID}-k1"


@pytest.fixture
def agent_key(tmp_path: Path) -> Path:
    """Write an ephemeral agent private seed (hex) and its <key_id>.pub."""
    sk = Ed25519PrivateKey.generate()
    key_file = tmp_path / "agent.key"
    key_file.write_text(sk.private_bytes_raw().hex())
    keys_dir = tmp_path / "pubkeys"
    keys_dir.mkdir()
    (keys_dir / f"{KEY_ID}.pub").write_bytes(sk.public_key().public_bytes_raw())
    return key_file


def _pubkeys_dir(agent_key: Path) -> Path:
    return agent_key.parent / "pubkeys"


def test_build_and_sign_matches_contract(agent_key: Path):
    seed = client.load_seed(agent_key)
    request = client.build_request(state="on", agent_id=AGENT_ID, target="ESP-LIGHT-01")
    envelope = client.sign_envelope(seed, request, key_id=KEY_ID)

    assert set(envelope) == {"request", "key_id", "signature"}
    assert set(request) == {
        "schema_version", "request_id", "agent_id", "action", "target",
        "parameters", "issued_at",
    }
    # Signature verifies over the exact canonical bytes the Pi will re-derive.
    pub = Ed25519PrivateKey.from_private_bytes(seed).public_key()
    pub.verify(base64.b64decode(envelope["signature"]), canonical_bytes(envelope["request"]))


def test_dry_run_builds_but_does_not_send(agent_key: Path):
    result = client.submit_governed_request(
        state="on", agent_id=AGENT_ID, key_file=agent_key, dry_run=True
    )
    assert result.sent is False
    assert result.http_status is None
    assert set(result.envelope) == {"request", "key_id", "signature"}
    assert result.envelope["request"]["request_id"] == result.request_id


def test_send_requires_base_url_when_not_dry_run(agent_key: Path):
    with pytest.raises(ValueError, match="base_url is required"):
        client.submit_governed_request(state="on", agent_id=AGENT_ID, key_file=agent_key)


@pytest.fixture
def running_ingress(agent_key: Path, tmp_path: Path):
    receipts = tmp_path / "receipts.jsonl"
    ingress = MockIngress(_load_public_keys(_pubkeys_dir(agent_key)), receipts_path=receipts)
    server = build_server("127.0.0.1", 0, ingress)  # port 0 -> ephemeral
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}", receipts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_end_to_end_verified_request_challenges_and_is_receipted(running_ingress, agent_key: Path):
    base_url, receipts = running_ingress

    ok, health = client.health(base_url)
    assert ok and health["service"] == "mock-enterprise-ingress"

    result = client.submit_governed_request(
        state="on", base_url=base_url, agent_id=AGENT_ID, key_file=agent_key,
        target="ESP-LIGHT-01", request_id="wireless-laptop-cloudtest",
    )
    assert result.sent is True
    assert result.http_status == 202          # CHALLENGE
    assert result.receipt_verified is True
    assert result.decision == "CHALLENGE"
    assert result.enterprise_receipt["request_id"] == "wireless-laptop-cloudtest"
    # Signature was preserved unmodified through the receipt.
    assert result.enterprise_receipt["signature"] == result.envelope["signature"]

    lines = receipts.read_text().strip().splitlines()
    recorded = [json.loads(x) for x in lines]
    assert any(r["request_id"] == "wireless-laptop-cloudtest" and r["verified"] for r in recorded)


def test_unknown_key_is_rejected_and_not_forwarded(running_ingress, tmp_path: Path):
    base_url, receipts = running_ingress
    # A different key the ingress does not know about.
    stranger = tmp_path / "stranger.key"
    stranger.write_text(Ed25519PrivateKey.generate().private_bytes_raw().hex())

    result = client.submit_governed_request(
        state="on", base_url=base_url, agent_id=AGENT_ID, key_file=stranger,
        request_id="stranger-req",
    )
    assert result.http_status == 401
    assert result.receipt_verified is False
    assert result.decision != "CHALLENGE"
    # Recorded as an unverified receipt, but never given a Pi decision.
    recorded = [json.loads(x) for x in receipts.read_text().strip().splitlines()]
    stranger_rows = [r for r in recorded if r["request_id"] == "stranger-req"]
    assert stranger_rows and all(r["verified"] is False for r in stranger_rows)
