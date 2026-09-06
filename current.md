# Current

Updated: 2026-09-06.
Baseline: upstream main `d5a0d56`; integrated thermal increment under review.

## Active objective

Finish and publish the integrated Pi thermal runtime, USB/Wazuh evidence path and
Xavier serial-v3 display for the team demo.

## Current state

- Agent tools on Pi `:8790` read governed fan, temperature, power and battery data
  and propose only fan targets. The thermal backend on Pi `:8080` owns the plant.
- The cloud ADK agent has an opt-in authenticated enterprise-ingress tool. Its smoke
  command remains read-only. Automatic local thermal trigger loops are unfinished.
- The plant derives power from actual fan speed, evolves temperature over time and
  draws battery only when consumption exceeds its 450 W simulated supply.
- Xavier's fixed display is yellow=power, blue=actual fan speed, red=temperature and
  white=two-segment battery remaining. Lights are read-only telemetry indicators.
- `alice-thermal-demo` is active on the Pi with the ext4 USB ledger, external ledger
  key, Wazuh worker, model and serial-v3 ESP. `light-mcp` is active and depends on it;
  legacy `alice-runtime` is inactive to enforce one ledger/serial owner.
- Permission-eligible normal changes ALLOW; a contextually unusual fan cut produces
  `ANOMALY_REVIEW_REQUIRED` and HOLD. The workstation LLM explains; a human decides.

## Evidence and limits

- Thermal USB/Wazuh, model, metrics and display checks: 33 passed, 1 skipped.
- Previous shared baseline: 509 Python tests passed; console typecheck and 136 Vitest
  tests passed. Those broader results remain historical for this increment.
- The mapping and plant relationships are implemented and covered by focused tests.
- `crash-thermal-realism.md` is absent from upstream main and all published branches;
  its committed effect is limited to the transition text currently in `docs/demo.md`.
- Pi replay from 90 F produced three executed +10 ALLOWs and an unexecuted eligible
  power-agent HOLD. Wazuh delivered through its decision; ESP-v3 acknowledged output.
- Accelerated zero-battery acceptance returned `EXHAUSTED_OFF`; every channel was
  commanded continuously off instead of using the unavailable-data flash pattern.
- Visible confirmation of all four light pairs is still separate from serial readback.
  Server-load input and autonomous trigger loops do not exist.

## Next steps

1. Confirm the four light pairs visually and complete a fresh signed technician review.
2. Rehearse router/enterprise loss and restore with explicit authority transfer.
3. Implement the agreed autonomous agent trigger loop after the manual demo is stable.

[Demo](docs/demo.md) · [Metrics](docs/guides/machine-metrics-integration.md) · [Runbook](docs/guides/demo-runbook.md) · [Tracker](docs/implementation-tracker.md)
