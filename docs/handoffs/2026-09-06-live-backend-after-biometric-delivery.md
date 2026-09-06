# Continue the native live backend after biometric delivery

Prepared 2026-09-06 EDT in a documentation-only side conversation. This is a
snapshot of saved work, not a claim that the backend is finished or deployed.
The delivery task may advance branches after this file is written. Reinspect
their actual state before using the commit IDs below.

## Objective and scope

After the biometric integration is pushed, finish the **native ALICE desktop
application** so a technician can see live collected traffic, ALICE decisions,
and approve or reject eligible HOLDs with fresh facial verification. The original
machine decision must remain immutable; technician action, controller receipt,
execution result and observed state are distinct records.

The user explicitly deferred device/base output adjustment controls. Do not add
those now. Deepfake detection is removed from this project: do not restore its
models, interfaces, training, dependencies or gates. Existing ArcFace identity,
native camera acquisition, MediaPipe pose tracking, MiniFAS presentation checks,
encrypted enrollment and session protections remain. Head rotation belongs to
enrollment; login and approval use automatic matching without repeating it.

The user wants network traffic visibility. Existing telemetry covers admitted
ALICE requests and audit events, **not every packet on the network**. Show all
available records with clear source, freshness and coverage. Any additional
network-wide observation needs a real telemetry source and separate integration;
do not imply packet visibility or fabricate missing action/risk/device data.

## Start with these rules and references

Read [AGENTS.md](../../AGENTS.md), [current.md](../../current.md),
[documentation index](../README.md), [script catalog](../scripts/README.md),
[console contributing](../guides/console-contributing.md),
[PRD](../prds/ALICE-DCAMR-PRD.md),
[technician integration](../integration/technician-console.md),
[upstream integration](../integration/upstream-alice.md), and relevant rows in the
[tracker](../implementation-tracker.md). Do not read `docs/archive/` by default.

Relevant tracker entries include 066, 068–072, 092, 113, SUP-02 and SUP-05.
Keep their existing IDs. Owners remain unassigned unless agreed. This side
conversation creates only this handoff; the active delivery task retains control
of shared `current.md`, tracker updates, commits and publication.

Theodore Berk's `theoberk25/Alice` is the authoritative upstream, not the user's
fork. Preserve newer team architecture, dashboard, LLM, agent/MCP, backend,
networking, hardware, database, security and contract changes. Adapt this work to
newer interfaces; do not replace shared files wholesale with WIP copies.

PRD FR-12 limits this local authorization path to eligible OFFLINE/DDIL holds
while ALICE owns execution. ONLINE enterprise-controlled actions must not become
locally executable through this feature. Connectivity alone is not authority.

## Saved branches and recovery locations

Observed locally while preparing this file; no fetch, push or branch mutation was
performed by this side conversation:

| Item | Observed value |
| --- | --- |
| Original face branch | `codex/live-facial-biometric-upgrade` at `0063629dd282f466bb65c02a68ae182ccfe0d811` |
| Original checkout | `/Users/alexdaoud/Documents/Alice` |
| Delivery branch | `codex/live-face-upstream-integration` at `9a72e7589f9022a725e6f8e7824a36402d73892b` |
| Delivery worktree | `/Users/alexdaoud/Documents/Alice/.tools/biometric-main-integration` |
| Available upstream main | `f79cd8e007d02c5abc7b4dffce146e882a51774a` |
| Saved unfinished backend | `codex/live-runtime-review-wip` at **`aa5bae869053403d6e66f336a16b99e55437e404`** |
| Parent of saved WIP | `1ba7a27` on the earlier integration baseline |

The WIP is a local Git branch, with no separate worktree at inspection time.
It contains backend **and partial native/UI work**. It also includes delivery
cleanup such as MIT notices and removal of the unused Motion dependency. Do not
blindly apply all 34 changed files again after delivery.

The delivery branch was advanced onto newer upstream and now contains these
biometric commits: `e775772` (service/storage), `70fce2f` (native camera/session
authority), `9a72e75` (automatic UI). Earlier IDs `8c9840d`, `6a354d9`, `1ba7a27`
describe the earlier baseline, not the current delivery history.

The original dirty work was backed up under
`/Users/alexdaoud/Documents/Alice/.tools/biometric-integration-backup-20260906/`
with a binary patch, untracked archive, source status/head and hash manifest.
Do not alter the original checkout, private stores or that backup to resume this
backend task. Preserve WIP even if some of it is replaced during adaptation.

**A local WIP branch is not automatically included in the delivery push.** If
continuing from another computer, arrange transfer of that branch separately;
this document alone does not carry its source code or authorize publication.

## What is saved in the WIP

### Python runtime and bridge

- `dcamr/technician_review.py`: `ReviewAuthority` loads explicit Ed25519 console
  trust scoped to technician IDs. It produces request-bound review snapshots and
  validates signed short-lived approve/reject proofs under the runtime owner lock.
