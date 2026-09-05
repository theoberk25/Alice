# Current

Updated: 2026-09-05
Baseline: `ce617cf` (main). Work branch: `first-light-test` (local, not pushed).
Prior console-layout state is preserved in the
[console handoff](docs/handoffs/2026-09-05-console-layout.md).

## Current objective

First-light integration test implemented: one OFFLINE terminal request
(`set_light_state -> ESP-LIGHT-01`) runs end to end against a mock ESP.
Start with [AGENTS.md](AGENTS.md).

## Current state

- Seam fills on `first-light-test`: action-request schema, package verifier,
  exact-match policy engine, additive `decide()` (teammate's assessment
  boundary in decision_model preserved), ESP enforcement gateway, and the
  `dcamr/main.py` runtime producing into the existing AuditLog.
- Lab tooling in `scripts/lab/first_light/` (`lab.first_light.*`): release
  builder (demo trust only), fixture assessment, mock ESP, terminal client,
  read-only technician view, verified USB export.
- Console source remains in apps/desktop, packages and services; lab tools in
  scripts/lab; Pi runtime in dcamr. Tracker rows 001/013/021/071 now Partial.

## Next steps

1. Agree the real ESP firmware HTTP contract, then run the physical first-light
   test (swap the mock URL); owner unassigned.
2. Check teammate branches for Pi-runtime work, then review/merge
   `first-light-test`.
3. Point the console's future remote transport at read-only `GET /events`.
4. Connect trusted permissions, technician transport and execution to
   assessments (full runtime plan); bind assessment contract to the ledger
   adapter beyond the fixture.
5. Complete model export and real sensor/Pi acceptance; owners unassigned.

## Blockers and decisions

- No blocker for the mock run. Physical run blocked on the ESP contract.
- The first-light assessment is an explicitly labelled fixture (wiring proof,
  not detection); all first-light keys are demonstration trust only.

## Verification

263 core tests passed (30 pre-existing skips), including 6 new first-light
tests, plus a multi-process Mac dry run: ALLOW/COMPLETED/observed=on, exactly
one ESP command across a retried request, verified+acknowledged USB export,
`validate()` clean after reopen.
[Commands and limitations](docs/handoffs/2026-09-05-first-light-test.md).
Console-layout evidence is [historical](docs/handoffs/2026-09-05-console-layout.md).

## Start here

[Rules](AGENTS.md) · [Docs](docs/README.md) · [Scripts](scripts/README.md)
