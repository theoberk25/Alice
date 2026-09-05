"""Emit a signed ALICE permissions bundle for the simulated base.

The bundle is the artifact the Pi stages, verifies and activates. This module
builds and signs it on the workstation. It is not the Pi-side verifier, and the
demonstration key it uses is not a trust root: a real deployment must issue the
signing key from an authorized enterprise identity service and install only the
public half on the Pi's read-only root filesystem.
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from .scenario import (
    AGENTS, CYBER_ACTIONS, ELECTRICAL, LOADS, OT_ACTIONS, SITE, SYSTEMS, UNITS, USERS,
)

BUNDLE_SCHEMA_VERSION = "alice-permissions-bundle-v1"

# The enterprise keeps publishing while an edge node is disconnected. GENERATION
# is what the simulated Pi last cached; PUBLISHED_GENERATIONS is what the SIEM
# actually holds. The gap between them is the condition the permissions tracker
# exists to detect, so the simulation has to contain one.
GENERATION = 42
PUBLISHED_GENERATIONS = (42, 43, 44)
CURRENT_GENERATION = 44

# What each release changed relative to its predecessor.
RELEASE_NOTES = {
    42: "Baseline release cached by alice-pi-01 before the DDIL window.",
    43: "Revoked vendor-agent-01 and its operator: the support contract ended "
        "early. An edge node still on 42 keeps honouring that agent's read "
        "grants until it resynchronizes.",
    44: "Extended elec-agent-07 to feeder A after its cohort review, and "
        "tightened the setpoint step-up threshold from 6.0 V to 4.0 V.",
}
ISSUER_ID = "sen.iam.permissions-authority"
ISSUED_AT = datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc)
VALID_FOR = timedelta(days=7)
OFFLINE_GRACE = timedelta(days=3)


def _utc(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    """Stable serialization used for every digest in the bundle."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


# --------------------------------------------------------------------------
# subjects.json — who exists, and which human answers for each agent
# --------------------------------------------------------------------------

def build_subjects(generation: int = GENERATION) -> dict:
    users = {}
    for user_id, user in sorted(USERS.items()):
        entry = {
            "user_id": user_id,
            "display_name": user["display_name"],
            "unit": user["unit"],
            "unit_name": UNITS[user["unit"]],
            "role": user["role"],
            "may_deploy_agents": user["deploys_agents"],
            "technician_console": user["technician_console"],
            "approval_authority": sorted(user["approval_authority"]),
            "purchase_ceiling_usd": user["purchase_ceiling_usd"],
        }
        for optional in ("escort_required", "access_window_utc", "note"):
            if optional in user:
                entry[optional] = user[optional]
        users[user_id] = entry

    agents = {}
    for agent_id, agent in sorted(AGENTS.items()):
        entry = {
            "agent_id": agent_id,
            "agent_type": agent["type"],
            "role": agent["role"],
            "mission_type": agent["mission_type"],
            # The attribution chain the audit must be able to reproduce.
            "responsible_user": agent["responsible_user"],
            "delegator": agent["delegator"],
            "attribution_source": "sen.iam.permissions-authority",
            "deployed_at": agent["deployed_at"],
            "permitted_targets": sorted(agent["targets"]),
            "baseline_profile": agent["baseline_profile"],
        }
        if agent["baseline_profile"] is None:
            entry["baseline_resolution"] = "COHORT"
            entry["novelty"] = "NO_AGENT_BASELINE"
        if "expires_at" in agent:
            entry["expires_at"] = agent["expires_at"]
        if "note" in agent:
            entry["note"] = agent["note"]
        agents[agent_id] = entry

    return {
        "schema_version": "alice-permissions-subjects-v1",
        "site_id": SITE["site_id"],
        "users": users,
        "agents": agents,
    }


# --------------------------------------------------------------------------
# grants.json — the allow surface, with parameter bounds and review triggers
# --------------------------------------------------------------------------

def _voltage_bounds(feeders: list[str], approval_delta: float | None = None) -> dict:
    return {
        "setpoint_v": {
            "min": ELECTRICAL["normal_min_v"],
            "max": ELECTRICAL["normal_max_v"],
            "unit": "volt",
            "approval_required_if_abs_delta_exceeds":
                ELECTRICAL["approval_delta_v"] if approval_delta is None else approval_delta,
        },
        "feeder_id": {"one_of": sorted(feeders)},
    }


