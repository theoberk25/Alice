# Rebuilt native app for popup testing

2026-09-06. User requested rebuilding the merged .app to sign in and test HOLD
approval/context popups. Baseline `498ebcd` retains Theo main `d5a0d56`.
Follow [working rules](../../AGENTS.md) and [current status](../../current.md).

## Test profile and preservation

The merged app is built under this integration worktree's standard
`apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`. Its private `.env`
selects mock request transport, real ArcFace, and manual context for popup testing.
The original checkout `.env`, native database, running local rehearsal and Dock
bundle remain unchanged. The previous merged bundle is preserved in ignored
`.tools/popup-testing-20260906/pre-popup-ALICE.app`.

SQLite backup created a preserved snapshot and a separate disposable test console
under ignored `.tools/popup-testing-20260906/`. Only the disposable copy's decision,
action, annotation, local-audit and runtime-submission tables were emptied before
launch; the original database was never reset. Enabled identity records (2), saved
enrollment metadata (1), settings and administrator hashes were retained. No raw
face frames, vectors, models or keys were copied. The existing ArcFace service
and encrypted enrollment store are shared, not replaced. Private directory/config/
database modes are 0700/0600; no private files are committed.

## Small testing-only change

`VITE_ALICE_MANUAL_CONTEXT_DEMO=true` opts mock requests into waiting for a manual
context click, avoiding the fixture's normal response arriving before real sign-in.
The profile exposes the existing scenario/reset controls in the packaged app and
labels pending context accurately. It defaults off, cannot enable remote context
delivery, does not change native auth/approval guards, and adds no dependency.

Sign in with the existing enrolled username. Request context before approval to
see the response and pending state; approval then obtains a separate fresh scan.
Use the sliders button → Reset scenario to repeat. Context uses an inline response
panel; it does not open a new free-text popup. Live Pi context delivery remains
unimplemented in the team baseline.

## Verification

- `npm run check`: passed with 192 frontend tests and 8 script tests, typecheck,
  lint and web build; explicit final normal-profile check also passed.
- Two unit regressions cover waiting through sign-in, explicit context delivery,
  immutable HOLD and remote rejection.
- An opt-in browser case covers 30-second waiting, correct pending copy, context
  response, simulated approval and scenario reset. Initial run passed.
- Normal profile browser suite: 31 passed; the opt-in case is skipped there.
- Manual profile browser case: 1 passed, including pending copy/context/approval/reset.
- Final `npm run build:app`: passed; app gracefully reopened on the final bundle.
- Final native accessibility first showed Sign in / IDENTITY REQUIRED, then the
  user signed in and continued testing. Retained research/context remained visible
  with the original HOLD; Approve once remained available. No user scan or approval
  was performed by the assistant.
- Authenticated local biometric `/health`: READY / ArcFace. Token was not exposed.
- Native app launched; accessibility showed SIMULATION, real camera verification,
  the signed-in account, a HOLD and enabled Request more context / Approve once.
  User facial matching and user approval are not asserted as automated checks.

No native/Rust or Python implementation changed. Their prior integration results
remain historical; real camera quality and physical Pi acceptance are separate.
