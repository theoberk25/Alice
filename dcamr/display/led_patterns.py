"""Pure thermal-demo telemetry -> eight LED patterns. No I/O or timing loop."""
from dataclasses import dataclass, asdict
import math
from typing import Mapping

# Matches services/light_mcp/machines.yaml; does not change signed targets/roles.
CHANNELS = (
    ('ESP-LIGHT-01', 'yellow', 'power_w', 1),
    ('ESP-LIGHT-02', 'blue', 'fan_pct', 1),
    ('ESP-LIGHT-03', 'red', 'temperature_f', 1),
    ('ESP-LIGHT-04', 'white', 'battery_pct', 1),
    ('ESP-LIGHT-05', 'yellow', 'power_w', 2),
    ('ESP-LIGHT-06', 'blue', 'fan_pct', 2),
    ('ESP-LIGHT-07', 'red', 'temperature_f', 2),
    ('ESP-LIGHT-08', 'white', 'battery_pct', 2),
)
FIELDS = frozenset(('temperature_f', 'fan_pct', 'power_w', 'battery_pct'))


@dataclass(frozen=True)
class Pattern:
    target: str
    color: str
    variable: str
    segment: int
    mode: str  # OFF, SOLID, BLINK, UNAVAILABLE
    hz: float = 0.0  # complete on/off cycles per second
    duty_cycle: float = 0.0


def _rate(value, low, high):
    fraction = min(1.0, max(0.0, (value - low) / (high - low)))
    return round(0.5 + 4.5 * fraction, 6)


def map_patterns(values: Mapping, *, stale=False):
    """Return immutable patterns in hardware channel order.

    Exact four-field input; null/nonfinite numeric values yield UNAVAILABLE only
    for that variable. Wrong types, missing/unknown fields are rejected. Finite
    values outside display endpoints clamp (this does not validate sensor safety).
    Caller determines freshness; stale=True marks all channels unavailable.
    """
    if not isinstance(values, Mapping) or set(values) != FIELDS:
        raise ValueError('Exactly temperature_f, fan_pct, power_w, battery_pct required')
    if type(stale) is not bool:
        raise ValueError('stale must be boolean')
    for name, value in values.items():
        if value is not None and type(value) not in (int, float):
            raise ValueError(f'{name} must be a number or null')
    result = []
    for target, color, variable, segment in CHANNELS:
        value = values[variable]
        mode, hz = 'BLINK', 0.0
        if stale or value is None or not math.isfinite(value):
            mode = 'UNAVAILABLE'
        elif variable == 'battery_pct':
            fill = min(50.0, max(0.0, value - (segment - 1) * 50))
            if fill == 0:
                mode = 'OFF'
            elif fill == 50:
                mode = 'SOLID'
            else:
                hz = _rate(50 - fill, 0, 50)
        elif variable == 'fan_pct' and value <= 0:
            mode = 'OFF'
        elif variable == 'fan_pct':
            hz = _rate(value, 0, 100)
        elif variable == 'temperature_f':
            hz = _rate(value, 80, 175)
        else:
            hz = _rate(value, 400, 500)
        duty = 0.5 if mode == 'BLINK' else 1.0 if mode == 'SOLID' else 0.0
        result.append(Pattern(target, color, variable, segment, mode, hz, duty))
    return tuple(result)


def display_document(values, *, stale=False):
    return {'schema_version': 'alice-led-display-v1', 'read_only': True,
            'patterns': [asdict(pattern) for pattern in map_patterns(values, stale=stale)]}
