"""Enterprise SIEM console for the ALICE edge fleet, served from this machine.

    .venv/bin/python -m lab.enterprise_sim.console

This is the **enterprise cybersecurity platform** view, not ALICE. The topology
it sits in has three tiers:

    Enterprise SIEM (this console, Wazuh)   authoritative, cloud side
      |  publishes permissions, baselines and model releases downstream
      v  receives DDIL activity, findings and audit back upstream
    ALICE Pi (edge decision node)           caches releases for offline use,
      ^                                     governs local actions while
      |  data and decisions                 disconnected, reports on reconnect
    ALICE technician software (Mac)         operator surface, talks to the Pi

The enterprise never sees an offline request as it happens. It sees the release
it published, and the record the edge node returned when connectivity came back.
Keeping that direction visible is the point of this console: everything here is
either something the enterprise sent down, or something the edge sent up.

Reads the live Wazuh indexer when reachable and falls back to the generated
artifacts on disk when not, and always says which. Read-only: it authorizes
nothing, executes nothing, and computes no decisions of its own. The permission
matrix is derived from the signed bundle; the decisions listed were made by an
edge node, offline, under its own authority.
"""

from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import json
import os
from pathlib import Path
from common.repository_paths import repository_root
import ssl
import urllib.error
import urllib.request

from ..scenario import AGENTS, ELECTRICAL, LOADS, SITE, SYSTEMS, UNITS, USERS
from ..wazuh import AGENT_GROUPS, ENDPOINTS

ROOT = repository_root()
ARTIFACTS = ROOT / "artifacts" / "enterprise-sim"
HERE = Path(__file__).resolve().parent

# First-light live edge feed: the console proxies the Pi runtime's read-only
# GET /events ledger projection. This is a lab shortcut for the demonstration —
# in the product topology the enterprise sees edge activity only after
# reconnect; the live view belongs to the technician surface.
EDGE_NODE = os.environ.get("ALICE_PI", "192.168.50.20:8080")

INDEXER = os.environ.get("ALICE_INDEXER", "https://localhost:9200")
INDEXER_USER = os.environ.get("ALICE_INDEXER_USER", "admin")
INDEXER_PW = os.environ.get("ALICE_INDEXER_PW", "SecretPassword")

# Self-signed certificates are expected for a local single-node deployment.
# This context is for talking to that local stack only.
_UNVERIFIED = ssl.create_default_context()
_UNVERIFIED.check_hostname = False
_UNVERIFIED.verify_mode = ssl.CERT_NONE


def _indexer_request(path: str, body: dict | None = None, timeout: float = 4.0):
    url = f"{INDEXER.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    token = base64.b64encode(f"{INDEXER_USER}:{INDEXER_PW}".encode()).decode()
    request = urllib.request.Request(
        url, data=data, method="POST" if data else "GET",
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout, context=_UNVERIFIED) as response:
        return json.loads(response.read())


def indexer_status() -> dict:
    try:
        info = _indexer_request("/")
        return {"reachable": True, "cluster": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
                "endpoint": INDEXER}
    except Exception as error:  # noqa: BLE001 - any failure means "use local files"
        return {"reachable": False, "endpoint": INDEXER,
                "detail": f"{type(error).__name__}"}


# --------------------------------------------------------------------------
# Loading: live indexer first, generated artifacts second
# --------------------------------------------------------------------------

def load_bundle() -> tuple[dict, str]:
    """Return (payloads, source). Payloads keyed by bundle filename."""
    try:
        hits = _indexer_request("/alice-permissions/_search",
                                {"size": 1, "sort": [{"generation": "desc"}]})
        rows = hits.get("hits", {}).get("hits", [])
        if rows:
            document = rows[0]["_source"]
            payloads = {name: json.loads(base64.b64decode(blob))
                        for name, blob in document["payload_b64"].items()}
            payloads["manifest.json"] = json.loads(
                base64.b64decode(document["manifest_b64"]))
            return payloads, "LIVE_INDEXER"
    except Exception:  # noqa: BLE001
        pass

    generation = (ARTIFACTS / "usb" / "permissions" / "active").read_text().strip()
    directory = ARTIFACTS / "usb" / "permissions" / generation
    payloads = {path.name: json.loads(path.read_text())
                for path in sorted(directory.glob("*.json"))}
    return payloads, "LOCAL_USB_IMAGE"


