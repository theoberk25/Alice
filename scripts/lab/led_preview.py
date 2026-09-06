"""Print LED patterns for supplied values. Never connects to hardware."""
import argparse
import json
from dcamr.display.led_patterns import display_document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temperature-f', type=float, required=True)
    parser.add_argument('--fan-pct', type=float, required=True)
    parser.add_argument('--power-w', type=float, required=True)
    parser.add_argument('--battery-pct', type=float, required=True)
    parser.add_argument('--stale', action='store_true')
    args = parser.parse_args()
    print(json.dumps(display_document({
        'temperature_f': args.temperature_f, 'fan_pct': args.fan_pct,
        'power_w': args.power_w, 'battery_pct': args.battery_pct,
    }, stale=args.stale), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
