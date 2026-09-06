"""Fictional energy-infrastructure org model for the ALICE enterprise simulation.

Every identifier, person, unit, address and measurement here is invented for a
demonstration. Nothing in this module is real base data, a real permissions
grant, or an agreed electrical operating limit. Voltage bands are placeholders
shaped after ANSI C84.1 Range A for a 480 V nominal service; they require
electrical-engineering sign-off before they gate any physical action.

This module holds data only. It performs no evaluation, signing or I/O.
"""

# --------------------------------------------------------------------------
# Site
# --------------------------------------------------------------------------

SITE = {
    "site_id": "SEN",
    "name": "DN-Hacks Energy Infrastructure Testbed",
    "note": "Fictional server-room energy environment used for the ALICE demonstration.",
    "networks": {
        "10.42.10.0/24": "ALICE and management enclave",
        "10.42.20.0/24": "OT / SCADA enclave (microgrid, feeders, metering)",
        "10.42.30.0/24": "IT services enclave (TRIRIGA, BUILDER, work orders)",
    },
}

UNITS = {
    "899-CES/POWER-PRO": "899th Civil Engineer Squadron, Power Production Flight",
    "899-CES/OPS-ENG": "899th Civil Engineer Squadron, Operations Engineering Flight",
    "899-CES/ENERGY": "899th Civil Engineer Squadron, Base Energy Management",
    "899-CS": "899th Communications Squadron, Cyber Defense",
    "899-LRS": "899th Logistics Readiness Squadron",
    "899-MSG": "899th Mission Support Group",
    "CTR-MGS": "Meridian Grid Systems (SCADA vendor, escorted contractor)",
}

# --------------------------------------------------------------------------
# Protected systems. `plane` separates the cyber contract from the OT contract.
# --------------------------------------------------------------------------

SYSTEMS = {
    "SPIDERS-MGC-01": {
        "name": "SPIDERS microgrid controller", "plane": "ot",
        "criticality": "mission_critical", "enclave": "10.42.20.0/24",
        "host": "10.42.20.10", "workflow": "microgrid_control",
    },
    "SPIDERS-RELAY-03": {
        "name": "Protective relay bank, substation 3", "plane": "ot",
        "criticality": "safety_critical", "enclave": "10.42.20.0/24",
        "host": "10.42.20.11", "workflow": "microgrid_control",
    },
    "BESS-CTRL-02": {
        "name": "Battery energy storage controller", "plane": "ot",
        "criticality": "mission_critical", "enclave": "10.42.20.0/24",
        "host": "10.42.20.12", "workflow": "microgrid_control",
    },
    "FEEDER-A-RTU": {
        "name": "Feeder A RTU (ESP demo node)", "plane": "ot",
        "criticality": "mission_critical", "enclave": "10.42.20.0/24",
        "host": "10.42.20.41", "workflow": "power_distribution",
    },
    "FEEDER-B-RTU": {
        "name": "Feeder B RTU (ESP demo node)", "plane": "ot",
        "criticality": "routine", "enclave": "10.42.20.0/24",
        "host": "10.42.20.42", "workflow": "power_distribution",
    },
    "METER-GW-01": {
        "name": "Utility metering / demand-response gateway", "plane": "ot",
        "criticality": "routine", "enclave": "10.42.20.0/24",
        "host": "10.42.20.44", "workflow": "demand_response",
    },
    "SCADA-HMI-02": {
        "name": "SCADA HMI workstation (IT/OT bridge)", "plane": "bridge",
        "criticality": "mission_critical", "enclave": "10.42.20.0/24",
        "host": "10.42.20.32", "workflow": "microgrid_control",
    },
    "TRIRIGA-APP-01": {
        "name": "TRIRIGA system of record", "plane": "it",
        "criticality": "authoritative_record", "enclave": "10.42.30.0/24",
        "host": "10.42.30.15", "workflow": "system_of_record",
    },
    "BUILDER-SVC-01": {
        "name": "BUILDER / Piton condition assessment service", "plane": "it",
        "criticality": "routine", "enclave": "10.42.30.0/24",
        "host": "10.42.30.16", "workflow": "facility_maintenance",
    },
    "WO-API-01": {
        "name": "Work order and parts requisition API", "plane": "it",
        "criticality": "routine", "enclave": "10.42.30.0/24",
        "host": "10.42.30.17", "workflow": "facility_maintenance",
    },
}

