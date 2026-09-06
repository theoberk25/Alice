"""Extend an existing signed demo release with two fan agents without key loss."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from dcamr.packages.package_verifier import _canonical_bytes, load_release

AGENTS = ('cooling-agent-01', 'power-agent-01')


def extend(source, destination, client_dir, trust_key, signing_seed):
    for path in (destination, client_dir):
        path.mkdir(parents=True, exist_ok=False)
    trusted = bytes.fromhex(Path(trust_key).read_text().strip())
    load_release(source, trusted)
    signer = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(Path(signing_seed).read_text().strip()))
    actual = signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    if actual != trusted:
        raise ValueError('manifest signing seed does not match active trust')
    for name in ('manifest.json', 'manifest.sig', 'grants.json', 'subjects.json', 'terminal_keys.json'):
        shutil.copy2(Path(source) / name, destination / name)
    keys = json.loads((destination / 'terminal_keys.json').read_text())
    subjects = json.loads((destination / 'subjects.json').read_text())
    for agent in AGENTS:
        key_id = agent + '-k1'
        if key_id in keys['keys'] or agent in subjects['agents']:
            raise ValueError('fan agent already exists')
        private = Ed25519PrivateKey.generate()
        seed_path = client_dir / (key_id + '.seed')
        seed_path.write_text(private.private_bytes_raw().hex() + '\n')
        seed_path.chmod(0o600)
        keys['keys'][key_id] = {'agent_id': agent,
            'ed25519_public_hex': private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()}
        subjects['agents'][agent] = {'responsible_user': 'TECH-DEMO'}
    grants = json.loads((destination / 'grants.json').read_text())
    grants['grants'].append({'grant_id': 'G-FAN-AGENTS', 'agents': list(AGENTS),
        'actions': ['set_fan_speed'], 'targets': ['SERVER-ROOM-FANS'], 'effect': 'PERMIT',
        'approval_required': False, 'parameter_bounds': {'value': {'min': 0, 'max': 100}}})
    payloads = {'grants.json': grants, 'subjects.json': subjects, 'terminal_keys.json': keys}
    for name, value in payloads.items():
        (destination / name).write_bytes(_canonical_bytes(value))
    manifest = json.loads((destination / 'manifest.json').read_text())
    manifest['generation'] += 1
    manifest['bundle_id'] = 'first-light-fan-model-%06d' % manifest['generation']
    manifest['release_note'] = 'Preserve light grants and keys; add permitted cooling/power fan agents.'
    manifest['content_digests'] = {name: sha256((destination / name).read_bytes()).hexdigest()
                                   for name in payloads}
    unsigned = {key: value for key, value in manifest.items() if key != 'signature'}
    (destination / 'manifest.json').write_bytes(_canonical_bytes(manifest))
    (destination / 'manifest.sig').write_bytes(signer.sign(_canonical_bytes(unsigned)))
    verified = load_release(destination, trusted)
    return verified


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--client-output', type=Path, required=True)
    p.add_argument('--trust-key', type=Path, required=True)
    p.add_argument('--signing-seed', type=Path, required=True)
    args = p.parse_args()
    release = extend(args.source, args.output, args.client_output,
                     args.trust_key, args.signing_seed)
    print(json.dumps({'bundle_id': release.bundle_id, 'generation': release.generation,
                      'grants': len(release.grants), 'terminal_keys': len(release.terminal_keys)}))

if __name__ == '__main__':
    main()
