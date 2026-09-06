"""Per-agent metrics poller for the machine-metrics MCP.

Each agent (the cloud ADK agent and the local Goose agent) runs ONE of these. It
opens a single Streamable-HTTP MCP session and calls ``get_metrics`` on a fixed
interval (default 0.1s = 10 Hz), pulling all three values — ``fan_speed``,
``server_temperature``, ``power_consumption``. Every sample is written to a
per-agent snapshot file (so the agent can read the latest values without its own
round-trip) and an INFO heartbeat is logged about once per second.

"cron every 0.1s" is not expressible in real cron (1-minute minimum), so this is
a long-running loop, deployed as a systemd service — the sub-second analog of a
cron job. See services/systemd/light-metrics-poller-*.service.

Usage (repo root, .venv active; MCP server already running):
    python -m services.light_mcp.poller --agent cloud
    python -m services.light_mcp.poller --agent local --url http://127.0.0.1:8790/mcp --interval 0.1
    python -m services.light_mcp.poller --agent cloud --once      # single poll, for tests
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import math
import re
import os
import signal
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

log = logging.getLogger("light_mcp.poller")

DEFAULT_URL = os.environ.get("LIGHT_MCP_URL", "http://127.0.0.1:8790/mcp")
DEFAULT_INTERVAL = float(os.environ.get("METRICS_POLL_INTERVAL", "0.1"))


def _payload(result) -> dict:
    """Never publish tool failures or incomplete metrics as a healthy sample."""
    if getattr(result, 'isError', False):
        raise ValueError('Metrics tool returned an error')
    value = getattr(result, 'structuredContent', None)
    if not value:
        for block in result.content:
            text = getattr(block, 'text', None)
            if text:
                value = json.loads(text)
                break
    if not isinstance(value, dict) or not all(k in value for k in ('fan_speed', 'server_temperature', 'power_consumption')):
        raise ValueError('Incomplete metrics')
    for key in ('fan_speed', 'server_temperature', 'power_consumption'):
        number = value[key]
        if number is not None and (type(number) not in (int, float) or not math.isfinite(number)):
            raise ValueError('Invalid metric value')
    return value


def _snapshot_path(agent: str, out: str | None) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', agent):
        raise ValueError('Invalid poller agent label')
    if out:
        return Path(out)
    return Path(__file__).with_name(f"poller_{agent}_latest.json")


async def poll(agent: str, url: str, interval: float, out: str | None, once: bool) -> int:
    if not math.isfinite(interval) or not .01 <= interval <= 60:
        raise ValueError('Poll interval must be between .01 and 60 seconds')
    snap = _snapshot_path(agent, out)
    snap.parent.mkdir(parents=True, exist_ok=True)
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    log.info("poller[%s] connecting to %s (interval=%.3fs, snapshot=%s)", agent, url, interval, snap)
    token = os.environ.get('LIGHT_MCP_TOKEN')
    headers = {'Authorization': 'Bearer ' + token} if token else None
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            n = 0
            # ~1s heartbeat regardless of interval.
            heartbeat_every = max(1, round(1.0 / interval)) if interval > 0 else 1
            while not stop.is_set():
                t0 = time.monotonic()
                try:
                    metrics = _payload(await session.call_tool("get_metrics", {}))
                    sample = {"agent": agent, "ts": time.time(), "available": True,
                              "max_age_seconds": 1, "metrics": metrics}
                except Exception:
                    sample = {"agent": agent, "ts": time.time(), "available": False,
                              "max_age_seconds": 1, "metrics": None}
                    tmp = snap.with_suffix(snap.suffix + ".tmp")
                    tmp.write_text(json.dumps(sample) + "\n")
                    os.replace(tmp, snap)
                    raise
                tmp = snap.with_suffix(snap.suffix + ".tmp")
                tmp.write_text(json.dumps(sample) + "\n")
                os.replace(tmp, snap)
                n += 1
                if once:
                    log.info("poller[%s] sample: %s", agent, json.dumps(metrics))
                    return 0
                if n % heartbeat_every == 0:
                    log.info("poller[%s] #%d %s", agent, n, json.dumps(metrics))
                else:
                    log.debug("poller[%s] #%d %s", agent, n, json.dumps(metrics))
                # Keep a steady cadence even if the call took time.
                await asyncio.sleep(max(0.0, interval - (time.monotonic() - t0)))
    log.info("poller[%s] stopped after %d samples", agent, n)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-agent 0.1s metrics poller for the machine-metrics MCP.")
    ap.add_argument("--agent", required=True, help="agent label, e.g. 'cloud' or 'local'")
    ap.add_argument("--url", default=DEFAULT_URL, help=f"MCP Streamable-HTTP URL (default {DEFAULT_URL})")
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="seconds between polls (default 0.1)")
    ap.add_argument("--out", default=None, help="snapshot file path (default poller_<agent>_latest.json beside this module)")
    ap.add_argument("--once", action="store_true", help="poll once and exit (for tests)")
    args = ap.parse_args()

    logging.basicConfig(
        level=os.environ.get("POLLER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(poll(args.agent, args.url, args.interval, args.out, args.once))


if __name__ == "__main__":
    raise SystemExit(main())
