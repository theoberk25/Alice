"""Cloud-agent OPERATOR client for the thermal plant lifecycle.

This lets the cloud agent bring the simulated plant (the Pi/breadboard "plant")
online and offline. It speaks the operator-role lifecycle of the thermal demo
server (``services.thermal_demo.server``): ``/demo/configure`` + ``/demo/start``
to spin up, ``/demo/stop`` to shut down, ``/demo/state`` to read status. These
routes require the OPERATOR bearer token (distinct from the per-agent tokens and
from the signed fan-request path in :mod:`cloud.thermal_governed_client`).

Demo intent (docs/demo.md "Part 1"): the plant starts OFF; a message to the
cloud agent — "good morning, all systems on!" — spins it up to the designated
levels (90 F / 60 % fan / 60 % battery, env-overridable). Turning the plant on
is an operator action, NOT a governed ALICE decision: it configures the
simulation, it does not command fans or lights through the gate.

Safety posture:
- **No hardcoded destination.** Base URL comes from arg or
  ``ALICE_THERMAL_REQUEST_URL``; nothing fires unless a caller supplies one.
- **Operator token is a secret**: read from ``ALICE_THERMAL_OPERATOR_TOKEN_FILE``
  (a mode-600 file, preferred) or ``ALICE_THERMAL_OPERATOR_TOKEN``. Never logged.
- Lifecycle only. Fan/temperature/power are never written here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error as urlerror, request as urlrequest

# Designated spin-up levels; env-overridable, default to the Part 1 story values.
DEFAULT_LEVELS = {"temperature_f": 90, "fan_pct": 60, "battery_pct": 60}


def designated_levels() -> dict[str, float]:
    def _num(name: str, default: float) -> float:
        raw = os.environ.get(name)
        return default if raw in (None, "") else float(raw)

    return {
        "temperature_f": _num("ALICE_PLANT_TEMPERATURE_F", DEFAULT_LEVELS["temperature_f"]),
        "fan_pct": _num("ALICE_PLANT_FAN_PCT", DEFAULT_LEVELS["fan_pct"]),
        "battery_pct": _num("ALICE_PLANT_BATTERY_PCT", DEFAULT_LEVELS["battery_pct"]),
    }


def _operator_token(token: str | None = None) -> str:
    if token:
        return token
    token_file = os.environ.get("ALICE_THERMAL_OPERATOR_TOKEN_FILE")
    if token_file:
        return Path(token_file).read_text().strip()
    token = os.environ.get("ALICE_THERMAL_OPERATOR_TOKEN")
    if not token:
        raise ValueError(
            "operator token required (set ALICE_THERMAL_OPERATOR_TOKEN_FILE or "
            "ALICE_THERMAL_OPERATOR_TOKEN)"
        )
    return token


def _base_url(base_url: str | None = None) -> str:
    base_url = base_url or os.environ.get("ALICE_THERMAL_REQUEST_URL")
    if not base_url:
        raise ValueError("base_url required (set ALICE_THERMAL_REQUEST_URL)")
    return base_url.rstrip("/")


def _call(method: str, base_url: str, token: str, path: str, body: dict | None, *, timeout: float) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": "Bearer " + token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urlrequest.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            return _read_json(response)
    except urlerror.HTTPError as exc:
        payload = _read_json(exc)
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {payload}") from None


def _read_json(response) -> dict[str, Any]:
    raw = response.read().decode("utf-8") if response is not None else ""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {"raw": raw}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def _summary(state: dict[str, Any], **extra: Any) -> dict[str, Any]:
    values = state.get("values") or {}
    return {
        "status": state.get("status"),
        "run_id": state.get("run_id"),
        "revision": state.get("revision"),
        "values": {k: values.get(k) for k in
                   ("temperature_f", "fan_target_pct", "fan_actual_pct", "power_w", "battery_pct")},
        **extra,
    }


def plant_state(*, base_url: str | None = None, token: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    return _call("GET", _base_url(base_url), _operator_token(token), "/demo/state", None, timeout=timeout)


def bring_all_systems_online(
    *,
    levels: dict[str, float] | None = None,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Bring the plant online at the designated levels and return its status.

    Idempotent-ish: if already RUNNING, reports it without re-configuring; if
    PAUSED, resumes; otherwise configures to ``levels`` (default: designated)
    and starts. This is an operator action, not a governed decision.
    """
    url, tok = _base_url(base_url), _operator_token(token)
    levels = levels or designated_levels()
    state = _call("GET", url, tok, "/demo/state", None, timeout=timeout)
    status = state.get("status")
    if status == "RUNNING":
        return _summary(state, action="already_online", requested_levels=levels)
    if status == "PAUSED":
        state = _call("POST", url, tok, "/demo/resume", {}, timeout=timeout)
        return _summary(state, action="resumed", requested_levels=levels)
    # From UNCONFIGURED / READY / STOPPED / EXHAUSTED: (re)configure then start.
    _call("POST", url, tok, "/demo/configure",
          {"temperature_f": levels["temperature_f"], "fan_pct": levels["fan_pct"],
           "battery_pct": levels["battery_pct"]}, timeout=timeout)
    state = _call("POST", url, tok, "/demo/start", {}, timeout=timeout)
    return _summary(state, action="configured_and_started", requested_levels=levels)


def all_systems_off(*, base_url: str | None = None, token: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    """Return the plant to the OFF baseline (stopped). No-op if already off."""
    url, tok = _base_url(base_url), _operator_token(token)
    state = _call("GET", url, tok, "/demo/state", None, timeout=timeout)
    if state.get("status") in ("READY", "RUNNING", "PAUSED", "EXHAUSTED"):
        state = _call("POST", url, tok, "/demo/stop", {}, timeout=timeout)
        return _summary(state, action="stopped")
    return _summary(state, action="already_off")


def _main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Cloud operator control for the thermal plant lifecycle.")
    p.add_argument("command", choices=["state", "on", "off"])
    p.add_argument("--url", default=None, help="plant base URL (default $ALICE_THERMAL_REQUEST_URL)")
    p.add_argument("--token", default=None, help="operator token (default file/env)")
    args = p.parse_args(argv)
    if args.command == "state":
        result = plant_state(base_url=args.url, token=args.token)
    elif args.command == "on":
        result = bring_all_systems_online(base_url=args.url, token=args.token)
    else:
        result = all_systems_off(base_url=args.url, token=args.token)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
