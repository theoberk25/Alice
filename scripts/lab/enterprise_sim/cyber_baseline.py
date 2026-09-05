"""Build a base-specific normal-behavior release for the fixed cyber contract.

`dcamr.anomaly_engine.baseline` pins the five cyber actions and their parameter
semantics. This module reuses that contract exactly and only changes the site's
targets, profiles, agents and cohorts. Electrical actions are deliberately
absent: `set_voltage_setpoint` is not a cyber feature column and must never be
smuggled into `cyber-behavior-v1`. It is scored, if at all, by the separate
contextual profiles.
"""

from .scenario import AGENTS, SITE, SYSTEMS

BASELINE_SCHEMA_VERSION = "1.0.0"
FEATURE_SCHEMA_VERSION = "cyber-behavior-v1"
PACKAGE_ID = "ops-sentinel"
VERSION = "42"

# Exactly the catalog dcamr.anomaly_engine.baseline.CYBER_ACTIONS enforces.
ACTION_CATALOG = {
    "read_logs": {"state_changing": False, "destination_required": False},
    "query_status": {"state_changing": False, "destination_required": False},
    "query_network": {"state_changing": False, "destination_required": False},
    "modify_firewall": {"state_changing": True, "destination_required": True},
    "allow_outbound": {"state_changing": True, "destination_required": True},
}

# Known destination relationships per target. An address absent here stays novel.
TARGETS = {
    "SCADA-HMI-02": [
        {"host": "10.42.30.15", "port": 443, "protocol": "tcp"},
        {"host": "10.42.30.16", "port": 443, "protocol": "tcp"},
        {"host": "10.42.30.17", "port": 8443, "protocol": "tcp"},
    ],
    "TRIRIGA-APP-01": [
        {"host": "10.42.30.16", "port": 443, "protocol": "tcp"},
        {"host": "10.42.30.17", "port": 8443, "protocol": "tcp"},
    ],
    "BUILDER-SVC-01": [
        {"host": "10.42.30.15", "port": 443, "protocol": "tcp"},
        {"host": "10.42.30.17", "port": 8443, "protocol": "tcp"},
    ],
    "WO-API-01": [
        {"host": "10.42.30.15", "port": 443, "protocol": "tcp"},
    ],
    "FEEDER-A-RTU": [
        {"host": "10.42.20.10", "port": 502, "protocol": "tcp"},
    ],
    "FEEDER-B-RTU": [
        {"host": "10.42.20.10", "port": 502, "protocol": "tcp"},
    ],
    "METER-GW-01": [
        {"host": "10.42.20.10", "port": 502, "protocol": "tcp"},
    ],
    "BESS-CTRL-02": [
        {"host": "10.42.20.10", "port": 502, "protocol": "tcp"},
    ],
    "SPIDERS-MGC-01": [
        {"host": "10.42.20.12", "port": 502, "protocol": "tcp"},
    ],
}


def _counts(read_logs, query_status, query_network, modify_firewall, allow_outbound) -> dict:
    """A complete row: every supported action appears, including explicit zeros."""
    return {"read_logs": read_logs, "query_status": query_status,
            "query_network": query_network, "modify_firewall": modify_firewall,
            "allow_outbound": allow_outbound}


