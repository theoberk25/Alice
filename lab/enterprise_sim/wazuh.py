"""Wazuh-side configuration artifacts for the simulated Sentinel AFB network.

Everything here is text this module writes to disk for a human to review and
apply. Nothing contacts a Wazuh manager, indexer or API. Endpoint paths and
field names follow Wazuh 4.x conventions and must be checked against the
version actually deployed before use.
"""

import json

from .scenario import AGENTS, SITE, SYSTEMS, USERS

# --------------------------------------------------------------------------
# Simulated enrolled endpoints
# --------------------------------------------------------------------------

ENDPOINTS = [
    {"id": "001", "name": "alice-pi-01", "ip": "10.42.10.11",
     "os": "Debian GNU/Linux 12 (aarch64)", "groups": ["default", "alice-pi"],
     "role": "ALICE decision node (Raspberry Pi 4, 2 GB)"},
    {"id": "002", "name": "agent-mac-01", "ip": "10.42.10.21",
     "os": "macOS 15.4", "groups": ["default", "workstations"],
     "role": "Agent Mac: proposes requests"},
    {"id": "003", "name": "tech-mac-01", "ip": "10.42.10.22",
     "os": "macOS 15.4", "groups": ["default", "workstations"],
     "role": "Technician Mac: console, face verification, local LLM"},
    {"id": "004", "name": "spiders-mgc-01", "ip": "10.42.20.10",
     "os": "Ubuntu 22.04.5 LTS", "groups": ["default", "ot-controllers"],
     "role": "SPIDERS microgrid controller"},
    {"id": "005", "name": "spiders-relay-03", "ip": "10.42.20.11",
     "os": "embedded (syslog only)", "groups": ["default", "ot-controllers"],
     "role": "Protective relay bank; syslog forwarded, no agent installed"},
    {"id": "006", "name": "bess-ctrl-02", "ip": "10.42.20.12",
     "os": "Ubuntu 22.04.5 LTS", "groups": ["default", "ot-controllers"],
     "role": "Battery energy storage controller"},
    {"id": "007", "name": "scada-hmi-02", "ip": "10.42.20.32",
     "os": "Windows 10 IoT Enterprise", "groups": ["default", "ot-workstations"],
     "role": "SCADA HMI, IT/OT bridge"},
    {"id": "008", "name": "feeder-a-rtu", "ip": "10.42.20.41",
     "os": "ESP32 firmware 1.4.2", "groups": ["default", "esp-controllers"],
     "role": "Feeder A RTU / ESP demo node"},
    {"id": "009", "name": "feeder-b-rtu", "ip": "10.42.20.42",
     "os": "ESP32 firmware 1.4.2", "groups": ["default", "esp-controllers"],
     "role": "Feeder B RTU / ESP demo node"},
    {"id": "010", "name": "meter-gw-01", "ip": "10.42.20.44",
     "os": "OpenWrt 23.05", "groups": ["default", "ot-controllers"],
     "role": "Metering and demand-response gateway"},
    {"id": "011", "name": "tririga-app-01", "ip": "10.42.30.15",
     "os": "Red Hat Enterprise Linux 9.4", "groups": ["default", "it-servers"],
     "role": "TRIRIGA system of record"},
    {"id": "012", "name": "builder-svc-01", "ip": "10.42.30.16",
     "os": "Windows Server 2022", "groups": ["default", "it-servers"],
     "role": "BUILDER / Piton condition assessment"},
    {"id": "013", "name": "wo-api-01", "ip": "10.42.30.17",
     "os": "Ubuntu 22.04.5 LTS", "groups": ["default", "it-servers"],
     "role": "Work order and parts requisition API"},
]

AGENT_GROUPS = {
    "alice-pi": "The ALICE decision node. Reads its permissions release and ships audit.",
    "esp-controllers": "ESP feeder nodes. Telemetry only; never a permissions source.",
    "ot-controllers": "Microgrid, storage and metering controllers.",
    "ot-workstations": "HMI and operator workstations bridging IT and OT.",
    "it-servers": "TRIRIGA, BUILDER and work-order services.",
    "workstations": "Agent and technician Macs.",
}

# --------------------------------------------------------------------------
# Rules. Wazuh's built-in JSON decoder parses the audit lines, so the rules
# match decoded fields directly and no custom decoder is needed for them.
# --------------------------------------------------------------------------

