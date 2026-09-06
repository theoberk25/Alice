# Automatic USB → Wazuh delivery

September 5 EDT / September 6 UTC 2026. Branch `codex/wazuh-log-sync` based on
main `44f4d73`. Continues the [76-event maintenance proof](2026-09-06-wazuh-ledger-sync.md).

## Implemented

An in-process worker shares the Pi runtime's AuditLog and lock, performs HTTPS
outside the lock, persists delivery attempts/acknowledgements and retries with
bounded backoff. Sustained outage probes do not spend ledger attempts. Restart
scans the persistent ledger from zero and skips acknowledged records. No events
are pruned, overwritten, or relabelled as reconciled. The read-only `/sync-status`
endpoint exposes worker state without credentials or new action authority.

## Physical deployment and proof

Jared explicitly selected ext4 at `/mnt/alice-usb`. The previously unmounted
58.6 GiB USB, serial `24262706`, old UUID `6C1A-C6EA`, was checked and formatted.
New UUID: `0742aa3f-38fe-44aa-a382-9be9c4d9bb52`. A persistent fstab entry uses it.

With the old writer stopped, its ledger was backed up and copied using SQLite's
backup API; evidence and the existing signed release were copied to USB. No
new ledger identity or signing key was generated. Private keys remain on internal
storage. The original internal ledger and a private migration backup were retained.
The runtime, USB guard and uploader modules were deployed, and the new
`alice-runtime.service` was installed/enabled with a mount dependency.

Observed service: active, PID 10321. Worker initially IDLE, delivered 0.
A signed `elec-agent-01` light-on request from Jared's Mac:

- Request: `2ba62d25-7da7-47f2-a775-e126ac46e7d3`.
- First response: HTTP 200, ALLOW, PERMITTED_NORMAL_AUTO, COMPLETED, observed on.
- Identical retry: HTTP 200, recorded-outcome replay.
- Mock controller command count: 10 → 11, exactly one new execution.
- Worker subsequently reported 7 delivered, no error, last event `.observed`.
- Independent Wazuh count: **83 total**, **7** matching this request ID.

Thus a newly admitted action was logged to the mounted USB and uploaded to Wazuh
without stopping the runtime or manually invoking the maintenance CLI.

## Tests and boundaries

Full Python suite after worker/runtime integration: **297 passed, 226 subtests**
in 20.65 seconds. After the final prolonged-outage probe refinement, the focused
uploader/worker suite: **21 passed**. It includes a 70-step simulated outage with
only one persisted delivery attempt, restart recovery, owner-lock release during
network I/O, storage loss before acknowledgement, conflicting records not starving
later events, thread shutdown and exhausted-attempt retention.

A live outage test was staged but **not executed**: automatic approval review
rejected its SSH execution because of account usage limits. Therefore the Pi's
hostname mapping was not altered, no outage test action was sent, and real-network
reconnect recovery remains unverified. The staged request ID
`b0c3167c-67d7-478e-bbcc-aa45e5afb91d` is not evidence of an executed action.
No reboot, unplug, power-loss, real ML or physical actuator acceptance is claimed.
The running mock controller remains a non-boot-persistent tmux session.

## Next joint test

Once privileged tool access is restored: exercise a bounded Wazuh-only outage,
verify the Pi still handles requests and USB records remain pending, restore the
connection, and observe autonomous delivery with no duplicate controller command.
Then test service restart and absent-USB fail-closed behavior in a maintenance window.
Do not run the maintenance writer beside the service or switch back to the stale
internal backup without an explicit reconciliation procedure.

Teammates can consume `/events` and `/sync-status`. Actual technician accept/prevent
commands are **not implemented by this upload worker**. The next integration must
bind an authenticated/biometric response to the held request, revalidate execution
prerequisites on the Pi, execute at most once, and audit both acceptance/rejection
and the actual result. Avoid adding a dashboard button that bypasses that protocol.

## Publication checks and repository placement

Fresh pre-publication regression: `pytest tests --ignore=tests/console -q`: **297
passed, 226 subtests passed in 22.18 seconds**, including the final outage probes.
Runtime remains in `dcamr/` and `cloud/`; maintenance CLI in `scripts/lab/` through
the existing `lab.*` namespace; tests in `tests/`; deployment unit in
`services/systemd/`; all detailed Markdown in `docs/`. No source moves were needed.
Changed Markdown links resolve; current.md is within both limits; git diff --check
passes. No private credentials, live ledger or signing seeds are part of publication.
The [team handoff](../integration/esp-technician-handoff.md) supplies actual interface
examples and explicitly separates pending technician/grid work from tested behavior.
