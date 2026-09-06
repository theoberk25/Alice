import unittest
from datetime import datetime, timezone
from lab.enterprise_sim.console.soc import snapshot, browser_safe, summarize
from lab.enterprise_sim.soc_seed import SCENARIO, build_alerts, bulk_body

class SocTests(unittest.TestCase):
    def test_unavailable_does_not_fabricate_zero_or_demo_data(self):
        def offline(*args):raise OSError('offline')
        data=snapshot(offline)
        self.assertFalse(data['alerts']['available'])
        self.assertIsNone(data['alerts']['total'])
        self.assertEqual(data['ledger']['rows'],[])
        self.assertEqual(data['enterprise']['rows'],[])

    def test_stream_failure_is_independent(self):
        def query(path,body):
            if path.startswith('/wazuh'):raise OSError()
            self.assertEqual(body['size'],100 if path.startswith('/alice') else 300)
            return {'hits':{'total':{'value':2},'hits':[]},'aggregations':{'nodes':{'buckets':[]}}}
        data=snapshot(query)
        self.assertFalse(data['alerts']['available'])
        self.assertTrue(data['ledger']['available'])
        self.assertEqual(data['ledger']['total'],2)
        self.assertTrue(data['enterprise']['available'])
        self.assertEqual(data['enterprise']['total'],2)

    def test_time_window_filters_alerts_only(self):
        calls=[]
        def query(path,body):calls.append((path,body));raise OSError()
        snapshot(query,'24h')
        self.assertEqual(calls[0][1]['query'],{'range':{'timestamp':{'gte':'now-24h'}}})
        self.assertNotIn('query',calls[1][1])
        self.assertNotIn('query',calls[2][1])

    def test_invalid_window_rejected_without_query(self):
        with self.assertRaises(ValueError):snapshot(lambda *_:self.fail('Unexpected query'),'invalid')

    def test_large_integer_projection_is_exact(self):
        raw={'clock':9223372036854775807,'seq':97,'ok':True}
        self.assertEqual(browser_safe(raw),{'clock':'9223372036854775807','seq':97,'ok':True})
        self.assertIsInstance(raw['clock'],int)

    def test_energy_infrastructure_seed_is_coherent_and_idempotent(self):
        rows=build_alerts(datetime(2026,9,6,12,0,tzinfo=timezone.utc))
        self.assertGreaterEqual(len(rows),400)
        self.assertTrue(all(row['data']['scenario']==SCENARIO for row in rows))
        self.assertTrue(all('Sentinel' not in row['full_log'] for row in rows))
        self.assertTrue(any(row['data'].get('vulnerability') for row in rows))
        self.assertTrue(any((row['rule'].get('mitre') or {}).get('id') for row in rows))
        body=bulk_body(rows).decode().splitlines()
        self.assertEqual(len(body),len(rows)*2)
        self.assertEqual(len({__import__('json').loads(body[i])['create']['_id']
                              for i in range(0,len(body),2)}),len(rows))

    def test_posture_is_derived_from_indexed_rows(self):
        rows=build_alerts(datetime(2026,9,6,12,0,tzinfo=timezone.utc))
        posture=summarize(rows)
        self.assertGreaterEqual(len(posture['vulnerabilities']),2)
        self.assertGreater(posture['mitre']['techniques']['T1078'],0)
        self.assertEqual(posture['compliance']['failed'],1)
        self.assertEqual(posture['compliance']['passed'],1)
