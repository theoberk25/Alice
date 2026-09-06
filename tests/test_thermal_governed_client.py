"""Contract tests for the cloud thermal governed client.

The heavy end-to-end (envelope -> runtime -> ALLOW) is already covered by
``tests/test_thermal_runtime.py::test_enterprise_signed_envelope_uses_request_route_and_preserves_identity``.
Here we prove the *client* produces byte-identical wire bytes to
``ThermalRuntime.wire`` and a schema-valid request, so it cannot drift out of
agreement with the runtime that verifies it.
"""
import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from dcamr.audit.event_contract import canonical_bytes
from services.thermal_demo.runtime import ThermalRuntime
from cloud import thermal_governed_client as tgc


_ACTION = {
    "request_id": "cloud-fixed-1",
    "run_id": "a" * 32,
    "expected_revision": 3,
    "agent_id": "cooling-agent-01",
    "action": "set_demo_fan_pct",
    "target": "DEMO-SERVER-01",
    "parameters": {"fan_pct": 70},
}


def test_wire_matches_runtime_byte_for_byte():
    runtime_wire = ThermalRuntime.wire(_ACTION)
    client_wire = tgc.build_wire_request(
        fan_pct=70, run_id="a" * 32, expected_revision=3,
        agent_id="cooling-agent-01", client_request_id="cloud-fixed-1",
    )
    assert client_wire == runtime_wire
    assert canonical_bytes(client_wire) == canonical_bytes(runtime_wire)


def test_wire_request_passes_fan_schema():
    request = tgc.build_wire_request(
        fan_pct=42.5, run_id="b" * 32, expected_revision=0, agent_id="power-agent-01",
    )
    validator = ThermalRuntime.request_validator()
    assert next(validator.iter_errors(request), None) is None
    assert request["parameters"]["fan_basis_points"] == 4250


def test_dry_run_builds_valid_signed_envelope(tmp_path):
    key = Ed25519PrivateKey.generate()
    seed_file = tmp_path / "cooling-agent-01-k1.seed"
    seed_file.write_text(key.private_bytes_raw().hex())

    result = tgc.submit_governed_fan_request(
        fan_pct=70, run_id="c" * 32, expected_revision=5,
        agent_id="cooling-agent-01", key_file=str(seed_file), dry_run=True,
    )
    assert result.sent is False
    env = result.envelope
    assert set(env) == {"request", "key_id", "signature"}
    assert env["key_id"] == "cooling-agent-01-k1"
    assert env["request"]["request_id"] == result.request_id
    # Signature verifies over canonical_bytes(request) with the seed's public half.
    key.public_key().verify(base64.b64decode(env["signature"]), canonical_bytes(env["request"]))


def test_requires_agent_and_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ALICE_AGENT_ID", raising=False)
    monkeypatch.delenv("ALICE_AGENT_KEY_FILE", raising=False)
    with pytest.raises(ValueError):
        tgc.submit_governed_fan_request(fan_pct=70, run_id="d" * 32, expected_revision=0, dry_run=True)


def test_rejects_out_of_range_and_stale_run():
    with pytest.raises(ValueError):
        tgc.build_wire_request(fan_pct=120, run_id="e" * 32, expected_revision=0, agent_id="cooling-agent-01")
    with pytest.raises(ValueError):
        tgc.build_wire_request(fan_pct=70, run_id="not-hex", expected_revision=0, agent_id="cooling-agent-01")
