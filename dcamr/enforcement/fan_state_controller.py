"""Atomic fan-state actuator for the demo machine-state file."""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile

from dcamr.enforcement.enforcement_gateway import ControllerError, ControllerReceipt, ObservedState


class FanStateController:
    def __init__(self, path):
        self.path = Path(path)
        self.read_metrics()

    def read_metrics(self):
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError
            value = json.loads(self.path.read_text())
            if set(value) != {'fan_speed', 'server_temperature', 'power_consumption'}:
                raise ValueError
            for key, item in value.items():
                if type(item) not in (int, float) or not math.isfinite(item):
                    raise ValueError
            if not 0 <= value['fan_speed'] <= 100:
                raise ValueError
            return value
        except (OSError, ValueError, TypeError):
            raise ControllerError('machine state unavailable') from None

    def execute(self, parameters):
        value = parameters.get('value')
        if type(value) is not int or not 0 <= value <= 100:
            return ControllerReceipt(False, None, {})
        current = self.read_metrics()
        current['fan_speed'] = value
        try:
            fd, name = tempfile.mkstemp(prefix='.alice-fan-', dir=self.path.parent)
            with os.fdopen(fd, 'w') as output:
                json.dump(current, output, sort_keys=True, separators=(',', ':'))
                output.write('\n'); output.flush(); os.fsync(output.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
        except OSError:
            try: Path(name).unlink(missing_ok=True)
            except UnboundLocalError: pass
            raise ControllerError('machine state write failed') from None
        return ControllerReceipt(True, None, {'fan_speed': value})

    def observe(self):
        try:
            return ObservedState(True, str(self.read_metrics()['fan_speed']))
        except ControllerError:
            return ObservedState(False, None)
