# Agent demo — status (2026-09-06)

Agents use the same MCP implementation, **repurposed from lights to governed
machine metrics**. Each physical agent runs its own loopback instance and private
ALICE signing identity. They read `{fan_speed, server_temperature,
power_consumption}` and request only `fan_speed` changes.
Dev runs off a local state file; the real path is the Pi state file governed
through ALICE. The standalone live-demo/agent-loop prototype has been extracted
to a separate folder outside this repo (`../test-simulation/`).

| # | Project | Status | Blocker / next |
| --- | --- | --- | --- |
| 1 | **Cloud agent** — Google ADK + Gemini | 🟡 Updated to the metrics contract | Cooling prompt and smoke test now use `get_metrics`/`set_fan_speed`; live Gemini rerun is pending. Vertex/Agent Engine remains gated behind the human checkpoint. |
| 2 | **Local agent** — Goose + Ollama | 🟢 Verified (interactive) | Chat at `http://127.0.0.1:8791`. Will see the new metrics tools on reconnect. |
| 3 | **Machine-metrics MCP** — `services/light_mcp/` | 🟢 Governed adapter implemented | Streamable HTTP `:8795`, tools `get_metrics` + signed `set_fan_speed`. ALICE owns protected writes. `poller.py` provides 10 Hz reads; legacy light drivers are dormant. |

## Local model (dashboard + local agent)
🟢 **Ollama up** on `:11434` with `qwen2.5-tools` (4.7 GB, custom tool-calling build) and base `qwen2.5`. Tool-calling **verified** through Goose.
🟡 **Dashboard not yet pointed at it:** `ALICE_LLM_MODEL` is empty and `ALICE_BIOMETRIC_MODE=mock` (ArcFace/InsightFace available but `ALICE_INSIGHTFACE_ROOT` unset). The model is ready on the host; the technician dashboard's LLM/biometric hooks still need wiring.

## Running now
`:8795` machine-metrics MCP · `:8791` Goose chat · `:11434` Ollama · `:8000` `adk web`.
Not running: technician dashboard, Decision-Brief MCP.
The live demo runs from `../test-simulation/` (standalone, outside this repo).

## To drive the real 8 lights (governed)
Tunnel to the Pi, set `LIGHT_DRIVER=alice` + `ALICE_AGENT_ID`/`ALICE_AGENT_KEY_FILE` (provisioned seed), restart the MCP. See `docs/agent-build/03-light-mcp.md` and `docs/integration/esp-handoff.md`.

## Notes
- Nothing committed yet (all on branch `feat/light-mcp`, up to date with `main` @ `3bceeac`).
- A 4th project appeared on `main` — **Decision-Brief MCP** (`services/brief_mcp/`, `:8793`, `docs/agent-build/04-brief-mcp.md`) — not built or verified here.
- Build doc `03-light-mcp.md` is slightly stale (predates the 8-light + governed drivers).