LOCAL_RULES = """<!--
  ALICE custom rules for the Sentinel AFB simulation.
  Install as /var/ossec/etc/rules/local_rules.xml and restart wazuh-manager.

  Custom rule IDs must be >= 100000. The 100100-100199 block is reserved here
  for ALICE. Levels are a starting point for the demonstration and should be
  agreed with whoever owns alerting before this reaches anything real.

  These rules describe what ALICE reported. A Wazuh alert is downstream
  evidence about a decision; it is not the decision, and it never becomes a
  normal-behavior training label.
-->
<group name="alice,">

  <!-- Parent: any well-formed ALICE audit event. Level 0 = no alert by itself. -->
  <rule id="100100" level="0">
    <decoded_as>json</decoded_as>
    <field name="alice.schema_version">alice-audit-event-v1</field>
    <description>ALICE audit event</description>
  </rule>

  <!-- ---------------- Offline machine decisions ---------------- -->
  <rule id="100110" level="3">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">DECISION</field>
    <field name="alice.decision">ALLOW</field>
    <description>ALICE allowed $(alice.action) on $(alice.target) for $(alice.agent_id)</description>
    <group>alice_decision,</group>
  </rule>

  <rule id="100111" level="5">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">DECISION</field>
    <field name="alice.decision">REQUEST_CONTEXT</field>
    <description>ALICE requested more context for $(alice.action) on $(alice.target)</description>
    <group>alice_decision,</group>
  </rule>

  <rule id="100112" level="8">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">DECISION</field>
    <field name="alice.decision">HOLD</field>
    <description>ALICE held $(alice.action) on $(alice.target) for technician review</description>
    <group>alice_decision,</group>
  </rule>

  <rule id="100113" level="10">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">DECISION</field>
    <field name="alice.decision">DENY</field>
    <description>ALICE denied $(alice.action) on $(alice.target) for $(alice.agent_id)</description>
    <group>alice_decision,</group>
  </rule>

  <!-- A hard prohibition is a different event from an ordinary denial. -->
  <rule id="100114" level="12">
    <if_sid>100113</if_sid>
    <field name="alice.prohibition_id">\\.+</field>
    <description>ALICE hard prohibition $(alice.prohibition_id) blocked $(alice.action) on $(alice.target)</description>
    <group>alice_decision,alice_prohibition,</group>
  </rule>

  <!-- ---------------- Permissions synchronization ---------------- -->
  <rule id="100120" level="5">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">PERMISSIONS_ACTIVATED</field>
    <description>ALICE activated permissions generation $(alice.generation)</description>
    <group>alice_permissions,</group>
  </rule>

  <rule id="100121" level="12">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">PERMISSIONS_REJECTED</field>
    <description>ALICE rejected a permissions candidate: $(alice.reason_code)</description>
    <group>alice_permissions,</group>
  </rule>

  <!-- Rollback attempt: a candidate older than what the Pi already accepted. -->
  <rule id="100122" level="14">
    <if_sid>100121</if_sid>
    <field name="alice.reason_code">STALE_GENERATION</field>
    <description>ALICE refused an older permissions generation; possible rollback attempt</description>
    <group>alice_permissions,alice_rollback,</group>
  </rule>

  <rule id="100123" level="10">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">PERMISSIONS_EXPIRED</field>
    <description>ALICE is deciding under an expired permissions generation $(alice.generation)</description>
    <group>alice_permissions,</group>
  </rule>

  <rule id="100124" level="7">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">PERMISSIONS_DRIFT</field>
    <description>ALICE found $(alice.affected_decisions) offline decisions made under a superseded generation</description>
    <group>alice_permissions,alice_reconciliation,</group>
  </rule>

  <!-- ---------------- Authority and mode ---------------- -->
  <rule id="100130" level="7">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">AUTHORITY_TRANSITION</field>
    <description>ALICE authority transition: $(alice.from_mode) to $(alice.to_mode)</description>
    <group>alice_authority,</group>
  </rule>

  <rule id="100131" level="13">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">AUTHORITY_UNCERTAIN</field>
    <description>ALICE cannot identify the current execution authority; execution is blocked</description>
    <group>alice_authority,</group>
  </rule>

  <!-- ---------------- Execution evidence ---------------- -->
  <rule id="100140" level="5">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">EXECUTION_ATTEMPTED</field>
    <description>ALICE forwarded $(alice.action) to $(alice.target)</description>
    <group>alice_execution,</group>
  </rule>

  <rule id="100141" level="5">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">EXECUTION_RESULT</field>
    <description>Controller reported $(alice.result) for $(alice.action) on $(alice.target)</description>
    <group>alice_execution,</group>
  </rule>

  <!-- The commanded value and the measured value disagree. This is the case a
       controller success receipt cannot tell you about. -->
  <rule id="100142" level="12">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">EXECUTION_EFFECT_MISMATCH</field>
    <description>Measured effect does not match the command on $(alice.target); observed $(alice.observed) against commanded $(alice.commanded)</description>
    <group>alice_execution,alice_telemetry,</group>
  </rule>

  <rule id="100143" level="9">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">TELEMETRY_UNAVAILABLE</field>
    <description>No independent measurement available for $(alice.action) on $(alice.target)</description>
    <group>alice_execution,alice_telemetry,</group>
  </rule>

  <!-- ---------------- Technician review ---------------- -->
  <rule id="100150" level="8">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">TECHNICIAN_APPROVAL_ACCEPTED</field>
    <description>ALICE accepted an approval from $(alice.technician_id) for $(alice.action)</description>
    <group>alice_review,</group>
  </rule>

  <rule id="100151" level="10">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">TECHNICIAN_APPROVAL_REJECTED</field>
    <description>ALICE rejected a technician approval: $(alice.reason_code)</description>
    <group>alice_review,</group>
  </rule>

  <rule id="100152" level="10">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">FACE_VERIFICATION_FAILED</field>
    <description>Face verification failed for $(alice.technician_id); the approval path stays closed</description>
    <group>alice_review,</group>
  </rule>

  <!-- ---------------- Anomaly assessments ---------------- -->
  <rule id="100160" level="7">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">ANOMALY_ASSESSMENT</field>
    <field name="alice.band">ELEVATED</field>
    <description>Elevated $(alice.phase) anomaly for $(alice.agent_id) on $(alice.target)</description>
    <group>alice_anomaly,</group>
  </rule>

  <rule id="100161" level="10">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">ANOMALY_ASSESSMENT</field>
    <field name="alice.band">HIGH</field>
    <description>High $(alice.phase) anomaly for $(alice.agent_id) on $(alice.target)</description>
    <group>alice_anomaly,</group>
  </rule>

  <!-- An unsupported context is not a low score. It is a refusal to score. -->
  <rule id="100162" level="6">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">ANOMALY_ASSESSMENT</field>
    <field name="alice.status">UNKNOWN_CONTEXT</field>
    <description>No fitted context for $(alice.context); ALICE returned a null score</description>
    <group>alice_anomaly,</group>
  </rule>

  <rule id="100163" level="6">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">ANOMALY_ASSESSMENT</field>
    <field name="alice.novelty">\\.+</field>
    <description>Novelty flag $(alice.novelty) retained for $(alice.agent_id)</description>
    <group>alice_anomaly,</group>
  </rule>

  <!-- ---------------- Audit integrity ---------------- -->
  <rule id="100170" level="14">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">AUDIT_CHAIN_GAP</field>
    <description>Audit sequence gap against the last trusted checkpoint on $(alice.node_id)</description>
    <group>alice_audit,alice_integrity,</group>
  </rule>

  <rule id="100171" level="12">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">AUDIT_CAPACITY_BLOCK</field>
    <description>ALICE blocked consequential actions: audit storage below reserve</description>
    <group>alice_audit,</group>
  </rule>

  <rule id="100172" level="3">
    <if_sid>100100</if_sid>
    <field name="alice.event_type">AUDIT_CHECKPOINT</field>
    <description>ALICE audit checkpoint at sequence $(alice.sequence)</description>
    <group>alice_audit,</group>
  </rule>

  <!-- ---------------- Correlation ---------------- -->
  <!-- Repeated denials for one agent inside five minutes. -->
  <rule id="100180" level="12" frequency="6" timeframe="300">
    <if_matched_sid>100113</if_matched_sid>
    <same_field>alice.agent_id</same_field>
    <description>Repeated ALICE denials for $(alice.agent_id) within five minutes</description>
    <group>alice_decision,alice_correlation,</group>
  </rule>

  <!-- Repeated setpoint changes: the rapid-cycling case the model also sees. -->
  <rule id="100181" level="11" frequency="8" timeframe="600">
    <if_matched_sid>100140</if_matched_sid>
    <same_field>alice.target</same_field>
    <description>Repeated command forwarding to $(alice.target) within ten minutes</description>
    <group>alice_execution,alice_correlation,</group>
  </rule>

</group>
"""

