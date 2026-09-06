"""Light-Control MCP server (FastMCP, Streamable HTTP).

Serves four stable tools — ``list_machines``, ``get_status``, ``set_machine``,
``blink`` — over Streamable HTTP at ``http://<host>:<port>/mcp`` so that both a
local Goose agent and a (possibly remote) cloud agent can share one tool layer.

Run from the repo root with the ``.venv`` active:

    python -m services.light_mcp.server

Config: machines come from ``machines.yaml``; the driver is chosen by
``LIGHT_DRIVER`` (mock | serial). See docs/agent-build/03-light-mcp.md.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

from .drivers import LightDriver, make_driver

logging.basicConfig(
    level=os.environ.get("LIGHT_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("light_mcp.server")

# --- Config (env-overridable) -------------------------------------------------
HOST = os.environ.get("LIGHT_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("LIGHT_MCP_PORT", "8790"))
DRIVER_KIND = os.environ.get("LIGHT_DRIVER", "mock")
SERIAL_PORT = os.environ.get("LIGHT_SERIAL_PORT") or None
SERIAL_BAUD = int(os.environ.get("LIGHT_SERIAL_BAUD", "115200"))
CONFIG_PATH = os.environ.get(
    "LIGHT_MACHINES_CONFIG", str(Path(__file__).with_name("machines.yaml"))
)


def _coerce_state(value: object) -> str:
    """Normalize a state to a string.

    Defensive against the YAML 1.1 footgun where bare ``on``/``off`` parse as
    booleans: ``True`` -> ``"on"``, ``False`` -> ``"off"``; everything else is
    ``str()``-ed. Keeps the string state contract even if the YAML is unquoted.
    """
    if value is True:
        return "on"
    if value is False:
        return "off"
    return str(value)


class _StatesAsStringsLoader(yaml.SafeLoader):
    """YAML loader that does NOT coerce on/off/yes/no/true/false to booleans.

    machines.yaml uses bare tokens like ``on``/``off`` as *state names*. Under
    YAML 1.1 (PyYAML) those bare words resolve to Python booleans, so
    ``allowed_states: [on, off]`` would load as ``[True, False]`` and a string
    state like ``"on"`` sent by an agent would never match. Dropping only the
    implicit bool resolver keeps these as the strings the tool contract requires;
    ints, floats and null still resolve normally. Scoped to this subclass so the
    rest of the repo's ``yaml.safe_load`` behavior is untouched.
    """


_StatesAsStringsLoader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for (tag, rx) in resolvers if tag != "tag:yaml.org,2002:bool"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _load_machines(path: str):
    """Return (ordered ids, allowed_states, default state, target, label) by id.

    ``target`` (the signed ESP-LIGHT-0N target for the esp driver) defaults to
    the machine id; ``label`` (verified LED color) is optional.
    """
    data = yaml.load(Path(path).read_text(), Loader=_StatesAsStringsLoader) or {}
    order: list[str] = []
    allowed: dict[str, list[str]] = {}
    defaults: dict[str, str] = {}
    targets: dict[str, str] = {}
    labels: dict[str, str] = {}
    for entry in data.get("machines", []):
        mid = str(entry["id"])
        states = [_coerce_state(s) for s in entry.get("allowed_states", ["on", "off"])]
        order.append(mid)
        allowed[mid] = states
        default = entry.get("default", states[0] if states else "off")
        defaults[mid] = _coerce_state(default)
        targets[mid] = str(entry.get("target", mid))
        if entry.get("label") is not None:
            labels[mid] = str(entry["label"])
    return order, allowed, defaults, targets, labels


ORDER, ALLOWED, DEFAULTS, TARGETS, LABELS = _load_machines(CONFIG_PATH)

# The driver is the single source of truth for state. Tools call it; the server
# never keeps a second copy of machine state.
driver: LightDriver = make_driver(
    DRIVER_KIND, DEFAULTS, serial_port=SERIAL_PORT, serial_baud=SERIAL_BAUD, targets=TARGETS
)

mcp = FastMCP("light-control", host=HOST, port=PORT)


@mcp.tool()
def list_machines() -> dict:
    """List every machine with its current state and allowed states."""
    states = driver.get_all()
    machines = []
    for mid in ORDER:
        entry = {
            "id": mid,
            "state": states.get(mid, "unknown"),
            "allowed_states": ALLOWED.get(mid, ["on", "off"]),
        }
        if mid in LABELS:
            entry["label"] = LABELS[mid]
        machines.append(entry)
    return {"machines": machines}


@mcp.tool()
def get_status(machine_id: str | None = None) -> dict:
    """Get one machine's state, or all machines' states if ``machine_id`` is omitted."""
    states = driver.get_all()
    if machine_id is None:
        return {"machines": {mid: states.get(mid, "unknown") for mid in ORDER}}
    if machine_id not in ALLOWED:
        return {"error": f"unknown machine_id {machine_id!r}", "known": ORDER}
    return {"machine_id": machine_id, "state": states.get(machine_id, "unknown")}


@mcp.tool()
def set_machine(machine_id: str, state: str) -> dict:
    """Set ``machine_id`` to ``state``.

    Returns ``ok: false`` with an error (no crash) if the machine is unknown or
    ``state`` is not in that machine's ``allowed_states``.
    """
    if machine_id not in ALLOWED:
        return {
            "machine_id": machine_id,
            "state": state,
            "ok": False,
            "error": f"unknown machine_id {machine_id!r}",
        }
    if state not in ALLOWED[machine_id]:
        return {
            "machine_id": machine_id,
            "state": state,
            "ok": False,
            "error": f"state {state!r} not allowed for {machine_id}; allowed={ALLOWED[machine_id]}",
        }
    try:
        driver.set(machine_id, state)
    except Exception as exc:
        # e.g. a governed ALICE DENY, or a hardware/transport refusal. A clean
        # ok:false result the agent can report, not a tool crash.
        return {"machine_id": machine_id, "state": state, "ok": False, "error": str(exc)}
    return {"machine_id": machine_id, "state": state, "ok": True}


@mcp.tool()
def blink(machine_id: str, count: int = 3, interval_ms: int = 300) -> dict:
    """Blink ``machine_id`` ``count`` times (transient); state returns to prior."""
    if machine_id not in ALLOWED:
        return {
            "machine_id": machine_id,
            "ok": False,
            "error": f"unknown machine_id {machine_id!r}",
        }
    try:
        driver.blink(machine_id, count, interval_ms)
    except Exception as exc:
        return {"machine_id": machine_id, "ok": False, "error": str(exc)}
    return {"machine_id": machine_id, "ok": True}


def main() -> None:
    path = getattr(mcp.settings, "streamable_http_path", "/mcp")
    log.info(
        "light-control MCP starting: driver=%s host=%s port=%s path=%s config=%s",
        DRIVER_KIND, HOST, PORT, path, CONFIG_PATH,
    )
    log.info("machines: %s", ORDER)
    log.info("serving streamable-http at http://%s:%s%s", HOST, PORT, path)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
