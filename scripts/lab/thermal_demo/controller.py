"""Research-inspired fan curve; produces proposals, never applies settings."""
from dataclasses import dataclass
from .model import bounded

# Demonstration thresholds in Fahrenheit, not vendor presets.
CURVE = ((80, 10), (90, 10), (110, 30), (130, 50), (145, 70), (155, 85), (160, 90), (175, 100))


def fan_curve(temperature_f):
    bounded(temperature_f, -100, 500, 'temperature_f')
    if temperature_f <= CURVE[0][0]:
        return float(CURVE[0][1])
    for (t0, f0), (t1, f1) in zip(CURVE, CURVE[1:]):
        if temperature_f <= t1:
            return f0 + (f1 - f0) * (temperature_f - t0) / (t1 - t0)
    return 100.0


@dataclass(frozen=True)
class FanProposal:
    previous_pct: float
    target_pct: float
    reason: str


class FanAgent:
    """Poll continuously; ordinary proposals at most once per 2 simulated seconds.

    Caller must avoid competing pending requests and revalidate before applying.
    Temperature unavailable/critical produces a full-cooling proposal, not a bypass.
    Real hardware retains its own firmware thermal protection.
    """
    def __init__(self):
        self.last_proposal_at = float('-inf')
        self.last_observed_at = float('-inf')

    def propose(self, now, temperature_f, applied_target_pct):
        bounded(now, 0, 1e12, 'now')
        bounded(applied_target_pct, 0, 100, 'applied target')
        if now < self.last_observed_at:
            raise ValueError('time must be monotonic')
        self.last_observed_at = now
        if temperature_f is None:
            desired, reason = 100.0, 'TELEMETRY_UNAVAILABLE'
        else:
            desired = fan_curve(temperature_f)
            reason = 'CRITICAL_TEMPERATURE' if temperature_f >= 175 else 'TEMPERATURE_CURVE'
        if reason != 'TEMPERATURE_CURVE':
            target = desired
        elif now - self.last_proposal_at < 2:
            return None
        elif desired >= applied_target_pct + 2:
            target = min(desired, applied_target_pct + 10)
        elif fan_curve(temperature_f + 5) <= applied_target_pct - 2:
            # Five-degree downshift hysteresis and slower ramp-down.
            target = max(desired, applied_target_pct - 5)
        else:
            return None
        if abs(target - applied_target_pct) < 0.01 or now - self.last_proposal_at < 2:
            return None
        self.last_proposal_at = now
        return FanProposal(applied_target_pct, target, reason)