# --------------------------------------------------------------------------
# A decoder for the ESP controller's plain syslog line. The ALICE audit is JSON
# and needs no custom decoder; this covers the non-JSON device.
# --------------------------------------------------------------------------

LOCAL_DECODERS = """<!--
  Install as /var/ossec/etc/decoders/local_decoder.xml.

  Example line this matches:
  feeder-a-rtu esp32[1421]: setpoint cmd=482.500 bus=480.100 load=214.30 mode=grid_tied

  Device telemetry is evidence about a feeder. It is not an authorization, and
  a line claiming a mode does not establish that mode.
-->
<decoder name="esp-feeder">
  <program_name>^esp32</program_name>
</decoder>

<decoder name="esp-feeder-setpoint">
  <parent>esp-feeder</parent>
  <regex>setpoint cmd=(\\S+) bus=(\\S+) load=(\\S+) mode=(\\w+)</regex>
  <order>esp.commanded_v, esp.bus_v, esp.load_a, esp.operating_mode</order>
</decoder>
"""

ESP_RULES = """<!--
  Append to local_rules.xml, or keep as a separate file listed in ossec.conf.
  These describe the device's own report, which is not independent measurement
  of whether the physical bus actually moved.
-->
<group name="esp,sentinel,">
  <rule id="100190" level="0">
    <decoded_as>esp-feeder</decoded_as>
    <description>ESP feeder controller telemetry</description>
  </rule>

  <rule id="100191" level="3">
    <if_sid>100190</if_sid>
    <field name="esp.operating_mode">grid_tied</field>
    <description>Feeder setpoint report (grid tied): commanded $(esp.commanded_v) V</description>
  </rule>

  <rule id="100192" level="6">
    <if_sid>100190</if_sid>
    <field name="esp.operating_mode">islanded</field>
    <description>Feeder setpoint report while islanded: commanded $(esp.commanded_v) V</description>
  </rule>
</group>
"""