- `dcamr/main.py`: adds `--console-trust-file`, `GET /review/<request_id>` and
  `POST /review`; retains exact authenticated request bytes as evidence; extracts
  existing controller execution into `_execute_request` for reuse after approval.
  No alternate controller, database or ledger writer is introduced.
- `dcamr/decision_model.py`: a verified `REVIEW_REQUIRED` permission with usable
  assessment becomes `CHALLENGE` (presented as HOLD), rather than immediate DENY.
  Ordinary ALLOW and nonreviewable denial paths must remain protected.
- `services/runtime_feed.py`: extends the authenticated loopback bridge with fixed
  review paths. Feed credentials alone cannot authorize execution: the Pi verifies
  the native signature independently. No arbitrary URL forwarding is intended.
- `tests/test_technician_review.py`: real signatures, temporary ledger and mock
  controller tests for approval/rejection, replay, restart, bad/stale bindings,
  authority/policy changes and interruption after durable action admission.
- `docs/contracts/technician-runtime-review.md`: draft contract and boundaries,
  preserved in WIP. Read it with `git show` before porting it; it is absent from
  the delivery checkout at this snapshot.

Proof bindings are request ID/hash, decision event ID/hash, release hash, authority
interval, runtime epoch and random review nonce. Additional signed fields include
console ID, technician ID, action ID, action, biometric session ID/policy and
issued/expiry times. Protocol domain is `alice-native-review-v1\0`.

An accepted review appends `TECHNICIAN_ACTION` before physical execution. Same-action
retries must never issue another command. A crash after admission can leave an
unknown outcome requiring reconciliation; automatic re-execution is prohibited.
Historical requests without retained canonical request bytes remain visible but
are not eligible for this review path.

### Native authority and frontend

- `apps/desktop/src-tauri/src/runtime_review.rs`: partial strict snapshot parsing,
  native snapshot cache, request hashing, fixed bridge client, private signing key
  loading, grant binding and proof consumption before network submission.
- `biometric_commands.rs`: remote approval scope branches alongside the existing
  local approval path. Existing enabled-technician, enrollment generation,
  activation/removal and session checks remain relevant.
- `biometric_sessions.rs`: optional `runtime_action` intent (`APPROVE_ONCE` or
  `REJECT`), fixed before starting the scan. Renderer supplies intent/IDs only.
- `lib.rs`, `commands_tests.rs`, `config.rs`, Cargo manifests: partial registration,
  state and signing dependency changes. Finder allowlist adds `ALICE_CONSOLE_ID`
  and `ALICE_REVIEW_KEY_FILE`.
- `packages/contracts/src/runtime-review.ts`: strict Zod snapshot/receipt schemas;
  first-light action remains `set_light_state`, target `ESP-LIGHT-01` through `08`.
- `packages/domain/src/runtime-review.ts` and
  `apps/desktop/src/features/biometrics/runtime-review.ts`: domain interface and
  native adapter. Browser review remains unavailable.
- `apps/desktop/src/components/runtime/RuntimeReview.tsx`: partial request details,
  approve/reject modal, automatic face capture and receipt handling.
- `RuntimePanels.tsx` and `App.tsx`: partial integration/copy changes. Existing
  runtime history, feed continuity, provenance and decision views must survive.

## Known failure and areas requiring completion

The saved native implementation **does not build**. Historical
`/tmp/alice-review-rust.log` reports E0308 at `runtime_review.rs:141`:

```rust
let envelope = consume(&mut lock(&state)?, &verification_id)?;
```

Use an explicit scoped mutex guard, call `consume` through it, and release the
guard before awaiting network I/O. This is the first known compile blocker, not
proof that it is the only remaining problem. Native review tests are not yet
present, and no full native review acceptance has passed.

Review and complete these items rather than assuming the saved design is final:

- Strict native/Python canonical serialization interoperability for exact request
  hashes and signed proof bytes; test malformed, duplicate and oversized JSON.
- Stale snapshot replacement, expired cache, logout/relogin, disabled technician,
  changed enrollment, cancellation, navigation and failed scans cannot sign or
  submit. Changing approve to reject must require a newly bound verification.
- WIP `consume` removes `view.verification` from a SUCCEEDED biometric session.
  `LiveBiometricSessionSchema` requires verification on successful APPROVAL.
  Reconcile that state contract so subsequent polling cannot create invalid
  success responses while preserving one-use authority.
- The native watcher calls eligibility repeatedly; current scope validation loads
  the signer each time. Avoid unnecessary key-file I/O on the camera/session path
  without weakening checks at signing/submission.
- UI review state resets when selected-request events change. A successful submit
  can cause feed updates before the HTTP acknowledgment. Keep receipt/unknown
  outcome presentation stable; prevent stale callbacks, duplicate submission and
  disappearing acknowledgments. Keep camera release and reduced-motion behavior.