def build_grants(generation: int = GENERATION) -> dict:
    grants = []
    # Release 44 tightened the threshold at which a setpoint change needs a
    # technician. A node still on 42 applies the looser one.
    approval_delta = 4.0 if generation >= 44 else ELECTRICAL["approval_delta_v"]

    def grant(grant_id, agents, actions, targets, *, bounds=None, approval=False,
              conditions=None, note=None):
        entry = {
            "grant_id": grant_id,
            "agents": sorted(agents),
            "actions": sorted(actions),
            "targets": sorted(targets),
            "effect": "PERMIT",
            "approval_required": approval,
        }
        if bounds:
            entry["parameter_bounds"] = bounds
        if conditions:
            entry["conditions"] = conditions
        if note:
            entry["note"] = note
        grants.append(entry)

    # --- Power distribution: the electrician workflow -----------------------
    grant("G-ELEC-READ", ["elec-agent-01", "elec-agent-02", "elec-agent-07", "appr-agent-01"],
          ["read_meter", "query_status", "read_logs"],
          ["FEEDER-A-RTU", "FEEDER-B-RTU", "METER-GW-01"])

    setpoint_a_agents = ["elec-agent-01", "elec-agent-02"]
    if generation >= 44:
        setpoint_a_agents.append("elec-agent-07")
    grant("G-ELEC-SETPOINT-A", setpoint_a_agents,
          ["set_voltage_setpoint"], ["FEEDER-A-RTU"],
          bounds=_voltage_bounds(["feeder-a"], approval_delta),
          conditions={"operating_mode": ["grid_tied", "islanded"],
                      "requires_current_authority": True},
          note="Feeder A carries protected loads; every setpoint change is audited "
               "and a change beyond the approval delta needs technician step-up.")

    grant("G-ELEC-SETPOINT-B", ["elec-agent-01", "elec-agent-02", "elec-agent-07"],
          ["set_voltage_setpoint"], ["FEEDER-B-RTU"],
          bounds=_voltage_bounds(["feeder-b"], approval_delta),
          conditions={"operating_mode": ["grid_tied", "islanded"],
                      "requires_current_authority": True})

    # --- Microgrid dispatch (SPIDERS) --------------------------------------
    grant("G-MG-DISPATCH", ["microgrid-agent-01"],
          ["dispatch_generator"], ["SPIDERS-MGC-01"],
          bounds={"output_kw": {"min": 0.0, "max": ELECTRICAL["generator_max_kw"],
                                "unit": "kilowatt"}},
          approval=True,
          conditions={"operating_mode": ["grid_tied", "islanded"]},
          note="Generator dispatch stays inside the published safety envelope and "
               "always requires a technician approval in the demonstration.")

    grant("G-MG-SHED", ["microgrid-agent-01"],
          ["set_load_shed_priority"], ["SPIDERS-MGC-01"],
          bounds={"load_id": {"one_of": sorted(k for k, v in LOADS.items()
                                               if v["class"] == "sheddable")}},
          note="Sheddable loads only. Protected loads are refused by prohibitions.")

    grant("G-MG-SWITCH", ["microgrid-agent-01"],
          ["close_switchgear"], ["SPIDERS-MGC-01"],
          approval=True,
          note="Close only. Opening switchgear is not granted to any agent.")

    grant("G-MG-BESS", ["microgrid-agent-01", "elec-agent-02"],
          ["query_status", "read_meter"], ["BESS-CTRL-02"])

    # --- Utility metering / demand response --------------------------------
    grant("G-DR-CURTAIL", ["dr-agent-01"],
          ["curtail_load"], ["METER-GW-01"],
          bounds={"curtail_kw": {"min": 0.0, "max": 350.0, "unit": "kilowatt"},
                  "load_id": {"one_of": sorted(k for k, v in LOADS.items()
                                               if v["class"] == "sheddable")}},
          approval=True,
          conditions={"utility_signal_verified": True},
          note="A price or utility signal is a claim until verified against the "
               "cached enterprise record; DR must keep working while disconnected.")

    grant("G-DR-READ", ["dr-agent-01"], ["read_meter", "read_logs"], ["METER-GW-01"])

    # --- Facility / maintenance prediction ---------------------------------
    grant("G-MAINT-ASSESS", ["maint-agent-01"],
          ["read_logs", "query_status", "read_asset_record"],
          ["BUILDER-SVC-01", "WO-API-01", "TRIRIGA-APP-01"])

    grant("G-MAINT-WO", ["maint-agent-01"],
          ["create_work_order"], ["WO-API-01"],
          bounds={"priority": {"one_of": ["routine", "urgent"]}},
          note="An emergency work order that reprioritizes crews is not granted; "
               "it must reach a technician as REQUEST_CONTEXT or HOLD.")

    grant("G-MAINT-PARTS", ["maint-agent-01"],
          ["order_parts"], ["WO-API-01"],
          bounds={"amount_usd": {"min": 0.0, "max": 2_500.0, "unit": "usd"}},
          approval=True,
          note="Every agent-initiated purchase requires technician step-up, and the "
               "ceiling is the responsible user's, not the agent's.")

    grant("G-MAINT-RECORD", ["maint-agent-01"],
          ["update_asset_record"], ["TRIRIGA-APP-01"],
          approval=True,
          note="TRIRIGA is the authoritative asset record; write-back is step-up gated.")

    # --- Cyber defense ------------------------------------------------------
    grant("G-CYBER-READ", ["cyber-agent-04"],
          ["read_logs", "query_status", "query_network"],
          ["SCADA-HMI-02", "TRIRIGA-APP-01"])

    grant("G-CYBER-FW", ["cyber-agent-04"],
          ["modify_firewall", "allow_outbound"], ["SCADA-HMI-02"],
          bounds={"destination_host": {"one_of": ["10.42.30.15", "10.42.30.16", "10.42.30.17"]},
                  "destination_port": {"one_of": [443, 8443]}},
          approval=True,
          note="Outbound permits are limited to cached known destinations inside the "
               "IT enclave. An unseen destination stays novel even at a low score.")

    # --- Vendor: deliberately read-only and time-boxed ----------------------
    if generation < 43:
        grant("G-VENDOR-READ", ["vendor-agent-01"],
          ["read_logs", "query_status"], ["SCADA-HMI-02"],
          conditions={"escort_required": True,
                      "valid_window_utc": USERS["ctr.p.osei"]["access_window_utc"],
                      "requires_online_authority": True},
              note="No state-changing action is granted. The window is enforced "
                   "against trusted time; an unknown clock must not widen it.")

    return {
        "schema_version": "alice-permissions-grants-v1",
        "site_id": SITE["site_id"],
        "default_effect": "DENY",
        "grants": grants,
    }