# --------------------------------------------------------------------------
# Agent-side collection config for the ALICE Pi
# --------------------------------------------------------------------------

AGENT_CONF = """<!--
  Shared configuration pushed to the `alice-pi` group.
  Place on the manager at /var/ossec/etc/shared/alice-pi/agent.conf

  The agent MIRRORS the audit for live visibility. It is not the durable
  outbox: when the manager is unreachable the client buffer drops events once
  full, and logcollector does not replay what it never read. ALICE keeps its
  own append-only log plus cursor on local disk and replays that on
  reconnection with idempotent event IDs.
-->
<agent_config>

  <localfile>
    <location>/var/lib/alice/audit/mission-audit.jsonl</location>
    <log_format>json</log_format>
  </localfile>

  <localfile>
    <location>/var/lib/alice/audit/sync-events.jsonl</location>
    <log_format>json</log_format>
  </localfile>

  <!-- Flow control. Raising queue_size costs agent memory on a 2 GB node;
       measure before changing it. -->
  <client_buffer>
    <disabled>no</disabled>
    <queue_size>8192</queue_size>
    <events_per_second>250</events_per_second>
  </client_buffer>

  <!-- Watch the trusted input tree for changes ALICE did not make. Only the
       privileged updater should ever write here. -->
  <syscheck>
    <disabled>no</disabled>
    <frequency>300</frequency>
    <directories check_all="yes" realtime="yes">/media/alice-usb/permissions</directories>
    <directories check_all="yes" realtime="yes">/media/alice-usb/normal_behavior</directories>
    <!-- The audit tree changes constantly by design; reporting every append
         would be noise, so only report new and removed files there. -->
    <directories check_all="no" check_sum="no" report_changes="no"
                 realtime="yes">/media/alice-usb/audit_logs</directories>
  </syscheck>

</agent_config>
"""

# --------------------------------------------------------------------------
# Indexer: templates and RBAC
# --------------------------------------------------------------------------

