"""Read-only technician display for the first-light test (CLI form).

Polls the Pi runtime's GET /events feed and prints the correlated chain
user/agent -> request -> permission finding -> assessment -> decision ->
receipt -> observed state per request_id. This is the seam the workstation
console can adopt later; no approval verbs exist on this feed. Note this feed
carries LEDGER events (alice-audit-event-v1), a different format from the
enterprise-sim alice-audit.jsonl chain. Placement per AGENTS.md.
"""

import argparse
import json
import time
from urllib import request as urlrequest


def fetch(url: str, after: int) -> list[dict]:
    with urlrequest.urlopen(f"{url.rstrip('/')}/events?after={after}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))["events"]


def describe(event: dict) -> str:
    correlation, attribution, detail = event["correlation"], event["attribution"], event["detail"]
    request_id = correlation["request_id"] or "-"
    who = attribution["agent_id"] or attribution["actor_kind"]
    user = attribution["responsible_user_id"]
    kind = event["event_type"]
    extra = ""
    if kind in ("REQUEST", "REJECTION", "DECISION"):
        extra = f"outcome={detail['outcome']} reasons={','.join(detail['reason_codes']) or '-'}"
    elif kind == "ASSESSMENT":
        extra = f"status={detail['status']} result={detail['result']} (fixture)"
    elif kind == "EXECUTION_ATTEMPT":
        extra = f"command={detail['command_ref']}"
    elif kind in ("CONTROLLER_RECEIPT", "EXECUTION_RESULT"):
        extra = f"outcome={detail['outcome']}"
    elif kind == "OBSERVED_STATE":
        extra = f"{detail['property']}={detail['value']} quality={detail['quality']}"
    user_part = f" user={user}" if user else ""
    return (f"[{event['sequence']:>4}] {event['time']['recorded_at']} {kind:<18} "
            f"request={request_id} actor={who}{user_part} {extra}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Pi runtime base URL")
    parser.add_argument("--request-id", default=None, help="only show one request chain")
    parser.add_argument("--follow", action="store_true", help="keep polling")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    after = 0
    while True:
        for event in fetch(args.url, after):
            after = max(after, event["sequence"])
            if args.request_id and event["correlation"]["request_id"] != args.request_id:
                continue
            print(describe(event))
        if not args.follow:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
