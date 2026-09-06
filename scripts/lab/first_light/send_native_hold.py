"""Submit one signed HOLD request to an existing local native rehearsal.

Follow AGENTS.md. This command uses the rehearsal's ephemeral agent identity and
existing loopback runtime. It cannot select a controller, target or remote URL.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler
import uuid

from common.repository_paths import repository_root
from dcamr.audit.event_contract import MAX_EVENT_BYTES, canonical_bytes, parse_json
from lab.first_light.native_review_demo import REHEARSAL_SOURCE
from lab.first_light.terminal_client import build_envelope
from services.runtime_feed import MAX_RESPONSE_BYTES, NoRedirect, loopback_url, unique_object


class HoldTestError(ValueError):
    """Bounded operator message; never include session contents or credentials."""


def _private_file(path, limit):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        metadata = os.fstat(stream.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o077 or metadata.st_size > limit):
            raise ValueError
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError
        return data


def load_rehearsal(session_file):
    """Validate the private helper-owned descriptor before creating any client."""
    try:
        supplied = Path(session_file).expanduser()
        if not supplied.is_absolute() or supplied.name != 'session.json' or supplied.is_symlink():
            raise ValueError
        path = supplied.resolve(strict=True)
        root = path.parent
        repository = repository_root()
        metadata = root.stat()
        if (root == repository or repository in root.parents
                or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077):
            raise ValueError
        value = parse_json(_private_file(path, MAX_EVENT_BYTES))
        if (type(value) is not dict
                or set(value) != {'source', 'directory', 'runtime_url', 'environment'}
                or value['source'] != REHEARSAL_SOURCE or value['directory'] != str(root)
                or type(value['environment']) is not dict
                or value['environment'].get('ALICE_TRANSPORT_MODE') != 'remote'
                or value['environment'].get('ALICE_BIOMETRIC_MODE') != 'arcface'):
            raise ValueError
        # Loopback literals only; no DNS, tunnel/public destination, path, query,
        # credentials or redirect supplied through arbitrary command-line flags.
        url = loopback_url(value['runtime_url'])
        feed_url = loopback_url(value['environment']['ALICE_FEED_URL'])
        token = value['environment']['ALICE_FEED_TOKEN']
        if (type(token) is not str or len(token) < 32 or not token.isascii()
                or any(character.isspace() for character in token)):
            raise ValueError
        key_path = root / 'bundle/client/term-agent-01-k1.seed'
        if key_path.resolve(strict=True).parent != root / 'bundle/client':
            raise ValueError
        encoded = _private_file(key_path, 128).decode('ascii').strip()
        if not re.fullmatch(r'[a-f0-9]{64}', encoded):
            raise ValueError
        return url, bytes.fromhex(encoded), feed_url, token
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise HoldTestError('INVALID_LOCAL_REHEARSAL_SESSION') from None


def send_hold(session_file):
    url, seed, feed_url, token = load_rehearsal(session_file)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        probe = Request(feed_url + '/events?after=0', headers={'Authorization': 'Bearer ' + token})
        with opener.open(probe, timeout=10) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError
            feed = json.loads(raw, object_pairs_hook=unique_object)
        if (type(feed) is not dict or feed.get('schema_version') != 'alice-runtime-feed-v1'
                or feed.get('source') != {'connection': 'local-runtime', 'controller': 'mock'}):
            raise ValueError
    except (OSError, HTTPError, ValueError, RecursionError):
        raise HoldTestError('LOCAL_MOCK_REHEARSAL_UNAVAILABLE') from None
    request_id = 'native-test-' + uuid.uuid4().hex
    envelope = build_envelope(seed, state='on', request_id=request_id)
    request = Request(url + '/request', data=canonical_bytes(envelope), method='POST',
                      headers={'Content-Type': 'application/json'})
    try:
        with opener.open(request, timeout=10) as response:
            status = response.status
            result = parse_json(response.read(MAX_EVENT_BYTES + 1))
        if (status != 202 or type(result) is not dict or result.get('request_id') != request_id
                or result.get('decision') != 'CHALLENGE' or result.get('execution') is not None
                or result.get('observed_state') is not None):
            raise ValueError
        check = Request(feed_url + '/review/' + request_id,
                        headers={'Authorization': 'Bearer ' + token})
        with opener.open(check, timeout=10) as response:
            snapshot = parse_json(response.read(MAX_EVENT_BYTES + 1))
            if response.status != 200:
                raise ValueError
        if (type(snapshot) is not dict or snapshot.get('schema_version') != 'alice-runtime-review-v1'
                or snapshot.get('request_id') != request_id or snapshot.get('request') != envelope['request']
                or snapshot.get('request_sha256') != sha256(canonical_bytes(envelope['request'])).hexdigest()
                or snapshot.get('decision') != 'CHALLENGE' or snapshot.get('eligible') is not True
                or snapshot.get('review_state') != 'PENDING'
                or snapshot.get('execution_status') != 'NOT_EXECUTED'):
            raise ValueError
    except (OSError, HTTPError, ValueError):
        # Delivery can have reached the runtime before the connection failed.
        # Never retry automatically or expose an upstream body/secret in stdout.
        raise HoldTestError('HOLD_DELIVERY_UNCONFIRMED_CHECK_LOCAL_REHEARSAL_HISTORY') from None
    return {'request_id': request_id, 'decision': snapshot['decision'],
            'execution': snapshot['execution_status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True,
                        help='Absolute private session.json produced by the active local rehearsal')
    args = parser.parse_args()
    try:
        print(json.dumps(send_hold(args.session)))
    except HoldTestError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
