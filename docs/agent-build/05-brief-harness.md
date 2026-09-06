# Build 05 — Decision-Brief Agent Harness (Goose + local Ollama)

> Build order: build `04-brief-mcp.md` first and confirm it passes its acceptance
> checks. This agent is a client of that MCP server. It reuses the **same harness
> strategy** as the Light-Control local agent (`02-local-harness.md`) — Goose +
> local Ollama — so this file only states the **deltas**; do not re-do the shared
> install.

## Session orientation (read first)
Working inside the **Alice** repo. Read `AGENTS.md` and `current.md` per `CLAUDE.md`.
Relevant facts:
- Alice already runs a **local Ollama** at `http://127.0.0.1:11434`. **Reuse it** —
  and reuse the same `qwen2.5-tools` (32K-context) model the Light harness derived
  in [`local-harness-setup.md`](local-harness-setup.md). Do not stand up a second
  Ollama or a second model.
- This is the **local / air-gapped** agent: everything runs on-box, nothing leaves
  the machine. That is the whole point — the held-action review at a base / in a
  power plant happens with no egress.

## Why Goose (same decision as file 02)
Goose (Block, Apache-2.0) is the out-of-the-box, air-gapped agent **harness**.
Same rationale as the Light agent; the only differences here are the **MCP it
connects to** (the Decision-Brief MCP on `:8793`) and the **role prompt**.

## Goal
A locally-running Goose agent that, driven by the local Ollama model, reads
ALICE's held decisions from the Decision-Brief MCP (file 04) and **publishes a
plain-language, provenance-first brief** for each one into the review dashboard —
so a human technician can decide the HOLD. The agent **formats and explains; it
never decides** the hold.

## Steps (deltas from file 02 / `local-harness-setup.md`)
The Goose + Ollama install and the `qwen2.5-tools` model are **already done** for
the Light harness — reuse them. New here:

1. **Point Goose at the Decision-Brief MCP** as a remote extension (Streamable
   HTTP), alongside or instead of `light_control`. In `goose configure` →
   *Add Extension* → *Remote*, or in `~/.config/goose/config.yaml`:
   ```yaml
   extensions:
     decision_brief:
       enabled: true
       type: streamable_http   # use the SSE/remote type your Goose version prints
       uri: http://127.0.0.1:8793/mcp
   ```
   > Goose's remote-extension config key/type names vary by version — verify
   > against `goose configure`'s own prompts. The target URL is fixed:
   > **`http://127.0.0.1:8793/mcp`**. Keeping a separate Goose profile/recipe for
   > this agent (vs the Light agent) keeps the two roles cleanly distinct.
2. **Give it the review-brief role prompt.** Frame it as the technician's
   decision-support drafter:
   > *You prepare held ALICE decisions for a human technician. For each hold: call
   > `get_decision`, then write a short, neutral `summary` and provenance-first
   > `factors` (`label`/`value`/`source`/`freshness`) mirroring the record, plus
   > `watch_items` worth checking, and `publish_brief` it. Never invent factors or
   > numbers not in the record. **Never recommend or state a verdict** — deciding
   > `APPROVE_ONCE`/`HOLD`/`RESEARCH`/`REJECT` is the technician's job, done after
   > biometric verification. If a field is missing, say "unknown", don't guess.*

## Acceptance / verification
With the Decision-Brief MCP (file 04) running in `mock` mode:
1. `goose session` starts and lists the `decision_brief` tools (`list_holds`,
   `get_decision`, `publish_brief`, `get_brief`).
2. Prompt: *"Brief the oldest open hold for the technician."* → Goose calls
   `list_holds` → `get_decision("req-2026-0906-0001")` → `publish_brief(...)`; the
   MCP logs the calls; `get_brief("req-2026-0906-0001")` returns a summary +
   factors, and `list_holds()` shows `brief_status: published`.
3. Prompt: *"Brief req-2026-0906-0002."* → the brief names the `HIGH` anomaly and
   the clean permission **without** telling the technician what to do (no verdict).
4. Confirm no network egress beyond localhost (Ollama :11434 + MCP :8793) — the
   air-gapped claim.

## Notes
- Nothing here depends on real ALICE data: the `MockSource` behind the MCP makes
  this fully demoable today; swapping to `AliceSource` later (real held decisions +
  real dashboard publish) is invisible to Goose.
- If the small model ever narrates a decision ("I approved it") — it can't; there
  is no such tool. Trust the **MCP log** over the model's prose, same rule as the
  Light harness. Keep Goose config out of git if it holds anything
  environment-specific (respect `.gitignore`).
