"""Request-bound native review on the existing Pi ledger and execution path.

Follow AGENTS.md and docs/contracts/technician-runtime-review.md. This is the
first-light OFFLINE runtime; it does not implement enterprise ownership transfer.
"""
import base64
from collections import OrderedDict
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import re
import secrets
import stat
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from dcamr.audit.audit_log import StorageError
from dcamr.audit.event_contract import MAX_EVENT_BYTES, canonical_bytes, parse_json
from dcamr.policy_engine.policy_engine import find_permission

DOMAIN = b'alice-native-review-v1\x00'
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
ACTION_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z')
HASH = re.compile(r'[a-f0-9]{64}\Z')
FIELDS = {'schema_version', 'console_id', 'technician_id', 'action_id', 'action',
          'biometric_session_id', 'biometric_policy', 'issued_at', 'expires_at',
          'request_id', 'request_sha256', 'decision_event_id', 'decision_event_hash',
          'release_sha256', 'authority_interval_ref', 'runtime_epoch', 'review_nonce'}
BINDINGS = ('request_id', 'request_sha256', 'decision_event_id', 'decision_event_hash',
            'release_sha256', 'authority_interval_ref', 'runtime_epoch', 'review_nonce')
DISPOSITIONS = {'REQUEST_APPROVAL': 'APPROVE_ONCE', 'REQUEST_DENIAL': 'REJECT'}
NONCE_TTL = 120
MAX_NONCES = 1024


class ReviewError(ValueError):
    """Bounded public refusal; never include attacker-controlled contents."""


