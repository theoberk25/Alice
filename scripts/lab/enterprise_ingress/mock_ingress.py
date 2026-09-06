"""Local mock enterprise ingress — a TEST STAND-IN, not the production .50 service.

Purpose: let the cloud-agent enterprise path
(:mod:`cloud.enterprise_ingress_client`) be exercised end to end **on one Mac**,
without Jared's .50 host, the Pi, or the ESP. It mirrors the enterprise-first
behaviour we want the real ingress to have:

    signed /request  ->  verify Ed25519 signature (preserving request_id + sig)
                     ->  record an enterprise receipt (a JSONL Wazuh stand-in)
                     ->  forward to the Pi (or synthesize its CHALLENGE)
                     ->  return {enterprise_receipt, pi, decision}

What it is NOT:
- It does not implement the production authenticated ingress on 192.168.50.50.
- Its "Wazuh" is an appended JSONL file, not the real indexer.
- By default it SYNTHESIZES the Pi's CHALLENGE; pass ``--pi-url`` to actually
  forward to a running Pi/mock runtime instead.

Binds 127.0.0.1 by default. Run::

    python -m lab.enterprise_ingress.mock_ingress --keys /path/to/pubkeys --port 8790

``--keys`` is a directory of ``<key_id>.pub`` files (raw 32-byte Ed25519 public
keys) that are allowed to submit. See ``docs/integration/cloud-agent-enterprise-ingress.md``.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error as urlerror, request as urlrequest

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from dcamr.audit.event_contract import canonical_bytes

_ENVELOPE_KEYS = {"request", "key_id", "signature"}


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_public_keys(keys_dir: Path) -> dict[str, Ed25519PublicKey]:
    keys: dict[str, Ed25519PublicKey] = {}
    for pub in sorted(keys_dir.glob("*.pub")):
        keys[pub.stem] = Ed25519PublicKey.from_public_bytes(pub.read_bytes())
    return keys


class MockIngress:
    """The verify -> receipt -> forward logic, independent of the HTTP layer."""

    def __init__(self, public_keys, *, receipts_path: Path, pi_url: str | None = None):
        self.public_keys = public_keys
        self.receipts_path = receipts_path
        self.pi_url = pi_url

    def handle(self, envelope) -> tuple[int, dict]:
        if type(envelope) is not dict or set(envelope) != _ENVELOPE_KEYS:
            return 400, {"enterprise_receipt": {"verified": False},
                         "decision": "DENY", "reason_code": "MALFORMED_ENVELOPE"}
        request = envelope["request"]
        key_id = envelope["key_id"]
        try:
            signature = base64.b64decode(envelope["signature"], validate=True)
            request_bytes = canonical_bytes(request)
        except Exception:
            return 400, {"enterprise_receipt": {"verified": False},
                         "decision": "DENY", "reason_code": "MALFORMED_ENVELOPE"}

        key = self.public_keys.get(key_id)
        verified = False
        if key is not None:
            try:
                key.verify(signature, request_bytes)
                verified = True
            except InvalidSignature:
                verified = False

        request_id = request.get("request_id") if isinstance(request, dict) else None
        receipt = {
            "verified": verified,
            "request_id": request_id,
            "key_id": key_id,
            "received_at": _utc_now_z(),
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "signature": envelope["signature"],  # preserved, unmodified
            "wazuh_indexed": False,
        }
        if not verified:
            # Enterprise-first guardrail: never forward an unverified request.
            self._record(receipt)
            return 401, {"enterprise_receipt": receipt,
                         "decision": "DENY", "reason_code": "BAD_SIGNATURE"}

        receipt["wazuh_indexed"] = True  # stand-in: appended to the JSONL "index"
        self._record(receipt)

        status, pi_response = self._forward_to_pi(envelope, request_id)
        return status, {"enterprise_receipt": receipt,
                        "pi": pi_response,
                        "decision": pi_response.get("decision")}

    def _forward_to_pi(self, envelope, request_id) -> tuple[int, dict]:
        if not self.pi_url:
            # Synthesize the Pi's first-light outcome: permission review -> CHALLENGE.
            return 202, {"request_id": request_id, "decision": "CHALLENGE",
                         "reason_code": "PERMISSION_REVIEW_REQUIRED",
                         "execution": None, "observed_state": None,
                         "note": "synthesized by mock ingress (no --pi-url)"}
        body = json.dumps(envelope).encode("utf-8")
        req = urlrequest.Request(self.pi_url.rstrip("/") + "/request", data=body,
                                 method="POST", headers={"Content-Type": "application/json"})
        try:
            with urlrequest.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except Exception:
                return exc.code, {"decision": "DENY", "reason_code": "PI_ERROR"}
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            return 502, {"decision": "DENY", "reason_code": "PI_UNAVAILABLE", "error": str(exc)}

    def _record(self, receipt: dict) -> None:
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.receipts_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, sort_keys=True) + "\n")


def make_handler(ingress: MockIngress):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):  # quiet by default
            pass

        def _send(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok", "service": "mock-enterprise-ingress",
                                 "time": _utc_now_z(), "forwards_to": ingress.pi_url or "synthesized"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/request":
                self._send(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                envelope = json.loads(raw.decode("utf-8"))
            except ValueError:
                self._send(400, {"enterprise_receipt": {"verified": False},
                                 "decision": "DENY", "reason_code": "MALFORMED_JSON"})
                return
            status, payload = ingress.handle(envelope)
            self._send(status, payload)

    return Handler


def build_server(host: str, port: int, ingress: MockIngress) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(ingress))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--keys", type=Path, required=True, help="dir of <key_id>.pub Ed25519 public keys")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8790)
    p.add_argument("--receipts", type=Path, default=Path("artifacts/enterprise-ingress/receipts.jsonl"),
                   help="JSONL Wazuh stand-in (enterprise receipts are appended here)")
    p.add_argument("--pi-url", default=None, help="if set, forward verified requests to this Pi runtime base URL")
    args = p.parse_args(argv)

    ingress = MockIngress(_load_public_keys(args.keys), receipts_path=args.receipts, pi_url=args.pi_url)
    server = build_server(args.host, args.port, ingress)
    print(f"mock enterprise ingress: http://{args.host}:{args.port}/  "
          f"(/health, /request)  keys={len(ingress.public_keys)}  "
          f"forward={'->'+args.pi_url if args.pi_url else 'synthesized CHALLENGE'}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