# Loads carried by the feeders. `protected` loads can never be shed or curtailed.
LOADS = {
    "LOAD-CLINIC-01": {"feeder": "feeder-a", "class": "protected", "name": "Base clinic"},
    "LOAD-TOWER-01": {"feeder": "feeder-a", "class": "protected", "name": "Flightline control tower"},
    "LOAD-ALERT-01": {"feeder": "feeder-a", "class": "protected", "name": "Alert facility"},
    "LOAD-FUELOPS-01": {"feeder": "feeder-a", "class": "protected", "name": "Fuels operations"},
    "LOAD-HANGAR-04": {"feeder": "feeder-b", "class": "sheddable", "name": "Hangar 4 shop air"},
    "LOAD-DORM-12": {"feeder": "feeder-b", "class": "sheddable", "name": "Dormitory 12 HVAC"},
    "LOAD-ADMIN-02": {"feeder": "feeder-b", "class": "sheddable", "name": "Admin building 2"},
    "LOAD-WAREHOUSE-07": {"feeder": "feeder-b", "class": "sheddable", "name": "Warehouse 7 lighting"},
}

# --------------------------------------------------------------------------
# Electrical envelope. PLACEHOLDER VALUES — require engineering sign-off.
# --------------------------------------------------------------------------

ELECTRICAL = {
    "nominal_v": 480.0,
    "hard_min_v": 456.0,          # ANSI C84.1 Range A service band, 480 V nominal
    "hard_max_v": 504.0,
    "normal_min_v": 468.0,        # tighter operating band used for grants
    "normal_max_v": 492.0,
    "approval_delta_v": 6.0,      # change larger than this needs technician step-up
    "settle_ms": 2_000,           # POST_ACTION measurements ignored before this
    "generator_max_kw": 1_250.0,
    "bess_min_soc_pct": 20.0,
    "note": "Placeholder envelope for the demonstration; not an approved limit set.",
}

# --------------------------------------------------------------------------
# Humans. `deploys_agents` marks who may stand up an AI agent at all.
# --------------------------------------------------------------------------

USERS = {
    "msgt.d.reyes": {
        "display_name": "MSgt D. Reyes", "unit": "899-CES/POWER-PRO",
        "role": "power_production_supervisor", "deploys_agents": True,
        "technician_console": True, "approval_authority": ["set_voltage_setpoint",
            "close_switchgear", "open_switchgear", "dispatch_generator"],
        "purchase_ceiling_usd": 5_000,
    },
    "ssgt.a.okafor": {
        "display_name": "SSgt A. Okafor", "unit": "899-CES/POWER-PRO",
        "role": "electrician", "deploys_agents": True,
        "technician_console": True, "approval_authority": ["set_voltage_setpoint"],
        "purchase_ceiling_usd": 1_000,
    },
    "a1c.r.delgado": {
        "display_name": "A1C R. Delgado", "unit": "899-CES/POWER-PRO",
        "role": "apprentice_electrician", "deploys_agents": True,
        "technician_console": False, "approval_authority": [],
        "purchase_ceiling_usd": 0,
    },
    "tsgt.m.lindqvist": {
        "display_name": "TSgt M. Lindqvist", "unit": "899-CS",
        "role": "cyber_defense_operator", "deploys_agents": True,
        "technician_console": True, "approval_authority": ["modify_firewall", "allow_outbound"],
        "purchase_ceiling_usd": 0,
    },
    "capt.j.whitfield": {
        "display_name": "Capt J. Whitfield", "unit": "899-CES/ENERGY",
        "role": "base_energy_manager", "deploys_agents": True,
        "technician_console": True, "approval_authority": ["curtail_load"],
        "purchase_ceiling_usd": 2_500,
    },
    "gs12.k.tran": {
        "display_name": "K. Tran, GS-12", "unit": "899-CES/OPS-ENG",
        "role": "facility_manager", "deploys_agents": True,
        "technician_console": True, "approval_authority": ["create_work_order", "order_parts"],
        "purchase_ceiling_usd": 2_500,
    },
    "ctr.p.osei": {
        "display_name": "P. Osei (contractor)", "unit": "CTR-MGS",
        "role": "vendor_support", "deploys_agents": True,
        "technician_console": False, "approval_authority": [],
        "purchase_ceiling_usd": 0,
        "escort_required": True,
        "access_window_utc": ["2026-09-08T13:00:00Z", "2026-09-08T21:00:00Z"],
    },
    "col.s.hargrove": {
        "display_name": "Col S. Hargrove", "unit": "899-MSG",
        "role": "squadron_commander", "deploys_agents": False,
        "technician_console": True,
        "approval_authority": ["set_voltage_setpoint", "open_switchgear", "close_switchgear",
                               "dispatch_generator", "curtail_load", "order_parts"],
        "purchase_ceiling_usd": 50_000,
    },
    "svc.alice-sync": {
        "display_name": "ALICE Pi synchronization principal", "unit": "899-CS",
        "role": "service_sync", "deploys_agents": False,
        "technician_console": False, "approval_authority": [],
        "purchase_ceiling_usd": 0,
        "note": "Non-human. Reads permissions releases, writes audit. Never a requester.",
    },
}

