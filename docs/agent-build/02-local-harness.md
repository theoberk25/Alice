# Build 02 — Local Agent Harness (Goose + local Ollama model)

> Build order: build `03-light-mcp.md` first and confirm it passes its acceptance checks. This agent is a client of that MCP server.

## Session orientation (read first)
Working inside the **Alice** repo. Read `AGENTS.md` and `current.md` per `CLAUDE.md`. Relevant facts:
- Alice already runs a **local Ollama** at `http://127.0.0.1:11434` (`OLLAMA_BASE_URL` in `.env.example`) and has an `ALICE_LLM_MODEL` var. **Reuse that same Ollama instance** — do not stand up a second one.
- This is the **local / air-gapped** agent: everything runs on-box, no data leaves the machine. That is the whole point of the "local machine at a base / in a power plant" story.

## Why Goose (decided)
Goose (Block, Apache-2.0, Agentic AI Foundation) is the out-of-the-box, air-gapped agent **harness** that mirrors how a DoD-style local deployment would run: install it, point it at a local model, give it tools over MCP. It is **net-new** and deliberately **separate from Alice's existing `agent/`** (that is a bespoke security agent; we want a clean "this is the harness" showcase). Turnkey alternatives if Goose is ever blocked: Tabby, or Aider+Ollama — but default to Goose.

## Goal
A locally-running Goose agent that, driven by a local Ollama model, controls the machine lights by calling the Light-Control MCP server from file 03.

## Steps
1. **Install Goose** (CLI; desktop app optional). Follow current install docs — do not assume a pinned version. Verify with `goose --version`.
2. **Local model on the existing Ollama.** Pick a **tool-calling-capable** model — small models handle tool calls poorly, so prefer a solid one your hardware can run:
   - Good default: `qwen3` (or `qwen2.5`) — strong tool-calling. Alternative: `llama3.1`.
   - `ollama pull <model>`; confirm with `ollama list`. Reuse `ALICE_LLM_MODEL` if it is already a tool-capable model.
   - Note the real constraint is the **model**, not the harness: agent loops burn tens of thousands of tokens, so favor a ≥32K-context model.
3. **Configure Goose provider = Ollama.** Via `goose configure` (or `~/.config/goose/config.yaml`): provider `ollama`, host `http://127.0.0.1:11434`, model = the one you pulled.
4. **Add the Light MCP as a remote extension.** Goose reaches the MCP server over the network (Streamable HTTP / SSE), matching file 03's transport. In `goose configure` → *Add Extension* → *Remote*, or in `config.yaml`:
   ```yaml
   extensions:
     light_control:
       enabled: true
       type: streamable_http   # use SSE/remote type per your Goose version
       uri: http://127.0.0.1:8790/mcp
   ```
   > Goose's remote-extension config key/type names vary by version — verify against `goose configure`'s own prompts and the installed version's docs. The target URL is fixed: **`http://127.0.0.1:8790/mcp`**.
5. **Give it a system/role prompt** framing it as the local machine-operations agent: it manages machines exposed by the `light_control` tools, can query status, and turn machines on/off or blink them on request. Keep a human in the loop for state changes if you want the demo to show confirmation.

## Acceptance / verification
With the Light MCP server (file 03) running in `mock` mode:
1. `goose session` starts and lists the `light_control` tools (`list_machines`, `get_status`, `set_machine`, `blink`).
2. Prompt: *"Which machines are off? Turn machine-02 on."* → Goose calls `get_status` then `set_machine("machine-02","on")`; the MCP server's MockDriver logs the calls; a follow-up `get_status` shows `machine-02: on`.
3. Prompt: *"Blink machine-02 three times."* → `blink` is called; state returns to `on`.
4. Confirm no network egress beyond localhost (Ollama :11434 + MCP :8790) — this is the air-gapped claim.

## Notes
- Nothing here depends on the PCB being real — the MockDriver behind the MCP makes this fully demoable today; swapping to real hardware later is invisible to Goose.
- Keep Goose config out of git if it holds anything environment-specific (respect `.gitignore`).
