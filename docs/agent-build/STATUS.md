# Agent demo — status (2026-09-06)

Two agents (cloud + local) operate machine "lights" through a shared MCP. Mock runs
everywhere today; the real 8-light XIAO is governed through ALICE on the Pi.

| # | Project | Status | Blocker / next |
| --- | --- | --- | --- |
| 1 | **Cloud agent** — Google ADK + Gemini | 🟡 Code-complete, imports clean, wired to MCP | Paused by request. One free AI Studio key (empty in `.env`) from a live run. Vertex/Agent Engine gated behind human checkpoint. |
| 2 | **Local agent** — Goose + Ollama | 🟢 Done & verified | Drives all tools end-to-end; chat window live at `http://127.0.0.1:8791`. |
| 3 | **Light-Control MCP** — `services/light_mcp/` | 🟢 Done & verified | Streamable HTTP `:8790`, 8 lights (Jared's mapping). 3 drivers: `mock` (default, live), `esp` (direct, on-Pi bench), `alice` (governed — signed requests through ALICE, verified vs stub). |

## Local model (dashboard + local agent)
🟢 **Ollama up** on `:11434` with `qwen2.5-tools` (4.7 GB, custom tool-calling build) and base `qwen2.5`. Tool-calling **verified** through Goose.
🟡 **Dashboard not yet pointed at it:** `ALICE_LLM_MODEL` is empty and `ALICE_BIOMETRIC_MODE=mock` (ArcFace/InsightFace available but `ALICE_INSIGHTFACE_ROOT` unset). The model is ready on the host; the technician dashboard's LLM/biometric hooks still need wiring.

## Running now
`:8790` Light MCP (mock, 8 lights) · `:8791` Goose chat · `:11434` Ollama.
Not running: cloud agent, technician dashboard, Decision-Brief MCP.

## To drive the real 8 lights (governed)
Tunnel to the Pi, set `LIGHT_DRIVER=alice` + `ALICE_AGENT_ID`/`ALICE_AGENT_KEY_FILE` (provisioned seed), restart the MCP. See `docs/agent-build/03-light-mcp.md` and `docs/integration/esp-handoff.md`.

## Notes
- Nothing committed yet (all on branch `feat/light-mcp`, up to date with `main` @ `3bceeac`).
- A 4th project appeared on `main` — **Decision-Brief MCP** (`services/brief_mcp/`, `:8793`, `docs/agent-build/04-brief-mcp.md`) — not built or verified here.
- Build doc `03-light-mcp.md` is slightly stale (predates the 8-light + governed drivers).
