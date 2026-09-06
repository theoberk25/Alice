# Native live backend validation

Validated locally on 2026-09-06 on `codex/native-live-backend`, based on Theodore
Berk's merged `upstream/main` at `d57c660`. This report covers the restored final
source and local tests; it does not establish physical-Pi or human-camera acceptance.
Final fetched upstream `de6c6cb` adds wireless DDIL demo documentation in ten
Markdown files; that upstream delta does not change the tested runtime source.
See [feature parity](../plans/native-live-backend-parity.md),
[review contract](../contracts/technician-runtime-review.md),
[operator setup](../guides/native-runtime-review.md) and
[workspace preservation](../handoffs/2026-09-06-native-live-backend-workspace.md).

## Result and scope

Native ALICE retains the working technician web views and adds exact retained
request details plus fresh-face approve/reject for eligible local HOLDs. The Pi
checks signed consent and remains the policy, audit and execution authority.
The existing bridge, ledger and controller path are reused. Web access remains
read-only; a viewer login or feed bearer cannot authorize execution.

Automated coverage includes strict canonical JSON/signature interoperability,
request/action/permission/authority binding, cancellation, expiry, replay,
restart, concurrent review, storage failure and uncertain delivery. Approval
admission, controller receipt, execution result and observed state remain distinct;
rejection appends history without executing or rewriting the machine decision.

## Final automated evidence

Commands ran from the repository root. Counts describe their own suites and must
not be added together as independent integrated acceptance tests.

| Command | Final result | Evidence scope |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests -q` | **435 passed, 266 subtests**, 76.73s | Core regression including runtime/bridge/review/security, concurrent admission, restart and failure cases. `/tmp/alice-native-core-final.log`. |
| `npm run test:python` | **166 passed**, two dependency deprecation warnings | Local biometric API/storage/session regression; no human camera scan. |
| `node scripts/console/rust.mjs test` | **60 passed, two ignored** | Native identity, proof, transport and durable submission checks. Live Ollama and the opt-in Python integration are intentionally ignored by default. |
| `npm run check` | **134 Vitest + eight script tests passed**; typecheck, lint and web build passed | Shared UI/contracts, authenticated web proxy and existing fixture flows. `/tmp/alice-native-frontend-check.log`. |
| `PLAYWRIGHT_BROWSERS_PATH=.tools/playwright npm run test:e2e -- --workers=1` | **Eight passed**, 12.8s | Five existing UI workflows; three browser tests with explicitly synthetic native IPC/camera for feed-before-ack, cancellation/rejection and uncertain delivery across renderer restart. `/tmp/alice-native-renderer-e2e.log`. |
| `PLAYWRIGHT_BROWSERS_PATH=.tools/playwright npm run test:e2e:runtime` | **One passed**, 7.0s | Real Vite → Python bridge → temporary runtime/ledger with mock controller; incremental feed, replay and reconnection. `/tmp/alice-native-runtime-e2e.log`. |
| `npm run build:app` | **Exit 0**; optimized native build 19.25s | Rebuilt after source restoration. Bundle: `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`. `/tmp/alice-native-app-build.log`. |
| Provisioning/rehearsal helper tests | **Seven passed**, 1.17s | Local key boundaries and final rehearsal helper, including unique default request IDs. |

The separately enabled integration used the real production Rust snapshot,
grant-consumption/signing and HTTP submission paths against the real local Python
runtime and authenticated bridge. Biometric success was injected by test code;
the controller was mock. Both public cross-language proof directions passed.

Final integration commands (session contents remain private):

```sh
.venv/bin/python -m lab.first_light.native_review_demo \
  --directory /private/tmp/alice-native-proof-20260906-03 \
  --technician-id TECH-001 --integration-test-ids
ALICE_REVIEW_INTEGRATION_SESSION=/private/tmp/alice-native-proof-20260906-03/session.json \
  node scripts/console/rust.mjs test native_to_python_local_rehearsal -- --ignored --nocapture
```

The helper ran with a persistent terminal. The opt-in test **passed one test**;
approval, rejection and replays left **exactly one mock command and 12 ledger
events**. The helper was then stopped. Session `-03` reconfirmed the earlier `-02`
pass after the helper's default IDs were made unique; fixed IDs now require the
explicit integration-test flag. Results were captured in task tool output.

## Failures and recovery

The initial opt-in attempt lost its helper because stdin closed. Restarting the
helper with a persistent terminal resolved that harness failure; later `-02` and
`-03` runs passed. No failed run is counted as acceptance.

A concurrent GitHub Desktop branch operation automatically stashed the working
source during validation. The first native build and two core test failures from
missing source/fixtures were invalidated. All 53 final files were recovered from
the preserved snapshot and independently reconstructed from a bundle; final
source bytes were checked. The final 435-test core run and successful app rebuild
supersede the interrupted runs. The interrupted build log remains at
`/tmp/alice-native-app-build-interrupted.log`. Frontend/E2E runs had already
completed; their 18 source/config/test files matched the recovered snapshot exactly.

## Remaining acceptance

The built app was prepared for a personal local rehearsal against the ready
biometric service and the existing enrolled database, which was backed up and
integrity-checked. The service reported READY with identity, pose and PAD readiness
checks passing; the app opened signed out and waits for login before reading the
remote feed. **No facial scan or physical-Pi review was performed.** Camera
quality, a person's fresh approval/rejection, physical execution and independent
sensor feedback require separate recorded acceptance and authorized Pi trust setup.

The rehearsal uses a signed first-light release, fixed OFFLINE ALICE ownership,
fixture assessment and mock controller. It does not test a real enterprise
ownership transfer. Enterprise SIEM/agent workbench adapters, live Decision-Brief
publication, missing numeric anomaly scores and packet-wide capture remain
unavailable in native as recorded in the parity inventory. Live Ollama was not
tested. Device output-adjustment controls and deepfake detection remain excluded.
No push, remote merge, deployment, remote trust provisioning or hardware operation was
performed for this increment.
