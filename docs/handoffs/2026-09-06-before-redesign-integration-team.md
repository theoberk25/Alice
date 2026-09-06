# Preserved team checkpoint before redesign integration

Historical snapshot of `4531277:current.md`, saved on 2026-09-06.
[Working rules](../../AGENTS.md) apply; see [current integration](../../current.md).
Commands and next steps below describe the prior session, not current authorization.

# Current
Updated: 2026-09-06.
Baseline: local `0e4e747` merged with upstream main `54634adc`; merge commit pending.

## Active objective

Finish the shared thermal-demo merge so teammates can pull one path from agent MCP
through model-backed ALICE decisions, native technician review and the simulated
fan/LED environment.

## Current state

- Upstream per-agent MCP on `:8790`, thermal backend on `:8795`, revision locking,
  simulated plant, LED renderer and native review contracts are preserved.
- The thermal runtime now loads the bounded data-only fan model and binds each score
  to the current fan target, temperature, power, signed request and audit evidence.
- Signed permissions permit cooling and power agents across 0–100%; LOW assessment
  ALLOWs, ELEVATED/HIGH produces `ANOMALY_REVIEW_REQUIRED`, and missing permission
  DENYs. The local LLM may explain a HOLD; human approval is still required.
- Direct legacy fan requests remain supported during the coordinated migration.

## Evidence and limits

- Python repository tests: 509 passed, 1 skipped, 266 subtests.
- Targeted fan/thermal/MCP tests: 13 passed, 1 skipped.
- Console: TypeScript typecheck passed; 136 Vitest tests passed.
- Full root pytest collection additionally requires the separate biometric service
  environment (`cv2`, FastAPI and Pydantic). Rust was not run on this Mac.
- No merged code from this session has been deployed to the Pi or physically accepted.

## Next steps

1. Complete and push the merge after final lint/build and secret/path checks.
2. Merek pulls main and runs the native console against the updated thermal backend.
3. Deploy the reviewed model and merged services to the Pi in a separate controlled step.
4. Rehearse +10/+10/+10 ALLOWs, then the power-agent 0% HOLD and signed rejection.

[Demo](docs/demo.md) · [Environmental guide](docs/guides/environmental-demo.md) · [Tracker](docs/implementation-tracker.md)
