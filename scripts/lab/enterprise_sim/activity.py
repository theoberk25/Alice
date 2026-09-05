"""Simulated base activity: an ALICE mission audit and surrounding IT events.

The audit stream is what the Pi would append locally and later replay upstream.
It is hash-chained and sequence-numbered so a gap is detectable against the last
uploaded checkpoint. These are invented events for a demonstration; none of them
records a real decision, approval or physical effect.

Field names are namespaced under `alice` so the Wazuh rules in `wazuh.py` match
decoded JSON fields directly.
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import random

from .scenario import AGENTS, ELECTRICAL, USERS

SCHEMA_VERSION = "alice-audit-event-v1"
NODE_ID = "alice-pi-01"
BOOT_ID = "boot.2026-09-05.a41f"
START = datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc)
GENERATION = 42


def _utc(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


class AuditChain:
    """Append-only chain with the identity scheme the outbox replays on."""

    def __init__(self, node_id: str = NODE_ID, boot_id: str = BOOT_ID):
        self.node_id = node_id
        self.boot_id = boot_id
        self.sequence = 0
        self.prev_hash = "0" * 64
        self.events: list[dict] = []
        self.clock = START

    def advance(self, seconds: float) -> None:
        self.clock += timedelta(seconds=seconds)

    def append(self, event_type: str, *, mode: str = "ONLINE",
               authority: str = "ENTERPRISE", after: float = 0.0, **fields) -> dict:
        self.advance(after)
        self.sequence += 1
        body = {
            "schema_version": SCHEMA_VERSION,
            # Monotonic and gap-detectable; also the indexer _id on replay.
            "event_id": f"{self.node_id}:{self.boot_id}:{self.sequence:08d}",
            "node_id": self.node_id,
            "boot_id": self.boot_id,
            "sequence": self.sequence,
            "recorded_at": _utc(self.clock),
            "event_type": event_type,
            "mode": mode,
            "authority": authority,
            **fields,
        }
        body["prev_hash"] = self.prev_hash
        body["event_hash"] = sha256(self.prev_hash.encode("ascii") + canonical(body)).hexdigest()
        self.prev_hash = body["event_hash"]
        record = {"timestamp": _utc(self.clock), "alice": body}
        self.events.append(record)
        return record

    def checkpoint(self, *, after: float = 0.0) -> dict:
        return self.append("AUDIT_CHECKPOINT", after=after,
                           checkpoint_sequence=self.sequence,
                           chain_head=self.prev_hash,
                           event_count=self.sequence,
                           signed_by=f"{self.node_id}.audit-key.2026-09",
                           note="Uploaded checkpoints are what make wholesale "
                                "deletion visible; the chain alone cannot.")


def _attribution(agent_id: str) -> dict:
    agent = AGENTS[agent_id]
    return {
        "agent_id": agent_id,
        "responsible_user": agent["responsible_user"],
        "delegator": agent["delegator"],
        "attribution_source": "sen.iam.permissions-authority",
        "attribution_generation": GENERATION,
    }


def build_audit_stream(seed: int = 1729) -> list[dict]:
    rng = random.Random(seed)
    chain = AuditChain()

    def perm(freshness="FRESH"):
        return {"permissions_generation": GENERATION, "permissions_freshness": freshness}

    # ---------------- ONLINE: sync, then routine enterprise-controlled work ----
    chain.append("PERMISSIONS_CANDIDATE_STAGED", generation=GENERATION,
                 issuer_id="sen.iam.permissions-authority",
                 transport="wazuh-indexer:alice-permissions",
                 staged_bytes=18_442,
                 note="Staged outside the active set; nothing is trusted yet.")
    chain.append("PERMISSIONS_VERIFIED", after=1.4, generation=GENERATION,
                 signature_algorithm="Ed25519",
                 key_id="sen.iam.permissions-authority.2026-09",
                 previous_generation=41, monotonic=True)
    chain.append("PERMISSIONS_ACTIVATED", after=0.3, generation=GENERATION,
                 activation="ATOMIC_POINTER_RENAME",
                 previous_generation=41, revocation_epoch=7, **perm())

    chain.append("SYNC_COMPLETED", after=2.0, cache="normal_behavior",
                 baseline_package="ops-sentinel", baseline_version="42",
                 contextual_profiles=["sen-feeder-voltage-pre", "sen-feeder-voltage-post"],
                 note="Curated release. Live Wazuh alerts never became training labels.")

    for _ in range(4):
        agent_id = rng.choice(["elec-agent-01", "microgrid-agent-01", "maint-agent-01"])
        chain.append("ENTERPRISE_FEED_RECEIVED", after=rng.uniform(20, 90),
                     feed="wazuh-alerts", coverage="COMPLETE",
                     cursor=f"wz-{rng.randrange(10**6, 10**7)}",
                     observed_agent=agent_id,
                     note="Online execution bypasses ALICE; this is feed coverage, "
                          "not a locally observed request.")

    chain.checkpoint(after=5.0)

    # ---------------- Uplink drops: controlled transfer to OFFLINE ------------
    chain.append("AUTHORITY_TRANSITION", after=120.0, from_mode="ONLINE",
                 to_mode="OFFLINE", authority="TRANSFERRING",
                 fence_token="lease.2026-09-05T06:14:22Z.0007",
                 enterprise_commands_retired=True,
                 note="Connectivity loss alone does not grant permission to execute.")
    chain.append("OFFLINE_READINESS", after=3.0, mode="OFFLINE", authority="ALICE",
                 caches_usable=True, model_loaded=True,
                 audit_capacity="OK", audit_free_bytes=41_233_408, **perm())

    off = {"mode": "OFFLINE", "authority": "ALICE"}

    def decision(agent_id, action, target, outcome, *, band=None, score=None,
                 phase="PRE_ACTION", grant=None, prohibition=None, reasons=(),
                 after=0.0, freshness="FRESH", **extra):
        if band is not None:
            chain.append("ANOMALY_ASSESSMENT", after=after, **off,
                         **_attribution(agent_id), action=action, target=target,
                         phase=phase, band=band, score=score, status="OK",
                         profile_id=("sen-feeder-voltage-pre" if phase == "PRE_ACTION"
                                     else "sen-feeder-voltage-post"),
                         model_id="sen-voltage-candidate-001",
                         note="A percentile is not a probability of compromise "
                              "and not a permission.")
            after = 0.2
        fields = dict(off, **_attribution(agent_id))
        fields.update(action=action, target=target, decision=outcome,
                      reason_codes=list(reasons), **perm(freshness), **extra)
        if grant:
            fields["grant_id"] = grant
        if prohibition:
            fields["prohibition_id"] = prohibition
        return chain.append("DECISION", after=after, **fields)

    # Routine allowed work: the electrician agent reads and nudges feeder B.
    decision("elec-agent-01", "read_meter", "FEEDER-B-RTU", "ALLOW", after=18.0,
             grant="G-ELEC-READ", reasons=["PERMITTED", "NO_MODEL_REQUIRED"])

    decision("elec-agent-01", "set_voltage_setpoint", "FEEDER-B-RTU", "ALLOW",
             after=41.0, band="NORMAL", score=0.41, grant="G-ELEC-SETPOINT-B",
             reasons=["PERMITTED", "WITHIN_PARAMETER_BOUNDS", "ANOMALY_NORMAL"],
             requested_setpoint_v=481.5, operating_mode="grid_tied", feeder_id="feeder-b")
    chain.append("EXECUTION_ATTEMPTED", after=0.4, **off, **_attribution("elec-agent-01"),
                 action="set_voltage_setpoint", target="FEEDER-B-RTU",
                 execution_id="exec.0001", idempotency_key="req.0007:gen42:lease0007",
                 commanded=481.5, unit="volt")
    chain.append("EXECUTION_RESULT", after=2.3, **off, **_attribution("elec-agent-01"),
                 action="set_voltage_setpoint", target="FEEDER-B-RTU",
                 execution_id="exec.0001", result="SUCCESS",
                 controller_receipt="ACK", note="Controller receipt only.")
    chain.append("ANOMALY_ASSESSMENT", after=1.9, **off, **_attribution("elec-agent-01"),
                 action="set_voltage_setpoint", target="FEEDER-B-RTU", phase="POST_ACTION",
                 band="NORMAL", score=0.38, status="OK", settled_bus_voltage_v=481.32,
                 setpoint_error_v=-0.18, profile_id="sen-feeder-voltage-post",
                 model_id="sen-voltage-candidate-001")

    # Hard prohibition: no model call at all.
    decision("microgrid-agent-01", "disable_protective_relay", "SPIDERS-RELAY-03",
             "DENY", after=95.0, prohibition="P-RELAY-DISABLE",
             reasons=["SAFETY_PROTECTIVE_DEVICE", "MODEL_NOT_INVOKED"],
             model_invoked=False,
             note="Denied deterministically. A model outage cannot prevent this.")

    # Protected load: the image's 'never shed protected loads' line.
    decision("dr-agent-01", "curtail_load", "METER-GW-01", "DENY", after=64.0,
             prohibition="P-PROTECTED-LOAD",
             reasons=["PROTECTED_LOAD", "MODEL_NOT_INVOKED"], model_invoked=False,
             load_id="LOAD-TOWER-01", curtail_kw=180.0,
             note="Flightline control tower is a protected load.")

    # Outside the hard envelope.
    decision("elec-agent-02", "set_voltage_setpoint", "FEEDER-A-RTU", "DENY",
             after=37.0, prohibition="P-VOLTAGE-ENVELOPE",
             reasons=["OUTSIDE_HARD_ENVELOPE", "MODEL_NOT_INVOKED"], model_invoked=False,
             requested_setpoint_v=512.0, hard_max_v=ELECTRICAL["hard_max_v"],
             operating_mode="grid_tied", feeder_id="feeder-a")

    # Vendor agent tries a state change while its window is open but offline.
    decision("vendor-agent-01", "modify_firewall", "SCADA-HMI-02", "DENY", after=52.0,
             prohibition="P-VENDOR-STATE-CHANGE",
             reasons=["VENDOR_READ_ONLY", "REQUIRES_ONLINE_AUTHORITY"], model_invoked=False)

    # Elevated anomaly on an otherwise permitted action: held, not denied.
    decision("elec-agent-02", "set_voltage_setpoint", "FEEDER-A-RTU", "HOLD",
             after=88.0, band="HIGH", score=0.994, grant="G-ELEC-SETPOINT-A",
             reasons=["PERMITTED", "ANOMALY_HIGH", "APPROVAL_REQUIRED"],
             requested_setpoint_v=463.0, requested_delta_v=-17.4,
             operating_mode="islanded", feeder_id="feeder-a")
    chain.append("TECHNICIAN_REVIEW_OPENED", after=6.0, **off,
                 **_attribution("elec-agent-02"), action="set_voltage_setpoint",
                 target="FEEDER-A-RTU", capabilities=["APPROVE_ONCE", "HOLD", "RESEARCH", "REJECT"])
    chain.append("FACE_VERIFICATION_FAILED", after=44.0, **off,
                 technician_id="msgt.d.reyes", reason_code="NO_MATCH_WITHIN_TIMEOUT",
                 grant_expires_s=60,
                 note="Login alone is not sufficient for a consequential approval.")
    chain.append("TECHNICIAN_APPROVAL_REJECTED", after=3.0, **off,
                 technician_id="msgt.d.reyes", action="set_voltage_setpoint",
                 target="FEEDER-A-RTU", reason_code="VERIFICATION_REQUIRED")

    # Same request, second attempt, verified this time.
    chain.append("TECHNICIAN_APPROVAL_ACCEPTED", after=71.0, **off,
                 technician_id="msgt.d.reyes", action="set_voltage_setpoint",
                 target="FEEDER-A-RTU", scope="APPROVE_ONCE",
                 proof_type="LOCAL_ARCFACE_GRANT", proof_expires_s=60,
                 bound_request="req.0031", bound_assessment="assess.0031.2",
                 note="Bound to one technician, one request, one use.")
    chain.append("EXECUTION_ATTEMPTED", after=1.1, **off, **_attribution("elec-agent-02"),
                 action="set_voltage_setpoint", target="FEEDER-A-RTU",
                 execution_id="exec.0002", commanded=463.0, unit="volt")

    # The controller says SUCCESS but the bus did not move.
    chain.append("EXECUTION_RESULT", after=2.6, **off, **_attribution("elec-agent-02"),
                 action="set_voltage_setpoint", target="FEEDER-A-RTU",
                 execution_id="exec.0002", result="SUCCESS", controller_receipt="ACK")
    chain.append("EXECUTION_EFFECT_MISMATCH", after=2.2, **off,
                 **_attribution("elec-agent-02"), action="set_voltage_setpoint",
                 target="FEEDER-A-RTU", execution_id="exec.0002",
                 commanded=463.0, observed=480.4, unit="volt",
                 telemetry_source="esp32-feeder-a", telemetry_freshness_ms=1_950,
                 note="A SUCCESS response is not an independent measurement.")
    chain.append("ANOMALY_ASSESSMENT", after=0.3, **off, **_attribution("elec-agent-02"),
                 action="set_voltage_setpoint", target="FEEDER-A-RTU",
                 phase="POST_ACTION", band="HIGH", score=0.998, status="OK",
                 setpoint_error_v=17.4, profile_id="sen-feeder-voltage-post",
                 model_id="sen-voltage-candidate-001")

    # New agent: cohort routing keeps an explicit novelty flag.
    chain.append("ANOMALY_ASSESSMENT", after=120.0, **off, **_attribution("elec-agent-07"),
                 action="set_voltage_setpoint", target="FEEDER-B-RTU", phase="PRE_ACTION",
                 band="NORMAL", score=0.52, status="OK", profile_source="COHORT",
                 novelty="NO_AGENT_BASELINE", profile_id="sen-feeder-voltage-pre",
                 note="A low score does not clear the novelty flag.")
    decision("elec-agent-07", "set_voltage_setpoint", "FEEDER-B-RTU", "REQUEST_CONTEXT",
             after=0.4, grant="G-ELEC-SETPOINT-B",
             reasons=["PERMITTED", "AGENT_NOVEL", "JUSTIFICATION_REQUIRED"],
             context_attempt=1)

    # Unsupported context: a refusal to score, not a low score.
    chain.append("ANOMALY_ASSESSMENT", after=66.0, **off, **_attribution("elec-agent-01"),
                 action="set_voltage_setpoint", target="FEEDER-A-RTU", phase="PRE_ACTION",
                 status="UNKNOWN_CONTEXT", band=None, score=None,
                 context="feeder-a/maintenance_bypass",
                 note="No fitted forest for this exact context; routing has no fallback.")
    decision("elec-agent-01", "set_voltage_setpoint", "FEEDER-A-RTU", "HOLD",
             after=0.3, grant="G-ELEC-SETPOINT-A",
             reasons=["PERMITTED", "ANOMALY_UNAVAILABLE", "TECHNICIAN_REQUIRED"])

    # Offline purchase attempt.
    decision("maint-agent-01", "order_parts", "WO-API-01", "DENY", after=143.0,
             prohibition="P-OFFLINE-PURCHASE",
             reasons=["NO_OFFLINE_PURCHASE_AUTHORITY", "HELD_FOR_RECONNECTION"],
             part_number="PMP-4471-B", amount_usd=14_200.0, model_invoked=False,
             note="Above the responsible user's ceiling and unreconcilable offline.")

    chain.checkpoint(after=30.0)

    # Permissions age past validity while still disconnected.
    chain.append("PERMISSIONS_EXPIRED", after=900.0, **off, generation=GENERATION,
                 not_after="2026-09-12T06:00:00Z", grace_seconds=259_200,
                 on_expiry_grants="REVIEW_REQUIRED", on_expiry_prohibitions="ENFORCED")
    decision("elec-agent-01", "set_voltage_setpoint", "FEEDER-B-RTU", "HOLD",
             after=22.0, band="NORMAL", score=0.44, grant="G-ELEC-SETPOINT-B",
             reasons=["PERMISSIONS_EXPIRED", "TECHNICIAN_REQUIRED"],
             freshness="EXPIRED")

    # Storage pressure blocks consequential work rather than dropping audit.
    chain.append("AUDIT_CAPACITY_BLOCK", after=210.0, **off,
                 audit_free_bytes=5_242_880, reserve_bytes=8_388_608,
                 blocked_classes=["STATE_CHANGING"],
                 note="Dropping audit is never the failure mode.")

    # ---------------- Reconnection ------------------------------------------
    chain.append("SERVICE_REAUTHENTICATED", after=480.0, mode="OFFLINE",
                 authority="ALICE", service="wazuh-manager",
                 note="A router link is not an authenticated ready service.")
    chain.append("OUTBOX_DELIVERY_RESUMED", after=4.0, mode="OFFLINE", authority="ALICE",
                 cursor_sequence=1, pending_events=chain.sequence,
                 delivery="bulk_create_idempotent", index="alice-audit-2026.09.05")
    chain.append("PERMISSIONS_REJECTED", after=12.0, mode="OFFLINE", authority="ALICE",
                 candidate_generation=41, active_generation=GENERATION,
                 reason_code="STALE_GENERATION",
                 note="A cached older release arrived first on reconnect; refused.")
    chain.append("PERMISSIONS_DRIFT", after=8.0, mode="OFFLINE", authority="ALICE",
                 active_generation=GENERATION, enterprise_generation=44,
                 affected_decisions=3,
                 note="Decisions taken under a superseded generation are reported, "
                      "not rewritten.")
    chain.append("EVIDENCE_RECONCILED", after=15.0, mode="OFFLINE", authority="ALICE",
                 queried="utility_demand_response_signal", finding="NOT_FOUND",
                 original_decision_preserved=True,
                 note="The original decision keeps its decision-time evidence state.")
    chain.append("AUTHORITY_TRANSITION", after=20.0, from_mode="OFFLINE",
                 to_mode="ONLINE", authority="ENTERPRISE",
                 fence_token="lease.2026-09-05T07:41:10Z.0008",
                 local_admission_retired=True, outbox_backlog_remaining=0,
                 note="ONLINE is not a claim that every historical event has landed.")
    chain.checkpoint(after=2.0)

    return chain.events


# --------------------------------------------------------------------------
# Surrounding IT activity, so the Wazuh dashboard shows a plausible base
# --------------------------------------------------------------------------

def build_it_activity(seed: int = 4242) -> list[dict]:
    rng = random.Random(seed)
    clock = START - timedelta(hours=3)
    rows = []

    hosts = ["tririga-app-01", "builder-svc-01", "wo-api-01", "scada-hmi-02",
             "spiders-mgc-01", "meter-gw-01", "agent-mac-01", "tech-mac-01"]
    operators = [u for u in USERS if USERS[u]["deploys_agents"]]

    def emit(host, program, message, **fields):
        nonlocal clock
        clock += timedelta(seconds=rng.uniform(4, 95))
        rows.append({
            "timestamp": _utc(clock),
            "agent": {"name": host},
            "program_name": program,
            "full_log": message,
            **fields,
        })

    for _ in range(60):
        kind = rng.random()
        if kind < 0.30:
            user = rng.choice(operators)
            host = rng.choice(hosts)
            emit(host, "sshd",
                 f"Accepted publickey for {user} from 10.42.10."
                 f"{rng.randrange(20, 60)} port {rng.randrange(40000, 60000)} ssh2",
                 srcuser=user, event="authentication_success")
        elif kind < 0.42:
            user = rng.choice(operators)
            emit(rng.choice(hosts), "sshd",
                 f"Failed password for {user} from 10.42.10."
                 f"{rng.randrange(20, 60)} port {rng.randrange(40000, 60000)} ssh2",
                 srcuser=user, event="authentication_failure")
        elif kind < 0.58:
            agent_id = rng.choice(list(AGENTS))
            owner = AGENTS[agent_id]["responsible_user"]
            emit("agent-mac-01", "alice-agentd",
                 f"agent {agent_id} heartbeat owner={owner} "
                 f"state=running proposals={rng.randrange(0, 12)}",
                 event="agent_heartbeat")
        elif kind < 0.68:
            agent_id = rng.choice(list(AGENTS))
            owner = AGENTS[agent_id]["responsible_user"]
            emit("agent-mac-01", "alice-agentd",
                 f"deploy agent={agent_id} by={owner} "
                 f"mission={AGENTS[agent_id]['mission_type']} result=accepted",
                 event="agent_deployed")
        elif kind < 0.80:
            emit("tririga-app-01", "tririga",
                 f"asset record read id=AST-{rng.randrange(1000, 9999)} "
                 f"by=maint-agent-01 result=200", event="record_read")
        elif kind < 0.90:
            emit("wo-api-01", "wo-api",
                 f"POST /workorders priority=routine asset=AST-{rng.randrange(1000, 9999)} "
                 f"requester=maint-agent-01 status=201", event="work_order_created")
        else:
            feeder = rng.choice(["feeder-a-rtu", "feeder-b-rtu"])
            mode = "islanded" if rng.random() < 0.25 else "grid_tied"
            bus = rng.gauss(480.0, 2.0)
            emit(feeder, "esp32",
                 f"setpoint cmd={bus + rng.gauss(0, 1):.3f} bus={bus:.3f} "
                 f"load={rng.gauss(180, 40):.2f} mode={mode}",
                 event="feeder_telemetry")

    # A deliberate cluster the correlation rules should catch.
    for index in range(9):
        clock += timedelta(seconds=18)
        rows.append({
            "timestamp": _utc(clock),
            "agent": {"name": "feeder-b-rtu"},
            "program_name": "esp32",
            "full_log": f"setpoint cmd={479 + index * 0.4:.3f} bus=479.100 "
                        f"load=96.40 mode=grid_tied",
            "event": "feeder_telemetry",
            "note": "rapid cycling cluster",
        })

    rows.sort(key=lambda row: row["timestamp"])
    return rows
