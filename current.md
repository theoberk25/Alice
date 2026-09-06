# Current
Updated: 2026-09-06 EDT.
Baseline: local checkout `e1e7506`; Pi review upgrade from this source on 2026-09-06.
Active checkout: `/Users/jaredviani/Desktop/Alice`; branch `codex/wazuh-log-sync`.

## Active objective

Native backend integration is the active major project. Locally implemented: collected request
and audit visibility, exact supplied details, immutable decisions, fresh-face
approve/reject of eligible OFFLINE ALICE-owned HOLDs, and separate acknowledgment,
execution and observation. No deepfake work or device-output adjustments.

## Current state

- Root is the sole registered worktree. Original biometric/WIP and verified source
  snapshots remain on named backup branches; private settings/models are preserved.
- Biometric PR #4 merged at `d57c660`; local commits now include the subsequent
  upstream wireless/fan roadmap and pitch deliverables. No duplicate biometric commits.
- Published to `Adaoud03/Alice:main` at the user's request; upstream [PR #5](https://github.com/theoberk25/Alice/pull/5)
  contains the implementation, evidence and limitations. Upstream merge is pending.
- Native/web share collected history, evidence and explicit freshness. Native adds
  exact retained requests and signed fresh-face approve/reject through the existing
  bridge, Pi ledger and execution path, with durable uncertain-delivery reconciliation.
- The built app is open for a local personal rehearsal with the existing enrollment;
  real facial service is ready. Controller/assessment are labeled mock/fixture.
  Dock/Finder launches now use the same saved remote settings; sign-in starts the feed.
  `npm run demo:hold -- --session /private/tmp/alice-native-personal-20260906-01/session.json`
  sends another signed, unexecuted test HOLD; final helper checks: 12 passed.
- Working scope is first-light `set_light_state`, fixed OFFLINE ALICE authority.
  Enterprise handover/reads, live brief/model factors and fan adapters remain upstream
  integration work. Device adjustments stay deferred. Owners are unassigned.

Pi deployment: review runtime installed with `merek-console-01` trust for
`merek.soriano`, `TECH-DEMO` and `Tech-2` (updated trust, same public key). Existing USB ledger, ESP serial and Wazuh settings
retained; pre-upgrade code is in `/home/pi/first-light/review-upgrade-20260906`.
Local review tests: 64 passed. Live `merek-live-allow-071902`: ALLOW, ESP
COMPLETED/ON, ledger sequences 630–636. Invalid target rejected at schema validation.
Merek confirmed live ALLOW/COMPLETED/ON display and disabled review controls.
Wazuh reports TRANSPORT_UNAVAILABLE/retrying; human camera→Pi→LED review
acceptance remains pending.

Synthetic fan corpus: 8,604 JSONL rows copied and hash-verified on Pi USB at
`/mnt/alice-usb/normal_behavior/fan-demo-20260906-v2/`. Two generator tests passed.
Fitting stopped at user request. Hybrid forest + nearest-normal candidate: 100%
recall on 3,000 fresh synthetic anomalies, 31/3,000 normal false positives (1.03%).
Data-only export verified; not activated on Pi. Six tests passed. [Usage](docs/guides/anomaly-training.md#fan-demo-jsonl-corpus-2026-09-06).

User confirms human HOLD approval turned the light on. Enterprise signed ingress
is live at `.50:8790`; Wazuh receipt now retained on USB before forwarding.
Seven ingress/cache tests pass; ML-triggered fan HOLD remains unimplemented.
Signed release generation 4 requires review for Yellow 1; both grants and agent
keys preserved. Backup: `/mnt/alice-usb/release-before-merek-review-004`.

## Evidence and limits

Core: 435 passed and 266 subtests. Biometrics: 166 passed. Rust: 60 passed plus
one opt-in real Rust→Python bridge/runtime test; approve/reject/replay produced one
mock command. Frontend: 134 tests plus eight script checks; eight UI E2E and one
real web/runtime E2E passed. Typecheck, lint, web/native builds passed.
Cross-language proofs, cancellation, replay, restart, concurrency and uncertainty
have automated evidence. No human camera→Pi/hardware acceptance or live Ollama test.
Telemetry covers collected ALICE request/audit traffic, not every network packet.
Verified preservation includes the concurrent Desktop auto-stash recovery; tracked
source is committed and published to the fork. Those implementation-session results preceded the Pi deployment recorded above;
no physical action was issued during this deployment.

## Next steps

1. Fitting paused at user request; retain hybrid candidate for later integration.
2. Connect Merek’s native bridge and record fresh-face physical approve/reject acceptance.
3. Coordinate enterprise authority/feed, real model/context and fan contracts before
   implementing the broader [upstream demo](docs/guides/demo-runbook.md).

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Workspace recovery](docs/handoffs/2026-09-06-native-live-backend-workspace.md) ·
[Ready handoff](docs/handoffs/2026-09-06-native-live-backend-ready.md) ·
[Parity](docs/plans/native-live-backend-parity.md) ·
[Validation](docs/reports/2026-09-06-native-live-backend-validation.md)
