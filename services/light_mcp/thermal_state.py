"""The teammate's metrics names projected from one ALICE-governed plant.

No JSON state writes, signing keys, serial access or local fan state live here.
"""
from hashlib import sha256
import math
from urllib.error import HTTPError


class ThermalState:
    def __init__(self, client, agent_id):
        self.client = client
        self.agent_id = agent_id

    @staticmethod
    def metrics(snapshot):
        values = snapshot.get('values')
        return {
            'fan_speed': values['fan_actual_pct'] if values else None,
            'server_temperature': values['temperature_f'] if values else None,
            'power_consumption': values['power_w'] if values else None,
            'fan_target_speed': values['fan_target_pct'] if values else None,
            'battery_pct': values['battery_pct'] if values else None,
            'run_id': snapshot['run_id'], 'revision': snapshot['revision'],
            'status': snapshot['status'], 'simulation': True,
            'units': {'fan_speed': 'percent', 'server_temperature': 'degF', 'power_consumption': 'W'},
            'metadata': snapshot['metadata'],
            'requests': snapshot['requests'],
        }

    def read(self):
        return self.metrics(self.client.state())

    def _receipt(self, record, snapshot):
        metrics = self.metrics(snapshot)
        applied = (record.get('application') == 'APPLIED'
                   and record.get('execution') == 'COMPLETED'
                   and record['action']['run_id'] == snapshot['run_id'])
        return {'ok': applied, 'fan_speed': metrics['fan_speed'], 'metrics': metrics,
                'request_id': record['action']['request_id'],
                'run_id': record['action']['run_id'],
                'expected_revision': record['action']['expected_revision'],
                'requested_fan_speed': record['action']['parameters']['fan_pct'],
                'decision': record['decision'], 'application': record['application'],
                'review_state': record.get('review_state'), 'execution': record.get('execution'),
                'audit_request_id': record.get('audit_request_id'),
                **({} if applied else {'error': 'Fan request was not confirmed applied; inspect decision and application'})}

    def set_fan_speed(self, value, *, request_id=None, run_id=None, expected_revision=None):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError('fan_speed must be a finite number from 0 to 100')
        if abs(value * 100 - round(value * 100)) > 1e-9:
            raise ValueError('fan_speed supports hundredths of a percent')
        if (run_id is None) != (expected_revision is None):
            raise ValueError('Supply run_id and expected_revision together')
        if request_id is not None and run_id is None:
            raise ValueError('Retries require request_id, run_id and expected_revision together')
        snapshot = self.client.state()
        if run_id is not None and (snapshot['run_id'] != run_id or type(expected_revision) is not int):
            raise ValueError('Run is stale or revision is invalid')
        bound = snapshot if run_id is None else {'run_id': run_id, 'revision': expected_revision}
        # Default calls have a stable identity for this run/revision/value. For an
        # uncertain response, callers may supply the returned binding explicitly.
        rid = request_id or sha256(f"{self.agent_id}:{bound['run_id']}:{bound['revision']}:{value:.2f}".encode()).hexdigest()
        records = snapshot['requests']
        previous = next((r for r in records if r['action']['request_id'] == rid), None)
        if previous and previous['action']['parameters']['fan_pct'] == value:
            # Let the backend authenticate identity and detect any binding conflict.
            record = self.client.request_fan(bound, value, rid)
            return self._receipt(record, self.client.state())
        if request_id is None and snapshot['values'] and snapshot['values']['fan_target_pct'] == value:
            # Repeating an already-authorized target is a read-only no-op. Do not
            # create another execution just because the agent repeats itself.
            metrics = self.metrics(snapshot)
            return {'ok': True, 'changed': False, 'application': 'UNCHANGED',
                    'decision': None, 'fan_speed': metrics['fan_speed'], 'metrics': metrics}
        try:
            record = self.client.request_fan(bound, value, rid)
        except HTTPError:
            raise  # Known refusal is not an uncertain transmission.
        except (OSError, TimeoutError):
            return {'ok': False, 'decision': 'UNKNOWN', 'application': 'RECONCILIATION_REQUIRED',
                    'request_id': rid, 'run_id': bound['run_id'], 'expected_revision': bound['revision'],
                    'error': 'Outcome unknown. Read metrics; retry only with this exact request binding.'}
        return self._receipt(record, self.client.state())
