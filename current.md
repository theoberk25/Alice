# Current
Updated: 2026-09-06 EDT. Owners unassigned.
Branch: `main`.
Team baseline: `41bbd045c35a2f8ebc59649d3ffb69394cd0fc4f` (latest fetched main before this update).
Initial integration checkpoint: `4b1f67e`, based on previous team main `4531277`.
Preserved redesign: `db730710750787af9064b495c6a236e0b504b2fe`.

## Active objective

Integrate the complete local redesign onto Theo's current main while preserving
all teammate content, contracts and behavior. Integration is complete; [PR #7](https://github.com/theoberk25/Alice/pull/7) is open for user merge. The user
requested the live-runtime app after testing. The rebuilt app is now open in
remote/ArcFace mode with the original saved database and feed. Popup profile is preserved.
[Popup setup/evidence](docs/reports/2026-09-06-popup-testing-app.md).
Worktree: `artifacts/console/main-redesign-integration` within the original checkout.
[Integration evidence](docs/reports/2026-09-06-main-redesign-integration.md).

## Scope and preservation

- Source commit includes closed/unmerged PR #6 and all later tracked/untracked work.
- Motion/Anime, themes, responsive shell, device clock, account/Face ID presentation
  and the existing narrow biometric/rehearsal fixes are carried forward.
- Team context-request guards/fifth action, fan review/schema/native additions and
  all newer thermal, enterprise, runtime and firmware implementation are preserved.
- Late telemetry alignment is included: battery units, LED roles and updated team
  docs/tracker row 035. [Team checkpoint](docs/handoffs/2026-09-06-before-telemetry-redesign-merge.md).
- The original checkout, private settings/models/stores and running services remain
  separate. The rebuilt integration app now uses the saved live-runtime profile;
  the original Dock-linked bundle and live profile remain unchanged. No deployment.

Latest team Pi deployment, USB/Wazuh and exhausted-light behavior are retained
unchanged. [Team checkpoint](docs/handoffs/2026-09-06-before-pr-thermal-deployment-merge.md).
Live readiness recheck: corrected the Pi MCP upstream to runtime port `8080` and
poller clients to MCP port `8790`; authenticated MCP metrics now pass from the
configured 90 F / 60% fan / 60% battery READY state.
Enterprise presentation now uses the DN-Hacks energy-infrastructure scenario.
The local Wazuh index contains 434 idempotent labelled scenario records spanning
authentication, vulnerabilities, MITRE ATT&CK, configuration assessment, file
integrity and ALICE agent governance; actual Pi ledger evidence remains separate.
Demo runbook now records thermal feed authentication and the agent's loopback MCP
forward; disabled metrics pollers remain optional for direct MCP clients.
The enterprise ingress now accepts the signed thermal fan contract, records and
reads back its Wazuh receipt, retains it on Pi USB, then forwards unchanged through
the enterprise host's SSH tunnel. The SIEM exposes those receipts as enterprise requests.

## Evidence and blockers

Latest upstream merge: repository Python543 and266 subtests passed.
Latest popup build: frontend192/scripts8/check and app build passed; default
browser31 plus the opt-in popup case passed. Historical popup app validation complete; real Face ID service READY.
Live profile restored and app reopened at sign-in. Saved feed HTTP200/22 events,
local-runtime with mock controller; physical Pi connection is not established.
Historical integration: frontend190/scripts8/browser31/native62 passed;
biometrics176 passed (1 model skip), repository Python541 and266 subtests passed.
Native2 opt-in tests ignored. Typecheck/lint/web build/native app build passed.
No software blocker remains; prior source/team results remain historical.
Real-camera, physical Pi and native visual acceptance remain outside automated tests.
The pre-merge checkpoints are preserved for both
[source](docs/handoffs/2026-09-06-before-redesign-integration-source.md) and
[team](docs/handoffs/2026-09-06-before-redesign-integration-team.md).

## Next steps

1. Sign in to the reopened live-runtime app to connect to the saved feed.
2. Perform real-camera/native appearance and physical-Pi operator acceptance.
3. User reviews/merges PR #7; keep the Dock app unchanged.
4. Use the Wazuh-backed enterprise console for the connected-mode demo rehearsal.
5. Live-test one cloud fan request through Wazuh, Pi decision, USB and ESP telemetry.

[Rules](AGENTS.md) · [Tracker](docs/implementation-tracker.md) ·
[Design sources](docs/guides/console/visual-sources.md) ·
[Original transfer handoff](docs/handoffs/2026-09-06-new-repository-merge.md)