- Pi startup/trust validation and malformed evidence must fail cleanly. Exercise
  concurrent reviewers, global action-ID collisions, stale release/authority,
  storage failure, process restart and lost HTTP acknowledgment. Review lookup
  currently scans the ledger: measure/bound its cost as history grows.
- Add bridge HTTP tests. A bearer token without a valid signed review must never
  execute; web sessions and Vite proxy must not acquire write authority.
- Add explicit local console-key provisioning (not yet implemented). WIP expects
  a private raw 32-byte Ed25519 seed file and console ID on the Mac, plus a Pi
  `alice-console-trust-v1` public-key file scoped to technician IDs. Keep secrets
  outside Git and the renderer, with restrictive permissions. Never deploy trust
  or keys to the Pi silently.
- Keep receipt acceptance separate from execution and observed feedback. After
  uncertain delivery, reconcile the ledger; do not retry as a fresh execution.

## New team changes to preserve

Available upstream `f79cd8e` adds `services/light_mcp`, `services/brief_mcp`,
systemd units, cloud-agent scaffolding and agent build guides. These landed after
the WIP's baseline. Read their latest contracts before deciding where to adapt
review and traffic data.

The Decision-Brief MCP currently describes fixture-backed held decisions and
explicitly excludes autonomous HOLD disposition. Do not treat a generated brief
as permission or give the LLM approval authority. Avoid a duplicate hold database
or a second execution path. Preserve current mode-aware routing and enterprise
execution ownership.

## Evidence: historical, not acceptance of the saved WIP

Observed log files while preparing this handoff:

| Command/run | Recorded result | Scope |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/test_technician_review.py tests/test_first_light.py -q` | 22 passed in 9.64s | Python review + first-light checks using mock controller; before full native/UI WIP |
| `.venv/bin/python -m pytest tests -q` | 362 passed, 1 skipped, 266 subtests passed | Earlier integration core baseline; not the complete WIP or newest upstream |
| `npm run test:rust` for WIP | Failed E0308 above | No passing native review build |

Log locations: `/tmp/alice-review-python.log`,
`/tmp/alice-integration-core-pytest.log`, `/tmp/alice-review-rust.log`.
Temporary logs may disappear. Earlier biometric-only checks are evidence for
that increment only. No real Mac-camera → signed proof → bridge → Pi → physical
controller review flow is established by these results. No deployment or key
provisioning was performed by this handoff task.

## Resume sequence after the delivery push

1. Inspect branch/worktree status and fetch current repository state when resuming.
   Verify whether the biometric PR is merely pushed or actually merged. Base a
   new `codex/` follow-up branch on current authoritative main if merged; otherwise
   stack on the verified delivered integration branch and document the dependency.
   Use a separate worktree. Preserve the delivery, original and WIP branches.
2. Inspect `git show --stat aa5bae869053403d6e66f336a16b99e55437e404` and its
   parent-to-commit diff. Port only unfinished backend/native/UI behavior, resolving
   against the newest base. Exclude duplicate delivery cleanup. Keep logical
   commits for runtime/contract, native authority, UI and verification.
3. Fix the native compile blocker; complete validation, cancellation/consumption,
   provisioning and UI handling above. Add cross-language proof and real bridge
   integration tests, plus negative-path native and UI tests. Keep device output
   controls and new deepfake work out of scope.
4. Run core Python, biometric Python, Rust, frontend checks, relevant Playwright
   console/runtime flows and `npm run build:app` on the actual follow-up branch.
   Use isolated test state; preserve private enrollments and active services.
   Existing command entry points are `npm run check`, `npm run test:python`,
   `npm run test:rust`, `npm run test:e2e`, `npm run test:e2e:runtime` and
   `.venv/bin/python -m pytest tests -q`. Supply the fixture interpreter/browser
   environment required by the current runbooks; never substitute a passing mock
   biometric policy for real camera acceptance.
5. Prepare a concrete operator test: sign in, receive a new eligible hold, inspect
   exact action/target/parameters, fresh-face approve once, confirm separate
   acceptance/execution/observation records, reject another hold without execution,
   then test cancellation, stale/replayed proof and restart. Update current/tracker
   with commands actually run and limits. Report local readiness separately from
   live deployment. A prior biometric delivery push does not authorize a new
   backend push, main merge, deployment or hardware operation.

## Prompt to start the continuation

> Continue the native live backend described in this handoff after checking what
> has actually been pushed and merged. Start from the latest team-compatible
> biometric delivery, recover the saved `codex/live-runtime-review-wip` work, and
> finish live traffic/decision visibility plus fresh-face approve/reject of eligible
> HOLDs. Preserve newer team work and original branches. No deepfake detection or
> device-output controls. Fix and test the incomplete native/backend/UI path and
> build the real application. Keep all changes on a separate reviewable branch;
> do not push, merge, deploy or operate hardware without current authorization.