def load_bundle_generation(generation: int) -> tuple[dict | None, str]:
    """Fetch one specific release. Used to show what an edge node still holds."""
    try:
        hits = _indexer_request("/alice-permissions/_search",
                                {"size": 1, "query": {"term": {"generation": generation}}})
        rows = hits.get("hits", {}).get("hits", [])
        if rows:
            document = rows[0]["_source"]
            payloads = {name: json.loads(base64.b64decode(blob))
                        for name, blob in document["payload_b64"].items()}
            payloads["manifest.json"] = json.loads(
                base64.b64decode(document["manifest_b64"]))
            return payloads, "LIVE_INDEXER"
    except Exception:  # noqa: BLE001
        pass

    # The USB image on disk is exactly what the simulated node cached.
    directory = (ARTIFACTS / "usb" / "permissions" / "generations" / f"{generation:06d}")
    if directory.is_dir():
        return ({path.name: json.loads(path.read_text())
                 for path in sorted(directory.glob("*.json"))}, "LOCAL_USB_IMAGE")
    return None, "UNAVAILABLE"


def build_sync_delta(published: dict, cached: dict | None) -> dict:
    """What an edge node is missing because it has not resynchronized.

    This is the enterprise's view of the gap, computed by comparing two signed
    releases. It is not a claim about what the node did with the release it has:
    that only appears in the activity it returns.
    """
    if not cached:
        return {"available": False,
                "note": "The release this node cached is not retrievable here."}

    def index(bundle, key, field):
        return {entry[field]: entry for entry in bundle[key][key.split(".")[0]]}

    new_grants = {g["grant_id"]: g for g in published["grants.json"]["grants"]}
    old_grants = {g["grant_id"]: g for g in cached["grants.json"]["grants"]}
    new_revs = {(r["subject_type"], r["subject_id"]): r
                for r in published["revocations.json"]["revocations"]}
    old_revs = {(r["subject_type"], r["subject_id"]): r
                for r in cached["revocations.json"]["revocations"]}

    changed = []
    for grant_id in sorted(set(new_grants) & set(old_grants)):
        new, old = new_grants[grant_id], old_grants[grant_id]
        if new.get("agents") != old.get("agents"):
            changed.append({"grant_id": grant_id, "field": "agents",
                            "was": old.get("agents"), "now": new.get("agents")})
        if new.get("parameter_bounds") != old.get("parameter_bounds"):
            changed.append({"grant_id": grant_id, "field": "parameter_bounds",
                            "was": old.get("parameter_bounds"),
                            "now": new.get("parameter_bounds")})

    # A revocation the node has not seen is the sharp end of a stale cache: it
    # keeps honouring a grant the enterprise has already withdrawn.
    unseen_revocations = [new_revs[key] for key in sorted(set(new_revs) - set(old_revs))]
    withdrawn = sorted(set(old_grants) - set(new_grants))
    still_honoured = []
    for grant_id in withdrawn:
        still_honoured.append({"grant_id": grant_id,
                               "agents": old_grants[grant_id]["agents"],
                               "actions": old_grants[grant_id]["actions"]})

    return {
        "available": True,
        "published_generation": published["manifest.json"]["generation"],
        "cached_generation": cached["manifest.json"]["generation"],
        "grants_added": sorted(set(new_grants) - set(old_grants)),
        "grants_withdrawn_but_still_cached": still_honoured,
        "grants_changed": changed,
        "unseen_revocations": unseen_revocations,
        "revocation_epoch": {
            "published": published["revocations.json"]["revocation_epoch"],
            "cached": cached["revocations.json"]["revocation_epoch"],
        },
    }


def load_decisions() -> tuple[list, str]:
    try:
        hits = _indexer_request(
            "/alice-audit-*/_search",
            {"size": 500, "sort": [{"sequence": "asc"}], "query": {"match_all": {}}})
        rows = hits.get("hits", {}).get("hits", [])
        if rows:
            return [row["_source"] for row in rows], "LIVE_INDEXER"
    except Exception:  # noqa: BLE001
        pass

    path = ARTIFACTS / "logs" / "alice-audit.jsonl"
    if not path.exists():
        return [], "UNAVAILABLE"
    events = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            events.append(json.loads(line)["alice"])
    return events, "LOCAL_AUDIT_LOG"


