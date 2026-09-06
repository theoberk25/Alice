"""Read-only cloud smoke test for the machine-metrics MCP; no fan execution.

`adk web` is a UI; this is the scriptable equivalent. It drives ``root_agent``
through one prompt with the ADK Runner and asserts the agent actually called
``get_metrics`` on the shared MCP. It really calls Gemini, so it also exercises
the internet-dependent path that the router-unplug demo severs.

Run from the repo root with the venv active and the Light MCP up (:8790):

    PYTHONPATH="$(pwd)" .venv/bin/python -m cloud.adk_light_agent.smoke_lights

Gemini Flash occasionally returns 503 (high demand); this retries across a small
set of current models before giving up.
"""

from __future__ import annotations

import asyncio
import os
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import build_agent  # see agent.py

PROMPT = (
    "Read current machine metrics and report fan speed, temperature and power. Do not change any setting. "
    "Use the tools; keep it brief."
)
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-3.6-flash", "gemini-2.0-flash"]


async def _run_once(model: str) -> tuple[list[tuple[str, dict]], str]:
    agent = build_agent(model=model)
    sess = InMemorySessionService()
    s = await sess.create_session(app_name="smoke", user_id="u")
    runner = Runner(app_name="smoke", agent=agent, session_service=sess)
    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    tool_calls: list[tuple[str, dict]] = []
    final = ""
    async for event in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        content = getattr(event, "content", None)
        for part in (getattr(content, "parts", None) or []):
            fc = getattr(part, "function_call", None)
            if fc:
                tool_calls.append((fc.name, dict(fc.args or {})))
            if getattr(part, "text", None) and getattr(event, "is_final_response", lambda: False)():
                final = part.text.strip()
    return tool_calls, final


async def main() -> int:
    models = [os.getenv("ADK_MODEL")] if os.getenv("ADK_MODEL") else FALLBACK_MODELS
    last_err: Exception | None = None
    for model in models:
        try:
            tool_calls, final = await _run_once(model)
        except Exception as exc:  # 503/high-demand etc. -> try next model
            last_err = exc
            print(f"[{model}] {type(exc).__name__}: {str(exc)[:120]} -- trying next", file=sys.stderr)
            await asyncio.sleep(2)
            continue
        print(f"MODEL={model}")
        print("TOOL CALLS:")
        for name, args in tool_calls:
            print(f"  - {name}({args})")
        print("FINAL:", (final or "")[:300])
        if any(n == "get_metrics" for n, _ in tool_calls):
            print("\nOK: cloud agent reached the MCP and called get_metrics.")
            return 0
        print("FAIL: agent ran but never called get_metrics.", file=sys.stderr)
        return 1
    print(f"FAIL: all models unavailable. Last error: {last_err}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
