"""Seed Wazuh with the DN-Hacks energy and infrastructure SOC scenario."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import os
import random
import ssl
import urllib.request

from .wazuh import ENDPOINTS

SCENARIO = "dnhacks-energy-infrastructure-v1"
INDEX_PREFIX = "wazuh-alerts-4.x"


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"


def _rule(rule_id, level, description, groups, *, mitre=(), nist=()):
    rule = {"id": str(rule_id), "level": level, "description": description,
            "groups": list(groups), "firedtimes": 1, "mail": False}
    if mitre:
        rule["mitre"] = {"id": [m[0] for m in mitre],
                         "technique": [m[1] for m in mitre],
                         "tactic": sorted({m[2] for m in mitre})}
    if nist:
        rule["nist_800_53"] = list(nist)
    return rule


def build_alerts(anchor: datetime | None = None, seed: int = 899) -> list[dict]:
    """Return deterministic, internally labelled Wazuh-shaped alert documents."""
    anchor = (anchor or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    rng = random.Random(seed)
    endpoints = {row["name"]: row for row in ENDPOINTS}
    rows: list[dict] = []

    def emit(minutes_ago, host, rule, message, *, decoder="json", location="journald", data=None):
        endpoint = endpoints[host]
        rows.append({
            "timestamp": _timestamp(anchor - timedelta(minutes=minutes_ago)),
            "rule": rule,
            "agent": {"id": endpoint["id"], "name": host, "ip": endpoint["ip"]},
            "manager": {"name": "wazuh.manager"},
            "decoder": {"name": decoder},
            "location": location,
            "full_log": message,
            "data": {"simulation": True, "scenario": SCENARIO, **(data or {})},
        })

    # Background volume makes the overview and time histogram look like a working SOC.
    routine_hosts = [name for name in endpoints if name not in {"esp-display-01", "cloud-agent-gcp-01"}]
    users = ["jared.operator", "merek.technician", "theo.agent-owner", "xavier.hardware"]
    for i in range(420):
        host = rng.choice(routine_hosts)
        user = rng.choice(users)
        age = 2 + i * 1.1 + rng.uniform(0, .9)
        choice = rng.random()
        if choice < .48:
            emit(age, host, _rule(5715, 3, "sshd: authentication success.",
                 ("syslog", "sshd", "authentication_success"),
                 mitre=(("T1078", "Valid Accounts", "Initial Access"),), nist=("AC.7", "AU.14")),
                 f"Accepted publickey for {user} from 192.168.50.{rng.randrange(20,80)}",
                 decoder="sshd", location="journald",
                 data={"srcuser": user, "srcip": f"192.168.50.{rng.randrange(20,80)}",
                       "event_category": "authentication", "outcome": "success"})
        elif choice < .70:
            emit(age, host, _rule(5501, 3, "PAM: Login session opened.",
                 ("pam", "authentication_success"), nist=("AC.2", "AU.12")),
                 f"session opened for user {user}", decoder="pam",
                 data={"srcuser": user, "event_category": "identity", "outcome": "success"})
        elif choice < .84:
            emit(age, host, _rule(80792, 4, "System inventory package scan completed.",
                 ("syscollector", "inventory"), nist=("CM.8",)),
                 "syscollector package inventory synchronized",
                 data={"event_category": "inventory", "packages": rng.randrange(384, 812)})
        else:
            emit(age, host, _rule(100200, 4, "Infrastructure service health heartbeat.",
                 ("infrastructure", "service_health"), nist=("SI.4",)),
                 "service status=healthy telemetry=available",
                 data={"event_category": "service_health", "status": "healthy"})

    # Curated analyst-worthy activity across standard Wazuh operating areas.
    curated = [
        (8, "local-agent-01", _rule(5763, 10, "Multiple authentication failures followed by success.",
            ("authentication_failures", "sshd"), mitre=(("T1110", "Brute Force", "Credential Access"),
            ("T1078", "Valid Accounts", "Initial Access")), nist=("AC.7", "SI.4")),
         "nine failed logins preceded a valid public-key session", {"event_category":"authentication","srcip":"192.168.50.77","dstuser":"jared.operator","failure_count":9,"outcome":"success_after_failures"}),
        (14, "server-room-controller-01", _rule(100310, 12, "Unsigned executable created in controller support directory.",
            ("syscheck", "fim", "malware"), mitre=(("T1105", "Ingress Tool Transfer", "Command and Control"),), nist=("SI.3", "SI.7")),
         "FIM added /opt/facility/support/diag-loader", {"event_category":"file_integrity","file_path":"/opt/facility/support/diag-loader","file_operation":"added","file_sha256":"8e52e6c7f63a1eb4721f96cd2d16ef3f9ab5ce9247bc59da77e8df176f936e6b","signature_status":"unsigned"}),
        (19, "technician-console-01", _rule(100211, 7, "Privileged security setting changed.",
            ("audit", "configuration_change"), mitre=(("T1562.001", "Impair Defenses", "Defense Evasion"),), nist=("CM.3", "AU.2")),
         "application firewall preference changed by authorized technician", {"event_category":"configuration","srcuser":"merek.technician","change_ticket":"CHG-DNH-2048","outcome":"authorized"}),
        (26, "application-server-01", _rule(23505, 9, "Vulnerable package detected.",
            ("vulnerability-detector",), nist=("RA.5", "SI.2")),
         "package libwebp 1.2.4 matched CVE-2023-4863", {"event_category":"vulnerability","vulnerability":{"cve":"CVE-2023-4863","package":{"name":"libwebp","version":"1.2.4"},"status":"Active","severity":"High","cvss":{"score":8.8,"version":"3.1"}}}),
        (31, "identity-service-01", _rule(23504, 7, "Vulnerable package detected.",
            ("vulnerability-detector",), nist=("RA.5", "SI.2")),
         "package openssl requires vendor security update", {"event_category":"vulnerability","vulnerability":{"cve":"CVE-2024-0727","package":{"name":"openssl","version":"3.0.7"},"status":"Active","severity":"Medium","cvss":{"score":5.5,"version":"3.1"}}}),
        (38, "application-server-01", _rule(100401, 5, "CIS benchmark check failed.",
            ("sca", "cis_debian12"), nist=("CM.6", "AC.6")),
         "CIS Debian 12 check 5.2.4 failed: SSH root login policy", {"event_category":"configuration_assessment","sca":{"policy":"CIS Debian Linux 12 Benchmark","check_id":"cis_debian12_5.2.4","result":"failed","remediation":"Set PermitRootLogin no"}}),
        (44, "alice-pi-01", _rule(100402, 3, "CIS benchmark check passed.",
            ("sca", "cis_debian12"), nist=("CM.6",)),
         "CIS Debian 12 check 1.4.1 passed: bootloader configuration protected", {"event_category":"configuration_assessment","sca":{"policy":"CIS Debian Linux 12 Benchmark","check_id":"cis_debian12_1.4.1","result":"passed"}}),
        (51, "server-room-controller-01", _rule(100320, 8, "Unexpected shell spawned by controller service.",
            ("linux", "process"), mitre=(("T1059.004", "Unix Shell", "Execution"),), nist=("SI.4",)),
         "/bin/sh spawned by facility-controller.service", {"event_category":"process","process":{"name":"sh","parent":"facility-controller","command_line":"/bin/sh -c [redacted]"},"outcome":"observed"}),
        (63, "server-room-controller-01", _rule(100331, 6, "Repeated denied connection to controller management port.",
            ("firewall", "network"), mitre=(("T1046", "Network Service Discovery", "Discovery"),), nist=("SC.7", "SI.4")),
         "firewall deny tcp 192.168.50.77:51244 -> 10.20.0.10:502", {"event_category":"network","srcip":"192.168.50.77","dstip":"10.20.0.10","dstport":502,"protocol":"tcp","action":"deny","count":14}),
        (72, "alice-pi-01", _rule(100520, 10, "ALICE anomalous fan shutdown request held for technician review.",
            ("alice", "agent_governance", "anomaly"), mitre=(("T0831", "Manipulation of Control", "Impair Process Control"),), nist=("AC.3", "AU.6", "SI.4")),
         "power-agent-01 requested fan 90% -> 0%; outcome=CHALLENGE", {"event_category":"agent_governance","agent_id":"power-agent-01","request_id":"demo-fan-cut-reference","decision":"CHALLENGE","reason_code":"ANOMALY_REVIEW_REQUIRED","anomaly_band":"HIGH","anomaly_score":0.997}),
        (86, "cloud-agent-gcp-01", _rule(100340, 9, "Cloud service account used from a new source network.",
            ("gcp", "iam", "authentication"), mitre=(("T1078.004", "Cloud Accounts", "Initial Access"),), nist=("AC.2", "IA.5")),
         "principal cloud-cooling-agent accessed enterprise ingress from new ASN", {"event_category":"cloud","cloud":{"provider":"gcp","principal":"cloud-cooling-agent","service":"alice-enterprise-ingress","region":"us-east4"},"outcome":"allowed_with_monitoring"}),
        (104, "alice-pi-01", _rule(100360, 5, "USB storage device connected to protected endpoint.",
            ("syscheck", "hardware"), nist=("MP.7", "CM.8")),
         "removable media device attached vendor=Kingston serial=[redacted]", {"event_category":"device_control","device_type":"usb_storage","outcome":"observed"}),
        (127, "server-room-controller-01", _rule(100370, 13, "Known malicious file hash detected.",
            ("malware", "syscheck"), mitre=(("T1204.002", "Malicious File", "Execution"),), nist=("SI.3", "SI.4")),
         "threat intelligence match for diag-loader.exe", {"event_category":"malware","threat":{"name":"Demo.Loader.EI","confidence":"high","source":"local IOC list"},"response_status":"not_connected"}),
        (149, "ups-battery-01", _rule(100380, 6, "Time synchronization offset exceeded policy.",
            ("system", "time_sync"), nist=("AU.8",)),
         "chronyd offset +2.84 seconds exceeds 2 second policy", {"event_category":"system_integrity","offset_seconds":2.84,"outcome":"degraded"}),
    ]
    for age, host, rule, message, data in curated:
        emit(age, host, rule, message, location="sentinel-scenario", data=data)

    rows.sort(key=lambda row: row["timestamp"])
    return rows


def bulk_body(alerts: list[dict]) -> bytes:
    lines = []
    for index, alert in enumerate(alerts, 1):
        day = alert["timestamp"][:10].replace("-", ".")
        lines.append(json.dumps({"create": {"_index": f"{INDEX_PREFIX}-{day}",
                                             "_id": f"{SCENARIO}-{index:04d}"}}, separators=(",", ":")))
        lines.append(json.dumps(alert, separators=(",", ":")))
    return ("\n".join(lines) + "\n").encode()


def load(alerts: list[dict], url: str, user: str, password: str) -> dict:
    body = bulk_body(alerts)
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    request = urllib.request.Request(url.rstrip("/") + "/_bulk", data=body, method="POST",
        headers={"Authorization": "Basic " + token, "Content-Type": "application/x-ndjson"})
    context = ssl.create_default_context(); context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        result = json.load(response)
    statuses = [item["create"]["status"] for item in result.get("items", [])]
    return {"submitted": len(alerts), "created": statuses.count(201),
            "already_present": statuses.count(409),
            "failed": sum(status not in (201, 409) for status in statuses)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write to the configured local indexer")
    parser.add_argument("--url", default=os.environ.get("ALICE_INDEXER", "https://localhost:9200"))
    parser.add_argument("--user", default=os.environ.get("ALICE_INDEXER_USER", "admin"))
    parser.add_argument("--password", default=os.environ.get("ALICE_INDEXER_PW", "SecretPassword"))
    args = parser.parse_args(argv)
    alerts = build_alerts()
    if not args.apply:
        print(json.dumps({"scenario": SCENARIO, "documents": len(alerts),
                          "note": "dry run; pass --apply to seed Wazuh"}, indent=2))
        return 0
    result = load(alerts, args.url, args.user, args.password)
    print(json.dumps({"scenario": SCENARIO, **result}, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
