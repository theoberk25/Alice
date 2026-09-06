"""Telemetry-only v3 pattern delivery through the runtime's sole serial owner."""
import time

from dcamr.display.led_patterns import map_patterns
from dcamr.enforcement.enforcement_gateway import ControllerError


class PatternRenderer:
    def __init__(self, controller, *, clock=time.monotonic):
        self.controller, self.clock = controller, clock
        self.configured = {}
        self.refreshed = {}
        self.status = {'state': 'UNAVAILABLE', 'measured_illumination': False}
        self.reconcile_required = False

    def update(self, snapshot, *, received_at):
        now = self.clock()
        values = snapshot.get('values')
        stale = (not values or not 0 <= now - received_at <= 1
                 or snapshot.get('status') in ('UNCONFIGURED', 'STOPPED', 'EXHAUSTED'))
        telemetry = dict.fromkeys(('temperature_f', 'fan_pct', 'power_w', 'battery_pct'))
        if values:
            telemetry.update(temperature_f=values['temperature_f'], fan_pct=values['fan_actual_pct'],
                             power_w=values['power_w'], battery_pct=values['battery_pct'])
        patterns = map_patterns(telemetry, stale=stale)
        exhausted = snapshot.get('status') == 'EXHAUSTED'
        # MCU updates yellow/blue/red pairs atomically; whites remain independent.
        desired = {i + 1: (('off', 0) if exhausted else (p.mode.lower(), round(p.hz * 1000)))
                   for i, p in enumerate(patterns) if i in (0, 1, 2, 3, 7)}
        try:
            if self.reconcile_required:
                # A lost ACK is not retried. GET reconciles, then a later call
                # delivers its newly sampled telemetry, never the failed frame.
                self.controller.pattern(1, operation='get')
                self.configured.clear()
                self.reconcile_required = False
                self.status = {'state': 'RECONCILED', 'measured_illumination': False}
                return
            for channel, setting in desired.items():
                boot = self.controller.boot_id
                if self.configured.get(channel) != setting:
                    reply = self.controller.pattern(channel, mode=setting[0], mhz=setting[1])
                elif now - self.refreshed.get(channel, 0) >= .5:
                    reply = self.controller.pattern(channel, operation='keep')
                else:
                    continue
                if boot is not None and self.controller.boot_id != boot:
                    self.configured.clear()
                    self.status = {'state': 'RESTARTED', 'measured_illumination': False}
                    return
                if (reply['mode'], reply['mhz']) != setting or reply['stale']:
                    self.configured.clear()
                    self.status = {'state': 'STALE_OR_OVERRIDDEN', 'measured_illumination': False}
                    return
                self.configured[channel] = setting
                self.refreshed[channel] = now
            self.status = {'state': 'EXHAUSTED_OFF' if exhausted else
                           'UNAVAILABLE' if stale else 'CONFIGURED',
                           'boot_id': self.controller.boot_id, 'measured_illumination': False}
        except ControllerError:
            self.reconcile_required = True
            self.status = {'state': 'RECONCILIATION_REQUIRED', 'measured_illumination': False}
