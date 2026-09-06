# Live facial upgrade integrated onto team main

Date: September 6, 2026. Delivery branch: `codex/live-face-upstream-integration`.
Authoritative repository: `theoberk25/Alice`; fetched main baseline: `f79cd8e007d02c5abc7b4dffce146e882a51774a`.
The user's fork is the publication destination only. No merge or deployment is authorized.

## Integration and preservation

The original branch `codex/live-facial-biometric-upgrade` remains at
`0063629dd282f466bb65c02a68ae182ccfe0d811`, with its dirty tree unchanged.
A binary patch, untracked-file archive, HEAD/status and 423-path SHA256 manifest
were saved locally before integration. Revalidation found no content, HEAD or
working-tree status differences. Private models/enrollments/keys were not copied
into Git or removed. No original branch was rewritten or deleted.

The source branch mixed earlier live-face commits with superseded detector work
and uncommitted refinements. Instead of merging it, three logical net commits were
curated from the current face-only implementation on the common ancestor, then
cherry-picked onto main. This avoids importing detector history and obsolete app
versions. The source commits trace to `a60d565`, `ed89625`, `0063629` and the saved
uncommitted v3 refinements; `0063629` itself was not blindly cherry-picked.

| Curated source commit | Final delivery commit | Scope |
| --- | --- | --- |
| `20ece5e` | `e775772` | Live service, pose gallery, PAD, encrypted generations, tests/tools |
| `15d9bb9` | `70fce2f` | Native camera, session authority, lifecycle, activation/recovery |
| `be85a87` | `9a72e75` | Automatic enrollment/login/local approval, progress and success UI |

The final polish removes unused Motion and retains the exact upstream npm lockfile;
adds redistributed source notices in the team's docs layout; updates setup guidance;
and tests identity transitions against the retained live read-only feed.

## Preserved biometric behavior

- Swift camera acquisition with independent smooth preview and bounded inference.
- Automatic capture; no manual shutter or renderer-supplied authentication frames.
- Seven-region, any-order enrollment after neutral calibration; retained progress
  during ordinary quality/position interruptions; encrypted staged activation.
- ArcFace multi-template matching for login and fresh local fixture approval,
  including slight-angle tolerance. Authentication does not repeat head rotations.
- MediaPipe pose and MiniFAS presentation checks, five-control v3 policy.
- Native session IDs, nonces, epochs, deadlines, cancellation, replay and generation
  checks. Failed/stale/cancelled sessions cannot create authentication authority.
- Persistent enrollment, removal/activation recovery, technician revocation and
  request-bound one-use local approval grants.
- Progress ring, success acknowledgement/fade and reduced-motion handling.

Deepfake detection is absent from active code, model provisioning, dependencies,
interfaces, fallbacks and gates. Negative tests explicitly prove the old forged-media
control is not accepted. Historical documents remain historical. Randomized head/blink
challenges were already retired at the user's request and are not restored.

## Conflicts and adaptation

| File | Resolution |
| --- | --- |
| `apps/desktop/src-tauri/src/config.rs` | Retained upstream `feed_config` validation/tests and added native Finder dotenv loading. Feed URL/token remain native-only allowed settings. |
| `.env.example` | Retained all upstream live-feed/web settings plus biometric provisioning notes. A second conflict on the fresh main rebase retained the newly added Light/Brief MCP and agent settings as well. |
| `packages/contracts/src/index.ts` | Retained the runtime export and added the biometric export. |

No entire shared conflicted file was selected from either side. Auto-merges were
reviewed: `commands.rs` retains the team's runtime reader; `lib.rs` registers it
alongside biometric commands; console state only gains enrollment/policy metadata.
The team's `App.tsx`, runtime panels, remote feed/proxy, Pi/core, cloud/MCP services,
networking/hardware and common schemas are unchanged against the baseline. The
shared modal only gains optional close locking/class support for camera lifecycles.
Cargo keeps existing versions; `reqwest` adds blocking support and existing
`tempfile` becomes a runtime dependency for the native helper.

## Excluded live review work

Unfinished live HOLD approval/rejection is retained locally on
`codex/live-runtime-review-wip` at `aa5bae8`. It is excluded from this delivery
and is not pushed. The snapshot contains draft signed-review/backend/native/UI
code and preliminary tests; it has known Rust/TypeScript compile failures and
must not be presented as working integration. Continue it separately.

Live Pi approve/reject controls remain disabled, with explicit unavailable text;
the native generic remote action path still refuses submission. The existing
local fixture HOLD flow continues to require fresh face verification. It never
constitutes physical Pi execution. Device/base output adjustments are deferred.
Existing live telemetry covers collected request/audit events, not all network packets.

## Verification actually run

