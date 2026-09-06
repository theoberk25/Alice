"""Machine-metrics MCP server (FastMCP, Streamable HTTP).

Repurposed from light control: the MCP no longer drives lights. It now reads and
writes a JSON state file **on the Raspberry Pi** holding three numbers —
``fan_speed``, ``server_temperature``, ``power_consumption`` (see state.py). The
agent may read all three and may set **only** ``fan_speed``.

Two tools (stable contract for both agents):
    get_metrics()          -> {"fan_speed", "server_temperature", "power_consumption"}
    set_fan_speed(value)   -> {"ok", "fan_speed", "metrics"} | {"ok": false, "error"}

Endpoint is unchanged: Streamable HTTP at ``http://127.0.0.1:8790/mcp`` so both a
local Goose agent and a (possibly remote) cloud agent share one tool layer. Run
from the repo root with the ``.venv`` active::

    python -m services.light_mcp.server

Version note: targets the v1 MCP SDK (``mcp.server.fastmcp.FastMCP``), pinned as
``mcp<2`` in requirements.txt — ``pip install mcp`` now resolves to 2.x, where
FastMCP was renamed to MCPServer and this import would fail. On v1,
``settings.streamable_http_path`` defaults to ``/mcp``.

NOTE: the package/dir is still named ``light_mcp`` and the port env vars keep the
``LIGHT_MCP_`` prefix, to preserve the import path, URL and deploy wiring the
other build files depend on. Only the tool surface changed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .state import METRIC_KEYS, MachineState

logging.basicConfig(
    level=os.environ.get("LIGHT_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("light_mcp.server")

# --- Config (env-overridable) -------------------------------------------------
HOST = os.environ.get("LIGHT_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("LIGHT_MCP_PORT", "8790"))

# The Pi state file. Local relative default for dev; set MACHINE_STATE_FILE to the
# real Pi path in deployment (see services/systemd/light-mcp.service).
_DEFAULT_STATE = str(Path(__file__).with_name("machine_state.json"))
STATE_FILE = os.environ.get("MACHINE_STATE_FILE", _DEFAULT_STATE)

FAN_SPEED_MIN = float(os.environ.get("FAN_SPEED_MIN", "0"))
FAN_SPEED_MAX = float(os.environ.get("FAN_SPEED_MAX", "100"))

# Seed values used only when the state file does not exist yet.
SEEDS = {
    "fan_speed": float(os.environ.get("SEED_FAN_SPEED", "50")),
    "server_temperature": float(os.environ.get("SEED_SERVER_TEMPERATURE", "45")),
    "power_consumption": float(os.environ.get("SEED_POWER_CONSUMPTION", "300")),
}

STATE = MachineState(
    STATE_FILE, seeds=SEEDS, fan_min=FAN_SPEED_MIN, fan_max=FAN_SPEED_MAX
)

mcp = FastMCP("machine-metrics", host=HOST, port=PORT)


@mcp.tool()
def get_metrics() -> dict:
    """Read the current machine metrics from the Pi state file.

    Returns all three numbers: ``fan_speed``, ``server_temperature`` and
    ``power_consumption``. Always reflects the file on disk (temperature and
    power may be updated externally).
    """
    return STATE.read()


@mcp.tool()
def set_fan_speed(value: float) -> dict:
    """Set the fan speed — the only metric the agent may write.

    Writes ``fan_speed`` to the Pi state file (preserving temperature and power).
    Returns ``{"ok": true, "fan_speed", "metrics"}`` on success, or a clean
    ``{"ok": false, "value", "error"}`` (no crash) if ``value`` is not a number
    or is outside ``[FAN_SPEED_MIN, FAN_SPEED_MAX]``.
    """
    try:
        metrics = STATE.set_fan_speed(value)
    except ValueError as exc:
        return {"ok": False, "value": value, "error": str(exc)}
    return {"ok": True, "fan_speed": metrics["fan_speed"], "metrics": metrics}


def main() -> None:
    path = getattr(mcp.settings, "streamable_http_path", "/mcp")
    log.info(
        "machine-metrics MCP starting: host=%s port=%s path=%s state=%s metrics=%s "
        "fan_range=[%s,%s]",
        HOST, PORT, path, STATE_FILE, list(METRIC_KEYS), FAN_SPEED_MIN, FAN_SPEED_MAX,
    )
    log.info("serving streamable-http at http://%s:%s%s", HOST, PORT, path)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
