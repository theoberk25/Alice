"""Checkout data roots, independent of caller working directory/module depth."""
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "common" / "schemas").is_dir() and (candidate / "dcamr").is_dir():
            return candidate
    raise RuntimeError("ALICE checkout data root not found")
