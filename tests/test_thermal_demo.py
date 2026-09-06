import unittest
from lab.thermal_demo.model import ThermalModel
from lab.thermal_demo.controller import FanAgent, fan_curve


class ThermalDemoTests(unittest.TestCase):
    def test_spectrum(self):
        for temperature in range(72, 201, 4):
            rates = [ThermalModel(temperature_f=temperature, fan_actual_pct=f).temperature_rate() for f in range(101)]
            self.assertTrue(all(a >= b for a, b in zip(rates, rates[1:])))
        self.assertGreater(ThermalModel(temperature_f=160, fan_actual_pct=80).temperature_rate(), 0)
        self.assertLess(abs(ThermalModel(temperature_f=160, fan_actual_pct=85).temperature_rate()), .01)
        self.assertLess(ThermalModel(temperature_f=160, fan_actual_pct=90).temperature_rate(), 0)

    def test_equilibrium_and_lag(self):
        model = ThermalModel(temperature_f=160, fan_actual_pct=90, fan_target_pct=90)
        model.step(1000)
        expected = 72 + 1.97 / (.004 + .03 * .9 ** 3)
        self.assertAlmostEqual(model.temperature_f, expected, places=5)
        model.apply_fan_target(100)
        model.step(.2)
        self.assertTrue(90 < model.fan_actual_pct < 100)

    def test_proposals_do_not_execute(self):
        model = ThermalModel(temperature_f=160)
        agent = FanAgent()
        for now in (0, 2, 4):
            self.assertEqual(agent.propose(now, 160, model.fan_target_pct).target_pct, 20)
        self.assertEqual(model.fan_target_pct, 10)

    def test_ramp_and_hysteresis(self):
        agent = FanAgent()
        self.assertEqual(agent.propose(0, 160, 60).target_pct, 70)
        self.assertIsNone(agent.propose(1, 160, 70))
        self.assertEqual(agent.propose(2, 160, 70).target_pct, 80)
        self.assertIsNone(agent.propose(4, 153, 85))
        self.assertEqual(agent.propose(6, 130, 85).target_pct, 80)

    def test_limits_and_unknown(self):
        self.assertEqual(fan_curve(80), 10)
        self.assertEqual(fan_curve(200), 100)
        self.assertEqual(FanAgent().propose(0, None, 10).target_pct, 100)
        for bad in (-1, 101, float('nan')):
            with self.assertRaises(ValueError):
                ThermalModel().apply_fan_target(bad)
        with self.assertRaises(ValueError):
            ThermalModel().step(-1)

    def test_energy_balance(self):
        model = ThermalModel(fan_actual_pct=90, fan_target_pct=90)
        model.step(60)
        self.assertAlmostEqual(model.battery_remaining_wh, 100 - 22.9 / 60, places=6)
        low = ThermalModel(fan_actual_pct=70, fan_target_pct=70)
        low.step(60)
        self.assertEqual(low.battery_remaining_wh, 100)

    def test_energy_acceleration_and_exhaustion(self):
        model = ThermalModel(fan_actual_pct=100, fan_target_pct=100, energy_time_scale=60)
        model.step(1)
        self.assertAlmostEqual(model.battery_remaining_wh, 100 - 50 / 60, places=6)
        empty = ThermalModel(fan_actual_pct=100, fan_target_pct=100, battery_remaining_wh=0)
        with self.assertRaises(RuntimeError):
            empty.step(1)
        self.assertEqual(empty.battery_remaining_wh, 0)
        self.assertEqual(empty.power_shortfall_w, 50)

    def test_power_increases(self):
        powers = [ThermalModel(fan_actual_pct=f).power_w for f in range(101)]
        self.assertTrue(all(a < b for a, b in zip(powers, powers[1:])))


if __name__ == '__main__':
    unittest.main()