def load_wazuh_alerts() -> tuple[list, str]:
    """Alerts Wazuh itself produced from the ingested logs, if the stack is up."""
    try:
        hits = _indexer_request(
            "/wazuh-alerts-*/_search",
            {"size": 200, "sort": [{"timestamp": "desc"}],
             "query": {"range": {"rule.level": {"gte": 5}}}})
        rows = hits.get("hits", {}).get("hits", [])
        return [{
            "timestamp": row["_source"].get("timestamp"),
            "level": row["_source"].get("rule", {}).get("level"),
            "rule_id": row["_source"].get("rule", {}).get("id"),
            "description": row["_source"].get("rule", {}).get("description"),
            "agent": row["_source"].get("agent", {}).get("name"),
        } for row in rows], "LIVE_INDEXER"
    except Exception:  # noqa: BLE001
        return [], "UNAVAILABLE"


def load_anomaly() -> dict | None:
    path = ARTIFACTS / "reports" / "voltage-model-experiment.json"
    return json.loads(path.read_text()) if path.exists() else None


# --------------------------------------------------------------------------
# The permission matrix: derived from the bundle, never invented here
# --------------------------------------------------------------------------

ALL_ACTIONS = [
    "read_logs", "query_status", "query_network", "read_meter", "read_asset_record",
    "modify_firewall", "allow_outbound", "set_voltage_setpoint",
    "set_load_shed_priority", "curtail_load", "open_switchgear", "close_switchgear",
    "dispatch_generator", "drop_islanding", "disable_protective_relay",
    "create_work_order", "order_parts", "update_asset_record",
]


def _applies(entry: dict, key: str, value: str) -> bool:
    values = entry.get(key, [])
    return "*" in values or value in values


def build_matrix(bundle: dict) -> dict:
    """Resolve each (agent, action) cell against prohibitions, then grants.

    A prohibition carrying `parameter_match` is CONDITIONAL: it forbids some
    parameter values, not the action outright. Rendering it as an absolute
    denial would misstate what the bundle says.
    """
    grants = bundle["grants.json"]["grants"]
    prohibitions = bundle["prohibitions.json"]["prohibitions"]
    cells = {}

    for agent_id in sorted(AGENTS):
        row = {}
        for action in ALL_ACTIONS:
            absolute, scoped = None, None
            for prohibition in prohibitions:
                if not (_applies(prohibition, "agents", agent_id)
                        and _applies(prohibition, "actions", action)):
                    continue
                # A prohibition only denies the whole cell when it is unscoped:
                # every target, no parameter match, no mode condition. Anything
                # narrower forbids a subset, and rendering it as an absolute
                # denial would misstate the bundle.
                narrowed = (prohibition.get("parameter_match")
                            or prohibition.get("conditions")
                            or "*" not in prohibition.get("targets", []))
                if narrowed:
                    scoped = scoped or prohibition
                else:
                    absolute = absolute or prohibition
                    break
            conditional = scoped

            matched = [grant for grant in grants
                       if _applies(grant, "agents", agent_id)
                       and _applies(grant, "actions", action)]

            if absolute is not None:
                row[action] = {"effect": "PROHIBITED",
                               "reason": absolute["reason_code"],
                               "rule": absolute["prohibition_id"]}
            elif matched:
                grant = matched[0]
                needs_approval = any(g.get("approval_required") for g in matched)
                effect = "PERMIT_WITH_APPROVAL" if needs_approval else "PERMIT"
                cell = {"effect": effect, "rule": grant["grant_id"],
                        "targets": sorted({t for g in matched for t in g["targets"]})}
                if conditional is not None:
                    cell["caveat"] = conditional["prohibition_id"]
                    cell["caveat_reason"] = conditional["reason_code"]
                if grant.get("parameter_bounds"):
                    cell["bounds"] = grant["parameter_bounds"]
                row[action] = cell
            else:
                # No grant: the operative reason is default deny, not the
                # scoped prohibition. Both refuse the request, but reporting
                # a safety rule where none was reached would misattribute it.
                cell = {"effect": "NOT_GRANTED"}
                if conditional is not None:
                    cell["caveat"] = conditional["prohibition_id"]
                    cell["caveat_reason"] = conditional["reason_code"]
                row[action] = cell
        cells[agent_id] = row
    return {"actions": ALL_ACTIONS, "cells": cells}


