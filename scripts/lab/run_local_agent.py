"""Use one privately provisioned ALICE identity for metrics checks or Goose.

Setup: docs/guides/local-agent-host.md. This launcher never starts or resets
the plant. --check only lists MCP tools and reads metrics; --text runs Goose.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

AGENTS = ("cooling-agent-01", "power-agent-01", "observer-agent-01")
MCP_URL = "http://127.0.0.1:8790/mcp"
ROLE = {
    "cooling-agent-01": "You are the cooling agent. Propose bounded cooling increases only when requested.",
    "power-agent-01": "You are the power agent. Propose fan changes to reduce power only when requested.",
    "observer-agent-01": "You are the observer. Read and summarize metrics only; never propose or execute changes.",
}
RULES = (
    " Read get_metrics before a proposal. Fan values and battery are percent; "
    "temperature is Fahrenheit and power is watts. These are simulated readings. "
    "Only set_fan_speed can propose a governed change. ALICE decides; report "
    "decision, application, execution and actual fan speed separately. "
    "CHALLENGE/HOLD, DENY and UNKNOWN never imply execution. Stop after a refusal "
    "or uncertain result. Never create a new request ID to bypass a HOLD. "
    "No plant lifecycle, LED, temperature, battery or policy changes are available."
)


def credentials(agent):
    root = Path.home() / ".config/alice/agents" / agent
    path = root / "mcp.token"
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Expected a private mode-0600 MCP token file")
    token = path.read_text().strip()
    if not token or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("Invalid MCP token")
    return root, token


async def check(agent, token):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(MCP_URL, headers={"Authorization": "Bearer " + token}) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("get_metrics", {})
            if result.isError:
                raise ValueError("Metrics tool returned an error")
            metrics = result.structuredContent
            if not metrics:
                metrics = json.loads(next(block.text for block in result.content if hasattr(block, "text")))
            if set(metrics) == {"result"}:
                metrics = metrics["result"]
            return {
                "agent": agent,
                "tools": [tool.name for tool in tools.tools],
                "metrics": {key: metrics.get(key) for key in (
                    "status", "run_id", "revision", "fan_target_speed", "fan_speed",
                    "server_temperature", "power_consumption", "battery_pct", "simulation", "units")},
                "request_count": len(metrics.get("requests", [])),
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=AGENTS, default="observer-agent-01")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Read live MCP metrics without model inference or actuation")
    mode.add_argument("--text", help="Run one Goose conversation with this identity")
    args = parser.parse_args()
    try:
        root, token = credentials(args.agent)
        if args.check:
            print(json.dumps(asyncio.run(asyncio.wait_for(check(args.agent, token), timeout=20)), indent=2))
            return 0
        goose = shutil.which("goose")
        if goose is None or not (root / "config/config.yaml").is_file():
            raise ValueError("Goose binary or agent profile is missing")
        env = dict(os.environ, GOOSE_PATH_ROOT=str(root), LIGHT_MCP_TOKEN=token,
                   GOOSE_PROVIDER="ollama", GOOSE_MODEL="qwen2.5-tools",
                   OLLAMA_HOST="http://127.0.0.1:11434", GOOSE_TELEMETRY_ENABLED="false")
        return subprocess.run([
            goose, "run", "--no-session", "--max-turns", "6", "--system",
            ROLE[args.agent] + RULES, "--text", args.text,
        ], cwd=root / "work", env=env).returncode
    except (OSError, ValueError, TimeoutError, ExceptionGroup) as error:
        # Do not expose library request objects, headers, or credential contents.
        print(f"Local agent unavailable ({type(error).__name__}); check the tunnel, private token and model profile.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
