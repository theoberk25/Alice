"""Compatibility namespace for developer tools housed in scripts/lab.

Keep python -m lab.* and imports stable; there is only one implementation.
"""
from common.repository_paths import repository_root

__path__ = [str(repository_root() / "scripts" / "lab")]
