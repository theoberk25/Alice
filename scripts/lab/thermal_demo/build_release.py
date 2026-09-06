"""Generate explicitly local demo trust and signed fan permissions; no provisioning."""
import argparse
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from lab.enterprise_sim.permissions import build_manifest, canonical_bytes, digest_of, sign_manifest
from lab.first_light.build_release import build_subjects_payload


def build(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    release = directory / 'release'
    release.mkdir()
    keys, config = {}, {}
    for agent in ('cooling-agent-01', 'power-agent-01', 'observer-agent-01'):
        key = Ed25519PrivateKey.generate()
        key_id = agent + '-k1'
        seed = directory / (key_id + '.seed')
        seed.touch(mode=0o600)
        seed.write_text(key.private_bytes_raw().hex() + '\n')
        keys[key_id] = {'agent_id': agent, 'ed25519_public_hex': key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()}
        config[agent] = {'key_id': key_id, 'seed_file': seed.name}
    grants = []
    for name, agents, low, high, review in (
        ('DEMO-AUTO', ['cooling-agent-01'], 60, 90, False),
        ('DEMO-REVIEW', ['cooling-agent-01', 'power-agent-01'], 0, 100, True)):
        grants.append({'grant_id': name, 'agents': agents, 'actions': ['set_demo_fan_pct'],
                       'targets': ['DEMO-SERVER-01'], 'effect': 'PERMIT',
                       'approval_required': review,
                       'parameter_bounds': {'fan_basis_points': {'min': low * 100, 'max': high * 100}}})
    payloads = {'grants.json': {'schema_version': 'alice-permissions-grants-v1',
                              'default_effect': 'DENY', 'grants': grants},
                'subjects.json': build_subjects_payload(config),
                'terminal_keys.json': {'schema_version': 'alice-terminal-keys-v1', 'keys': keys}}
    for name, payload in payloads.items():
        (release / name).write_bytes(canonical_bytes(payload))
    manifest = build_manifest({name: digest_of(payload) for name, payload in payloads.items()},
                              model_binding={'model_ids': []}, generation=1)
    manifest.update(bundle_id='thermal-demo-000001', site_id='thermal-demo-lab',
                    release_note='Local simulation demo trust only; no hardware fan permission')
    signer = Ed25519PrivateKey.generate()
    raw, signature = sign_manifest(manifest, signer)
    (release / 'manifest.json').write_bytes(raw)
    (release / 'manifest.sig').write_bytes(signature)
    (directory / 'manifest-public.hex').write_text(signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex() + '\n')
    (directory / 'agent-keys.json').write_text(json.dumps(config, indent=2) + '\n')
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(build(args.directory))
    print('Generated local simulation trust only. Signed policy: cooling 60–90 auto, other eligible fan settings require review.')


if __name__ == '__main__':
    main()
