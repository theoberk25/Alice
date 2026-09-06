# Agent demo status

Updated 2026-09-06. Upstream machine-metrics pivot `237c307` is integrated into the
`codex/led-display` branch. Historical host/running claims are
[preserved separately](../handoffs/2026-09-06-before-metrics-reconciliation.md).

- Preferred shared tools: `get_metrics()` and `set_fan_speed(value)` on :8790/mcp.
- Default MCP backend delegates to the single governed thermal plant on :8795;
  direct file mutation remains explicit standalone test mode only.
- Cloud ADK prompt and read-only smoke command now match the metrics tools.
- Each agent and poller supplies its own bearer credential. Poller labels do not
  establish identity. Existing 10 Hz polling is retained, with freshness metadata.
- The external agent-loop console retains :8792. Cold-start restore and cloud-outage
  concepts are separate future work. Existing direct-light drivers are dormant.

[Run/configuration](../guides/machine-metrics-integration.md) ·
[Topology](topology.md) · [Test evidence](../reports/2026-09-06-metrics-reconciliation.md)

No live Gemini calls, camera sessions, Pi service deployment or hardware verification
were performed as part of this reconciliation. Historical native SDK build limits
remain unchanged; this reconciliation does not edit the native review layer.
