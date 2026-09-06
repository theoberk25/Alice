"""Terminal agent client for the first-light test (Mac side).

Builds the agreed fixed request, signs its canonical bytes with the test-only
terminal private key, POSTs it to the Pi runtime and prints the decision and
execution status. --repeat re-sends the IDENTICAL request_id to demonstrate
that a retry never executes twice. Placement per AGENTS.md.
"""

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from urllib import error as urlerror, request as urlrequest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from dcamr.audit.event_contract import canonical_bytes

KEY_ID = "term-agent-01-k1"
AGENT_ID = "term-agent-01"


def build_envelope(seed: bytes, *, state: str, request_id: str | None = None,
                   action: str = "set_light_state", target: str = "ESP-LIGHT-01",
                   agent_id: str = AGENT_ID, key_id: str = KEY_ID) -> dict:
    request = {
        "schema_version": "1.0",
        "request_id": request_id or str(uuid.uuid4()),
        "agent_id": agent_id,
        "action": action,
        "target": target,
        "parameters": {"state": state},
        "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    signature = Ed25519PrivateKey.from_private_bytes(seed).sign(canonical_bytes(request))
    return {"request": request, "key_id": key_id,
            "signature": base64.b64encode(signature).decode("ascii")}


def send(url: str, envelope: dict) -> tuple[int, dict]:
    body = json.dumps(envelope).encode("utf-8")
    req = urlrequest.Request(url.rstrip("/") + "/request", data=body, method="POST",
                             headers={"Content-Type": "application/json"})
    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Pi runtime base URL")
    parser.add_argument("--key-file", type=Path, required=True,
                        help="terminal private key seed (hex) from build_release")
    parser.add_argument("--state", choices=("on", "off"), default="on")
    parser.add_argument("--agent", default=AGENT_ID,
                        help="agent id (key file must match <agent>-k1)")
    parser.add_argument("--request-id", default=None)
    parser.add_argument("--repeat", type=int, default=1,
                        help="send the identical envelope N times (idempotency check)")
    args = parser.parse_args()
    seed = bytes.fromhex(args.key_file.read_text().strip())
    envelope = build_envelope(seed, state=args.state, request_id=args.request_id,
                              agent_id=args.agent, key_id=f"{args.agent}-k1")
    print(f"request_id: {envelope['request']['request_id']}")
    for attempt in range(max(1, args.repeat)):
        status, payload = send(args.url, envelope)
        replay = " (replayed recorded outcome)" if payload.get("idempotent_replay") else ""
        print(f"attempt {attempt + 1}: HTTP {status} decision={payload.get('decision')} "
              f"reason={payload.get('reason_code')} execution={payload.get('execution')} "
              f"observed={payload.get('observed_state')}{replay}")


if __name__ == "__main__":
    main()
