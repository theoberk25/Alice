import unittest
from lab.enterprise_sim.esp_operator import profile, indexer_role

class EspOperatorTests(unittest.TestCase):
    def test_profile_does_not_enable_provisional_grid_controls(self):
        p=profile()
        self.assertEqual(p['agent_id'],'elec-agent-01')
        self.assertEqual(p['authority'],'DESCRIPTIVE_ONLY_NOT_A_SIGNED_RELEASE')
        self.assertTrue(all(c['status'] != 'ENABLED' for c in p['proposed_capabilities']))
        self.assertEqual(p['confirmed_demo_interface']['parameters'],{'state':['on','off']})

    def test_role_contains_no_operational_write_or_admin_wildcard(self):
        role=indexer_role()
        for entry in role['index_permissions']:
            self.assertNotIn('*',entry['index_patterns'])
            self.assertTrue(set(entry['allowed_actions']) <= {'read','indices:admin/mappings/get','indices:admin/aliases/get'})
        self.assertEqual(role['cluster_permissions'],['cluster_composite_ops_ro'])

    def test_callers_cannot_mutate_shared_role(self):
        r=indexer_role();r['index_permissions'].clear()
        self.assertTrue(indexer_role()['index_permissions'])
