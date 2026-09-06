# Current

Updated: 2026-09-05
Baseline: `7081b6a` (main fetched; no newer commit at latest live-test check).
Prior console-layout state is preserved in the
[console handoff](docs/handoffs/2026-09-05-console-layout.md).

## Current objective

Prepare enterprise/Pi/technician integration for incoming storage backend.
Wazuh and enterprise console are live; simulated operator already exists.
[Network readiness and contract gaps](docs/reports/2026-09-05-enterprise-network-readiness.md).
Start with [AGENTS.md](AGENTS.md).

## Current state

- Jared Mac → Pi test succeeded: signed ALLOW/COMPLETED against mock ESP,
  seven correlated events, retry executed once. Demo release first-light-jared-2
  active; existing ledger retained. [Evidence](docs/reports/2026-09-05-jared-first-light-test.md).

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

Additional live tests: four bad-identity/envelope rejections, one ALLOW, identical
replay and conflicting-ID rejection; exactly one mock command, cursor resume OK,
SQLite quick_check OK. Conflict response currently adds no audit event. USB is
58.6 GiB exFAT, unmounted; waiting for backend filesystem/mount contract.

Historical first-light checkpoint: 263 core tests passed (30 pre-existing skips), including 6 new first-light
tests, plus a multi-process Mac dry run: ALLOW/COMPLETED/observed=on, exactly
one ESP command across a retried request, verified+acknowledged USB export,
`validate()` clean after reopen.
[Commands and limitations](docs/handoffs/2026-09-05-first-light-test.md).
Console-layout evidence is [historical](docs/handoffs/2026-09-05-console-layout.md).

## Start here

[Rules](AGENTS.md) · [Docs](docs/README.md) · [Scripts](scripts/README.md)
