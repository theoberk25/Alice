"""Find console resources from a checkout, independent of script depth and cwd."""
import json
from pathlib import Path


def repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        manifest = candidate / "package.json"
        if manifest.is_file() and json.loads(manifest.read_text())["name"] == "alice-technician-console":
            return candidate
    raise RuntimeError("ALICE console checkout not found")


REPOSITORY_ROOT = repository_root()
CONSOLE_ROOT = REPOSITORY_ROOT
