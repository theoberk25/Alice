"""Temperature/fan interaction. Coefficients are demo tuning, not hardware limits."""
from dataclasses import dataclass
import math


def bounded(value, low, high, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and in [{low}, {high}]")
    return value


@dataclass
class ThermalModel:
    temperature_f: float = 85.0
    ambient_f: float = 72.0
    fan_target_pct: float = 10.0
    fan_actual_pct: float = 10.0

    supply_w: float = 450.0
    battery_capacity_wh: float = 100.0
    battery_remaining_wh: float = 100.0
    energy_time_scale: float = 1.0
    sim_seconds: float = 0.0

    def __post_init__(self):
        bounded(self.supply_w, 0, 10000, 'supply_w')
        bounded(self.battery_capacity_wh, 0.001, 100000, 'battery_capacity_wh')
        bounded(self.battery_remaining_wh, 0, self.battery_capacity_wh, 'battery_remaining_wh')
        bounded(self.energy_time_scale, 0.001, 10000, 'energy_time_scale')
        bounded(self.temperature_f, -100, 500, 'temperature_f')
        bounded(self.ambient_f, -100, 500, 'ambient_f')
        bounded(self.fan_target_pct, 0, 100, 'fan_target_pct')
        bounded(self.fan_actual_pct, 0, 100, 'fan_actual_pct')

    def apply_fan_target(self, percent):
        """Execution boundary: call only after external authorization in integration."""
        self.fan_target_pct = bounded(percent, 0, 100, 'fan target')

    def temperature_rate(self, heat=1.97):
        """Degrees F / simulated second; heat is a temperature-rate contribution."""
        bounded(heat, 0, 10, 'heat')
        conductance = 0.004 + 0.030 * (self.fan_actual_pct / 100) ** 3
        return heat - conductance * (self.temperature_f - self.ambient_f)

    @property
    def power_w(self):
        """Illustrative fixed 400 W workload plus up to 100 W of fan power."""
        return 400 + 100 * (self.fan_actual_pct / 100) ** 3

    @property
    def battery_pct(self):
        return 100 * self.battery_remaining_wh / self.battery_capacity_wh

    @property
    def battery_draw_w(self):
        return max(0.0, self.power_w - self.supply_w)

    @property
    def power_shortfall_w(self):
        return self.battery_draw_w if self.battery_remaining_wh <= 0 else 0.0

    def step(self, dt, heat=1.97):
        bounded(dt, 0, 3600, 'dt')
        bounded(heat, 0, 10, 'heat')
        # Small bounded integration steps; exact thermal update per substep.
        steps = max(1, math.ceil(dt / 0.05))
        h = dt / steps
        for _ in range(steps):
            if self.power_shortfall_w > 0:
                raise RuntimeError("Energy reserve exhausted; powered-operation simulation stopped")
            self.fan_actual_pct += (self.fan_target_pct - self.fan_actual_pct) * (1 - math.exp(-h))
            drain_wh = self.battery_draw_w * h * self.energy_time_scale / 3600
            self.sim_seconds += h
            self.battery_remaining_wh = max(0.0, self.battery_remaining_wh - drain_wh)
            if self.power_shortfall_w > 0:
                raise RuntimeError("Energy reserve exhausted; powered-operation simulation stopped")
            k = 0.004 + 0.030 * (self.fan_actual_pct / 100) ** 3
            equilibrium = self.ambient_f + heat / k
            self.temperature_f = equilibrium + (self.temperature_f - equilibrium) * math.exp(-k * h)
        return self.temperature_f
