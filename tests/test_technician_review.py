"""Real signed review, ledger and mock controller checks; no biometric qualification."""
import base64
from dataclasses import replace
import json
import time
import uuid
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from dcamr.audit.event_contract import canonical_bytes
from dcamr.main import FirstLightRuntime
from dcamr.technician_review import BINDINGS, DOMAIN
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
import threading


@pytest.fixture
def review_runtime(tmp_path):
    release = build_release.build(tmp_path / 'bundle', approval_required=True)
    key = Ed25519PrivateKey.generate()
    trust = tmp_path / 'consoles.json'
    trust.write_text(json.dumps({'schema_version': 'alice-console-trust-v1', 'consoles': [{
        'console_id': 'console-test', 'public_key': key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
        'technician_ids': ['T1']}]}))
    server, esp = mock_esp.make_server()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    args = dict(release_dir=release,
                trusted_manifest_key=bytes.fromhex((tmp_path / 'bundle/trust/manifest_public.hex').read_text().strip()),
                data_dir=tmp_path / 'data', esp_base_url='http://%s:%s' % server.server_address,
                console_trust_file=trust)
    rt = FirstLightRuntime(**args)
    seed = bytes.fromhex((tmp_path / 'bundle/client/term-agent-01-k1.seed').read_text().strip())
    def pending():
        request = build_envelope(seed, state='on')
        code, result = rt.handle_request(request)
        assert code == 202 and result['decision'] == 'CHALLENGE'
        code, view = rt.review(request_id=request['request']['request_id'])
        assert code == 200 and view['eligible']
        return view
    def signed(view, **changes):
        now = int(time.time())
        proof = {k: view[k] for k in BINDINGS}
        proof.update(schema_version='alice-review-action-v1', console_id='console-test', technician_id='T1',
                     action_id=str(uuid.uuid4()), action='APPROVE_ONCE', biometric_session_id=str(uuid.uuid4()),
                     biometric_policy='alice.live-face.v3', issued_at=now, expires_at=now+60)
        proof.update(changes)
        return {'proof': proof, 'signature': base64.b64encode(key.sign(DOMAIN+canonical_bytes(proof))).decode()}
    yield rt, esp, pending, signed, args
    rt.close()
    server.shutdown()
    server.server_close()


def test_approve_once_replay_and_restart(review_runtime):
    rt, esp, pending, signed, args = review_runtime
    view = pending()
    assert esp.commands == 0
    proof = signed(view)
    code, receipt = rt.review(envelope=proof)
    assert code == 200, receipt
    assert receipt['review_state'] == 'APPROVED' and receipt['execution_status'] == 'COMPLETED'
    assert esp.commands == 1
    assert rt.review(envelope=proof)[1]['idempotent_replay']
    assert esp.commands == 1
    events = list(rt.iter_events())
    assert [e['detail']['outcome'] for e in events if e['event_type']=='DECISION'] == ['CHALLENGE']
    assert sum(e['event_type']=='TECHNICIAN_ACTION' for e in events)==1
    # Separate read-only reopen checks durable replay without replacing fixture owner.
    rt.close()
    reopened = FirstLightRuntime(**args)
    try:
        assert reopened.review(envelope=proof)[1]['idempotent_replay']
        assert esp.commands == 1
    finally:
        reopened.close()