# --------------------------------------------------------------------------
# prohibitions.json — evaluated independently, before any model call
# --------------------------------------------------------------------------

def build_prohibitions(generation: int = GENERATION) -> dict:
    protected = sorted(k for k, v in LOADS.items() if v["class"] == "protected")
    return {
        "schema_version": "alice-permissions-prohibitions-v1",
        "site_id": SITE["site_id"],
        "evaluation": {
            "order": "BEFORE_GRANTS",
            "model_invocation": "FORBIDDEN",
            "override": "NONE",
            "note": "A hard prohibition returns DENY without building features, "
                    "calling the anomaly model, opening a context round or "
                    "accepting a technician approval. Model unavailability must "
                    "not prevent this denial.",
        },
        "prohibitions": [
            {"prohibition_id": "P-RELAY-DISABLE",
             "reason_code": "SAFETY_PROTECTIVE_DEVICE",
             "actions": ["disable_protective_relay"],
             "targets": ["*"], "agents": ["*"],
             "note": "No agent, user, mode or approval may disable a protective relay."},

            {"prohibition_id": "P-RELAY-SWITCHGEAR",
             "reason_code": "SAFETY_PROTECTIVE_DEVICE",
             "actions": ["open_switchgear", "close_switchgear", "set_voltage_setpoint"],
             "targets": ["SPIDERS-RELAY-03"], "agents": ["*"]},

            {"prohibition_id": "P-PROTECTED-LOAD",
             "reason_code": "PROTECTED_LOAD",
             "actions": ["curtail_load", "set_load_shed_priority"],
             "targets": ["*"], "agents": ["*"],
             "parameter_match": {"load_id": {"one_of": protected}},
             "note": "Clinic, tower, alert facility and fuels operations are never "
                     "shed or curtailed by an agent under any mode."},

            {"prohibition_id": "P-VOLTAGE-ENVELOPE",
             "reason_code": "OUTSIDE_HARD_ENVELOPE",
             "actions": ["set_voltage_setpoint"],
             "targets": ["*"], "agents": ["*"],
             "parameter_match": {"setpoint_v": {"outside": [ELECTRICAL["hard_min_v"],
                                                            ELECTRICAL["hard_max_v"]],
                                                "unit": "volt"}},
             "note": "Placeholder ANSI-shaped service band; requires engineering "
                     "sign-off before it gates a real feeder."},

            {"prohibition_id": "P-GEN-ENVELOPE",
             "reason_code": "OUTSIDE_HARD_ENVELOPE",
             "actions": ["dispatch_generator"],
             "targets": ["*"], "agents": ["*"],
             "parameter_match": {"output_kw": {"outside": [0.0, ELECTRICAL["generator_max_kw"]],
                                               "unit": "kilowatt"}}},

            {"prohibition_id": "P-DROP-ISLANDING",
             "reason_code": "MISSION_CONTINUITY",
             "actions": ["drop_islanding"],
             "targets": ["*"], "agents": ["*"],
             "note": "Leaving islanded operation is a human decision; no agent "
                     "may drop islanding, least of all while disconnected."},

            {"prohibition_id": "P-VENDOR-STATE-CHANGE",
             "reason_code": "VENDOR_READ_ONLY",
             "actions": [name for name, spec in sorted(OT_ACTIONS.items())
                         if spec["state_changing"]] + ["modify_firewall", "allow_outbound"],
             "targets": ["*"], "agents": ["vendor-agent-01"]},

            {"prohibition_id": "P-APPRENTICE-STATE-CHANGE",
             "reason_code": "TRAINING_ACCOUNT_READ_ONLY",
             "actions": [name for name, spec in sorted(OT_ACTIONS.items())
                         if spec["state_changing"]] + ["modify_firewall", "allow_outbound"],
             "targets": ["*"], "agents": ["appr-agent-01"]},

            {"prohibition_id": "P-OFFLINE-PURCHASE",
             "reason_code": "NO_OFFLINE_PURCHASE_AUTHORITY",
             "actions": ["order_parts"],
             "targets": ["*"], "agents": ["*"],
             "conditions": {"mode": "OFFLINE"},
             "note": "A purchase cannot be reconciled while disconnected, so the "
                     "offline path never commits one. It is held for reconnection."},
        ],
    }


