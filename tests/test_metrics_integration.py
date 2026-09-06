"""Real Streamable-HTTP MCP -> authenticated demo -> signed ALICE -> plant."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip('mcp')
import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from services.light_mcp.server import create_server, build_server
from services.light_mcp.thermal_state import ThermalState
from services.light_mcp.poller import _payload, _snapshot_path, poll
from services.thermal_demo.client import DemoClient
from services.thermal_demo.server import make_server
# Pytest must discover both the shared fixture and its model dependency here.
from tests.test_thermal_runtime import integrated, thermal_model_file


@pytest.fixture
def metrics(integrated):
    env, rt, now, _, sign, _ = integrated
    tokens = {'cooling-agent-01': 'cooling-token', 'power-agent-01': 'power-token',
              'observer-agent-01': 'observer-token'}
    api = make_server(env, 'operator-token', agents=tokens, runtime=rt)
    api_thread = threading.Thread(target=api.serve_forever, daemon=True)
    api_thread.start()
    backends = {agent: ThermalState(DemoClient(f'http://127.0.0.1:{api.server_port}', token), agent)
                for agent, token in tokens.items()}
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    mcp = create_server(backends, port=port, agent_tokens=tokens)
    server = uvicorn.Server(uvicorn.Config(mcp.streamable_http_app(), log_level='error'))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.01)
    assert server.started
    yield env, rt, now, sign, backends, f'http://127.0.0.1:{port}/mcp'
    server.should_exit = True
    thread.join(timeout=5)
    sock.close()
    api.shutdown()
    api.server_close()
    api_thread.join()


async def call(url, token, tool, args):
    async with streamablehttp_client(url, headers={'Authorization': 'Bearer '+token}) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {'get_metrics', 'set_fan_speed'}
            return await session.call_tool(tool, args)


def payload(result):
    assert not result.isError, result
    return result.structuredContent or json.loads(result.content[0].text)


def test_mcp_allow_reads_actual_fan_and_retains_percentage_interface(metrics):
    env, rt, now, _, _, url = metrics
    original = _payload(asyncio.run(call(url, 'cooling-token', 'get_metrics', {})))
    assert original['fan_speed'] == 60 and original['server_temperature'] == 100
    assert original['power_consumption'] == pytest.approx(421.6)
    assert original['battery_pct'] == 60
    assert original['units']['battery_pct'] == 'percent'
    result = asyncio.run(call(url, 'cooling-token', 'set_fan_speed', {'value': 70}))
    assert not result.isError, result
    value = payload(result)
    assert value['ok'] and value['decision'] == 'ALLOW', result
    assert value['fan_speed'] == 60 and value['metrics']['fan_target_speed'] == 70
    again = payload(asyncio.run(call(url, 'cooling-token', 'set_fan_speed', {'value': 70})))
    assert again['application'] == 'UNCHANGED'
    assert sum(e['event_type']=='EXECUTION_ATTEMPT' for e in rt.iter_events()) == 1
    now[0] = 2
    changed = _payload(asyncio.run(call(url, 'cooling-token', 'get_metrics', {})))
    assert 60 < changed['fan_speed'] < 70 and changed['power_consumption'] > 421.6


def test_identity_hold_deny_and_real_review(metrics):
    env, rt, _, sign, _, url = metrics
    denied = payload(asyncio.run(call(url, 'observer-token', 'set_fan_speed', {'value': 70})))
    assert denied['decision'] == 'DENY' and not denied['ok']
    held = payload(asyncio.run(call(url, 'power-token', 'set_fan_speed', {'value': 0})))
    assert held['decision'] == 'CHALLENGE' and not held['ok']
    assert env.model.fan_target_pct == 60
    record = next(r for r in env.requests.values() if r['action']['request_id'] == held['request_id'])
    assert record['action']['agent_id'] == 'power-agent-01'
    code, receipt = rt.review(envelope=sign(record, action='REJECT'))
    assert code == 200 and receipt['review_state'] == 'REJECTED'
    env.reconcile()
    snapshot = _payload(asyncio.run(call(url, 'power-token', 'get_metrics', {})))
    assert snapshot['fan_target_speed'] == 60
    assert snapshot['requests'][-1]['review_state'] == 'REJECTED'
    response = httpx.post(url, json={})
    assert response.status_code == 401


def test_invalid_values_never_reach_alice(metrics):
    env, _, _, _, _, url = metrics
    for value in (True, '90', -1, 101):
        response = asyncio.run(call(url, 'cooling-token', 'set_fan_speed', {'value': value}))
        assert response.isError
    assert not env.requests


def test_lost_ack_exact_retry_and_reset_guard(metrics):
    env, rt, _, _, backends, _ = metrics
    backend = backends['cooling-agent-01']
    real = backend.client.request_fan
    def lost(*args):
        real(*args)
        raise OSError('lost response')
    with patch.object(backend.client, 'request_fan', side_effect=lost):
        result = backend.set_fan_speed(70)
    assert result['application'] == 'RECONCILIATION_REQUIRED'
    binding = {k: result[k] for k in ('request_id','run_id','expected_revision')}
    assert backend.set_fan_speed(70, **binding)['ok']
    assert env.revision == 1
    assert sum(e['event_type']=='EXECUTION_ATTEMPT' for e in rt.iter_events()) == 1
    env.control('stop')
    env.configure({'temperature_f': 140, 'fan_pct': 60, 'battery_pct': 60})
    env.control('start')
    with pytest.raises(ValueError, match='stale'):
        backend.set_fan_speed(70, **binding)
    assert env.model.fan_target_pct == 60


def test_poller_uses_existing_tools_with_auth(metrics, tmp_path, monkeypatch):
    *_, url = metrics
    monkeypatch.setenv('LIGHT_MCP_TOKEN', 'cooling-token')
    path = tmp_path/'sample.json'
    assert asyncio.run(poll('cloud', url, .1, str(path), True)) == 0
    value = json.loads(path.read_text())
    assert value['available'] and value['metrics']['fan_speed'] == 60
    assert value['max_age_seconds'] == 1


def test_bad_poller_payloads_and_labels_are_not_healthy():
    for response in (SimpleNamespace(isError=True),
                     SimpleNamespace(isError=False, structuredContent={'error':'offline'}),
                     SimpleNamespace(isError=False, structuredContent={'fan_speed':True,'server_temperature':1,'power_consumption':1})):
        with pytest.raises(ValueError):
            _payload(response)
    with pytest.raises(ValueError):
        _snapshot_path('../outside', None)


def test_default_does_not_create_a_second_state_file(tmp_path, monkeypatch):
    monkeypatch.setenv('MACHINE_STATE_FILE', str(tmp_path/'must-not-exist.json'))
    monkeypatch.delenv('MACHINE_BACKEND', raising=False)
    monkeypatch.setenv('THERMAL_AGENT_TOKENS', json.dumps({'cooling-agent-01':'token'}))
    build_server()
    assert not (tmp_path/'must-not-exist.json').exists()


def test_agents_do_not_share_request_ids_at_same_revision(metrics):
    env, rt, _, _, backends, _ = metrics
    denied = backends['observer-agent-01'].set_fan_speed(70)
    allowed = backends['cooling-agent-01'].set_fan_speed(70)
    assert denied['decision'] == 'DENY'
    assert allowed['decision'] == 'ALLOW' and allowed['ok']
    assert denied['request_id'] != allowed['request_id']
    assert env.model.fan_target_pct == 70
