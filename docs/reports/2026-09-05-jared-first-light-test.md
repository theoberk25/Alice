# First-light test from Jared's Mac

Baseline checkout: `7081b6a`. Executed against alice-pi-01 at 192.168.50.20:8080.
Mac Ethernet: 192.168.50.50/24, router unset. SSH host fingerprint verified
against the independently supplied ED25519 fingerprint before access.

## Demo key provisioning

The original private terminal seed was unavailable. Prepared and verified a new
signed demo release, `first-light-jared-2`, replacing only elec-agent-01-k1's
public key. Grants, subjects and other terminal public keys were preserved.
The replacement manifest uses a new demonstration signing key. Only public
release/trust files were transferred to ~/first-light/jared-2/ on the Pi.
Private seeds remain in the ignored artifacts/local-state/jared-first-light/client/
directory on Jared's Mac with restricted permissions; do not commit them.

Runtime restarted in tmux session runtime with the new release and trust key,
existing ~/first-light/pi-data audit directory and http://127.0.0.1:8090 mock ESP.
The original ~/first-light/release and trust directories remain available.
No application code was changed or deployed in this operation.

## Observed result

Command: lab.first_light.terminal_client, agent elec-agent-01, state on, repeat 2.
Request ID: `072b8ef7-897e-45dc-8163-996771177261`.
Identity resolves to simulated user ssgt.a.okafor, not Jared's personal identity.

- First send: HTTP 200, ALLOW, PERMITTED_NORMAL_AUTO, COMPLETED, observed on.
- Retry: same request ID, replayed recorded outcome.
- Mock ESP /stats: 8 commands before, 9 after — exactly one additional execution.
- Seven correlated events verified: REQUEST, ASSESSMENT, DECISION,
  EXECUTION_ATTEMPT, CONTROLLER_RECEIPT, EXECUTION_RESULT, OBSERVED_STATE.
- Pi read-only events endpoint returned HTTP 200 after restart.

This verifies wired request authentication, first-light permission handling,
fixture assessment, mock execution and ledger event visibility. It does not
verify a physical light, real anomaly inference, USB export for this request,
or technician approval. Theo's dashboard has not been launched from this Mac.

## Technician setup

On Theo's Mac, use Ethernet 192.168.50.10/24 (its existing assigned address).
From the updated repository root, install dependencies if needed with npm ci,
then run:

```sh
VITE_ALICE_PREVIEW_MODE=remote VITE_ALICE_EDGE_URL=http://192.168.50.20:8080 npm run dev
```

Open http://127.0.0.1:1420/. This first-light dashboard is a read-only observer;
it cannot approve or execute actions in this slice.

## Additional live checks before storage integration

Request: `8d84aa34-8d4c-4b52-b0f8-a59fec9738aa`. Ran seven bounded requests; the valid action
was state on against the existing mock ESP.

| Check | HTTP | Reason | Round trip ms |
| --- | --- | --- | --- |
| invalid signature | 401 | SIGNATURE_INVALID | 75.1 |
| unknown key | 401 | UNKNOWN_KEY | 74.8 |
| authenticated key claiming another agent | 401 | AGENT_KEY_BINDING_MISMATCH | 59.5 |
| malformed envelope | 401 | MALFORMED_ENVELOPE | 72.7 |
| valid on request | 200 | PERMITTED_NORMAL_AUTO | 622.8 |
| identical replay | 200 | PERMITTED_NORMAL_AUTO | 5.2 |
| same ID different signed content | 409 | REQUEST_ID_CONFLICT | 4.7 |

Verified 11 new events: four unauthenticated REJECTIONs and the seven-event
successful chain. Identical replay and conflicting-ID response produced no
additional events. Resume after the last event returned an empty page. Mock ESP
commands increased from 9 to 10: one execution across the whole test set.
Theo's visibility of this additional batch has not been independently confirmed.

Read-only SQLite quick_check returned ok (database integrity, not cryptographic
chain verification). Runtime RSS sampled at 43,820 KiB (~42.8 MiB); whole-Pi
available memory ~1,605 MiB, swap unused. Single-request latency is a spot check,
not a percentile benchmark; it includes signing verification, ledger and mock
execution, and does not isolate model scoring (still a fixture).

Follow-up: REQUEST_ID_CONFLICT is rejected but not audited in the current runtime.
Decide how the backend records authenticated rejected attempts without mutating
original decisions. Do not manufacture a second execution record for a retry.

USB remains unmounted exFAT, UUID 6C1A-C6EA, 58.6 GiB. Erasure is user-authorized,
but filesystem/mount contract is still pending with the storage teammate. Main
fetch returned no newer commit at this checkpoint (local baseline 7081b6a).
Preserve ~/first-light/pi-data including its ledger signing seed and evidence;
preserve ~/first-light/jared-2 and the old release/trust during deployment.
First backend checks: actual mount identity, read-only decision access to accepted
packages, durable audit storage/export, restart persistence and unavailable-drive
behavior. Do not change these storage contracts before reviewing the incoming code.