def build_edge_nodes(decisions: list, manifest: dict) -> list:
    """Summarize each ALICE node from the record it returned upstream.

    Everything here is reconstructed from delivered audit events. A node that
    has not reported since going offline shows its last known state, which is
    not the same as its current one -- the enterprise cannot see a disconnected
    node, and this view must not imply otherwise.
    """
    nodes: dict[str, dict] = {}
    for event in decisions:
        node_id = event.get("node_id")
        if not node_id:
            continue
        node = nodes.setdefault(node_id, {
            "node_id": node_id, "boot_id": event.get("boot_id"),
            "first_seen": event.get("recorded_at"), "last_seen": None,
            "events_returned": 0, "highest_sequence": 0,
            "last_mode": None, "last_authority": None,
            "active_generation": None, "permissions_freshness": None,
            "baseline_package": None, "baseline_version": None,
            "contextual_profiles": [], "checkpoints": 0,
            "last_checkpoint_sequence": None, "chain_head": None,
            "rejected_candidate": None, "reject_reason": None,
            "drift_enterprise_generation": None, "drift_affected": 0,
            "outbox_pending_at_resume": None, "outbox_backlog_remaining": None,
            "audit_capacity_blocked": False,
            "outcomes": {}, "prohibition_denials": 0,
        })
        node["events_returned"] += 1
        node["last_seen"] = event.get("recorded_at")
        node["highest_sequence"] = max(node["highest_sequence"],
                                       event.get("sequence") or 0)
        node["last_mode"] = event.get("mode") or node["last_mode"]
        node["last_authority"] = event.get("authority") or node["last_authority"]
        if event.get("permissions_freshness"):
            node["permissions_freshness"] = event["permissions_freshness"]

        kind = event.get("event_type")
        if kind == "PERMISSIONS_ACTIVATED":
            node["active_generation"] = event.get("generation")
        elif kind == "SYNC_COMPLETED":
            node["baseline_package"] = event.get("baseline_package")
            node["baseline_version"] = event.get("baseline_version")
            node["contextual_profiles"] = event.get("contextual_profiles") or []
        elif kind == "AUDIT_CHECKPOINT":
            node["checkpoints"] += 1
            node["last_checkpoint_sequence"] = event.get("checkpoint_sequence")
            node["chain_head"] = event.get("chain_head")
        elif kind == "PERMISSIONS_REJECTED":
            node["rejected_candidate"] = event.get("candidate_generation")
            node["reject_reason"] = event.get("reason_code")
        elif kind == "PERMISSIONS_DRIFT":
            node["drift_enterprise_generation"] = event.get("enterprise_generation")
            node["drift_affected"] = event.get("affected_decisions") or 0
        elif kind == "OUTBOX_DELIVERY_RESUMED":
            node["outbox_pending_at_resume"] = event.get("pending_events")
        elif kind == "AUTHORITY_TRANSITION":
            if event.get("outbox_backlog_remaining") is not None:
                node["outbox_backlog_remaining"] = event["outbox_backlog_remaining"]
        elif kind == "AUDIT_CAPACITY_BLOCK":
            node["audit_capacity_blocked"] = True
        elif kind == "DECISION":
            outcome = event.get("decision")
            if outcome:
                node["outcomes"][outcome] = node["outcomes"].get(outcome, 0) + 1
            if event.get("prohibition_id"):
                node["prohibition_denials"] += 1

    published = manifest.get("generation")
    for node in nodes.values():
        active = node["active_generation"]
        node["published_generation"] = published
        node["in_sync"] = (active is not None and active == published)
        # Sequence gaps are the enterprise's own integrity check against the
        # last checkpoint it holds. A complete return has no missing numbers.
        node["sequence_complete"] = node["highest_sequence"] == node["events_returned"]
    return sorted(nodes.values(), key=lambda n: n["node_id"])


