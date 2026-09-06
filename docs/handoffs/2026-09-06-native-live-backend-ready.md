# Native backend ready for local operator acceptance

September 6, 2026. Follow [working rules](../../AGENTS.md).
Use `/Users/alexdaoud/Documents/Alice` and `codex/native-live-backend` in GitHub
Desktop. Root is the only registered checkout. All implementation is committed;
ignored private recovery storage, environments and build outputs are intentional.

## Delivered locally

The [parity inventory](../plans/native-live-backend-parity.md) identifies executable
web endpoints and unavailable producers. Native retains collected ALICE history,
audit evidence and reconnection, adds exact retained request details, and supports
fresh-face approval/rejection of eligible first-light HOLDs. Proofs bind the exact
request, original decision, action, permission/release, nonce, current authority
and technician session. The Pi verifies and durably admits consent before using
its existing execution method. Rejection never calls that method. Native saves
submission identity before sending and reconciles uncertain outcomes by read only.

Focused commits cover workspace preservation, Python/bridge contracts, native
authority, shared UI, local operator tools and evidence. Original WIP `aa5bae8`
was selectively adapted; its incomplete implementation and already-delivered
cleanup were not blindly cherry-picked. Original biometric and WIP references,
source snapshots and independent recovery bundles remain available in the
[workspace record](2026-09-06-native-live-backend-workspace.md).

Core, biometric, native, frontend and web/renderer end-to-end tests and the actual
macOS app build passed. See the [validation report](../reports/2026-09-06-native-live-backend-validation.md)
for exact commands, counts, superseded failures and scope. Automated face-session
fixtures and a mock controller do not establish human-camera or physical acceptance.

## Personal test prepared

The built app is at
`apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app` and was opened using
the existing enrolled `console-mock.sqlite3`, explicitly selected for remote mode.
Both original external native stores were backed up through SQLite and checked
before launch. The existing biometric service on loopback port 8766 reports
READY for identity, pose and presentation checks. No camera scan was performed.

The running local rehearsal uses private directory
`/private/tmp/alice-native-personal-20260906-01`. It creates two synthetic HOLDs
with unique IDs beginning `native-test-approve-` and `native-test-reject-` from a
signed approval-required fixture release. Its controller is mock; no physical Pi
or remote trust is involved. Native viewing waits for technician sign-in.
Choose **Sign in**, then follow the [operator sequence](../guides/native-runtime-review.md).
Enrollment rotation is not repeated during login or review.

To send a new simulated Pi-side HOLD into this running app:

```sh
cd /Users/alexdaoud/Documents/Alice
npm run demo:hold -- --session /private/tmp/alice-native-personal-20260906-01/session.json
```

This sends a fresh signed agent request to the local Pi-runtime simulation. It
prints its request ID and confirms `CHALLENGE` / `NOT_EXECUTED`; native review
still requires the person's fresh face and explicit approve/reject choice.
The command was verified once on the running session: events rose from 11 to 14,
while mock commands stayed at one. This added request caused no new execution.

The rehearsal terminal accepts `hold`, `status` and `stop`. It remains running
for the personal test, alongside the facial service. `stop` shuts down the app
and local mock/runtime/bridge; the data remains private. A later session can use
the guide to start a new directory. The private `session.json` includes a bearer
and must not be shared. Root `.env` was not modified during initial delivery.

### Dock/Finder launch follow-up

On the user's subsequent request, the Dock entry was verified to point to this
checkout's exact built `ALICE.app`. Its different behavior came from `.env` still
selecting mock transport, while the initial rehearsal used process overrides.
The original `.env` was preserved byte-for-byte in private recovery storage as
`env-before-dock-live-015407.env`. The same active rehearsal feed, enrolled database,
console key and remote/ArcFace settings are now saved privately in `.env`.
No credentials were added to the app bundle or committed documentation.

A fresh direct app launch was verified to open remote mode rather than the
fixture console. The feed waits for technician sign-in. The configured backend
is still the local mock-Pi rehearsal and must remain running; a stopped backend
shows unavailable rather than falling back to fixtures. Physical Pi communication
uses the existing authenticated bridge and a separately established SSH tunnel.

## Latest upstream retained

Biometric PR #4 is merged at `d57c660`. A final fetch found `de6c6cb`, the wireless
DDIL fan-demo documentation update. All local commits were rebased onto it; an
additional `codex/backup-native-before-upstream-20260906` reference preserves the
pre-rebase history. Non-Markdown Git blobs were compared and are identical across
the rebase, so the tested source/build remains applicable.

The upstream checkpoint reports the Opal at `192.168.50.1` with DHCP `.100-.199`,
Pi `.20` wired through it and direct venue Wi-Fi autoconnect disabled; Wazuh resolves
to the enterprise Mac at `.50`. USB uses `/mnt/alice-usb` with `pi-data` and `release`;
Wazuh uses `alice-ledger-v1` and its existing service account. Those are upstream
observations, not new hardware checks by this task. Existing light/USB/Wazuh
evidence is retained in the [demo runbook](../guides/demo-runbook.md).

Upstream next work remains stable DDIL addresses, authenticated cloud/cooling/power
identities and gateway/MCP deployment, fan training/calibration/evaluation and a
real forest, enterprise offline presentation, native supplied-factor explanation,
and router-loss/fan-shutdown/reconciliation acceptance. The new PRDs, tracker
SUP-10/SUP-11 and runbook are preserved. This task did not perform those operations.

## Remaining boundaries

The current executable runtime accepts first-light `set_light_state` requests and
uses fixed confirmed OFFLINE ALICE ownership plus fixture assessment. The native
proof protocol rejects ONLINE/enterprise-owned and unconfirmed authority; it does
not implement authority handover. The fan action/sensor/model adapters, enterprise
native read authorization, live Decision-Brief source and rich reassessment feed
are not available upstream. Do not substitute fixture output for those producers.

Native live history has a 16 MiB initial replay bound and reloads from the Pi after
restart; disconnected restart has no local history mirror. Telemetry covers
admitted ALICE requests/audit, not all network packets. Existing team UI, agent,
MCP, network, hardware and database implementations are preserved. Deepfake work
and device/base output-adjustment controls remain excluded.

No push, remote merge, deployment, remote trust provisioning or hardware operation
was performed. Real facial and separately authorized physical-Pi acceptance are
the next concrete external dependencies; no owner is assigned by this handoff.
