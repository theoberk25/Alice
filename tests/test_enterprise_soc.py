import unittest
from lab.enterprise_sim.console.soc import snapshot, browser_safe

class SocTests(unittest.TestCase):
    def test_unavailable_does_not_fabricate_zero_or_demo_data(self):
        def offline(*args):raise OSError('offline')
        data=snapshot(offline)
        self.assertFalse(data['alerts']['available'])
        self.assertIsNone(data['alerts']['total'])
        self.assertEqual(data['ledger']['rows'],[])

    def test_stream_failure_is_independent(self):
        def query(path,body):
            if path.startswith('/wazuh'):raise OSError()
            self.assertEqual(body['size'],100)
            return {'hits':{'total':{'value':2},'hits':[]},'aggregations':{'nodes':{'buckets':[]}}}
        data=snapshot(query)
        self.assertFalse(data['alerts']['available'])
        self.assertTrue(data['ledger']['available'])
        self.assertEqual(data['ledger']['total'],2)

    def test_time_window_filters_alerts_only(self):
        calls=[]
        def query(path,body):calls.append((path,body));raise OSError()
        snapshot(query,'24h')
        self.assertEqual(calls[0][1]['query'],{'range':{'timestamp':{'gte':'now-24h'}}})
        self.assertNotIn('query',calls[1][1])

    def test_invalid_window_rejected_without_query(self):
        with self.assertRaises(ValueError):snapshot(lambda *_:self.fail('Unexpected query'),'invalid')

    def test_large_integer_projection_is_exact(self):
        raw={'clock':9223372036854775807,'seq':97,'ok':True}
        self.assertEqual(browser_safe(raw),{'clock':'9223372036854775807','seq':97,'ok':True})
        self.assertIsInstance(raw['clock'],int)
