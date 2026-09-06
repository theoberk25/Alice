# Current
Updated: 2026-09-06 EDT. Owners unassigned.
Branch: `codex/local-agent-model-setup`.
Baseline: upstream main `2aa5c343a51eba63de86726490ed61a8cba0989f`.
Integration merge: `3dd14ee33443777e600bad0dea481a719dd1351b`.

## Active objective

Publish the preserved local agent setup after integrating the latest main.
The merge is conflict-free; implementation and dependency files from main remain
intact. User authorized branch publication and pull-request creation.
[Integration evidence](docs/reports/2026-09-06-local-agent-main-integration.md).

## Preserved setup

- Existing private cooling, power and observer Goose/MCP profiles and tokens.
- Local Qwen 7B/32K alias, Llama/Dolphin and ArcFace/pose/PAD models.
- Loopback MCP forward to the Pi; all three authenticated metrics reads pass.
- Pi remains on its existing RUNNING simulation, revision 1, target 70%, battery
  80%, one request. No plant lifecycle or fan-changing action was sent.
- Saved console feed, enrollment, app bundles and Pi services preserved.

[Setup guide](docs/guides/local-agent-host.md) ·
[Historical setup evidence](docs/reports/2026-09-06-local-agent-model-setup.md) ·
[Pre-integration snapshot](docs/handoffs/2026-09-06-before-agent-main-integration.md).

## Fresh evidence and limitations

Console check/build and npm dependency resolution pass. Root pip check passes.
Runtime tests: 562 passed, 266 subtests passed, one failure independently reproduced
on unmodified upstream main (stale published enterprise manifest).
Biometrics: 177 tests and real ArcFace inference pass. Its pip check retains the
intentional MediaPipe/headless OpenCV metadata exception. Vision imports pass.
Qwen/Goose observer performs a real read-only metrics call successfully.
Full physical/demo acceptance remains unperformed; no Pi or app deployment.

## Next steps

1. Review the integration PR and its documented upstream test exception.
2. Reconcile enterprise generator/published fixture drift in a separate change.
3. Coordinate the plant baseline before the requested Part 2 demonstration.
4. Complete physical camera/technician and indicator acceptance.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Demo plan](docs/plans/2026-09-06-demo-part2-local-agent-workflow.md)
