import json
from pathlib import Path
import unittest
from dcamr.display.led_patterns import map_patterns, display_document


class LedPatternTests(unittest.TestCase):
    def patterns(self, **changes):
        return map_patterns(dict(temperature_f=80, fan_pct=0, power_w=400, battery_pct=60, **{}) | changes)

    def test_mapping_matches_hardware(self):
        config = (Path(__file__).resolve().parents[1] / 'services/light_mcp/machines.yaml').read_text()
        for p in self.patterns():
            self.assertIn(f'target: {p.target}, label: "{p.color.title()} {p.segment}"', config)

    def test_endpoints_and_pair_agreement(self):
        low = self.patterns()
        self.assertEqual(low[1].mode, 'OFF')
        self.assertEqual(low[0].hz, .5)
        self.assertEqual(low[2].hz, .5)
        high = self.patterns(temperature_f=175, fan_pct=100, power_w=500)
        for i in (0, 1, 2):
            self.assertEqual(high[i].hz, 5)
            self.assertEqual(high[i].hz, high[i+4].hz)
            self.assertEqual(high[i].duty_cycle, .5)

    def test_white_boundaries(self):
        for pct, expected in ((0, ('OFF','OFF')), (50, ('SOLID','OFF')), (100, ('SOLID','SOLID'))):
            p = self.patterns(battery_pct=pct)
            self.assertEqual((p[3].mode, p[7].mode), expected)
        p = self.patterns(battery_pct=60)
        self.assertEqual(p[3].mode, 'SOLID')
        self.assertEqual(p[7].hz, 4.1)
        self.assertEqual(self.patterns(battery_pct=10)[3].hz, 4.1)

    def test_battery_active_segment_speeds_up_when_draining(self):
        for upper in (0, 50):
            index = 3 if upper == 0 else 7
            rates = [self.patterns(battery_pct=upper+i)[index].hz for i in range(49,0,-1)]
            self.assertTrue(all(a < b for a,b in zip(rates,rates[1:])))

    def test_clamping(self):
        self.assertEqual(self.patterns(temperature_f=500)[2].hz, 5)
        self.assertEqual(self.patterns(power_w=-1)[0].hz, .5)
        self.assertEqual(self.patterns(battery_pct=101)[7].mode, 'SOLID')
        self.assertEqual(self.patterns(battery_pct=-1)[3].mode, 'OFF')

    def test_unavailable_and_stale(self):
        for bad in (None, float('nan'), float('inf')):
            p = self.patterns(temperature_f=bad)
            self.assertEqual(p[2].mode, 'UNAVAILABLE')
            self.assertEqual(p[6].mode, 'UNAVAILABLE')
            self.assertEqual(p[0].mode, 'BLINK')
        values = dict(temperature_f=80, fan_pct=10, power_w=401, battery_pct=50)
        self.assertTrue(all(p.mode == 'UNAVAILABLE' for p in map_patterns(values, stale=True)))
        json.dumps(display_document(values), allow_nan=False)

    def test_invalid_contract(self):
        with self.assertRaises(ValueError):
            map_patterns({})
        with self.assertRaises(ValueError):
            self.patterns(fan_pct=True)
        with self.assertRaises(ValueError):
            self.patterns(power_w='450')
        with self.assertRaises(ValueError):
            self.patterns(extra=1)

    def test_independence_and_no_input_mutation(self):
        values = dict(temperature_f=80, fan_pct=10, power_w=410, battery_pct=50)
        before = values.copy()
        baseline = map_patterns(values)
        self.assertEqual(values, before)
        values['fan_pct'] = 90
        changed = map_patterns(values)
        for i in (0,2,3,4,6,7):
            self.assertEqual(baseline[i], changed[i])


if __name__ == '__main__':
    unittest.main()
