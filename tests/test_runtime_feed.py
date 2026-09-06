"""Authenticated read-only bridge acceptance using the real first-light runtime."""
import copy
import json
import threading
from urllib import request, error

import pytest

from dcamr.main import FirstLightRuntime, make_server as runtime_server
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope, send
from services.runtime_feed import make_server, validate_page


@pytest.fixture
def connected(tmp_path):
    release = build_release.build(tmp_path / 'bundle')
    trust = bytes.fromhex((tmp_path / 'bundle/trust/manifest_public.hex').read_text().strip())
    seed = bytes.fromhex((tmp_path / 'bundle/client/term-agent-01-k1.seed').read_text().strip())
    esp_server, esp = mock_esp.make_server()
    runtime = FirstLightRuntime(release_dir=release, trusted_manifest_key=trust,
                               data_dir=tmp_path / 'data',
                               esp_base_url=f'http://127.0.0.1:{esp_server.server_port}')
    pi = runtime_server(runtime, '127.0.0.1', 0)
    upstream = f'http://127.0.0.1:{pi.server_port}'
    bridge = make_server(upstream=upstream, token='t' * 32, source='local-runtime',
                         controller='mock', port=0)
    servers = [esp_server, pi, bridge]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    def read(after=0, token='t' * 32):
        req = request.Request(f'http://127.0.0.1:{bridge.server_port}/events?after={after}',
                              headers={'Authorization': f'Bearer {token}'})
        with request.urlopen(req, timeout=5) as response:
            return json.load(response)
    yield runtime, esp, upstream, seed, read, bridge
    for server in reversed(servers):
        server.shutdown()
        server.server_close()
    runtime.close()


def test_authenticated_initial_incremental_and_idempotent_runtime(connected):
    runtime, esp, upstream, seed, read, bridge = connected
    assert read()['events'] == []
    with pytest.raises(error.HTTPError) as exc:
        read(token='wrong')
    assert exc.value.code == 401
    envelope = build_envelope(seed, state='on', request_id='live-test')
    assert send(upstream, envelope)[0] == 200
    page = read()
    assert len(page['events']) == 7
    assert page['source'] == {'connection': 'local-runtime', 'controller': 'mock'}
    assert {e['correlation']['request_id'] for e in page['events']} == {'live-test'}
    assert page['events'][-1]['detail']['value'] == '1'
    assert page['events'][1]['detail']['contextual']['context'][1] == {'key': 'fixture_mode', 'value': 'true'}
    assert send(upstream, envelope)[1]['idempotent_replay']
    assert esp.commands == 1
    # Overlap the acknowledged head: reconnect can check continuity even with no new events.
    assert read(7)['events'] == [page['events'][-1]]
    assert send(upstream, build_envelope(seed, state='off', request_id='next-test'))[0] == 200
    assert [e['sequence'] for e in read(7)['events']] == list(range(7, 15))
    assert read(7)['events'][-1]['detail']['value'] == '0'
    assert runtime.ledger.validate().event_count == 14
    with pytest.raises(error.HTTPError) as exc:
        read(99)
    assert exc.value.code == 409


def test_malformed_hash_gap_and_source_changes_fail_closed(connected):
    _, _, upstream, seed, read, _ = connected
    send(upstream, build_envelope(seed, state='on'))
    events = read()['events']
    # Bridge carries monotonic timestamps as lossless decimal strings to JS.
    for e in events:
        e['time']['monotonic_ns'] = int(e['time']['monotonic_ns'])
    bad = copy.deepcopy(events)
    bad[-1]['detail']['value'] = '99'
    with pytest.raises(ValueError):
        validate_page({'events': bad}, 0)
    with pytest.raises(ValueError):
        validate_page({'events': events[1:]}, 0)
    with pytest.raises(ValueError):
        validate_page({'events': [{'sequence': 1}]}, 0)


def test_bridge_refuses_public_http_and_weak_credentials():
    with pytest.raises(ValueError):
        make_server(upstream='http://192.168.1.8:8080', token='t' * 32,
                    source='ssh-tunnel', controller='unavailable')
    with pytest.raises(ValueError):
        make_server(upstream='http://127.0.0.1:8080', token='',
                    source='local-runtime', controller='mock')


def test_lost_ledger_returns_unavailable_without_command(connected):
    runtime, esp, upstream, seed, read, _ = connected
    runtime.ledger.path.unlink()
    code, payload = send(upstream, build_envelope(seed, state='on'))
    assert code == 503
    assert payload['reason_code'] == 'AUDIT_NOT_READY'
    assert esp.commands == 0
    with pytest.raises(error.HTTPError) as exc:
        read()
    assert exc.value.code == 502


def test_durable_append_failure_prevents_controller_command(connected):
    from unittest.mock import patch
    from dcamr.audit.audit_log import StorageError
    runtime, esp, upstream, seed, _, _ = connected
    with patch.object(runtime.ledger, 'append', side_effect=StorageError('I/O failed')):
        code, payload = send(upstream, build_envelope(seed, state='on'))
    assert code == 503
    assert payload['reason_code'] == 'STORAGE_UNAVAILABLE'
    assert esp.commands == 0
