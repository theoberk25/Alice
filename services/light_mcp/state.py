"""File-backed machine-state store for the Light/Metrics MCP server.

The MCP no longer drives lights directly. Its public tool reads a JSON state
file **on the Raspberry Pi** holding three numbers:

    {"fan_speed": <num>, "server_temperature": <num>, "power_consumption": <num>}

The agent may READ all three (``get_metrics``) and requests fan changes through
ALICE. Only ALICE's protected controller writes ``fan_speed`` after authorization.
``server_temperature`` and ``power_consumption`` are treated
as externally-owned (e.g. updated by a simulator or sensor loop on the Pi), so
reads always hit disk rather than caching, and writes preserve those fields.

The file path is the dev→Pi seam: a local path during development, the real Pi
path in deployment (``MACHINE_STATE_FILE``). Writes are atomic (temp file +
``os.replace``) so a concurrent reader never sees a torn file.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path

log = logging.getLogger("light_mcp.state")

#: The three metrics, in a stable order. Only ``fan_speed`` is agent-writable.
METRIC_KEYS = ("fan_speed", "server_temperature", "power_consumption")


class MachineState:
    """Atomic, locked JSON store for the three machine metrics."""

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        seeds: dict[str, float],
        fan_min: float,
        fan_max: float,
    ) -> None:
        self.path = Path(path)
        self._seeds = {k: seeds[k] for k in METRIC_KEYS}
        self.fan_min = fan_min
        self.fan_max = fan_max
        self._lock = threading.Lock()
        self._ensure()

    # -- internals -----------------------------------------------------------
    def _ensure(self) -> None:
        """Create the file with seed values if it does not exist yet."""
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(dict(self._seeds))
            log.info("MachineState seeded %s = %s", self.path, self._seeds)

    def _atomic_write(self, data: dict) -> None:
        tmp = tempfile.NamedTemporaryFile(
            "w", dir=str(self.path.parent), delete=False, suffix=".tmp"
        )
        try:
            json.dump(data, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            tmp.close()
        os.replace(tmp.name, self.path)  # atomic on POSIX

    def _read_locked(self) -> dict:
        """Read + normalize the file. Caller must hold ``self._lock``."""
        try:
            raw = json.loads(self.path.read_text())
            if not isinstance(raw, dict):
                raise ValueError("state file is not a JSON object")
        except (FileNotFoundError, ValueError, OSError) as exc:
            log.warning("state read failed (%s); reseeding %s", exc, self.path)
            raw = dict(self._seeds)
            self._atomic_write(raw)
        # Keep only the known metrics; fall back to seeds for any missing key.
        return {k: raw.get(k, self._seeds[k]) for k in METRIC_KEYS}

    # -- public API ----------------------------------------------------------
    def read(self) -> dict:
        """Return the current ``{fan_speed, server_temperature, power_consumption}``."""
        with self._lock:
            return self._read_locked()

    def set_fan_speed(self, value: float) -> dict:
        """Write ``fan_speed`` only, preserving the other fields. Returns the new
        full metrics dict. Raises ``ValueError`` (never crashes) if ``value`` is
        not a number or is outside ``[fan_min, fan_max]``."""
        # bool is an int subclass — reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"fan_speed must be a number, got {value!r}")
        if not (self.fan_min <= value <= self.fan_max):
            raise ValueError(
                f"fan_speed {value} out of range [{self.fan_min}, {self.fan_max}]"
            )
        with self._lock:
            data = self._read_locked()
            data["fan_speed"] = value
            self._atomic_write(data)
            log.info("set_fan_speed -> %s (state=%s)", value, self.path)
            return data
