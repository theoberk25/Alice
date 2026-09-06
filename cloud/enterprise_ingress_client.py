"""Cloud-agent client for the enterprise-first ingress path.

This is the **cloud side** of getting the ADK cloud agent into the governed
directed flow. Instead of the agent talking straight to the Pi, a governed
action becomes a signed envelope that is POSTed to the **enterprise ingress**
(on the enterprise/SIEM Mac, e.g. ``http://192.168.50.50:8790``). The ingress
records an enterprise receipt in Wazuh and only then forwards to the Pi, which
returns the decision (CHALLENGE -> HOLD for the first-light test).

Contract (identical to the Pi's ``/request`` and to
``scripts/lab/first_light/terminal_client.py``): the wire envelope is exactly

    {"request": {...}, "key_id": "<id>", "signature": "<b64 Ed25519>"}

where the signature is over ``canonical_bytes(request)`` — the one authoritative
canonicalization in :mod:`dcamr.audit.event_contract`. We deliberately reuse it
rather than inventing a second format. See
``docs/integration/cloud-agent-enterprise-ingress.md``.

Safety posture:
- **No hardcoded destination.** The base URL is always supplied explicitly
  (arg or ``ALICE_ENTERPRISE_INGRESS_URL``); nothing fires unless a caller
  provides one.
- **request_id and signature are preserved end to end** — the ingress and Pi
  must see the same signed bytes the agent produced.
- This module never marks anything as a trusted permission and never retries a
  decision; it submits once and returns what came back.
"""
from __future__ import annotations

import base64
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urlerror, request as urlrequest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from dcamr.audit.event_contract import canonical_bytes

