"""Google ADK cooling agent for the governed machine-metrics MCP server.

``root_agent`` is an ``LlmAgent`` (Gemini) whose tools are the four Light MCP
tools, reached over **Streamable HTTP** at the canonical, fixed URL
``http://127.0.0.1:8795/mcp`` (build 03). Each physical agent deployment runs
its own loopback MCP instance with its own ALICE signing identity.

Auth defaults to the **free AI Studio key path** (no GCP needed):
``GOOGLE_GENAI_USE_VERTEXAI=FALSE`` + ``GOOGLE_API_KEY`` in the local ``.env``.
The Vertex/Agent-Engine path is deliberately NOT wired here — it is gated behind
the human checkpoint in docs/agent-build/01-cloud-agent.md.

Run it (from this directory's parent, ``cloud/``, with the venv active and the
Light MCP server up in mock mode):

    adk web        # http://localhost:8000 -> pick machine_ops_cloud, watch Trace tab
"""

from __future__ import annotations

import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

# Load this agent's local .env (API key / model) when imported directly. `adk web`
# / `adk run` also load it; this makes plain `import` and scripts behave the same.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except ModuleNotFoundError:  # pragma: no cover - dotenv ships with google-adk
    pass

# FIXED canonical endpoint — both agents depend on it (see build docs 01/02/03).
LIGHT_MCP_URL = os.getenv("LIGHT_MCP_URL", "http://127.0.0.1:8795/mcp")

# Model is env-overridable but defaults to a current Gemini Flash. The free
# AI Studio key serves this model on the non-Vertex path.
MODEL = os.getenv("ADK_MODEL", "gemini-flash-latest")

_INSTRUCTION = (
    "You are the cooling agent for the server room. Read get_metrics before acting. "
    "When temperature requires more cooling, request small set_fan_speed changes, "
    "normally no more than 10 percentage points at a time. Never invent metric values, "
    "and report ALLOW, CHALLENGE/HOLD, or DENY exactly as the tool returns it. "
    "If a tool returns ok:false, "
    "report the error instead of retrying blindly."
)


def build_agent(model: str = MODEL) -> LlmAgent:
    """Construct the cloud machine-ops agent bound to the Light MCP.

    A factory (not just a module global) so headless callers -- e.g.
    ``smoke_lights.py`` -- can pick a specific/fallback Gemini model while
    ``adk web`` keeps discovering ``root_agent`` below.
    """
    return LlmAgent(
        model=model,
        name="machine_ops_cloud",
        description="Cloud cooling agent that requests governed server-room fan changes.",
        instruction=_INSTRUCTION,
        tools=[
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(url=LIGHT_MCP_URL),
            )
        ],
    )


# `adk web` / `adk run` discover this module-level agent by name.
root_agent = build_agent()
