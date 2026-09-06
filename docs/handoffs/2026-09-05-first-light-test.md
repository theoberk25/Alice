# 2026-09-05 — First-light integration test slice

Session record per [AGENTS.md](../../AGENTS.md). Branch: `first-light-test`
(from `main`); committed locally, not pushed or deployed.

## What was built

Minimal implementation of the agreed first integration test — one OFFLINE
action `set_light_state -> ESP-LIGHT-01 -> {"state": "on"}` from a terminal
agent through the Pi runtime to a (mock) ESP, producing a durable audit trail
in the existing `AuditLog` and a verified USB export. Nothing beyond the test
slice was written; the full runtime plan grows these seams later.

- `common/schemas/action_request.json` — strict, test-scoped request schema.
- `dcamr/packages/package_verifier.py` — fail-closed release verification
  (manifest Ed25519 signature + per-payload sha256, mirroring
  `lab.enterprise_sim.permissions` canonical bytes).
- `dcamr/policy_engine/policy_engine.py` — deterministic exact-match resolver
  returning the shared `PermissionFinding` type; default deny; no model in any
  denial path; `approval_required` maps to `REVIEW_REQUIRED`.
- `dcamr/decision_model.py` — **additive only**: `Decision` + `decide()`
  appended; the teammate-owned assessment boundary landed since the plan was
  written and is preserved unchanged.
- `dcamr/enforcement/enforcement_gateway.py` — ESP HTTP transport; receipt and
  observed state kept separate; idempotency owned by the runtime.
- `dcamr/main.py` — stdlib runtime: authenticate by verified key (agent_id must
  match the key binding), idempotency check, admission refused unless ledger
  headroom covers the full event set, REQUEST/ASSESSMENT/DECISION/
  EXECUTION_ATTEMPT (committed before the ESP is commanded)/CONTROLLER_RECEIPT/
  EXECUTION_RESULT/OBSERVED_STATE, seal per request; read-only `GET /events`
  technician feed (the seam the console can adopt later).
- `scripts/lab/first_light/` (importable as `lab.first_light.*`):
  `build_release.py` (demo-trust keys), `assessment_fixture.py`
  (`fixture_mode` marker lives in the retained context map because
  `contextual_projection` forbids extra top-level keys), `mock_esp.py`,
  `terminal_client.py` (`--repeat` idempotency demo), `technician_view.py`,
  `usb_export.py` (queue → NDJSON write → hash verify → acknowledge;
  ledger events only, labelled as such — not the enterprise-sim
  `alice-audit.jsonl` chain).
- `tests/test_first_light.py` — acceptance checklist end to end.

## Commands run and results

- `.venv/bin/python -m unittest tests.test_first_light -v` — 6 tests OK
  (bad signature → REJECTION without execution; key/agent binding mismatch
  rejected; NO_PERMISSION deny with REQUEST+REJECTION chain; happy path with
  full 7-event correlated chain and evidence-hash match; identical request_id
  retried → one ESP command and replayed outcome; conflicting reuse → 409;
  validate() after seal + reopen; USB export records match ledger hashes).
- `.venv/bin/python -m unittest discover -v` — **263 tests OK, 30 skips**
  (skips pre-existing, unrelated suites).
- Multi-process dry run on the Mac: `build_release` → `mock_esp` →
  `python -m dcamr.main` → `terminal_client --repeat 2` (ALLOW, COMPLETED,
  observed on; second attempt replayed) → `technician_view` (chain printed) →
  ESP `/stats` = 1 command → `usb_export` (exported + acknowledged) →
  `validate()` → `ValidationReport(event_count=7, covered_sequence=7, ...)`.

## Limitations

- Component/integration evidence on a Mac with a mock ESP; **not** physical
  acceptance. The ESP firmware HTTP contract is an open coordination item.
- The assessment is an explicitly labelled fixture (`fixture_mode` in context);
  it proves ledger wiring, not detection.
- All keys are demonstration trust only; never provision them in production.
- The NO_PERMISSION end-to-end case swaps in a grantless release view because
  the strict schema pins the action/target enums.
- Local `.venv` (Python 3.14) created with requirements-audit + anomaly deps.

## Open items

1. Agree the real ESP firmware contract; swap the URL for the physical run.
2. Point the console's future remote transport at read-only `GET /events`.
3. Check teammate branches for Pi-runtime work before merging the seam fills.
