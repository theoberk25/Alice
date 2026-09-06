# Current

Updated: 2026-09-06.
Baseline: upstream main `4531277`; telemetry-alignment update in progress.

## Active objective

Align the cloud/local agent story, governed thermal data and Xavier's physical
light display before the team deploys the combined services to the Pi.

## Current state

- Agent tools on `:8790` read governed fan, temperature, power and battery data and
  propose only fan targets. The thermal backend on `:8795` owns the simulated plant.
- The cloud ADK agent has an opt-in authenticated enterprise-ingress tool. Its smoke
  command remains read-only. Automatic local thermal trigger loops are unfinished.
- The plant derives power from actual fan speed, evolves temperature over time and
  draws battery only when consumption exceeds its 450 W simulated supply.
- Xavier's fixed display is yellow=power, blue=actual fan speed, red=temperature and
  white=two-segment battery remaining. Lights are read-only telemetry indicators.
- Permission-eligible normal changes ALLOW; a contextually unusual fan cut produces
  `ANOMALY_REVIEW_REQUIRED` and HOLD. The workstation LLM explains; a human decides.

## Evidence and limits

- Previous shared baseline: 509 Python tests passed; console typecheck and 136 Vitest
  tests passed. Treat these as historical until this update's checks complete.
- The mapping and plant relationships are implemented and covered by focused tests.
- `crash-thermal-realism.md` is absent from upstream main and all published branches;
  its committed effect is limited to the transition text currently in `docs/demo.md`.
- Physical serial-v3 firmware plus the thermal runtime are not yet jointly deployed
  or accepted on the Pi. Server-load input and autonomous trigger loops do not exist.

## Next steps

1. Validate and publish this mapping/data alignment for teammates.
2. Deploy one thermal runtime as the Pi's sole plant and serial owner.
3. Rehearse 60→70→80→90 ALLOWs, then a power-agent 0% HOLD and signed rejection.
4. Confirm all four light pairs, technician review, USB evidence and Wazuh correlation.

[Demo](docs/demo.md) · [Metrics](docs/guides/machine-metrics-integration.md) · [Runbook](docs/guides/demo-runbook.md) · [Tracker](docs/implementation-tracker.md)
