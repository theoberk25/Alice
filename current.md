# Current

Updated: 2026-09-05
Product baseline: `2d0d32b` (GitHub main checked during this session).
Delivery: repository organization approved for `main`; use Git history for its commit.

## Current objective

Maintain the shared session rules and organized documentation; continue product
integration from the tracker. Start each session with [AGENTS.md](AGENTS.md).

## Current state

- Core model, ledger and Pi assessment components exist; end-to-end integration
  remains unfinished. [Detailed tracker](docs/implementation-tracker.md).
- Tracker reports 12 done components, 35 partial tasks and 71 planned tasks.
- Workstation source is integrated; authenticated core transport and protected
  execution remain outstanding. [Integration](docs/integration/technician-console.md).
- Documents are grouped by purpose; completed ledger session records are in the
  archive (read only when explicitly requested). Path-dependent tools retain their locations
  and are listed in the central [script catalog](scripts/README.md).

## Next steps

1. Lab/workstation owners: plan any script relocation with path updates and tests.
2. Compare Theo's workflow with existing components before adding implementations.
3. Agree application/enforcement contracts for Pi assessment and final decisions.
4. Connect trusted permissions, authority transfer, console transport and execution.
5. Establish real sensor contracts/data and integrated hardware acceptance.

## Blockers and decisions

- Lab/workstation owners will handle future script relocation and path updates
  separately; this cleanup introduces no dependency repair requirement. [Exceptions and move map](docs/handoffs/2026-09-05-repository-organization.md).
- Application decision/enforcement contracts and real sensor limits need agreement.
  [Workflow handoff](docs/handoffs/core-workflow-wip-handoff.md).

## Verification

Review verification: `.venv/bin/python -m unittest discover -v` passed all 253
tests with zero skips on 2026-09-05. Code/configuration paths and bytes are unchanged.
The linked organization handoff records preservation, link checks and review limits.

## Start here

[Rules](AGENTS.md) · [Documentation map](docs/README.md) ·
[PRD](docs/prds/ALICE-DCAMR-PRD.md) · [Architecture](docs/architecture.md) ·
[Tracker](docs/implementation-tracker.md) · [Scripts](scripts/README.md)
