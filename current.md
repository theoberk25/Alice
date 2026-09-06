# Current
Updated: 2026-09-06 EDT.
Baseline: Theodore Berk's `upstream/main` at `f79cd8e007d02c5abc7b4dffce146e882a51774a`.
Delivery branch: `codex/live-face-upstream-integration`.
Objective: deliver the completed live facial upgrade on the latest team main;
keep unfinished live HOLD review separate and preserve newer team behavior.

## Delivery scope

- Native automatic camera, multi-pose enrollment, ArcFace gallery login, MediaPipe
  pose, MiniFAS presentation checks, encrypted generations and stale/replay guards.
- Enrollment rotates once; login and fresh local fixture approval are automatic.
  Success animation and camera cancellation/lifecycle fixes are retained.
- Deepfake detection is excluded. No detector models, interfaces or fallbacks.
- New team dashboard, read-only live feed, MCP/cloud agents, LLM, Pi/core, hardware,
  network, common contracts and package versions are preserved.
- Live HOLD approve/reject controls remain unavailable. Local fixture approval
  still requires fresh facial verification; it does not command the Pi.
- Unfinished live review is saved locally as `codex/live-runtime-review-wip`
  at `aa5bae8`; it is not part of the delivery or authorized for deployment.
- Original `codex/live-facial-biometric-upgrade` remains at `0063629` with its
  complete uncommitted work unchanged. Backup metadata is under `.tools/`.

## Evidence and limits

Current delivery checks: 117 frontend, 8 script, 166 biometric service and 44 native
Rust tests passed; one live Ollama test intentionally ignored. Core: 362 passed,
266 subtests, one optional serial check initially skipped (follow-up result in report).
Five console E2E tests and one real mock-runtime feed E2E passed. Typecheck, lint,
web build and macOS `ALICE.app` build passed. Public-image ArcFace inference and
retired renderer-frame IPC rejection passed. No integrated human camera acceptance,
physical Pi review, packet-wide monitoring or hardware deployment is claimed.

Historical physical team configuration and evidence are preserved in the
[prior checkpoint](docs/handoffs/2026-09-06-upstream-checkpoint-before-face-integration.md)
and existing [demo runbook](docs/guides/demo-runbook.md). Do not infer new deployment
or authority changes from this source integration. Owners are unassigned.

## Next steps

1. Review the biometric delivery PR; no main merge is authorized.
2. Teammates provision private local models/settings and exercise the built native app.
3. Repeat live enrollment, restart, angled login and fresh local approval with a person.
4. Continue saved live HOLD review separately after delivery; device outputs stay deferred.

[Delivery report](docs/reports/2026-09-06-live-face-main-integration.md) ·
[Facial setup](docs/guides/console/facial-verification-quickstart.md) ·
[Tracker](docs/implementation-tracker.md) · [Rules](AGENTS.md)