def build_state() -> dict:
    bundle, bundle_source = load_bundle()
    decisions, decision_source = load_decisions()
    alerts, alert_source = load_wazuh_alerts()
    manifest = bundle.get("manifest.json", {})
    subjects = bundle["subjects.json"]

    # Chain continuity, recomputed here rather than trusted from the record.
    chain_ok, previous = True, "0" * 64
    for event in decisions:
        if event.get("prev_hash") != previous:
            chain_ok = False
            break
        previous = event.get("event_hash", "")

    edge_nodes = build_edge_nodes(decisions, manifest)
    cached_generation = next((node["active_generation"] for node in edge_nodes
                              if node["active_generation"] is not None), None)
    cached_bundle, cached_source = (load_bundle_generation(cached_generation)
                                    if cached_generation is not None else (None, "UNAVAILABLE"))
    delta = build_sync_delta(bundle, cached_bundle)

    return {
        "site": SITE,
        "units": UNITS,
        "sync_delta": delta,
        "cached_bundle_source": cached_source,
        "electrical": ELECTRICAL,
        "sources": {
            "permissions": bundle_source,
            "decisions": decision_source,
            "wazuh_alerts": alert_source,
            "indexer": indexer_status(),
        },
        "manifest": manifest,
        "subjects": subjects,
        "agents": AGENTS,
        "users": USERS,
        "systems": SYSTEMS,
        "loads": LOADS,
        "endpoints": ENDPOINTS,
        "groups": AGENT_GROUPS,
        "matrix": build_matrix(bundle),
        "prohibitions": bundle["prohibitions.json"]["prohibitions"],
        "revocations": bundle["revocations.json"],
        "grants": bundle["grants.json"]["grants"],
        "decisions": decisions,
        "edge_nodes": edge_nodes,
        "chain_intact": chain_ok,
        "wazuh_alerts": alerts,
        "anomaly": load_anomaly(),
    }


# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the console quiet
        pass

    def _send(self, code, body, content_type):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path.split('?')[0] == '/api/soc':
            from urllib.parse import parse_qs, urlsplit
            from .soc import snapshot
            window = parse_qs(urlsplit(self.path).query).get('window', ['all'])[0]
            try:
                self._send(200, json.dumps(snapshot(_indexer_request, window)), 'application/json')
            except ValueError:
                self._send(400, json.dumps({'error':'Unsupported window'}), 'application/json')
            return
        if self.path in ('/soc.css', '/soc.js'):
            mime = 'text/css' if self.path.endswith('.css') else 'text/javascript'
            self._send(200, (HERE / self.path[1:]).read_bytes(), mime)
            return
        if self.path.startswith("/api/edge"):
            after = 0
            if "after=" in self.path:
                try:
                    after = int(self.path.split("after=")[1].split("&")[0])
                except ValueError:
                    pass
            try:
                with urllib.request.urlopen(
                        f"http://{EDGE_NODE}/events?after={after}", timeout=3) as response:
                    events = json.loads(response.read())["events"]
                body = {"reachable": True, "endpoint": EDGE_NODE, "events": events}
            except Exception as error:  # noqa: BLE001 - render the outage, don't crash
                body = {"reachable": False, "endpoint": EDGE_NODE,
                        "detail": type(error).__name__, "events": []}
            self._send(200, json.dumps(body), "application/json")
            return
        if self.path.startswith("/api/state"):
            try:
                self._send(200, json.dumps(build_state()), "application/json")
            except Exception as error:  # noqa: BLE001
                self._send(500, json.dumps({"error": f"{type(error).__name__}: {error}"}),
                           "application/json")
            return
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        self._send(404, "not found", "text/plain")


def main() -> int:
    port = int(os.environ.get("ALICE_CONSOLE_PORT", "8787"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    status = indexer_status()
    print(f"Enterprise SIEM console  http://127.0.0.1:{port}")
    print(f"indexer        {status['endpoint']} "
          f"{'reachable' if status['reachable'] else 'not reachable (serving local files)'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