PERMISSIONS_TEMPLATE = {
    "index_patterns": ["alice-permissions*"],
    "template": {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0,
                     "refresh_interval": "5s"},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "bundle_id": {"type": "keyword"},
                "generation": {"type": "long"},
                "issuer_id": {"type": "keyword"},
                "site_id": {"type": "keyword"},
                "issued_at": {"type": "date"},
                "not_before": {"type": "date"},
                "not_after": {"type": "date"},
                "revocation_epoch": {"type": "long"},
                "status": {"type": "keyword"},
                "release_note": {"type": "text"},
                "manifest_sha256": {"type": "keyword"},
                "manifest_b64": {"type": "binary"},
                "signature_b64": {"type": "binary"},
                "payload_b64": {"type": "object", "enabled": False},
                "compatibility": {"type": "object", "enabled": False},
            },
        },
    },
    "priority": 500,
    "_meta": {"owner": "ALICE", "note": "Wazuh distributes these releases; the "
              "issuer_id above is what authorizes their contents."},
}

AUDIT_TEMPLATE = {
    "index_patterns": ["alice-audit-*"],
    "template": {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "dynamic": "true",
            "properties": {
                "event_id": {"type": "keyword"},
                "node_id": {"type": "keyword"},
                "boot_id": {"type": "keyword"},
                "sequence": {"type": "long"},
                "recorded_at": {"type": "date"},
                "event_type": {"type": "keyword"},
                "mode": {"type": "keyword"},
                "authority": {"type": "keyword"},
                "decision": {"type": "keyword"},
                "agent_id": {"type": "keyword"},
                "responsible_user": {"type": "keyword"},
                "delegator": {"type": "keyword"},
                "action": {"type": "keyword"},
                "target": {"type": "keyword"},
                "prohibition_id": {"type": "keyword"},
                "grant_id": {"type": "keyword"},
                "permissions_generation": {"type": "long"},
                "permissions_freshness": {"type": "keyword"},
                "band": {"type": "keyword"},
                "score": {"type": "float"},
                "reason_codes": {"type": "keyword"},
                "prev_hash": {"type": "keyword"},
                "event_hash": {"type": "keyword"},
            },
        },
    },
    "priority": 500,
    "_meta": {"owner": "ALICE", "note": "Written by the Pi on reconnection with "
              "_bulk create and _id = event_id, so replay is idempotent."},
}

# Wazuh manager API RBAC: what the Pi's own API principal may read.
API_POLICY = {
    "name": "alice_pi_readonly",
    "policy": {
        "actions": ["agent:read", "group:read", "cluster:read"],
        "resources": ["agent:id:001", "agent:group:alice-pi", "*:*:*"],
        "effect": "allow",
    },
}

API_ROLE = {"name": "alice_pi_sync"}

# Indexer (OpenSearch security plugin) role: read releases, write audit only.
INDEXER_ROLE = {
    "cluster_permissions": ["cluster_composite_ops_ro", "indices:data/write/bulk"],
    "index_permissions": [
        {"index_patterns": ["alice-permissions*"],
         "allowed_actions": ["read", "search", "get"]},
        {"index_patterns": ["alice-audit-*"],
         "allowed_actions": ["create_index", "write", "index", "indices:data/write/bulk*"]},
    ],
    "tenant_permissions": [],
}

INDEXER_ROLE_MAPPING = {
    "users": ["alice_pi"],
    "description": "The ALICE Pi. Reads permissions releases, appends audit, "
                   "and can do nothing else.",
}


def dumps(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=False) + "\n"


def build_inventory() -> dict:
    return {
        "site": SITE,
        "note": "Simulated enrollment inventory. `wazuh-agent` runs on the hosts "
                "marked agent_installed; the relay and ESP nodes forward syslog "
                "instead, because a microcontroller does not run a Wazuh agent.",
        "groups": AGENT_GROUPS,
        "endpoints": [
            {**endpoint,
             "agent_installed": endpoint["os"] not in
             ("embedded (syslog only)", "ESP32 firmware 1.4.2")}
            for endpoint in ENDPOINTS
        ],
        "protected_systems": SYSTEMS,
        "human_users": {user_id: {"display_name": user["display_name"],
                                  "unit": user["unit"], "role": user["role"]}
                        for user_id, user in sorted(USERS.items())},
        "ai_agents": {agent_id: {"type": agent["type"],
                                 "responsible_user": agent["responsible_user"],
                                 "targets": agent["targets"]}
                      for agent_id, agent in sorted(AGENTS.items())},
    }
