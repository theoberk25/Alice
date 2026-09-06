# Machine metrics reconciliation — 2026-09-06

Integrated upstream main `237c307` into `codex/led-display` (merge `0e66e2a`).
The teammate's public MCP interface is retained: `get_metrics`,
`set_fan_speed(value)` in percent, and Streamable HTTP on port 8790.

The default MCP backend now routes fan proposals through the existing ALICE
thermal runtime. Its plant is the shared source of state; signed basis-point
requests remain an internal adapter detail. Actual fan speed and requested target
are separate, and temperature/power units are explicit. Independent JSON state
is available only through explicitly selected standalone file test mode.

Per-agent bearer credentials bind requests to the same configured runtime
identities. Retry bindings preserve request identity, revision and run; rejected
or held proposals do not change the target. Pollers authenticate and report tool
errors as unavailable samples. Consumers must respect sample timestamps and age.
The cloud agent prompt and read-only smoke script now use the current tools.

Thermal HTTP defaults to 8795, leaving upstream's agent-loop console port 8792
available. Example configuration and systemd templates document the change;
existing deployments need the matching URL and private token configuration.
See the [run guide](../guides/machine-metrics-integration.md).

## Validation

`python -m pytest -q tests --ignore=tests/console --tb=short`:
**467 passed, 30 skipped, 246 subtests passed**, in 77.20 seconds.
The 12 warnings concern the MCP SDK's deprecated client spelling.
Eight new integration tests exercise real MCP HTTP and the ALICE thermal runtime,
including authorization, signed rejection, single execution after lost response,
run reset, strict inputs, authenticated polling, and independent agent identities.
Python compilation and `git diff --check` passed.

No console, native, camera, runtime-feed or firmware source changed in this
reconciliation. No live Gemini call, deployment, hardware control or flashing was
performed. Earlier environmental validation remains recorded in the
[original report](2026-09-06-environmental-demo-validation.md); its native build
and physical acceptance limits remain unchanged.
