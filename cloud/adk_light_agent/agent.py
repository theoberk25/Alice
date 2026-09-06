"""Google ADK cloud agent for the Light-Control MCP server.

``root_agent`` is an ``LlmAgent`` (Gemini) whose tools are the two machine-metrics MCP
tools, reached over **Streamable HTTP** at the canonical, fixed URL
``http://127.0.0.1:8790/mcp`` (build 03). This is one of two clients of that
shared MCP tool layer — the other is the Goose local harness (build 02).

Auth defaults to the **free AI Studio key path** (no GCP needed):
``GOOGLE_GENAI_USE_VERTEXAI=FALSE`` + ``GOOGLE_API_KEY`` in the local ``.env``.
The Vertex/Agent-Engine path is deliberately NOT wired here — it is gated behind
the human checkpoint in docs/agent-build/01-cloud-agent.md.

Run it (from this directory's parent, ``cloud/``, with the venv active and the
metrics MCP server configured for the governed demo):

    adk web        # http://localhost:8000 -> pick machine_ops_cloud, watch Trace tab
"""

from __future__ import annotations

import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

# Load this agent's local .env (API key / model) when imported directly. `adk web`
# / `adk run` also load it; this makes plain `import` and scripts behave the same.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except ModuleNotFoundError:  # pragma: no cover - dotenv ships with google-adk
    pass

# FIXED canonical endpoint — both agents depend on it (see build docs 01/02/03).
LIGHT_MCP_URL = "http://127.0.0.1:8790/mcp"

# Model is env-overridable but defaults to a current Gemini Flash. The free
# AI Studio key serves this model on the non-Vertex path.
MODEL = os.getenv("ADK_MODEL", "gemini-flash-latest")

_INSTRUCTION = (
    "Use only get_metrics and set_fan_speed(value) through the shared metrics MCP. "
    "Read metrics before proposing a fan change. fan_speed is actual percent; "
    "fan_target_speed is the authorized target. server_temperature is Fahrenheit "
    "and power_consumption is watts; battery_pct is remaining reserve percent. "
    "You may propose fan percent only; never write temperature/power or control LEDs. "
    "ALICE governs every change. Report decision, review and application separately. "
    "HOLD/CHALLENGE, DENY and UNKNOWN do not mean the fan changed. "
    "If ok:false, inspect get_metrics and report the outcome; do not blindly retry. "
    "An uncertain retry must use the exact returned request_id, run_id and expected_revision. "
    "Do not claim actual fan speed instantly reaches its target or that simulated readings are real hardware. "
    "For a GOVERNED fan change, call submit_governed_fan_request when it is available: "
    "first call get_metrics, then pass its run_id and revision as run_id and "
    "expected_revision along with the requested fan percent. Report the decision and "
    "application (ALLOW/applied, or a CHALLENGE that is a HOLD awaiting a technician) "
    "and never resubmit the same request. "
    "For a GOVERNED action that must go through enterprise review, call "
    "submit_governed_request when it is available; report the enterprise receipt and "
    "the decision (a CHALLENGE is a HOLD awaiting a technician) and never resubmit the "
    "same request."
)

# Enterprise-first ingress is OPT-IN: only when ALICE_ENTERPRISE_INGRESS_URL is
# set do we add the governed-submission tool, so default `adk web` behaviour
# (MCP tools only) is unchanged. See docs/integration/cloud-agent-enterprise-ingress.md.
ENTERPRISE_INGRESS_URL = os.getenv("ALICE_ENTERPRISE_INGRESS_URL")

# Thermal governed path is OPT-IN too: only when ALICE_THERMAL_REQUEST_URL is set
# do we add the signed fan-request tool. In connected mode this URL is the
# enterprise ingress, which accepts the same alice-demo-fan-v1 envelope, writes
# the Wazuh receipt, and forwards the unchanged signed bytes to the live Pi. See
# docs/plans/2026-09-06-demo-part1-cloud-governed-ingress.md.
THERMAL_REQUEST_URL = os.getenv("ALICE_THERMAL_REQUEST_URL")


def submit_governed_fan_request(fan_pct: float, run_id: str, expected_revision: int) -> dict:
    """Submit one signed, governed fan change to the ALICE thermal runtime.

    Call get_metrics FIRST and pass its current run_id and revision here as
    run_id and expected_revision (the runtime rejects a stale run). The action is
    signed with this agent's provisioned fan-permitted key (ALICE_AGENT_ID /
    ALICE_AGENT_KEY_FILE) and POSTed to ALICE_THERMAL_REQUEST_URL/request, where
    ALICE decides. Returns the request_id, decision, application and raw response.
    Never resubmit; on an uncertain outcome, read get_metrics and report it.
    Args:
        fan_pct: requested fan percent, 0..100.
        run_id: the current plant run_id from get_metrics.
        expected_revision: the current plant revision from get_metrics.
    """
    from cloud.thermal_governed_client import submit_governed_fan_request as _submit

    result = _submit(fan_pct=fan_pct, run_id=run_id, expected_revision=expected_revision)
    return {
        "request_id": result.request_id,
        "client_request_id": result.client_request_id,
        "enterprise_receipt_verified": result.enterprise_receipt_verified,
        "decision": result.decision,
        "demo_application": result.demo_application,
        "http_status": result.http_status,
        "response": result.response,
    }


def submit_governed_request(state: str, target: str = "ESP-LIGHT-01") -> dict:
    """Submit a signed, governed set_light_state to the enterprise ingress.

    The action is signed with this agent's provisioned key (ALICE_AGENT_ID /
    ALICE_AGENT_KEY_FILE), recorded as an enterprise receipt in Wazuh, then
    forwarded to the Pi which decides. Returns the request_id, whether the
    enterprise receipt verified, the decision, and the raw ingress response.
    Args:
        state: desired light state, "on" or "off".
        target: ESP light id, e.g. "ESP-LIGHT-01".
    """
    # Imported lazily so agent construction never depends on the ingress module.
    from cloud.enterprise_ingress_client import submit_governed_request as _submit

    result = _submit(state=state, target=target)
    return {
        "request_id": result.request_id,
        "enterprise_receipt_verified": result.receipt_verified,
        "decision": result.decision,
        "http_status": result.http_status,
        "response": result.response,
    }



def build_agent(model: str = MODEL) -> LlmAgent:
    """Construct the cloud machine-ops agent bound to the Light MCP.

    A factory (not just a module global) so headless callers -- e.g.
    ``smoke_lights.py`` -- can pick a specific/fallback Gemini model while
    ``adk web`` keeps discovering ``root_agent`` below.
    """
    tools = [
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=LIGHT_MCP_URL, headers=(
                {"Authorization": "Bearer " + os.environ["LIGHT_MCP_TOKEN"]}
                if os.environ.get("LIGHT_MCP_TOKEN") else None)),
        )
    ]
    if ENTERPRISE_INGRESS_URL:
        tools.append(FunctionTool(submit_governed_request))
    if THERMAL_REQUEST_URL:
        tools.append(FunctionTool(submit_governed_fan_request))
    return LlmAgent(
        model=model,
        name="machine_ops_cloud",
        description="Cloud agent that observes machine metrics and proposes governed fan changes.",
        instruction=_INSTRUCTION,
        tools=tools,
    )


# `adk web` / `adk run` discover this module-level agent by name.
root_agent = build_agent()
