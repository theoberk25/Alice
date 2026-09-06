"""Cloud-agent client for a governed **thermal** fan request (alice-demo-fan-v1).

This is the thermal counterpart to :mod:`cloud.enterprise_ingress_client`. The
live Pi runs the thermal demo runtime (``services.thermal_demo``), whose
``/request`` route accepts a *signed* ``alice-demo-fan-v1`` envelope via
``ThermalRuntime.submit_envelope`` (added in 92c65dc). That contract is
different from the first-light lights contract the enterprise ingress client
speaks, so this module builds the fan contract instead:

- action ``set_demo_fan_pct`` on ``DEMO-SERVER-01`` with ``fan_basis_points``,
- carrying a **current** ``run_id`` / ``expected_revision`` from the live plant
  (the runtime rejects a stale run), and
- signed with a **fan-permitted** agent key (``cooling-agent-01`` /
  ``power-agent-01``; ``observer-agent-01`` is trusted but not in the fan grant,
  so it would DENY).

Wire shape and canonicalization are kept byte-identical to the runtime:
``request_id = sha256(run_id + '.' + client_request_id)`` and the signature is
over :func:`dcamr.audit.event_contract.canonical_bytes` of the wire request —
the one authoritative canonicalization, reused, never a second format. The
``build_wire_request`` transform mirrors ``ThermalRuntime.wire``; a test asserts
they agree so this cannot drift.

Safety posture (same as the enterprise ingress client):
- **No hardcoded destination.** The base URL is always supplied explicitly
  (arg or ``ALICE_THERMAL_REQUEST_URL``); nothing fires unless a caller gives
  one. For the connected demo this is the enterprise ingress on ``.50``, which
  records the unchanged envelope in Wazuh before forwarding it to ALICE. See
  docs/plans/2026-09-06-demo-part1-cloud-governed-ingress.md.
- **request_id and signature are preserved end to end.**
- Submits once, returns what came back; never retries a decision.
"""
from __future__ import annotations

import base64
import os
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib import error as urlerror, request as urlrequest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from dcamr.audit.event_contract import canonical_bytes

WIRE_SCHEMA = "alice-demo-fan-v1"
FAN_ACTION = "set_demo_fan_pct"
FAN_TARGET = "DEMO-SERVER-01"


def _new_client_request_id() -> str:
    # Matches the runtime's client_request_id pattern ^[A-Za-z0-9_-]{1,64}$.
    return "cloud-" + uuid.uuid4().hex


def build_wire_request(
    *,
    fan_pct: float,
    run_id: str,
    expected_revision: int,
    agent_id: str,
    client_request_id: str | None = None,
) -> dict[str, Any]:
    """Build the signed inner ``alice-demo-fan-v1`` wire request.

    Mirrors ``services.thermal_demo.runtime.ThermalRuntime.wire`` exactly:
    ``request_id`` is ``sha256(run_id + '.' + client_request_id)`` and the fan
    percent is carried as integer ``fan_basis_points``.
    """
    if type(fan_pct) not in (int, float) or not 0 <= fan_pct <= 100:
        raise ValueError("fan_pct must be a number in [0, 100]")
    if abs(fan_pct * 100 - round(fan_pct * 100)) > 1e-9:
        raise ValueError("fan_pct supports at most hundredths of a percent")
    if not (isinstance(run_id, str) and len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id)):
        raise ValueError("run_id must be the plant run_id (32 lowercase hex chars)")
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("expected_revision must be a non-negative integer")
    client_request_id = client_request_id or _new_client_request_id()
    request_id = sha256((run_id + "." + client_request_id).encode()).hexdigest()
    return {
        "schema_version": WIRE_SCHEMA,
        "request_id": request_id,
        "agent_id": agent_id,
        "action": FAN_ACTION,
        "target": FAN_TARGET,
        "parameters": {"fan_basis_points": round(fan_pct * 100)},
        "run_id": run_id,
        "expected_revision": expected_revision,
        "client_request_id": client_request_id,
    }


