# Before agent/main integration — 2026-09-06

Follow [AGENTS.md](../../AGENTS.md). Historical setup snapshot preserved before
the user-authorized merge and PR. New evidence belongs in
[the integration report](../reports/2026-09-06-local-agent-main-integration.md).

# Current
Updated: 2026-09-06 EDT. Owners unassigned.
Branch: `codex/local-agent-model-setup`.
Baseline: `11ccd6aaa340742796cb2fb350f4db847d1a3f6f`, matching locally available
`origin/main` and `upstream/main` before setup. No push or Pi deployment.

## Active objective

Install and configure the local models and authenticated agent clients on this
Mac, as requested after the teammate authorized its SSH key. Installation and
read-only verification are complete. The actuation demo remains a separate step.
[Setup guide](../guides/local-agent-host.md) ·
[Detailed evidence](../reports/2026-09-06-local-agent-model-setup.md).

## Current setup

- Verified Pi host key, key-authenticated SSH and passwordless sudo.
- Pi thermal-demo and MCP services active; ordinary alice-runtime inactive.
  Existing fan anomaly artifact verified present; no model replacement.
- Mac MCP forward at `127.0.0.1:8790`; three private per-agent token/profile
  pairs configured. All three can authenticate and read live metrics.
- MCP/PyYAML dependencies and Goose CLI installed. Qwen 7B downloaded;
  default/named Goose profiles use the verified 32K `qwen2.5-tools` alias.
- Existing Llama 3.1/Dolphin and ArcFace/pose/PAD models retained and verified.
  Console remains on its saved local-runtime/mock-controller feed.

## Evidence and blockers

Fresh: pip dependency check passes; eight isolated MCP integration tests pass.
Both existing Llama models respond locally. Goose observer with Qwen calls
get_metrics successfully at 32K context. ArcFace public-image inference passes;
live facial endpoint reports identity/pose/PAD PASS and READY.
Pi synthetic fan-model probes score LOW/LOW/LOW/HIGH. The plant remains RUNNING,
revision 1, fan target 70%, battery 80%, one existing request. No lifecycle or
fan-changing command was sent; this is not the Part 2 READY 90/60/60 baseline.
Physical camera acceptance and the full agent/technician demo remain unperformed.

## Preserved prior work

The previous integration/redesign and saved-console state is preserved in the
[pre-setup checkpoint](../handoffs/2026-09-06-before-local-model-setup.md).
All prior test and deployment claims there are historical. Existing app bundles,
settings, enrollment stores, models and Pi services remain intact.

## Next steps

1. Use the observer launcher for read-only metrics or local Qwen explanations.
2. Coordinate the desired plant baseline with its operator before the next demo.
3. Run the cooling/power sequence only when requested, preserving HOLD IDs.
4. Complete fresh technician-camera review and physical indicator acceptance.

[Rules](../../AGENTS.md) · [Tracker](../implementation-tracker.md) ·
[Demo plan](../plans/2026-09-06-demo-part2-local-agent-workflow.md)
