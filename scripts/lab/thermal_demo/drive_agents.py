"""Deterministic Part-2 agent driver for the governed machine-metrics MCP.

Runs ONE authenticated agent identity per process (its bearer token in
LIGHT_MCP_TOKEN), speaking Streamable-HTTP MCP to :8790/mcp exactly like the
per-agent poller. It calls the shared get_metrics()/set_fan_speed(value) tools and
acts on the returned ALICE decision -- it never assumes the fan moved and never
mints a new request id to bypass a held request.

Modes (see docs/demo.md "Part 2" and docs/plans/2026-09-06-demo-part2-...):
  cooling : read fan_target, propose target+delta, expect ALLOW+APPLIED; repeat N
            times, re-reading each step so the total is +N*delta.
  power   : read metrics, propose an absolute value (0), expect the anomaly
            CHALLENGE / ANOMALY_REVIEW_REQUIRED HOLD; fan_target must not change.

Usage (repo root, .venv, MCP reachable, token in env -- never printed):
  LIGHT_MCP_TOKEN=... .venv/bin/python -m scripts... is not importable; run by path:
  LIGHT_MCP_TOKEN=... .venv/bin/python scripts/lab/thermal_demo/drive_agents.py \
      --agent cooling-agent-01 --mode cooling --steps 3 --delta 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = os.environ.get("LIGHT_MCP_URL", "http://127.0.0.1:8790/mcp")


def _result_payload(result) -> dict:
    """Extract the tool's structured dict; a tool error is a real failure."""
    if getattr(result, "isError", False):
        # Surface the text so a refusal/binding error is legible.
        text = ""
        for block in getattr(result, "content", []) or []:
            text = getattr(block, "text", None) or text
        raise RuntimeError(f"tool returned error: {text[:300]}")
    value = getattr(result, "structuredContent", None)
    if not value:
        for block in getattr(result, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                value = json.loads(text)
                break
    if not isinstance(value, dict):
        raise RuntimeError("tool returned no structured payload")
    # FastMCP wraps a non-object return; our tools already return objects.
    return value.get("result", value) if set(value.keys()) == {"result"} else value


def _fmt(metrics: dict) -> str:
    return (f"fan_target={metrics.get('fan_target_speed')} "
            f"fan_actual={metrics.get('fan_speed')} "
            f"temp_f={_round(metrics.get('server_temperature'))} "
            f"power_w={_round(metrics.get('power_consumption'))} "
            f"battery={_round(metrics.get('battery_pct'))} "
            f"status={metrics.get('status')} rev={metrics.get('revision')}")


def _round(x):
    return round(x, 1) if isinstance(x, (int, float)) else x


async def get_metrics(session) -> dict:
    return _result_payload(await session.call_tool("get_metrics", {}))


async def set_fan_speed(session, value: float) -> dict:
    return _result_payload(await session.call_tool("set_fan_speed", {"value": value}))


async def run(agent: str, mode: str, url: str, steps: int, delta: float, value: float) -> int:
    token = os.environ.get("LIGHT_MCP_TOKEN")
    if not token:
        print("ERROR: LIGHT_MCP_TOKEN not set", file=sys.stderr)
        return 2
    headers = {"Authorization": "Bearer " + token}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            m = await get_metrics(session)
            print(f"[{agent}] start   {_fmt(m)}")
            if m.get("fan_target_speed") is None or m.get("status") != "RUNNING":
                print(f"[{agent}] ABORT: plant not RUNNING/configured", file=sys.stderr)
                return 1

            if mode == "cooling":
                ok_all = True
                for i in range(1, steps + 1):
                    m = await get_metrics(session)
                    cur = m["fan_target_speed"]
                    target = round(min(100.0, cur + delta), 2)
                    r = await set_fan_speed(session, target)
                    dec = r.get("decision")
                    app = r.get("application")
                    execu = r.get("execution")
                    applied = bool(r.get("ok")) and dec == "ALLOW" and app == "APPLIED" and execu == "COMPLETED"
                    print(f"[{agent}] step {i}: {cur:g}->{target:g}  decision={dec} "
                          f"application={app} execution={execu} ok={r.get('ok')} "
                          f"req={str(r.get('request_id'))[:12]}")
                    if not applied:
                        ok_all = False
                        print(f"[{agent}] step {i} NOT applied as ALLOW; stopping. detail={json.dumps({k: r.get(k) for k in ('decision','application','execution','review_state','error')})}",
                              file=sys.stderr)
                        break
                    # Wait for the applied setpoint before the next proposal.
                    for _ in range(50):
                        m = await get_metrics(session)
                        if m["fan_target_speed"] == target:
                            break
                        await asyncio.sleep(0.1)
                m = await get_metrics(session)
                print(f"[{agent}] end     {_fmt(m)}")
                return 0 if ok_all else 1

            if mode == "power":
                before = m["fan_target_speed"]
                r = await set_fan_speed(session, value)
                dec = r.get("decision")
                app = r.get("application")
                rev_state = r.get("review_state")
                held = (r.get("ok") is False) and dec == "CHALLENGE"
                print(f"[{agent}] cut {before:g}->{value:g}  ok={r.get('ok')} decision={dec} "
                      f"application={app} review_state={rev_state} "
                      f"req={str(r.get('request_id'))[:12]} audit={str(r.get('audit_request_id'))[:12]}")
                print(f"[{agent}] raw={json.dumps({k: r.get(k) for k in ('ok','decision','application','execution','review_state','request_id','audit_request_id','error')})}")
                m = await get_metrics(session)
                print(f"[{agent}] after   {_fmt(m)}")
                unchanged = m["fan_target_speed"] == before
                if held and unchanged:
                    print(f"[{agent}] HOLD confirmed: fan_target stayed {before:g}")
                    return 0
                print(f"[{agent}] UNEXPECTED: held={held} unchanged={unchanged}", file=sys.stderr)
                return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Part-2 governed-MCP agent driver (one identity per process).")
    ap.add_argument("--agent", required=True, help="agent label for logs (identity comes from the token)")
    ap.add_argument("--mode", required=True, choices=("cooling", "power"))
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--steps", type=int, default=3, help="cooling: number of +delta steps")
    ap.add_argument("--delta", type=float, default=10.0, help="cooling: fan increase per step")
    ap.add_argument("--value", type=float, default=0.0, help="power: absolute fan value to propose")
    args = ap.parse_args()
    return asyncio.run(run(args.agent, args.mode, args.url, args.steps, args.delta, args.value))


if __name__ == "__main__":
    raise SystemExit(main())