# Transition rows may only reference actions with a nonzero count in the same
# profile, and every row's source action must itself be nonzero.
_ELECTRICIAN = {
    "action_counts": _counts(38, 62, 4, 0, 0),
    "transitions": {
        "read_logs": {"query_status": 9, "read_logs": 1},
        "query_status": {"query_status": 6, "read_logs": 5, "query_network": 1},
        "query_network": {"query_status": 8, "read_logs": 2},
    },
}
_MICROGRID = {
    "action_counts": _counts(30, 58, 12, 0, 0),
    "transitions": {
        "read_logs": {"query_status": 8, "query_network": 2},
        "query_status": {"query_status": 5, "read_logs": 4, "query_network": 1},
        "query_network": {"query_status": 7, "read_logs": 3},
    },
}
_DEMAND_RESPONSE = {
    "action_counts": _counts(22, 70, 8, 0, 0),
    "transitions": {
        "read_logs": {"query_status": 9, "read_logs": 1},
        "query_status": {"query_status": 7, "read_logs": 2, "query_network": 1},
        "query_network": {"query_status": 9, "read_logs": 1},
    },
}
_MAINTENANCE = {
    "action_counts": _counts(55, 33, 12, 0, 0),
    "transitions": {
        "read_logs": {"read_logs": 4, "query_status": 5, "query_network": 1},
        "query_status": {"read_logs": 7, "query_network": 2, "query_status": 1},
        "query_network": {"read_logs": 8, "query_status": 2},
    },
}
_CYBER = {
    "action_counts": _counts(50, 25, 20, 3, 2),
    "transitions": {
        "read_logs": {"query_status": 8, "query_network": 2},
        "query_status": {"query_network": 9, "read_logs": 1},
        "query_network": {"read_logs": 8, "modify_firewall": 1, "allow_outbound": 1},
        "modify_firewall": {"query_status": 5},
        "allow_outbound": {"query_status": 5},
    },
}
_OBSERVER = {
    "action_counts": _counts(45, 55, 0, 0, 0),
    "transitions": {
        "read_logs": {"query_status": 7, "read_logs": 3},
        "query_status": {"read_logs": 8, "query_status": 2},
    },
}
_VENDOR = {
    "action_counts": _counts(60, 40, 0, 0, 0),
    "transitions": {
        "read_logs": {"query_status": 6, "read_logs": 4},
        "query_status": {"read_logs": 9, "query_status": 1},
    },
}

_SHAPES = {
    "electrician": _ELECTRICIAN,
    "power_production": _MICROGRID,
    "energy_manager": _DEMAND_RESPONSE,
    "facility_maintenance": _MAINTENANCE,
    "cyber_defense": _CYBER,
    "apprentice": _OBSERVER,
    "vendor_support": _VENDOR,
}


def build_baseline() -> dict:
    """Emit a baseline that `load_baseline` accepts for this site."""
    profiles, agents, cohorts = {}, {}, {}
    seen_cohorts = {}

    for agent_id, agent in sorted(AGENTS.items()):
        role, mission = agent["role"], agent["mission_type"]
        shape = _SHAPES[role]
        targets = sorted(t for t in agent["targets"] if t in TARGETS)

        if agent["baseline_profile"] is not None:
            profiles[agent_id] = {
                "role": role, "mission_type": mission, "targets": targets,
                "action_counts": dict(shape["action_counts"]),
                "transitions": {k: dict(v) for k, v in shape["transitions"].items()},
            }
            agents[agent_id] = {"role": role, "mission_type": mission, "profile_id": agent_id}

        # Every (role, mission) pair also gets a cohort so an authenticated agent
        # with no personal profile is still comparable, while staying novel.
        key = (role, mission)
        if key not in seen_cohorts:
            cohort_id = f"{role}-{mission}-cohort"
            seen_cohorts[key] = cohort_id
            profiles[cohort_id] = {
                "role": role, "mission_type": mission, "targets": targets,
                "action_counts": dict(shape["action_counts"]),
                "transitions": {k: dict(v) for k, v in shape["transitions"].items()},
            }
            cohorts[cohort_id] = {"role": role, "mission_type": mission,
                                  "profile_id": cohort_id}
        else:
            cohort_id = seen_cohorts[key]
            merged = sorted(set(profiles[cohort_id]["targets"]) | set(targets))
            profiles[cohort_id]["targets"] = merged

    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "package_id": PACKAGE_ID,
        "version": VERSION,
        "action_catalog": ACTION_CATALOG,
        "targets": {name: {"destinations": destinations}
                    for name, destinations in sorted(TARGETS.items())},
        "profiles": profiles,
        "agents": agents,
        "cohorts": [cohorts[cohort_id] for cohort_id in sorted(cohorts)],
    }