# --------------------------------------------------------------------------
# AI agents. `role` / `mission_type` are the pair the cyber baseline routes on.
# --------------------------------------------------------------------------

AGENTS = {
    "elec-agent-01": {
        "type": "electrician", "role": "electrician", "mission_type": "power_distribution",
        "responsible_user": "ssgt.a.okafor", "delegator": "msgt.d.reyes",
        "deployed_at": "2026-06-02T14:10:00Z", "targets": ["FEEDER-A-RTU", "FEEDER-B-RTU", "METER-GW-01"],
        "feeders": ["feeder-a", "feeder-b"], "baseline_profile": "elec-agent-01",
    },
    "elec-agent-02": {
        "type": "electrician", "role": "electrician", "mission_type": "power_distribution",
        "responsible_user": "msgt.d.reyes", "delegator": "col.s.hargrove",
        "deployed_at": "2026-05-18T09:40:00Z", "targets": ["FEEDER-A-RTU", "FEEDER-B-RTU", "BESS-CTRL-02"],
        "feeders": ["feeder-a", "feeder-b"], "baseline_profile": "elec-agent-02",
    },
    "elec-agent-07": {
        "type": "electrician", "role": "electrician", "mission_type": "power_distribution",
        "responsible_user": "ssgt.a.okafor", "delegator": "msgt.d.reyes",
        "deployed_at": "2026-09-04T22:05:00Z", "targets": ["FEEDER-B-RTU"],
        "feeders": ["feeder-b"], "baseline_profile": None,
        "note": "Deployed after the current baseline release; resolves to the role/mission cohort "
                "and keeps an explicit novelty flag.",
    },
    "microgrid-agent-01": {
        "type": "microgrid_dispatch", "role": "power_production", "mission_type": "microgrid_dispatch",
        "responsible_user": "msgt.d.reyes", "delegator": "col.s.hargrove",
        "deployed_at": "2026-04-21T11:00:00Z", "targets": ["SPIDERS-MGC-01", "BESS-CTRL-02"],
        "feeders": ["feeder-a", "feeder-b"], "baseline_profile": "microgrid-agent-01",
    },
    "dr-agent-01": {
        "type": "demand_response", "role": "energy_manager", "mission_type": "demand_response",
        "responsible_user": "capt.j.whitfield", "delegator": "col.s.hargrove",
        "deployed_at": "2026-07-09T16:25:00Z", "targets": ["METER-GW-01"],
        "feeders": ["feeder-b"], "baseline_profile": "dr-agent-01",
    },
    "maint-agent-01": {
        "type": "facility_maintenance", "role": "facility_maintenance",
        "mission_type": "predictive_maintenance",
        "responsible_user": "gs12.k.tran", "delegator": "col.s.hargrove",
        "deployed_at": "2026-03-30T08:15:00Z",
        "targets": ["BUILDER-SVC-01", "WO-API-01", "TRIRIGA-APP-01"],
        "feeders": [], "baseline_profile": "maint-agent-01",
    },
    "cyber-agent-04": {
        "type": "cyber_defense", "role": "cyber_defense", "mission_type": "network_investigation",
        "responsible_user": "tsgt.m.lindqvist", "delegator": "col.s.hargrove",
        "deployed_at": "2026-02-11T13:45:00Z", "targets": ["SCADA-HMI-02", "TRIRIGA-APP-01"],
        "feeders": [], "baseline_profile": "cyber-agent-04",
    },
    "appr-agent-01": {
        "type": "apprentice_readonly", "role": "apprentice", "mission_type": "training_observation",
        "responsible_user": "a1c.r.delgado", "delegator": "msgt.d.reyes",
        "deployed_at": "2026-08-24T10:00:00Z", "targets": ["FEEDER-A-RTU"],
        "feeders": ["feeder-a"], "baseline_profile": "appr-agent-01",
    },
    "vendor-agent-01": {
        "type": "vendor_support", "role": "vendor_support", "mission_type": "scada_maintenance",
        "responsible_user": "ctr.p.osei", "delegator": "tsgt.m.lindqvist",
        "deployed_at": "2026-09-08T13:00:00Z", "targets": ["SCADA-HMI-02"],
        "feeders": [], "baseline_profile": "vendor-agent-01",
        "expires_at": "2026-09-08T21:00:00Z",
    },
}

