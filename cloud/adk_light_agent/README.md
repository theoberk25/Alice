> **Current tools and authentication:** [machine-metrics integration](../../docs/guides/machine-metrics-integration.md). The agent now uses `get_metrics` / `set_fan_speed(value)` and `LIGHT_MCP_TOKEN`. Earlier light-tool examples below are historical. The `smoke_lights` entry point is retained but now performs a read-only metrics check.

# ADK cloud agent — `machine_ops_cloud`

A Google **ADK** (`LlmAgent`, Gemini) agent that controls the machine lights by
calling the [Light-Control MCP server](../../services/light_mcp/) over Streamable
HTTP at the fixed URL **`http://127.0.0.1:8790/mcp`**. It is one of two clients
of that shared tool layer; the other is the Goose local harness (build 02).

Spec: [docs/agent-build/01-cloud-agent.md](../../docs/agent-build/01-cloud-agent.md).
Repo rules: [AGENTS.md](../../AGENTS.md).

## Install

```bash
.venv/bin/python -m pip install -r cloud/adk_light_agent/requirements.txt
```

Installed/verified: `google-adk 2.8.0`, `google-genai 2.22.0`, `mcp 1.29.1`
(v1 FastMCP client), Python 3.14.

## Auth — free path (default, no GCP)

1. Get an **AI Studio** key: <https://aistudio.google.com/apikey>.
2. Put it in the local, gitignored `.env` (copy from `.env.example`):
   ```
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   GOOGLE_API_KEY=<your key>
   ```
This runs the whole agent + the `adk web` visualization at $0.

> The **Vertex AI / Agent Engine** (GCP console) path is intentionally NOT wired
> here. It is a **paid managed runtime** and is gated behind the ⛔ human
> checkpoint in the build doc — do not enable `GOOGLE_GENAI_USE_VERTEXAI=TRUE`
> or set a project until the account/project/billing questions are answered.

## Run + verify (free/local)

Start the Light MCP server (build 03) in mock mode first, then:

```bash
cd cloud
adk web            # opens http://localhost:8000
```

Select **`machine_ops_cloud`**, then prompt:

> List machines, then turn machine-03 on.

Expected: the agent calls `list_machines` then `set_machine("machine-03","on")`;
the MCP MockDriver logs the calls; the **Trace tab** shows `execute_tool` spans
in a waterfall. `blink` and `get_status` prompts behave correspondingly.

## Implementation notes

- Toolset: `McpToolset(connection_params=StreamableHTTPConnectionParams(url=...))`
  — the current (non-deprecated) ADK symbol; the connection URL is fixed.
- The agent is model- and driver-agnostic: swapping the MCP's MockDriver for real
  PCB hardware later is invisible to this agent, exactly like the Goose harness.
