"""Plant and HTTP contract checks; real governance acceptance is in runtime tests."""
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest
from services.thermal_demo.environment import Environment, DemoError, GatewayUnavailable
from services.thermal_demo.server import make_server


def configured(clock=lambda: 0, **options):
    env = Environment(clock=clock, **options)
    env.configure({'temperature_f': 160, 'fan_pct': 60, 'battery_pct': 40})
    env.control('start')
    return env


@pytest.mark.parametrize('bad', [True, '60', float('nan'), float('inf'), -1, 101])
def test_input_validation(bad):
    with pytest.raises(DemoError):
        Environment().configure({'temperature_f': 140, 'fan_pct': bad, 'battery_pct': 60})


def test_derived_power_capacity_metadata_and_snapshot_isolation():
    env = configured(capacity_wh=200, energy_time_scale=60)
    state = env.snapshot()
    assert state['values']['power_w'] == pytest.approx(421.6)
    assert state['values']['battery_remaining_wh'] == 80
    assert state['metadata']['energy_time_scale'] == 60
    state['events'][0]['initial']['fan_pct'] = 99
    assert env.snapshot()['events'][0]['initial']['fan_pct'] == 60
    with pytest.raises(DemoError):
        Environment().configure({'temperature_f': 140, 'fan_pct': 60, 'battery_pct': 60, 'power_w': 400})


def test_pause_resume_gap_and_determinism():
    now = [0]
    env = configured(clock=lambda: now[0])
    now[0] = 2
    hot = env.snapshot()['values']['temperature_f']
    assert hot > 160
    env.control('pause')
    now[0] = 8
    assert env.snapshot()['values']['temperature_f'] == hot
    env.control('resume')
    now[0] = 9
    assert env.snapshot()['elapsed_seconds'] == pytest.approx(3)
    now[0] = 30
    assert env.snapshot()['status'] == 'PAUSED'
    assert env.snapshot()['events'][-1]['type'] == 'CLOCK_GAP_PAUSED'
    other = configured(clock=lambda: 0)
    other.model.step(3)
    assert env.model.temperature_f == pytest.approx(other.model.temperature_f)


def test_exhaustion_and_zero_reserve_under_supply():
    now = [0]
    env = Environment(clock=lambda: now[0])
    env.configure({'temperature_f': 160, 'fan_pct': 100, 'battery_pct': .0001})
    env.control('start')
    now[0] = 1
    state = env.snapshot()
    assert state['status'] == 'EXHAUSTED'
    assert state['values']['battery_pct'] == 0
    assert 0 < state['elapsed_seconds'] < 1
    env.control('stop')
    old = env.run_id
    env.configure({'temperature_f': 160, 'fan_pct': 0, 'battery_pct': 0})
    assert old != env.run_id
    env.control('start')
    now[0] = 2
    assert env.snapshot()['status'] == 'RUNNING'


def test_no_gateway_cannot_execute():
    env = configured()
    with pytest.raises(GatewayUnavailable):
        env.request_fan({'request_id': 'r', 'run_id': env.run_id, 'expected_revision': 0, 'fan_pct': 70}, 'agent')
    assert env.model.fan_target_pct == 60 and not env.requests


def test_http_roles_resume_and_strict_json():
    env = configured()
    server = make_server(env, 'operator-secret', 'agent-secret')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(path, body=None, token='operator-secret'):
        data = body if isinstance(body, bytes) else json.dumps(body).encode() if body is not None else None
        req = Request(f'http://127.0.0.1:{server.server_port}/demo/{path}', data=data,
                      headers={'Authorization': 'Bearer ' + token})
        with urlopen(req, timeout=3) as response:
            return json.load(response)
    try:
        assert call('state', token='agent-secret')['simulation']
        with pytest.raises(HTTPError) as err:
            call('stop', {}, token='agent-secret')
        assert err.value.code == 403
        assert call('pause', {})['status'] == 'PAUSED'
        assert call('resume', {})['status'] == 'RUNNING'
        with pytest.raises(HTTPError):
            call('configure', b'{"fan_pct":60,"fan_pct":70}')
        with pytest.raises(HTTPError):
            call('approve', {})
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