# Only the two states the first-light action uses; matches the Pi enforcement.
_STATES = ("on", "off")
_LIGHT_TARGETS = tuple(f"ESP-LIGHT-{i:02d}" for i in range(1, 9))


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_request(
    *,
    state: str,
    action: str = "set_light_state",
    target: str = "ESP-LIGHT-01",
    agent_id: str,
    request_id: str | None = None,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Build the fixed-shape request object (the signed inner payload)."""
    if state not in _STATES:
        raise ValueError(f"state must be one of {_STATES}, got {state!r}")
    return {
        "schema_version": "1.0",
        "request_id": request_id or str(uuid.uuid4()),
        "agent_id": agent_id,
        "action": action,
        "target": target,
        "parameters": {"state": state},
        "issued_at": issued_at or _utc_now_z(),
    }


def sign_envelope(seed: bytes, request: dict[str, Any], *, key_id: str) -> dict[str, Any]:
    """Return the ``{request, key_id, signature}`` envelope for a request.

    ``seed`` is the 32-byte Ed25519 private seed. The signature covers
    ``canonical_bytes(request)`` so the ingress and Pi verify the exact bytes.
    """
    signature = Ed25519PrivateKey.from_private_bytes(seed).sign(canonical_bytes(request))
    return {
        "request": request,
        "key_id": key_id,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def load_seed(key_file: str | Path) -> bytes:
    """Read a hex-encoded Ed25519 seed from ``key_file`` (same format the lab
    tooling writes). Kept secret; never logged."""
    seed = bytes.fromhex(Path(key_file).read_text().strip())
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes (64 hex chars)")
    return seed


@dataclass(frozen=True)
class IngressResult:
    """Outcome of an ingress submission.

    ``sent`` is False for a dry run (envelope built but not transmitted).
    """

    request_id: str
    envelope: dict[str, Any]
    sent: bool
    http_status: int | None = None
    response: dict[str, Any] | None = None

    @property
    def enterprise_receipt(self) -> dict[str, Any] | None:
        return (self.response or {}).get("enterprise_receipt")

    @property
    def receipt_verified(self) -> bool:
        return bool((self.enterprise_receipt or {}).get("verified"))

    @property
    def decision(self) -> str | None:
        resp = self.response or {}
        # The ingress echoes the Pi decision at top level and/or under "pi".
        return resp.get("decision") or (resp.get("pi") or {}).get("decision")


def health(base_url: str, *, timeout: float = 5.0) -> tuple[bool, dict[str, Any]]:
    """GET ``<base_url>/health``. Returns ``(ok, payload)``; never raises for a
    reachable-but-unhealthy endpoint."""
    url = base_url.rstrip("/") + "/health"
    req = urlrequest.Request(url, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            payload = _read_json(response)
            return 200 <= response.status < 300, payload
    except urlerror.HTTPError as exc:
        return False, _read_json(exc)
    except (urlerror.URLError, TimeoutError, OSError) as exc:  # unreachable host
        return False, {"error": str(exc)}


def _post_request(base_url: str, envelope: dict[str, Any], *, timeout: float) -> tuple[int, dict[str, Any]]:
    import json

    url = base_url.rstrip("/") + "/request"
    body = json.dumps(envelope).encode("utf-8")
    req = urlrequest.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
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


def submit_governed_request(
    *,
    state: str,
    base_url: str | None = None,
    agent_id: str | None = None,
    key_file: str | Path | None = None,
    action: str = "set_light_state",
    target: str = "ESP-LIGHT-01",
    request_id: str | None = None,
    dry_run: bool = False,
    preflight_health: bool = True,
    timeout: float = 15.0,
) -> IngressResult:
    """Build, sign and (unless ``dry_run``) submit one governed request.

    Configuration falls back to the documented env vars:
      * ``base_url``  <- ``ALICE_ENTERPRISE_INGRESS_URL``
      * ``agent_id``  <- ``ALICE_AGENT_ID``
      * ``key_file``  <- ``ALICE_AGENT_KEY_FILE``  (private seed; never committed)

    ``dry_run=True`` returns the signed envelope WITHOUT sending — useful for
    handing a fresh signed request to the ingress owner without firing it.
    """
    base_url = base_url or os.environ.get("ALICE_ENTERPRISE_INGRESS_URL")
    agent_id = agent_id or os.environ.get("ALICE_AGENT_ID")
    key_file = key_file or os.environ.get("ALICE_AGENT_KEY_FILE")
    if not agent_id:
        raise ValueError("agent_id is required (set ALICE_AGENT_ID)")
    if not key_file:
        raise ValueError("key_file is required (set ALICE_AGENT_KEY_FILE)")

    request = build_request(
        state=state, action=action, target=target, agent_id=agent_id, request_id=request_id
    )
    envelope = sign_envelope(load_seed(key_file), request, key_id=f"{agent_id}-k1")
    rid = request["request_id"]

    if dry_run:
        return IngressResult(request_id=rid, envelope=envelope, sent=False)

    if not base_url:
        raise ValueError(
            "base_url is required to send (set ALICE_ENTERPRISE_INGRESS_URL), "
            "or pass dry_run=True to only build the signed envelope"
        )
    if preflight_health:
        ok, payload = health(base_url, timeout=min(timeout, 5.0))
        if not ok:
            raise ConnectionError(f"ingress /health not ready at {base_url}: {payload}")

    status, response = _post_request(base_url, envelope, timeout=timeout)
    return IngressResult(
        request_id=rid, envelope=envelope, sent=True, http_status=status, response=response
    )


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Submit one governed request to the enterprise ingress.")
    p.add_argument("--url", default=None, help="ingress base URL (default $ALICE_ENTERPRISE_INGRESS_URL)")
    p.add_argument("--agent", default=None, help="agent id (default $ALICE_AGENT_ID); key_id is <agent>-k1")
    p.add_argument("--key-file", default=None, help="private Ed25519 seed hex (default $ALICE_AGENT_KEY_FILE)")
    p.add_argument("--state", choices=_STATES, default="on")
    p.add_argument("--target", choices=_LIGHT_TARGETS, default="ESP-LIGHT-01")
    p.add_argument("--request-id", default=None)
    p.add_argument("--dry-run", action="store_true", help="build+print the signed envelope, do not send")
    p.add_argument("--no-health", action="store_true", help="skip the /health preflight")
    args = p.parse_args(argv)

    result = submit_governed_request(
        state=args.state,
        base_url=args.url,
        agent_id=args.agent,
        key_file=args.key_file,
        target=args.target,
        request_id=args.request_id,
        dry_run=args.dry_run,
        preflight_health=not args.no_health,
    )
    if not result.sent:
        print(f"request_id: {result.request_id} (dry run — not sent)")
        print(json.dumps(result.envelope, indent=2))
        return 0
    print(
        f"request_id: {result.request_id} HTTP {result.http_status} "
        f"receipt.verified={result.receipt_verified} decision={result.decision}"
    )
    print(json.dumps(result.response, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