| Command/check | Result |
| --- | --- |
| `npm run check` | Typecheck, lint, 117 frontend tests, 8 script tests and web build passed |
| `npm run test:python` | 166 passed; two existing dependency warnings |
| `CARGO_NET_OFFLINE=true npm run test:rust` | 44 passed, one intentional live Ollama ignore |
| `.venv/bin/python -m pytest tests -q` | 362 passed, 266 subtests, one optional serial dependency skip |
| `.venv/bin/python -m pytest tests/test_first_light_serial.py -q` after pinned pyserial provisioning | 31 passed, 18 subtests passed in 1.19s |
| Playwright `console.spec.ts`, isolated port 1432 | 5 passed: local HOLD failure/retry, immutable DENY/reconciliation, context reassessment, responsive layout |
| `npm run test:e2e:runtime` | 1 passed: real mock-Pi updates, history replay, disconnect/reconnect and disabled live approval |
| `scripts/biometrics/smoke_native_identity.py` | Actual public-image ArcFace inference and no-face/multiple-face rejection passed; retired renderer IPC rejected |
| `CARGO_NET_OFFLINE=true npm run build:app` | Release macOS `ALICE.app` and Swift camera helper built successfully |
| Source preservation / protected-file comparison | Original 423-path manifest/HEAD/status unchanged; protected team runtime paths unchanged |
| `git diff --check` | Passed |

The core suite needed an isolated local environment with the team's pinned audit
and anomaly dependencies plus pytest/subtests; missing-dependency attempts were
setup failures, not product acceptance. The live-review WIP's separate test results
are not counted toward this delivery.

The built app is at
`apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app` in the integration
worktree. Models, service environment and private credentials are separately
provisioned; the app bundle is not committed or deployed. See the
[setup guide](../guides/console/facial-verification-quickstart.md).

## Remaining acceptance

A person still needs to exercise this integrated build's camera permissions,
automatic enrollment, restart persistence, angled login, cancellation and fresh
local fixture approval on their Mac. Earlier user-reported successes and a friend
rejection belong to the original branch and are historical evidence only. Synthetic
pose/PAD tests do not establish physical anti-spoof accuracy or iPhone-equivalent
behavior. Live Pi proof delivery/review, full packet telemetry and deployment remain
outside this PR. The latest main's new MCP/cloud services are preserved unchanged;
no provider-backed cloud or physical-hardware acceptance was run here.

## Changed-file inventory

Generated against the authoritative main baseline; private files and build outputs
are excluded. The separate continuation handoff written by another task is not
included in this delivery commit.

- `.env.example`
- `apps/desktop/src-tauri/Cargo.lock`
- `apps/desktop/src-tauri/Cargo.toml`
- `apps/desktop/src-tauri/build.rs`
- `apps/desktop/src-tauri/src/biometric_camera.swift`
- `apps/desktop/src-tauri/src/biometric_capture.rs`
- `apps/desktop/src-tauri/src/biometric_commands.rs`
- `apps/desktop/src-tauri/src/biometric_sessions.rs`
- `apps/desktop/src-tauri/src/commands.rs`
- `apps/desktop/src-tauri/src/commands_tests.rs`
- `apps/desktop/src-tauri/src/config.rs`
- `apps/desktop/src-tauri/src/db.rs`
- `apps/desktop/src-tauri/src/lib.rs`
- `apps/desktop/src-tauri/src/security.rs`
- `apps/desktop/src-tauri/tauri.conf.json`
- `apps/desktop/src/components/biometrics/ApprovalModal.tsx`
- `apps/desktop/src/components/biometrics/CameraCapture.tsx`
- `apps/desktop/src/components/biometrics/biometrics.css`
- `apps/desktop/src/components/layout/SettingsModal.tsx`
- `apps/desktop/src/components/status/SystemPanel.tsx`
- `apps/desktop/src/components/technicians/AdminPanel.tsx`
- `apps/desktop/src/components/technicians/IdentityPanel.tsx`
- `apps/desktop/src/features/biometrics/verify.ts`
- `apps/desktop/src/lib/native.ts`
- `apps/desktop/src/state/console.ts`
- `current.md`
- `docs/README.md`
- `docs/guides/biometrics-service.md`
- `docs/guides/console/facial-verification-quickstart.md`
- `docs/guides/live-face-third-party-notices.md`
- `docs/handoffs/2026-09-06-upstream-checkpoint-before-face-integration.md`
- `docs/implementation-tracker.md`
- `docs/integration/upstream-alice.md`
- `docs/reports/2026-09-06-live-face-main-integration.md`
- `docs/scripts/biometrics.md`
- `package.json`
- `packages/contracts/src/biometrics.ts`
- `packages/contracts/src/index.ts`
- `packages/domain/src/biometrics.ts`
- `packages/ui/src/index.tsx`
- `scripts/biometrics/setup_live_models.py`
- `scripts/biometrics/setup_model.py`
- `scripts/biometrics/smoke_live_camera.py`
- `scripts/biometrics/smoke_native_identity.py`
- `scripts/console/desktop.mjs`
- `scripts/console/tests/locations.test.mjs`
- `services/biometrics/app/engine.py`
- `services/biometrics/app/live_contract.py`
- `services/biometrics/app/live_models.py`
- `services/biometrics/app/main.py`
- `services/biometrics/app/pad.py`
- `services/biometrics/app/pose.py`
- `services/biometrics/app/sessions.py`
- `services/biometrics/app/storage.py`
- `services/biometrics/requirements-live.txt`
- `services/biometrics/tests/fixtures/minifasnet-v2-golden.json`
- `services/biometrics/tests/test_engine_observations.py`
- `services/biometrics/tests/test_generation_removal.py`
- `services/biometrics/tests/test_live_biometrics.py`
- `services/biometrics/tests/test_live_workflow.py`
- `tests/console/dashboard.test.tsx`
- `tests/console/enrollment-recovery.test.tsx`
- `tests/console/identity-acknowledgement.test.tsx`
- `tests/console/live-biometrics.test.tsx`