def test_reject_never_executes_or_changes_machine_decision(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    view = pending()
    code, result = rt.review(envelope=signed(view, action='REJECT'))
    assert code == 200, result
    assert result['review_state'] == 'REJECTED'
    assert result['execution_status'] == 'NOT_EXECUTED'
    assert esp.commands == 0
    assert rt.review(envelope=signed(view))[0] == 409


@pytest.mark.parametrize('change', [
    {'technician_id':'T2'}, {'console_id':'unknown'}, {'biometric_policy':'alice.fake.v1'},
    {'request_sha256':'0'*64}, {'decision_event_hash':'0'*64}, {'runtime_epoch':'old'},
    {'review_nonce':'wrong'}, {'release_sha256':'0'*64}, {'authority_interval_ref':'old'},
    {'expires_at':1}, {'action':'ALLOW'}, {'issued_at':True},
])
def test_invalid_or_stale_proof_cannot_execute(review_runtime, change):
    rt, esp, pending, signed, _ = review_runtime
    proof = signed(pending(), **change)
    assert rt.review(envelope=proof)[0] == 409
    assert esp.commands == 0
    assert not any(e['event_type']=='TECHNICIAN_ACTION' for e in rt.iter_events())


def test_signature_scope_policy_and_authority_are_rechecked(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    view, other = pending(), pending()
    proof = signed(view)
    proof['proof']['request_id'] = other['request_id']
    assert rt.review(envelope=proof)[0] == 409
    proof = signed(view)
    with patch.object(rt, 'current_authority', return_value={**rt.current_authority(), 'execution_owner':'ENTERPRISE'}):
        assert rt.review(envelope=proof)[0] == 409
    release = rt.release
    rt.release = replace(release, grants=())
    assert rt.review(envelope=proof)[0] == 409
    rt.release = release
    rt._evidence_dir.joinpath(view['request_id']+'.request.json').write_text('{}')
    assert rt.review(envelope=proof)[0] == 409
    assert esp.commands == 0


def test_admitted_action_with_failed_execution_is_never_reissued(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    proof = signed(pending())
    with patch.object(rt, '_execute_request', side_effect=OSError('test failure')):
        assert rt.review(envelope=proof)[0] == 503
    code, result = rt.review(envelope=proof)
    assert code == 200 and result['idempotent_replay']
    assert result['execution_status'] == 'UNKNOWN'
    assert esp.commands == 0


def test_resolution_contains_exact_action_and_signed_evidence(review_runtime):
    from hashlib import sha256
    from dcamr.audit.event_contract import parse_json
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    rt, esp, pending, signed, _ = review_runtime
    envelope = signed(pending(), action='REJECT')
    assert rt.review(envelope=envelope)[0] == 200
    view = rt.review(request_id=envelope['proof']['request_id'])[1]
    assert view['accepted_action_id'] == envelope['proof']['action_id']
    assert view['accepted_action'] == 'REJECT' and not view['eligible']
    event = next(e for e in rt.iter_events() if e['event_type'] == 'TECHNICIAN_ACTION')
    evidence = rt._evidence_dir.joinpath(envelope['proof']['action_id'] + '.review.json').read_bytes()
    assert parse_json(evidence) == envelope
    assert event['provenance']['evidence'][0]['sha256'] == sha256(evidence).hexdigest()
    key_ref = event['provenance']['evidence'][1]
    public = rt._evidence_dir.joinpath(key_ref['sha256'] + '.console-public-key').read_bytes()
    assert sha256(public).hexdigest() == key_ref['sha256']
    Ed25519PublicKey.from_public_bytes(public).verify(base64.b64decode(envelope['signature']),
                                                    DOMAIN + canonical_bytes(envelope['proof']))
    assert esp.commands == 0


def test_expired_admitted_proof_only_recovers_receipt(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    envelope = signed(pending())
    assert rt.review(envelope=envelope)[0] == 200
    with patch('dcamr.technician_review.time.time', return_value=envelope['proof']['expires_at'] + 1000):
        code, result = rt.review(envelope=envelope)
    assert code == 200 and result['idempotent_replay']
    assert esp.commands == 1


@pytest.mark.parametrize('raw', [b'{', b'[]', b'{"a":1,"a":2}', b'\xff', b'x' * 16385])
def test_corrupt_request_evidence_is_unavailable_not_reviewable(review_runtime, raw):
    rt, esp, pending, signed, _ = review_runtime
    view = pending()
    rt._evidence_dir.joinpath(view['request_id'] + '.request.json').write_bytes(raw)
    code, current = rt.review(request_id=view['request_id'])
    assert code == 200 and current['request'] is None and not current['eligible']
    assert current['reason'] == 'REQUEST_DETAILS_UNAVAILABLE'
    assert rt.review(envelope=signed(view))[0] == 409
    assert esp.commands == 0


def test_online_unknown_authority_displays_history_without_review(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    view = pending()
    for mode, owner, confirmation in [('ONLINE', 'ENTERPRISE', 'CONFIRMED'),
                                      ('OFFLINE', 'UNKNOWN', 'UNCONFIRMED')]:
        authority = {**rt.current_authority(), 'product_mode': mode, 'execution_owner': owner,
                     'confirmation': confirmation, 'authority_interval_ref': None}
        with patch.object(rt, 'current_authority', return_value=authority):
            code, current = rt.review(request_id=view['request_id'])
            assert code == 200 and current['request'] == view['request']
            assert current['authority_interval_ref'] is None and not current['eligible']
            assert current['reason'] == 'AUTHORITY_NOT_LOCAL'
            assert rt.review(envelope=signed(view))[0] == 409
    assert esp.commands == 0


def test_review_requires_explicit_trust_and_never_changes_allow_path(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    view = pending()
    rt.reviews.trust = {}
    current = rt.review(request_id=view['request_id'])[1]
    assert current['reason'] == 'CONSOLE_TRUST_NOT_CONFIGURED' and not current['eligible']
    assert rt.review(envelope=signed(view))[0] == 409
    assert esp.commands == 0


@pytest.mark.parametrize('value', [1.0, 2**63, True, [], {}, None])
def test_malformed_signed_time_returns_bounded_refusal(review_runtime, value):
    rt, esp, pending, signed, _ = review_runtime
    envelope = signed(pending())
    envelope['proof']['issued_at'] = value
    assert rt.review(envelope=envelope)[0] == 409
    assert esp.commands == 0


def test_global_action_id_conflict_survives_missing_evidence(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    first, second = pending(), pending()
    proof = signed(first, action='REJECT')
    assert rt.review(envelope=proof)[0] == 200
    rt._evidence_dir.joinpath(proof['proof']['action_id'] + '.review.json').unlink()
    other = signed(second, action_id=proof['proof']['action_id'])
    code, result = rt.review(envelope=other)
    assert code == 409 and result['error'] == 'REVIEW_ACTION_ID_CONFLICT'
    assert esp.commands == 0


@pytest.mark.parametrize('same_proof', [True, False])
def test_concurrent_review_has_one_durable_winner(review_runtime, same_proof):
    from concurrent.futures import ThreadPoolExecutor
    rt, esp, pending, signed, _ = review_runtime
    view = pending()
    first = signed(view)
    second = first if same_proof else signed(view, action='REJECT')
    barrier = threading.Barrier(2)
    def submit(envelope):
        barrier.wait(timeout=5)
        return rt.review(envelope=envelope)
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(submit, p) for p in (first, second)]
        results = [f.result(timeout=10) for f in futures]
    events = [e for e in rt.iter_events() if e['event_type'] == 'TECHNICIAN_ACTION']
    assert len(events) == 1
    approved = events[0]['detail']['intent'] == 'REQUEST_APPROVAL'
    assert esp.commands == int(approved)
    if same_proof:
        assert [code for code, _ in results] == [200, 200]
        assert sum(result['idempotent_replay'] for _, result in results) == 1
    else:
        assert sorted(code for code, _ in results) == [200, 409]


def test_reject_winner_cannot_be_followed_by_approval(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    view = pending()
    assert rt.review(envelope=signed(view, action='REJECT'))[0] == 200
    assert rt.review(envelope=signed(view))[0] == 409
    assert esp.commands == 0


def test_second_runtime_process_cannot_acquire_same_execution_ledger(review_runtime):
    import pickle
    import subprocess
    import sys
    rt, esp, pending, signed, args = review_runtime
    code = '''import pickle, sys
from dcamr.main import FirstLightRuntime, StartupError
try:
    rt = FirstLightRuntime(**pickle.loads(sys.stdin.buffer.read()))
except StartupError as exc:
    assert str(exc) == 'RUNTIME_DATA_ALREADY_OWNED_OR_UNAVAILABLE'
else:
    rt.close()
    raise AssertionError('second runtime acquired execution authority')
'''
    result = subprocess.run([sys.executable, '-c', code], input=pickle.dumps(args),
                            capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode()
    proof = signed(pending(), action='REJECT')
    assert rt.review(envelope=proof)[0] == 200
    assert esp.commands == 0


def test_owner_released_on_clean_close_and_failed_startup(review_runtime):
    from dcamr.main import StartupError
    rt, _, _, _, args = review_runtime
    with pytest.raises(StartupError, match='ALREADY_OWNED'):
        FirstLightRuntime(**args)
    rt.close()
    with patch('dcamr.main._make_controller', side_effect=OSError('controller init failure')):
        with pytest.raises(OSError):
            FirstLightRuntime(**args)
    reopened = FirstLightRuntime(**args)
    reopened.close()
    reopened.close()


@pytest.mark.parametrize('trust', [b'{}', b'{"a":1,"a":2}', b'\xff', b'x' * 16385,
                                   b'{"schema_version":"alice-console-trust-v1","consoles":[]}'])
def test_bad_trust_fails_before_opening_controller(review_runtime, trust):
    from dcamr.main import StartupError
    rt, _, _, _, args = review_runtime
    args['console_trust_file'].write_bytes(trust)
    with patch('dcamr.main._make_controller') as controller:
        with pytest.raises(StartupError, match='INVALID_CONSOLE_TRUST'):
            FirstLightRuntime(**args)
    controller.assert_not_called()


def test_pending_proof_is_stale_after_runtime_restart(review_runtime):
    rt, esp, pending, signed, args = review_runtime
    proof = signed(pending())
    rt.close()
    reopened = FirstLightRuntime(**args)
    try:
        assert reopened.review(envelope=proof)[0] == 409
        assert esp.commands == 0
    finally:
        reopened.close()


@pytest.mark.parametrize('phase', ['proof', 'admission', 'result'])
def test_storage_failure_never_reexecutes_and_preserves_unknown_outcome(review_runtime, phase):
    from dcamr.audit.audit_log import StorageError
    rt, esp, pending, signed, _ = review_runtime
    proof = signed(pending())
    original = rt._append
    def append(event_id, kind, **kwargs):
        if kind == ('TECHNICIAN_ACTION' if phase == 'admission' else 'EXECUTION_RESULT'):
            raise StorageError('test storage failure')
        return original(event_id, kind, **kwargs)
    if phase == 'proof':
        with patch.object(rt, '_write_evidence', side_effect=OSError('test failure')):
            assert rt.review(envelope=proof)[0] == 503
    else:
        with patch.object(rt, '_append', side_effect=append):
            assert rt.review(envelope=proof)[0] == 503
    if phase == 'result':
        assert esp.commands == 1
        code, recovered = rt.review(envelope=proof)
        assert code == 200 and recovered['idempotent_replay']
        assert recovered['execution_status'] == 'UNKNOWN' and esp.commands == 1
    else:
        assert esp.commands == 0
        assert not any(e['event_type'] == 'TECHNICIAN_ACTION' for e in rt.iter_events())


def test_snapshot_lookup_only_reads_incremental_tail_and_nonce_cache_is_bounded(review_runtime):
    from dcamr.technician_review import MAX_NONCES
    rt, _, pending, _, _ = review_runtime
    view = pending()
    after = rt.reviews._after
    assert after > 0
    with patch.object(rt.ledger, 'read', wraps=rt.ledger.read) as read:
        for _ in range(5):
            assert rt.review(request_id=view['request_id'])[0] == 200
    assert read.call_count == 5
    assert all(call.kwargs['after'] == after for call in read.call_args_list)
    for i in range(MAX_NONCES + 2):
        rt.reviews._nonce(f'R{i}', True)
    assert len(rt.reviews.nonces) == MAX_NONCES
    assert view['request_id'] not in rt.reviews.nonces
    with patch('dcamr.technician_review.time.monotonic', return_value=time.monotonic() + 121):
        assert rt.reviews._nonce('expired', False) == 'unavailable'
    assert len(rt.reviews.nonces) == 0


@pytest.fixture
def review_http(review_runtime):
    from dcamr.main import make_server as runtime_server
    from services.runtime_feed import make_server as bridge_server
    rt, esp, pending, signed, args = review_runtime
    pi = runtime_server(rt, '127.0.0.1', 0)
    bridge = bridge_server(upstream=f'http://127.0.0.1:{pi.server_port}', token='t' * 32,
                           source='local-runtime', controller='mock', port=0)
    servers = [pi, bridge]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    yield (*review_runtime, pi, bridge)
    for server in reversed(servers):
        server.shutdown()
        server.server_close()


def http_review(server, path, body=None, token='t' * 32):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    request = Request(f'http://127.0.0.1:{server.server_port}{path}', data=body, headers=headers)
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as exc:
        response = exc
    with response:
        return response.code, json.loads(response.read()), response.headers


def test_real_bridge_preserves_exact_snapshot_and_requires_signed_consent(review_http):
    rt, esp, pending, signed, _, pi, bridge = review_http
    view = pending()
    assert http_review(bridge, '/review/' + view['request_id'])[1] == view
    assert http_review(bridge, '/review/' + view['request_id'], token='wrong')[0] == 401
    assert http_review(bridge, '/review', b'{}')[0] == 409
    assert esp.commands == 0
    proof = signed(view)
    code, receipt, headers = http_review(bridge, '/review', canonical_bytes(proof))
    assert code == 200 and receipt['status'] == 'ACCEPTED'
    assert receipt['execution_status'] == 'COMPLETED'
    assert headers['Cache-Control'] == 'no-store'
    assert headers.get('Access-Control-Allow-Origin') is None
    assert esp.commands == 1
    current = http_review(bridge, '/review/' + view['request_id'])[1]
    assert current['accepted_action_id'] == proof['proof']['action_id']
    assert current['accepted_action'] == 'APPROVE_ONCE'
    assert http_review(bridge, '/review', canonical_bytes(proof))[1]['idempotent_replay']
    assert esp.commands == 1


@pytest.mark.parametrize('body', [b'{"proof":{},"proof":{},"signature":"x"}',
                                  b'{"x":1.2}', b'{"x":9223372036854775808}',
                                  b'\xff', b'[' * 18 + b'0' + b']' * 18,
                                  b'x' * 16385])
def test_pi_and_bridge_reject_malformed_canonical_json(review_http, body):
    _, esp, _, _, _, pi, bridge = review_http
    for server in (pi, bridge):
        assert http_review(server, '/review', body)[0] == 400
    assert esp.commands == 0


def test_bridge_forwards_only_fixed_review_paths(review_http):
    _, esp, _, _, _, _, bridge = review_http
    for path in ['/request', '/review?url=http://example.com', '/review/../request',
                 '/review/R?next=/request', '/review/R/extra']:
        assert http_review(bridge, path, b'{}')[0] == 404
        assert http_review(bridge, path)[0] == 404
    assert esp.commands == 0


def test_dropped_http_acknowledgment_reconciles_without_new_execution(review_http):
    import socket
    rt, esp, pending, signed, _, pi, bridge = review_http
    view = pending()
    envelope = signed(view)
    reply = pi.RequestHandlerClass._reply
    def drop_after_admission(handler, code, payload):
        if handler.path == '/review' and code == 200:
            handler.close_connection = True
            handler.connection.shutdown(socket.SHUT_RDWR)
            handler.connection.close()
        else:
            reply(handler, code, payload)
    with patch.object(pi.RequestHandlerClass, '_reply', new=drop_after_admission):
        code, response, _ = http_review(bridge, '/review', canonical_bytes(envelope))
    assert code == 502 and esp.commands == 1
    code, recovered, _ = http_review(bridge, '/review/' + view['request_id'])
    assert code == 200 and recovered['accepted_action_id'] == envelope['proof']['action_id']
    assert recovered['execution_status'] == 'COMPLETED'
    assert esp.commands == 1
    assert http_review(bridge, '/review', canonical_bytes(envelope))[1]['idempotent_replay']
    assert esp.commands == 1


def test_public_cross_language_golden_vector():
    from hashlib import sha256
    from pathlib import Path
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    vector = json.loads(Path('tests/fixtures/runtime-review/golden.json').read_text())
    assert bytes.fromhex(vector['domain_hex']) == DOMAIN
    assert canonical_bytes(vector['request']).decode() == vector['request_canonical']
    assert sha256(canonical_bytes(vector['request'])).hexdigest() == vector['request_sha256']
    assert canonical_bytes(vector['proof']).decode() == vector['proof_canonical']
    for case in vector['canonical_cases']:
        assert canonical_bytes(case['value']).decode() == case['canonical']
    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(vector['public_key']))
    key.verify(base64.b64decode(vector['signature']), DOMAIN + canonical_bytes(vector['proof']))
    with pytest.raises(Exception):
        key.verify(base64.b64decode(vector['signature']), b'wrong-domain\0' + canonical_bytes(vector['proof']))


@pytest.mark.parametrize('phase,commands', [('admission', 0), ('attempt', 0), ('result', 1)])
def test_restart_after_durable_admission_never_reissues_uncertain_execution(review_runtime, phase, commands):
    from dcamr.audit.audit_log import StorageError
    rt, esp, pending, signed, args = review_runtime
    proof = signed(pending())
    original = rt._append
    def append(event_id, kind, **kwargs):
        if kind == ('EXECUTION_ATTEMPT' if phase == 'attempt' else 'EXECUTION_RESULT'):
            raise StorageError('injected interrupted persistence')
        return original(event_id, kind, **kwargs)
    if phase == 'admission':
        with patch.object(rt, '_execute_request', side_effect=OSError('interrupted dispatch')):
            assert rt.review(envelope=proof)[0] == 503
    else:
        with patch.object(rt, '_append', side_effect=append):
            assert rt.review(envelope=proof)[0] == 503
    assert esp.commands == commands
    rt.close()
    reopened = FirstLightRuntime(**args)
    try:
        code, receipt = reopened.review(envelope=proof)
        assert code == 200 and receipt['idempotent_replay']
        assert receipt['review_state'] == 'APPROVED' and receipt['execution_status'] == 'UNKNOWN'
        assert esp.commands == commands
    finally:
        reopened.close()


def test_evidence_never_overwrites_original_or_follows_symlinks(review_runtime):
    from dcamr.audit.audit_log import StorageError
    rt, _, pending, _, _ = review_runtime
    view = pending()
    path = rt._evidence_dir / (view['request_id'] + '.request.json')
    original = path.read_bytes()
    rt._write_evidence(path, original)
    with pytest.raises(StorageError, match='Evidence identity conflict'):
        rt._write_evidence(path, b'changed')
    link = rt._evidence_dir / 'untrusted-link'
    link.symlink_to(path)
    with pytest.raises(OSError):
        rt._write_evidence(link, b'changed')
    assert path.read_bytes() == original


def test_informational_technician_action_is_not_a_disposition(review_runtime):
    rt, esp, pending, _, _ = review_runtime
    view = pending()
    request = view['request']
    attribution = rt._attribution(request['agent_id'])
    attribution.update(actor_kind='TECHNICIAN', actor_id='T1', technician_id='T1')
    rt._append('context-note', 'TECHNICIAN_ACTION',
               correlation=rt._correlation(request['request_id'], view['request_sha256']),
               attribution=attribution, detail={'intent': 'PROVIDE_CONTEXT', 'reason_codes': []})
    current = rt.review(request_id=view['request_id'])[1]
    assert current['eligible'] and current['accepted_action_id'] is None
    assert esp.commands == 0



def test_biometric_session_cannot_authorize_a_second_request_after_restart(review_runtime):
    rt, esp, pending, signed, args = review_runtime
    first, second = pending(), pending()
    proof = signed(first, action='REJECT')
    assert rt.review(envelope=proof)[0] == 200
    reused = signed(second, biometric_session_id=proof['proof']['biometric_session_id'])
    assert rt.review(envelope=reused)[1]['error'] == 'BIOMETRIC_SESSION_ALREADY_USED'
    rt.close()
    reopened = FirstLightRuntime(**args)
    try:
        current = reopened.review(request_id=second['request_id'])[1]
        reused = signed(current, biometric_session_id=proof['proof']['biometric_session_id'])
        assert reopened.review(envelope=reused)[1]['error'] == 'BIOMETRIC_SESSION_ALREADY_USED'
        assert esp.commands == 0
    finally:
        reopened.close()


def test_matching_evidence_retry_must_complete_fsync_before_admission(review_runtime):
    rt, esp, pending, signed, _ = review_runtime
    proof = signed(pending())
    with patch('dcamr.main.os.fsync', side_effect=OSError('storage cannot sync')):
        assert rt.review(envelope=proof)[0] == 503
        # Bytes exist after the first write but do not establish durable consent.
        assert rt._evidence_dir.joinpath(proof['proof']['action_id'] + '.review.json').is_file()
        assert rt.review(envelope=proof)[0] == 503
    assert esp.commands == 0
    assert not any(e['event_type'] == 'TECHNICIAN_ACTION' for e in rt.iter_events())
    assert rt.review(envelope=proof)[0] == 200
    assert esp.commands == 1
