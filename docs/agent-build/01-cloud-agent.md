> **Current contract:** [machine-metrics integration](../guides/machine-metrics-integration.md) supersedes the light tools, driver-selection, prompts and acceptance steps below. Use `get_metrics` / `set_fan_speed`, per-agent bearer credentials, and the governed backend. Earlier light-only build instructions are retained as historical context; model-provider setup remains separate.

# Build 01 — Cloud Agent Framework (Google ADK + Gemini)

> Build order: build `03-light-mcp.md` first and confirm it passes. This agent is a client of that MCP server. Can be built independently of the Goose harness (file 02).

## Session orientation (read first)
Working inside the **Alice** repo. Read `AGENTS.md` and `current.md` per `CLAUDE.md`. Python runs in the repo `.venv`; config via `.env`.

## Why Google ADK + Gemini (decided)
Chosen because it uniquely satisfies **both** constraints for this demo:
- **Free to build/run:** the Agent Development Kit (ADK) is open-source (Apache-2.0) and the Gemini API has a real **free tier** via a Google **AI Studio** key. The whole cloud agent can run at **$0** for the demo.
- **A real DoD agent provider:** Google is a CDAO $200M frontier-AI awardee, and **Gemini for Government** is the first enterprise AI on **GenAI.mil** (rolled out to ~3M DoD personnel, IL5). The demo line: *"the cloud agent runs on the platform DoD just put on 3 million desktops."*
- ADK is **model-agnostic and MCP-native**, so it reuses the exact same Light-Control MCP tool layer as the local Goose agent.

(If the user ever prefers OpenAI: the OpenAI Agents SDK is the equivalent — open-source, MCP-native, $200M DoD contract + $1/agency GSA deal. Keep Google as default unless told otherwise.)

## Goal
A Google ADK agent that controls the machine lights by calling the Light-Control MCP server (file 03), viewable in a UI — free locally via `adk web`, and optionally in the **GCP console** via Vertex AI Agent Engine.

## Location
```
Alice/cloud/adk_light_agent/
├── __init__.py
├── agent.py     # root_agent: LlmAgent(model=gemini-*, tools=[light MCP toolset])
├── .env         # local only (gitignored) — API key / project config
└── README.md
```
(Placed under `cloud/` alongside the other cloud integrations.)

## Steps
1. **Install:** `pip install google-adk` (and `google-genai`). Pin versions in a requirements file.
2. **Define the agent** in `agent.py`: an `LlmAgent` with model `gemini-flash-latest` (or a current `gemini-2.5-flash`), a role instruction framing it as the machine-operations agent, and its tools = the Light MCP over Streamable HTTP:
   ```python
   from google.adk.agents import LlmAgent
   from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

   root_agent = LlmAgent(
       model="gemini-flash-latest",
       name="machine_ops_cloud",
       instruction="You operate base/plant machines via the light_control tools. "
                    "Query status before acting; confirm state changes.",
       tools=[MCPToolset(connection_params=StreamableHTTPConnectionParams(
           url="http://127.0.0.1:8790/mcp"))],
   )
   ```
   > ADK's MCP connection-params class name has shifted across versions (`StreamableHTTPConnectionParams` / `StreamableHTTPServerParams` / `SseServerParams`). Verify the exact symbol in the installed `google.adk.tools.mcp_tool` and adjust. Target URL is fixed: **`http://127.0.0.1:8790/mcp`**.
3. **Auth — default to the FREE path first (no GCP needed):**
   - Get an **AI Studio** API key. In `.env`: `GOOGLE_API_KEY=...` and `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.
   - This path needs **no GCP account at all** and is enough for the whole agent + the `adk web` visualization.

## ⛔ HUMAN CHECKPOINT — ask the user before any GCP/Vertex/billing step
Do **not** guess GCP settings. Before deploying anything to Google Cloud, **stop and ask the user**:
1. **Which path?** Free AI Studio key (default, $0, no GCP) — or run through their existing GCP project (needed only for the GCP-console visuals)?
2. If GCP: is the account **personal** or **work/org-managed**? (Org-managed may block API enablement or billing without an admin.)
3. If GCP: **project ID**, **region**, and confirm **billing is enabled** and they're **authorized** to incur Agent Engine charges on that project.
Only after clear answers, proceed to the Vertex path below. Record the answers in `.env`/README; never hardcode a project ID from memory.

## Visualization
- **Free / local (do this for the demo by default):** `adk web` → opens `http://localhost:8000`. Use the **Trace tab** — the agent's calls to `set_machine`/`blink` appear as `execute_tool` spans in a waterfall. Also a chat playground + Events tab. Works with the free AI Studio key.
- **GCP console (only after the checkpoint):** deploy the same agent to **Vertex AI Agent Engine** with `enable_tracing=True`. In the existing project's Vertex AI console you then get: a dashboard (tokens/latency/error rates/tool calls), a **Traces tab** (tool auditing + orchestrator view), and a **Playground**; traces/logs flow to Cloud Trace / Cloud Logging / Monitoring. For the Vertex path set `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and auth via `gcloud auth application-default login`. **Agent Engine is a paid managed runtime** — that is what the billing question above is about.

## Acceptance / verification
With the Light MCP server (file 03) running in `mock` mode and the free AI Studio key set:
1. `adk web`, select `machine_ops_cloud`. Prompt: *"List machines, then turn machine-03 on."* → the agent calls `list_machines` then `set_machine("machine-03","on")`; MCP MockDriver logs the calls; Trace tab shows the `execute_tool` spans.
2. `blink` and `get_status` prompts behave correctly.
3. (Optional, only after the human checkpoint) deploy to Agent Engine and confirm the same run appears in the GCP console with traces.

## Notes
- Same MCP, same tools as the Goose local agent — the only differences are the harness and where it runs. Swapping the MCP's MockDriver for real PCB hardware later is invisible to this agent.