# --------------------------------------------------------------------------
# Action catalog. CYBER_ACTIONS are fixed by dcamr.anomaly_engine.baseline and
# must not gain members. OT_ACTIONS live only in the permissions bundle and are
# scored, when scored at all, by the separate contextual profiles.
# --------------------------------------------------------------------------

CYBER_ACTIONS = ("read_logs", "query_status", "query_network", "modify_firewall", "allow_outbound")

OT_ACTIONS = {
    "read_meter": {"state_changing": False, "workflow": "power_distribution"},
    "read_asset_record": {"state_changing": False, "workflow": "system_of_record"},
    "set_voltage_setpoint": {"state_changing": True, "workflow": "power_distribution",
                             "parameters": {"setpoint_v": "volt"}},
    "set_load_shed_priority": {"state_changing": True, "workflow": "microgrid_control",
                               "parameters": {"load_id": "identifier", "priority": "rank"}},
    "curtail_load": {"state_changing": True, "workflow": "demand_response",
                     "parameters": {"load_id": "identifier", "curtail_kw": "kilowatt"}},
    "open_switchgear": {"state_changing": True, "workflow": "microgrid_control",
                        "parameters": {"switch_id": "identifier"}},
    "close_switchgear": {"state_changing": True, "workflow": "microgrid_control",
                         "parameters": {"switch_id": "identifier"}},
    "dispatch_generator": {"state_changing": True, "workflow": "microgrid_control",
                           "parameters": {"generator_id": "identifier", "output_kw": "kilowatt"}},
    "disable_protective_relay": {"state_changing": True, "workflow": "microgrid_control",
                                 "parameters": {"relay_id": "identifier"}},
    "drop_islanding": {"state_changing": True, "workflow": "microgrid_control"},
    "create_work_order": {"state_changing": True, "workflow": "facility_maintenance",
                          "parameters": {"asset_id": "identifier", "priority": "rank"}},
    "order_parts": {"state_changing": True, "workflow": "facility_maintenance",
                    "parameters": {"part_number": "identifier", "amount_usd": "usd"}},
    "update_asset_record": {"state_changing": True, "workflow": "system_of_record",
                            "parameters": {"asset_id": "identifier"}},
}
