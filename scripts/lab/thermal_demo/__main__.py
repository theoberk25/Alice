"""CSV runner. --auto-apply is a simulated actuator, NEVER an ALICE decision."""
import argparse
import csv
import random
import sys
from .model import ThermalModel, bounded
from .controller import FanAgent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--temperature', type=float, default=85)
    parser.add_argument('--fan', type=float, default=10)
    parser.add_argument('--heat', type=float, default=1.97)
    parser.add_argument('--supply-w', type=float, default=450)
    parser.add_argument('--battery-wh', type=float, default=100)
    parser.add_argument('--energy-time-scale', type=float, default=1, help='Explicit energy-only demo acceleration; 1 is unscaled')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--auto-apply', action='store_true')
    args = parser.parse_args()
    bounded(args.seconds, 0.2, 3600, 'seconds')
    bounded(args.heat, 0, 10, 'heat')
    model = ThermalModel(temperature_f=args.temperature, fan_target_pct=args.fan, fan_actual_pct=args.fan, supply_w=args.supply_w, battery_capacity_wh=args.battery_wh, battery_remaining_wh=args.battery_wh, energy_time_scale=args.energy_time_scale)
    agent = FanAgent()
    rng = random.Random(args.seed)
    writer = csv.writer(sys.stdout)
    writer.writerow(['sim_seconds', 'temperature_f', 'fan_target_pct', 'fan_actual_pct', 'power_w', 'battery_pct', 'battery_draw_w', 'energy_time_scale', 'proposed_pct', 'application'])
    for tick in range(int(args.seconds * 5) + 1):
        now = tick / 5
        proposal = agent.propose(now, model.temperature_f, model.fan_target_pct)
        if proposal and args.auto_apply:
            model.apply_fan_target(proposal.target_pct)
        writer.writerow([now, round(model.temperature_f, 3), round(model.fan_target_pct, 2), round(model.fan_actual_pct, 2), round(model.power_w, 2), round(model.battery_pct, 4), round(model.battery_draw_w, 2), model.energy_time_scale, round(proposal.target_pct, 2) if proposal else '', 'SIMULATED_APPLY' if proposal and args.auto_apply else 'PROPOSAL_ONLY' if proposal else ''])
        model.step(0.2, args.heat * (1 + rng.uniform(-0.01, 0.01)))


if __name__ == '__main__':
    main()