class RuntimeOwner:
    """One executing process per data directory; readers can still open the ledger.

    The lock file is retained across restart. Never unlink it: replacement would
    let two processes acquire locks on different inodes. Inherited runtime objects
    cannot execute after fork; the child must open its own runtime after release.
    """
    def __init__(self, directory):
        self.path = Path(directory) / 'runtime-owner.lock'
        self.fd = None
        self.pid = os.getpid()
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            metadata = os.fstat(self.fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.identity = (metadata.st_dev, metadata.st_ino)
        except OSError:
            self.close()
            raise ReviewError('RUNTIME_DATA_ALREADY_OWNED_OR_UNAVAILABLE') from None

    def check(self):
        try:
            stat = self.path.lstat()
            if (self.fd is None or self.pid != os.getpid()
                    or (stat.st_dev, stat.st_ino) != self.identity):
                raise OSError
        except OSError:
            raise StorageError('Runtime ownership is unavailable') from None

    def close(self):
        if self.fd is not None:
            # close, rather than explicit LOCK_UN: forked child descriptors must
            # not unlock the parent's still-running authority.
            os.close(self.fd)
            self.fd = None


def load_trust(trust_file):
    """Explicit local public trust. Absent configuration disables review."""
    if trust_file is None:
        return {}
    try:
        path = Path(trust_file)
        if path.is_symlink() or not path.is_file():
            raise ValueError
        with path.open('rb') as source:
            value = parse_json(source.read(MAX_EVENT_BYTES + 1))
        if (type(value) is not dict or set(value) != {'schema_version', 'consoles'}
                or value['schema_version'] != 'alice-console-trust-v1'
                or type(value['consoles']) is not list or not 1 <= len(value['consoles']) <= 32):
            raise ValueError
        trust = {}
        for item in value['consoles']:
            if (type(item) is not dict or set(item) != {'console_id', 'public_key', 'technician_ids'}
                    or type(item['console_id']) is not str or not ID.fullmatch(item['console_id'])
                    or item['console_id'] in trust or type(item['public_key']) is not str
                    or not HASH.fullmatch(item['public_key'])
                    or type(item['technician_ids']) is not list or not 1 <= len(item['technician_ids']) <= 64
                    or any(type(t) is not str or not ID.fullmatch(t) for t in item['technician_ids'])
                    or len(set(item['technician_ids'])) != len(item['technician_ids'])):
                raise ValueError
            raw = bytes.fromhex(item['public_key'])
            trust[item['console_id']] = (Ed25519PublicKey.from_public_bytes(raw),
                                         frozenset(item['technician_ids']))
        return trust
    except (OSError, ValueError, TypeError, KeyError):
        raise ReviewError('INVALID_CONSOLE_TRUST') from None


class ReviewAuthority:
    def __init__(self, runtime, trust):
        self.runtime = runtime
        self.trust = trust
        self.nonces = OrderedDict()
        # Derived projection only: the existing immutable ledger is authoritative.
        # One compact record per retained request; no duplicate hold queue/database.
        self._requests = {}
        self._actions = {}
        self._sessions = {}
        self._after = 0

    def _sync(self):
        """Replay once, then inspect only the ledger tail in bounded pages."""
        while True:
            batch = self.runtime.ledger.read(after=self._after, limit=64)
            if not batch:
                return
            for event in batch:
                request_id = event['correlation']['request_id']
                if request_id is None:
                    continue
                item = self._requests.setdefault(request_id, {})
                kind = event['event_type']
                if kind in ('DECISION', 'REJECTION'):
                    item['decision'] = {
                        'request_sha256': event['correlation']['request_sha256'],
                        'event_id': event['event_id'], 'event_hash': event['event_hash'],
                        'assessment_id': event['correlation']['assessment_id'],
                        'outcome': event['detail']['outcome'],
                        'release_sha256': event['provenance']['policy']['sha256'],
                        'authority': event['authority'],
                    }
                elif kind == 'TECHNICIAN_ACTION' and event['detail']['intent'] in DISPOSITIONS:
                    if 'action' in item:
                        # Never reinterpret a conflicting imported/admitted history.
                        item['conflict'] = True
                    action_id = event['correlation']['action_id']
                    previous_request = self._actions.setdefault(action_id, request_id)
                    if previous_request != request_id:
                        item['conflict'] = True
                        self._requests[previous_request]['conflict'] = True
                    for evidence in event['provenance']['evidence']:
                        if evidence['ref'] == f'{action_id}.proof':
                            source = evidence['source']
                            session = (source['source_id'], source['source_event_id'])
                            previous = self._sessions.setdefault(session, action_id)
                            if previous != action_id:
                                item['conflict'] = True
                    item['action'] = {
                        'action_id': event['correlation']['action_id'],
                        'action': DISPOSITIONS[event['detail']['intent']],
                        'proof_digests': tuple(e['sha256'] for e in event['provenance']['evidence']),
                    }
                elif kind == 'EXECUTION_RESULT':
                    item['execution_status'] = event['detail']['outcome']
            self._after = batch[-1]['sequence']

    def _nonce(self, request_id, eligible):
        now = time.monotonic()
        while self.nonces and next(iter(self.nonces.values()))[1] <= now:
            self.nonces.popitem(last=False)
        if not eligible:
            self.nonces.pop(request_id, None)
            return 'unavailable'
        if request_id not in self.nonces:
            while len(self.nonces) >= MAX_NONCES:
                self.nonces.popitem(last=False)
            self.nonces[request_id] = (secrets.token_hex(24), now + NONCE_TTL)
        return self.nonces[request_id][0]

    def view(self, request_id):
        if type(request_id) is not str or not ID.fullmatch(request_id):
            raise ReviewError('INVALID_REQUEST_ID')
        self._sync()
        item = self._requests.get(request_id, {})
        decision = item.get('decision')
        if not decision:
            raise ReviewError('REQUEST_NOT_FOUND')
        path = self.runtime._evidence_dir / f'{request_id}.request.json'
        request = None
        try:
            if not path.is_symlink() and path.is_file():
                with path.open('rb') as source:
                    candidate = parse_json(source.read(MAX_EVENT_BYTES + 1))
                if (sha256(canonical_bytes(candidate)).hexdigest() == decision['request_sha256']
                        and next(self.runtime._validator.iter_errors(candidate), None) is None):
                    request = candidate
        except ValueError:
            # Corrupt historical evidence is visible as unavailable, never eligible.
            pass
        action = item.get('action')
        authority = self.runtime.current_authority()
        owner = (authority['product_mode'] == 'OFFLINE' and authority['execution_owner'] == 'ALICE'
                 and authority['confirmation'] == 'CONFIRMED'
                 and type(authority['authority_interval_ref']) is str
                 and ID.fullmatch(authority['authority_interval_ref']))
        reason = 'READY'
        if item.get('conflict'):
            reason = 'REVIEW_HISTORY_CONFLICT'
        elif action:
            reason = 'REVIEW_ALREADY_RESOLVED'
        elif request is None:
            reason = 'REQUEST_DETAILS_UNAVAILABLE'
        elif decision['outcome'] != 'CHALLENGE':
            reason = 'MACHINE_DECISION_NOT_REVIEWABLE'
        elif not owner:
            reason = 'AUTHORITY_NOT_LOCAL'
        elif not self.trust:
            reason = 'CONSOLE_TRUST_NOT_CONFIGURED'
        else:
            finding = find_permission(self.runtime.release, request['agent_id'], request['action'],
                                      request['target'], request['parameters'],
                                      request_sha256=decision['request_sha256'])
            if (finding.outcome != 'REVIEW_REQUIRED'
                    or decision['release_sha256'] != self.runtime.release.manifest_sha256
                    or decision['authority'] != authority):
                reason = 'POLICY_OR_AUTHORITY_CHANGED'
        state = ('APPROVED' if action['action'] == 'APPROVE_ONCE' else 'REJECTED') if action else 'PENDING'
        eligible = reason == 'READY'
        return {'schema_version': 'alice-runtime-review-v1', 'request_id': request_id,
                'request_sha256': decision['request_sha256'],
                'decision_event_id': decision['event_id'], 'decision_event_hash': decision['event_hash'],
                'release_sha256': self.runtime.release.manifest_sha256,
                'authority_interval_ref': authority['authority_interval_ref'],
                'runtime_epoch': self.runtime._boot_id,
                'review_nonce': self._nonce(request_id, eligible),
                'request': request, 'decision': decision['outcome'],
                'review_state': state, 'eligible': eligible, 'reason': reason,
                'accepted_action_id': action['action_id'] if action else None,
                'accepted_action': action['action'] if action else None,
                'execution_status': item.get('execution_status', 'UNKNOWN' if state == 'APPROVED' else 'NOT_EXECUTED')}

    def submit(self, envelope):
        if type(envelope) is not dict or set(envelope) != {'proof', 'signature'}:
            raise ReviewError('INVALID_REVIEW_ENVELOPE')
        proof = envelope['proof']
        if type(proof) is not dict or set(proof) != FIELDS:
            raise ReviewError('INVALID_REVIEW_PROOF')
        for name in FIELDS - {'issued_at', 'expires_at'}:
            if type(proof[name]) is not str or not ID.fullmatch(proof[name]):
                raise ReviewError('INVALID_REVIEW_FIELD')
        if (not ACTION_ID.fullmatch(proof['action_id'])
                or any(not HASH.fullmatch(proof[k]) for k in ('request_sha256', 'decision_event_hash', 'release_sha256'))
                or type(proof['issued_at']) is not int or type(proof['expires_at']) is not int
                or type(envelope['signature']) is not str or len(envelope['signature']) != 88):
            raise ReviewError('INVALID_REVIEW_FIELD')
        if (proof['schema_version'] != 'alice-review-action-v1'
                or proof['biometric_policy'] != 'alice.live-face.v3'
                or proof['action'] not in ('APPROVE_ONCE', 'REJECT')):
            raise ReviewError('INVALID_REVIEW_POLICY_OR_ACTION')
        trusted = self.trust.get(proof['console_id'])
        if trusted is None or proof['technician_id'] not in trusted[1]:
            raise ReviewError('UNTRUSTED_CONSOLE_OR_TECHNICIAN')
        body = canonical_bytes(proof)
        try:
            signature = base64.b64decode(envelope['signature'], validate=True)
            if base64.b64encode(signature).decode('ascii') != envelope['signature']:
                raise ValueError
            trusted[0].verify(signature, DOMAIN + body)
        except Exception:
            raise ReviewError('REVIEW_SIGNATURE_INVALID') from None
        view = self.view(proof['request_id'])
        item = self._requests[proof['request_id']]
        if item.get('conflict'):
            raise ReviewError('REVIEW_HISTORY_CONFLICT')
        # Preserve the signature with the exact canonical proof. The ledger binds
        # the complete envelope; auditing can independently verify native consent.
        evidence = canonical_bytes(envelope)
        digest = sha256(evidence).hexdigest()
        prior = item.get('action')
        if prior:
            if prior['action_id'] != proof['action_id'] or digest not in prior['proof_digests']:
                raise ReviewError('REVIEW_ALREADY_RESOLVED')
            # An expired admitted proof may recover its receipt, never authority.
            return self._receipt(view, proof, True)
        if proof['action_id'] in self._actions:
            raise ReviewError('REVIEW_ACTION_ID_CONFLICT')
        if (proof['console_id'], proof['biometric_session_id']) in self._sessions:
            raise ReviewError('BIOMETRIC_SESSION_ALREADY_USED')
        now = int(time.time())
        if (not now - 60 <= proof['issued_at'] <= now + 5
                or not proof['issued_at'] < proof['expires_at'] <= proof['issued_at'] + 60
                or proof['expires_at'] <= now):
            raise ReviewError('REVIEW_PROOF_EXPIRED')
        if not view['eligible'] or any(proof[k] != view[k] for k in BINDINGS):
            raise ReviewError('REVIEW_SCOPE_STALE_OR_INELIGIBLE')
        rt = self.runtime
        readiness = rt.ledger.readiness()
        headroom = rt.ledger._metadata['quota_bytes'] - rt.ledger._metadata['reserve_bytes'] - readiness.get('allocated_budget_bytes', 0)
        if not readiness['ready'] or headroom < 8 * 3 * MAX_EVENT_BYTES:
            raise ReviewError('AUDIT_NOT_READY')
        proof_path = rt._evidence_dir / f"{proof['action_id']}.review.json"
        if proof_path.exists():
            with proof_path.open('rb') as source:
                if source.read(MAX_EVENT_BYTES + 1) != evidence:
                    raise ReviewError('REVIEW_ACTION_ID_CONFLICT')
        rt._write_evidence(proof_path, evidence)
        public_key = trusted[0].public_bytes(Encoding.Raw, PublicFormat.Raw)
        key_digest = sha256(public_key).hexdigest()
        rt._write_evidence(rt._evidence_dir / f'{key_digest}.console-public-key', public_key)
        request = view['request']
        correlation = rt._correlation(request['request_id'], view['request_sha256'],
                                      assessment_id=item['decision']['assessment_id'], action_id=proof['action_id'],
                                      parent_event_id=view['decision_event_id'])
        attribution = rt._attribution(request['agent_id'])
        attribution.update(actor_kind='TECHNICIAN', actor_id=proof['technician_id'],
                           technician_id=proof['technician_id'], authenticated_requester_id=proof['console_id'])
        rt._append(f"{proof['action_id']}.review", 'TECHNICIAN_ACTION', correlation=correlation,
                   attribution=attribution,
                   detail={'intent': 'REQUEST_APPROVAL' if proof['action'] == 'APPROVE_ONCE' else 'REQUEST_DENIAL',
                           'reason_codes': ['FRESH_NATIVE_FACE_VERIFIED']},
                   evidence=[{'ref': f"{proof['action_id']}.proof", 'sha256': digest,
                              'source': rt._source(proof['console_id'], proof['biometric_session_id'])},
                             {'ref': f'console-key-{key_digest}', 'sha256': key_digest,
                              'source': rt._source(proof['console_id'], 'configured-public-key')}])
        # Admission commits synchronously before command dispatch. After admission,
        # every retry/restart only returns ledger state, even if execution is unknown.
        if proof['action'] == 'APPROVE_ONCE':
            response = dict(rt._outcomes[request['request_id']]['response'])
            rt._execute_request(request, view['request_sha256'], response, correlation, attribution)
        rt.ledger.seal()
        return self._receipt(self.view(proof['request_id']), proof, False)

    @staticmethod
    def _receipt(view, proof, replay):
        return {'schema_version': 'alice-review-receipt-v1', 'action_id': proof['action_id'],
                'request_id': proof['request_id'], 'status': 'ACCEPTED',
                'review_state': view['review_state'], 'execution_status': view['execution_status'],
                'idempotent_replay': replay}
