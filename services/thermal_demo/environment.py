"""Thread-safe simulated plant. Authorization and execution belong to ALICE."""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import math
import threading
import time
import uuid

from lab.thermal_demo.model import ThermalModel


class DemoError(ValueError):
    pass


class GatewayUnavailable(RuntimeError):
    pass


def number(value, low, high, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise DemoError(f'{name} must be a finite number in [{low}, {high}]')
    return float(value)


class Environment:
    def __init__(self, gateway=None, *, clock=time.monotonic, capacity_wh=100, energy_time_scale=1):
        self.gateway, self.clock = gateway, clock
        self.capacity = number(capacity_wh, .001, 100000, 'capacity_wh')
        self.energy_scale = number(energy_time_scale, .001, 10000, 'energy_time_scale')
        self.lock = threading.RLock()
        self.model = None
        self.run_id = None
        self.status = 'UNCONFIGURED'
        self.revision = 0  # authorization revision, separate from observations
        self.observation_sequence = 0
        self.elapsed = 0.0
        self.last_time = clock()
        self.requests = {}
        self.pending = None
        self.events = deque(maxlen=256)
        self.history = deque(maxlen=600)
        self.event_sequence = 0

    def _event(self, kind, **detail):
        self.event_sequence += 1
        self.events.append({'sequence': self.event_sequence, 'type': kind,
                            'sim_seconds': self.elapsed, **detail})

    def configure(self, body):
        if type(body) is not dict or set(body) != {'temperature_f', 'fan_pct', 'battery_pct'}:
            raise DemoError('Exactly temperature_f, fan_pct, battery_pct required; power is derived')
        t = number(body['temperature_f'], 32, 250, 'temperature_f')
        f = number(body['fan_pct'], 0, 100, 'fan_pct')
        b = number(body['battery_pct'], 0, 100, 'battery_pct')
        with self.lock:
            if self.status in ('RUNNING', 'PAUSED') or self.pending:
                raise DemoError('Stop the current run before configuring a new run')
            self.model = ThermalModel(temperature_f=t, fan_target_pct=f, fan_actual_pct=f,
                                      battery_capacity_wh=self.capacity,
                                      battery_remaining_wh=b * self.capacity / 100,
                                      energy_time_scale=self.energy_scale)
            self.run_id = uuid.uuid4().hex
            self.status = 'READY'
            self.revision = self.observation_sequence = 0
            self.elapsed = 0.0
            self.requests, self.pending = {}, None
            self.events.clear()
            self.history.clear()
            self.event_sequence = 0
            self.last_time = self.clock()
            self._event('CONFIGURED', initial=deepcopy(body))
            return self.snapshot()

    def control(self, operation):
        with self.lock:
            self._advance()
            if operation == 'start' and self.status == 'READY':
                self.status = 'RUNNING'
            elif operation == 'resume' and self.status == 'PAUSED':
                self.status = 'RUNNING'
            elif operation == 'pause' and self.status == 'RUNNING':
                self.status = 'PAUSED'
            elif operation == 'stop' and self.status in ('READY', 'RUNNING', 'PAUSED', 'EXHAUSTED'):
                self.status = 'STOPPED'
                if self.pending:
                    self.requests[self.pending]['application'] = 'INVALIDATED'
                    self.pending = None
            else:
                raise DemoError('Invalid lifecycle transition')
            self.last_time = self.clock()
            self._event(operation.upper())
            return self.snapshot()

    def _advance(self):
        now = self.clock()
        if self.status == 'RUNNING':
            dt = now - self.last_time
            if dt < 0 or dt > 10:
                self.status = 'PAUSED'
                self._event('CLOCK_GAP_PAUSED', gap_seconds=dt)
            elif dt > 0:
                # Account for completed substeps even when the reserve is exhausted.
                advanced = self.model.sim_seconds
                try:
                    self.model.step(dt)
                except RuntimeError:
                    self.status = 'EXHAUSTED'
                self.elapsed += self.model.sim_seconds - advanced
                self.observation_sequence += 1
                self.history.append({'sequence': self.observation_sequence,
                                     'elapsed_seconds': self.elapsed, **self._values()})
                if self.status == 'EXHAUSTED':
                    self._event('ENERGY_EXHAUSTED')
                    if self.pending:
                        self.requests[self.pending]['application'] = 'INVALIDATED'
                        self.pending = None
        self.last_time = now

    def _values(self):
        m = self.model
        return None if m is None else {
            'temperature_f': m.temperature_f, 'fan_target_pct': m.fan_target_pct,
            'fan_actual_pct': m.fan_actual_pct, 'power_w': m.power_w,
            'battery_pct': m.battery_pct, 'battery_remaining_wh': m.battery_remaining_wh,
            'battery_draw_w': m.battery_draw_w, 'supply_w': m.supply_w,
            'camera_status': 'NORMAL', 'camera_simulated': True}

    def snapshot(self):
        with self.lock:
            self._advance()
            return deepcopy({'schema_version': 'thermal-demo-v1', 'simulation': True,
                'run_id': self.run_id, 'status': self.status, 'revision': self.revision,
                'observation_sequence': self.observation_sequence, 'elapsed_seconds': self.elapsed,
                'metadata': {'battery_capacity_wh': self.capacity, 'energy_time_scale': self.energy_scale,
                             'ambient_f': 72, 'model': 'accelerated-demo-not-calibrated'},
                'governance_connected': self.gateway is not None, 'values': self._values(),
                'requests': list(self.requests.values()), 'events': list(self.events),
                'history': list(self.history)})

    def current(self, action):
        self._advance()
        return (self.status == 'RUNNING' and action['run_id'] == self.run_id
                and action['expected_revision'] == self.revision
                and self.pending == action['request_id']
                and self.requests[self.pending]['action'] == action)

    def apply_authorized(self, action):
        """Called only by the trusted executor after durable execution admission."""
        with self.lock:
            if not self.current(action):
                raise DemoError('Execution scope is stale')
            self.model.apply_fan_target(action['parameters']['fan_pct'])
            self.revision += 1
            self.requests[action['request_id']]['application'] = 'APPLIED'
            self.requests[action['request_id']]['applied_revision'] = self.revision

    def request_fan(self, body, agent_id):
        if type(body) is not dict or set(body) != {'request_id', 'run_id', 'expected_revision', 'fan_pct'}:
            raise DemoError('Expected request_id, run_id, expected_revision, fan_pct')
        rid = body['request_id']
        if (type(rid) is not str or not 1 <= len(rid) <= 64
                or not rid.isascii() or not all(c.isalnum() or c in '-_' for c in rid)):
            raise DemoError('Invalid request_id')
        fan = number(body['fan_pct'], 0, 100, 'fan_pct')
        if abs(fan * 100 - round(fan * 100)) > 1e-9:
            raise DemoError('Fan requests support hundredths of a percent')
        if type(body['expected_revision']) is not int:
            raise DemoError('expected_revision must be an integer')
        with self.lock:
            self._advance()
            action = {'request_id': rid, 'run_id': body['run_id'],
                      'expected_revision': body['expected_revision'], 'agent_id': agent_id,
                      'action': 'set_demo_fan_pct', 'target': 'DEMO-SERVER-01',
                      'parameters': {'fan_pct': fan}}
            if rid in self.requests:
                if self.requests[rid]['action'] != action:
                    raise DemoError('Request ID conflict')
                return deepcopy(self.requests[rid])
            if self.status != 'RUNNING' or body['run_id'] != self.run_id or body['expected_revision'] != self.revision:
                raise DemoError('Run is not current and running')
            if self.pending:
                raise DemoError('Resolve the pending request first')
            if self.gateway is None:
                raise GatewayUnavailable('ALICE fan adapter is not configured; no action executed')
            if len(self.requests) >= 256:
                raise DemoError('Request limit reached; stop and configure a new run')
            record = {'action': action, 'decision': 'UNKNOWN', 'application': 'PENDING'}
            self.requests[rid], self.pending = record, rid
            self._event('REQUESTED', request_id=rid)
            try:
                result = self.gateway.submit(deepcopy(action))
            except Exception:
                record['application'] = 'RECONCILIATION_REQUIRED'
            else:
                self._resolve(rid, result)
            return deepcopy(record)

    def reconcile(self):
        with self.lock:
            self._advance()
            if not self.pending or self.gateway is None:
                return
            try:
                result = self.gateway.result(self.requests[self.pending]['action'])
            except Exception:
                return
            self._resolve(self.pending, result)

    def _resolve(self, rid, result):
        record = self.requests[rid]
        if type(result) is not dict or result.get('action') != record['action']:
            record['application'] = 'RECONCILIATION_REQUIRED'
            return
        decision = result.get('decision')
        if decision not in ('ALLOW', 'DENY', 'CHALLENGE'):
            record['application'] = 'RECONCILIATION_REQUIRED'
            return
        record.update(decision=decision, review_state=result.get('review_state'),
                      execution=result.get('execution'), audit_request_id=result.get('audit_request_id'))
        if result.get('execution') == 'COMPLETED' and record.get('applied_revision') == record['action']['expected_revision'] + 1:
            record['application'] = 'APPLIED'
            self.pending = None
        elif decision == 'DENY' or result.get('review_state') == 'REJECTED':
            record['application'], self.pending = 'NOT_APPLIED', None
        elif result.get('execution') == 'FAILED':
            record['application'], self.pending = 'INVALIDATED', None
        elif decision == 'ALLOW' or result.get('review_state') == 'APPROVED':
            record['application'] = 'RECONCILIATION_REQUIRED'
        if self.pending is None:
            self._event('RESOLVED', request_id=rid, decision=decision, application=record['application'])
