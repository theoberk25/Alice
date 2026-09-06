"""Sentinel ESP demo operator metadata, not a signed Pi permissions release."""
from copy import deepcopy

USER_ID = 'ssgt.a.okafor'
ROLE_ID = 'sentinel_esp_operator'
INDEX = 'alice-operator-profiles'


def profile():
    return {
        'schema_version': 'alice-demo-operator-profile-v1',
        'user_id': USER_ID, 'display_name': 'SSgt A. Okafor',
        'unit': '899-CES/POWER-PRO', 'role': ROLE_ID,
        'agent_id': 'elec-agent-01', 'mission': 'ESP simulated power-grid demonstration',
        'authority': 'DESCRIPTIVE_ONLY_NOT_A_SIGNED_RELEASE',
        'confirmed_demo_interface': {
            'action': 'set_light_state', 'target': 'ESP-LIGHT-01',
            'parameters': {'state': ['on', 'off']},
            'execution_path': 'Signed agent request -> Pi verified release -> controller',
            'permission_source': 'Existing first-light release; this profile grants nothing',
        },
        'proposed_capabilities': [
            {'action': 'read_voltage', 'status': 'PENDING_SENSOR_CONTRACT',
             'requires': ['units', 'sensor identity', 'timestamp', 'freshness', 'calibration']},
            {'action': 'set_voltage_setpoint', 'status': 'NOT_ENABLED_FOR_ESP',
             'requires': ['hardware-owner limits', 'signed grant', 'adapter', 'human review contract']},
            {'action': 'switch_feeder', 'status': 'NOT_ENABLED_FOR_ESP',
             'requires': ['target mapping', 'interlocks', 'signed grant', 'human review contract']},
        ],
        'enterprise_access': ['read demo permissions', 'read demo audit and ledger',
                              'read operator profiles', 'read dashboard saved objects'],
        'excluded_authority': ['publish permissions', 'write/delete audit', 'manage users',
                               'approve own held actions', 'bypass hard deny', 'direct ESP commands'],
        'warning': 'Synthetic base identity. Historical enterprise voltage grants do not authorize new ESP hardware.',
    }


_ROLE = {
    'cluster_permissions': ['cluster_composite_ops_ro'],
    'index_permissions': [
        {'index_patterns': ['alice-permissions', 'alice-audit-*', 'alice-ledger-v1', INDEX],
         'allowed_actions': ['read', 'indices:admin/mappings/get', 'indices:admin/aliases/get']},
        {'index_patterns': ['.kibana', '.kibana_*', '.opensearch_dashboards', '.opensearch_dashboards_*'],
         'allowed_actions': ['read']},
    ],
    'tenant_permissions': [{'tenant_patterns': ['global_tenant'], 'allowed_actions': ['kibana_all_read']}],
}


def indexer_role():
    return deepcopy(_ROLE)
