# Current
Updated: 2026-09-06.
Branch: `codex/led-display`; environmental delivery `40ae904`, merged main `237c307`.

## Active objective

Reconcile the teammate's machine-metrics MCP with the environmental demo,
preserving their public interface and the shared ALICE fan authority.

## Current state

- Main merged cleanly; MCP retains `get_metrics` and percent `set_fan_speed` on 8790.
- Default MCP reads the shared thermal plant and submits governed fan proposals.
- Per-agent credentials, exact retry bindings and authenticated pollers integrated.
- Cloud prompt and read-only smoke script use the current metrics tools.
- Thermal backend moved to 8795, preserving the teammate's console port 8792.
- Independent file state requires explicit standalone test mode.
- No console, native, camera or firmware changes in this reconciliation.

## Evidence and limits

Python regression: 467 passed, 30 skipped, 246 subtests, including eight new
real HTTP/MCP integration tests. Compilation and diff checks passed.
See [reconciliation](docs/reports/2026-09-06-metrics-reconciliation.md).
Earlier console/firmware validation and native SDK limits remain in the
[environmental report](docs/reports/2026-09-06-environmental-demo-validation.md).
No live Gemini calls, deployment, flashing or physical acceptance performed.

## Next steps

1. Configure matching private agent tokens and thermal URL for a separate deployment.
2. Teammate completes the operator page against the shared environmental contract.
3. Verify physical Pi/XIAO operation and resolve native SDK compatibility separately.

[Metrics run guide](docs/guides/machine-metrics-integration.md) · [Tracker](docs/implementation-tracker.md)