def sign_envelope(seed: bytes, request: dict[str, Any], *, key_id: str) -> dict[str, Any]:
    """Return the ``{request, key_id, signature}`` envelope, signing
    ``canonical_bytes(request)`` so the Pi verifies the exact bytes."""
    signature = Ed25519PrivateKey.from_private_bytes(seed).sign(canonical_bytes(request))
    return {
        "request": request,
        "key_id": key_id,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def load_seed(key_file: str | Path) -> bytes:
    """Read a hex-encoded 32-byte Ed25519 seed. Kept secret; never logged."""
    seed = bytes.fromhex(Path(key_file).read_text().strip())
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes (64 hex chars)")
    return seed


@dataclass(frozen=True)
class FanRequestResult:
    """Outcome of a governed fan submission. ``sent`` is False for a dry run."""

    request_id: str  # the signed wire request_id (sha256)
    client_request_id: str
    envelope: dict[str, Any]
    sent: bool
    http_status: int | None = None
    response: dict[str, Any] | None = None

    @property
    def decision(self) -> str | None:
        response = self.response or {}
        return response.get("decision") or (response.get("pi") or {}).get("decision")

    @property
    def demo_application(self) -> str | None:
        response = self.response or {}
        return response.get("demo_application") or (response.get("pi") or {}).get("demo_application")

    @property
    def enterprise_receipt_verified(self) -> bool:
        return bool(((self.response or {}).get("enterprise_receipt") or {}).get("verified"))


def fetch_run_context(state_url: str, token: str, *, timeout: float = 5.0) -> dict[str, Any]:
    """GET ``<state_url>/demo/state`` (Bearer ``token``) and return the current
    ``run_id``/``revision``/``values``. Raises if the plant is not RUNNING, so a
    stale run is never signed."""
    import json

    url = state_url.rstrip("/") + "/demo/state"
    req = urlrequest.Request(url, method="GET", headers={"Authorization": "Bearer " + token})
    with urlrequest.urlopen(req, timeout=timeout) as response:
        state = json.loads(response.read().decode("utf-8"))
    if state.get("status") != "RUNNING":
        raise RuntimeError(f"plant is not RUNNING (status={state.get('status')!r}); configure+start it first")
    return {"run_id": state["run_id"], "revision": state["revision"], "values": state.get("values")}


def _post_request(base_url: str, envelope: dict[str, Any], *, timeout: float) -> tuple[int, dict[str, Any]]:
    import json

    url = base_url.rstrip("/") + "/request"
    body = canonical_bytes(envelope)  # exact bytes; the Pi re-verifies the request
    req = urlrequest.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            return response.status, _read_json(response)
    except urlerror.HTTPError as exc:
        return exc.code, _read_json(exc)


def _read_json(response) -> dict[str, Any]:
    import json

    raw = response.read().decode("utf-8") if response is not None else ""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {"raw": raw}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def submit_governed_fan_request(
    *,
    fan_pct: float,
    run_id: str,
    expected_revision: int,
    base_url: str | None = None,
    agent_id: str | None = None,
    key_file: str | Path | None = None,
    client_request_id: str | None = None,
    dry_run: bool = False,
    timeout: float = 15.0,
) -> FanRequestResult:
    """Build, sign and (unless ``dry_run``) submit one governed fan request.

    Config falls back to env: ``base_url`` <- ``ALICE_THERMAL_REQUEST_URL``,
    ``agent_id`` <- ``ALICE_AGENT_ID`` (key_id becomes ``<agent>-k1``),
    ``key_file`` <- ``ALICE_AGENT_KEY_FILE`` (private seed; never committed).

    ``run_id``/``expected_revision`` must come from a current plant snapshot
    (e.g. the agent's ``get_metrics``); a stale run is rejected by the runtime.
    """
    base_url = base_url or os.environ.get("ALICE_THERMAL_REQUEST_URL")
    agent_id = agent_id or os.environ.get("ALICE_AGENT_ID")
    key_file = key_file or os.environ.get("ALICE_AGENT_KEY_FILE")
    if not agent_id:
        raise ValueError("agent_id is required (set ALICE_AGENT_ID)")
    if not key_file:
        raise ValueError("key_file is required (set ALICE_AGENT_KEY_FILE)")

    request = build_wire_request(
        fan_pct=fan_pct, run_id=run_id, expected_revision=expected_revision,
        agent_id=agent_id, client_request_id=client_request_id,
    )
    envelope = sign_envelope(load_seed(key_file), request, key_id=f"{agent_id}-k1")
    rid, crid = request["request_id"], request["client_request_id"]

    if dry_run:
        return FanRequestResult(request_id=rid, client_request_id=crid, envelope=envelope, sent=False)

    if not base_url:
        raise ValueError(
            "base_url is required to send (set ALICE_THERMAL_REQUEST_URL), "
            "or pass dry_run=True to only build the signed envelope"
        )
    status, response = _post_request(base_url, envelope, timeout=timeout)
    return FanRequestResult(
        request_id=rid, client_request_id=crid, envelope=envelope, sent=True,
        http_status=status, response=response,
    )


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Submit one governed thermal fan request (alice-demo-fan-v1).")
    p.add_argument("--url", default=None, help="Pi /request base URL (default $ALICE_THERMAL_REQUEST_URL), e.g. http://192.168.50.20:8080")
    p.add_argument("--agent", default=None, help="agent id (default $ALICE_AGENT_ID); must be fan-permitted (cooling/power)")
    p.add_argument("--key-file", default=None, help="private Ed25519 seed hex (default $ALICE_AGENT_KEY_FILE)")
    p.add_argument("--fan-pct", type=float, required=True, help="requested fan percent [0..100]")
    p.add_argument("--run-id", default=None, help="current plant run_id (32 hex); omit only with --dry-run")
    p.add_argument("--expected-revision", type=int, default=None, help="current plant revision; omit only with --dry-run")
    p.add_argument("--client-request-id", default=None)
    p.add_argument("--state-url", default=None, help="optional: GET <state-url>/demo/state to auto-fill run-id/revision")
    p.add_argument("--state-token", default=None, help="bearer token for --state-url (or $ALICE_THERMAL_STATE_TOKEN)")
    p.add_argument("--dry-run", action="store_true", help="build+print the signed envelope, do not send")
    args = p.parse_args(argv)

    run_id, revision = args.run_id, args.expected_revision
    if args.state_url and (run_id is None or revision is None):
        token = args.state_token or os.environ.get("ALICE_THERMAL_STATE_TOKEN")
        if not token:
            p.error("--state-url requires --state-token or $ALICE_THERMAL_STATE_TOKEN")
        ctx = fetch_run_context(args.state_url, token)
        run_id, revision = ctx["run_id"], ctx["revision"]
    if run_id is None or revision is None:
        if not args.dry_run:
            p.error("a real send needs --run-id and --expected-revision (from get_metrics), or --state-url")
        run_id, revision = run_id or "0" * 32, 0 if revision is None else revision

    result = submit_governed_fan_request(
        fan_pct=args.fan_pct, run_id=run_id, expected_revision=revision,
        base_url=args.url, agent_id=args.agent, key_file=args.key_file,
        client_request_id=args.client_request_id, dry_run=args.dry_run,
    )
    if not result.sent:
        print(f"request_id: {result.request_id} client_request_id: {result.client_request_id} (dry run — not sent)")
        print(json.dumps(result.envelope, indent=2))
        return 0
    print(
        f"request_id: {result.request_id} client_request_id: {result.client_request_id} "
        f"HTTP {result.http_status} receipt.verified={result.enterprise_receipt_verified} "
        f"decision={result.decision} application={result.demo_application}"
    )
    print(json.dumps(result.response, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
