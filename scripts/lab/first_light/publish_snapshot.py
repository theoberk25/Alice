"""Package a verified first-light release as an immutable SQL input snapshot.

Uses existing signed release bytes and trust; does not generate keys, fetch
enterprise data, activate a release or replace the Pi ledger. See AGENTS.md and
docs/integration/release-snapshot.md.
"""
import argparse
from pathlib import Path

from dcamr.packages.release_snapshot import publish_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--trust-key', required=True, type=Path)
    args = parser.parse_args()
    trusted = bytes.fromhex(args.trust_key.read_text().strip())
    release = publish_snapshot(args.release, args.output, trusted)
    print(f"Published signed first-light SQL snapshot: {args.output}")
    print(f"Release {release.bundle_id}, generation {release.generation}, manifest {release.manifest_sha256}")


if __name__ == '__main__':
    main()