# --------------------------------------------------------------------------
# revocations.json — explicit, with an epoch the Pi tracks for rollback checks
# --------------------------------------------------------------------------

def build_revocations(generation: int = GENERATION) -> dict:
    entries = []
    if generation >= 43:
        entries += [
            {"subject_type": "agent", "subject_id": "vendor-agent-01",
             "revoked_at": "2026-09-05T11:40:00Z",
             "reason_code": "CONTRACT_ENDED_EARLY",
             "note": "Revoked in release 43. A node still on 42 has not seen this."},
            {"subject_type": "user", "subject_id": "ctr.p.osei",
             "revoked_at": "2026-09-05T11:40:00Z",
             "reason_code": "CONTRACT_ENDED_EARLY"},
        ]
    return {
        "schema_version": "alice-permissions-revocations-v1",
        "site_id": SITE["site_id"],
        "revocation_epoch": 8 if generation >= 43 else 7,
        "revocations": entries + [
            {"subject_type": "agent", "subject_id": "elec-agent-04",
             "revoked_at": "2026-08-30T17:22:00Z",
             "reason_code": "AGENT_DECOMMISSIONED",
             "note": "Superseded by elec-agent-07. Kept in the list so a stale "
                     "cached bundle cannot resurrect it."},
            {"subject_type": "user", "subject_id": "ctr.b.marchetti",
             "revoked_at": "2026-07-14T12:00:00Z",
             "reason_code": "CONTRACT_ENDED"},
            {"subject_type": "grant", "subject_id": "G-ELEC-SETPOINT-LEGACY",
             "revoked_at": "2026-06-11T09:05:00Z",
             "reason_code": "SUPERSEDED_BY_BOUNDED_GRANT"},
        ],
    }


# --------------------------------------------------------------------------
# manifest.json + detached signature
# --------------------------------------------------------------------------

def build_manifest(payload_digests: dict, *, model_binding: dict,
                   generation: int = GENERATION) -> dict:
    offset = generation - GENERATION
    issued = ISSUED_AT + timedelta(hours=6 * offset)
    not_before = issued
    not_after = issued + VALID_FOR
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": f"sen-permissions-{generation:06d}",
        "generation": generation,
        "release_note": RELEASE_NOTES.get(generation, ""),
        "issuer_id": ISSUER_ID,
        "transport": "wazuh-indexer:alice-permissions",
        "transport_note": "Wazuh distributes and timestamps this release. Authority "
                          "for its contents is the issuer above, not the SIEM.",
        "site_id": SITE["site_id"],
        "issued_at": _utc(issued),
        "not_before": _utc(not_before),
        "not_after": _utc(not_after),
        "offline_grace_seconds": int(OFFLINE_GRACE.total_seconds()),
        "on_expiry": {
            "prohibitions": "ENFORCED",
            "grants": "REVIEW_REQUIRED",
            "note": "Expiry never widens permission. Hard prohibitions keep binding "
                    "and every other eligible request escalates to a technician "
                    "instead of silently allowing or silently denying.",
        },
        "revocation_epoch": build_revocations(generation)["revocation_epoch"],
        "content_digests": payload_digests,
        "compatibility": model_binding,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": "sen.iam.permissions-authority.2026-09",
            "detached_file": "manifest.sig",
            "signed_bytes": "canonical JSON of this manifest with the signature "
                            "block removed",
        },
    }


def sign_manifest(manifest: dict, private_key) -> tuple[bytes, bytes]:
    """Return (signed manifest bytes, detached signature bytes)."""
    unsigned = {key: value for key, value in manifest.items() if key != "signature"}
    signature = private_key.sign(canonical_bytes(unsigned))
    return canonical_bytes(manifest), signature


def digest_of(payload: dict) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()
