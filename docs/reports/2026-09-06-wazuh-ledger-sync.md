# Wazuh ledger delivery live proof

Date: September 5 EDT / September 6 UTC 2026. GitHub backend/storage main
`44f4d73` merged into `codex/wazuh-log-sync` at `4eb6238`, preserving earlier
Jared first-light/network reports. [Integration contract](../integration/wazuh-audit-sync.md).

## What ran

The existing Pi runtime was stopped for exclusive ledger ownership. The bounded
uploader read `/home/pi/first-light/pi-data/ledger.sqlite`, using the existing
private signing key on the Pi. It delivered to Jared's Wazuh 4.14.7 indexer over
the wired LAN using verified TLS and a dedicated service account. Only the two
new sync Python modules were staged on the Pi; its full runtime was not upgraded.

Initial upload attempts received authorization errors and remained queued. Wazuh
reported missing `indices:data/write/bulk[s]`; adding that permission exclusively
to `alice-ledger-v1` fixed delivery. No failed records were dropped or acknowledged.
The client now stops a batch on global outages/auth failures rather than spending
an attempt on every event. That refinement passed its local regression test and was staged on the Pi after
the successful live passes; the action runtime remained running.

Results from `python -m lab.wazuh_sync`:

| Pass | Scanned | Newly acknowledged | Previously acknowledged | Errors |
| --- | ---: | ---: | ---: | ---: |
| Initial successful probe | 1 | 1 | 0 | 0 |
| First page | 64 | 63 | 1 | 0 |
| Remaining page (`--after 64`) | 12 | 12 | 0 | 0 |
| Replay first page | 64 | 0 | 64 | 0 |
| Replay remaining page | 12 | 0 | 12 | 0 |

Every new acknowledgement followed exact canonical read-back verification of the
stored document. An independent `GET /alice-ledger-v1/_count` returned **76**.
The original `runtime` tmux session was restarted with its original signed
`jared-2` release, internal data directory and mock ESP URL. Afterwards:
`GET /events?after=76` returned `{"events": []}`; mock ESP stats stayed at
**10 commands**, and both `runtime` and `esp` tmux sessions were present.

## Automated checks

Final Python suite including the batch-stop refinement:
`.venv/bin/python -m pytest tests --ignore=tests/console -q`:
**290 passed, 226 subtests passed in 21.08 seconds**.
The new `tests/test_wazuh_audit.py` suite contains **14 passing tests**.
Checks cover lost receipts, retry after reopen, exact-content conflicts, bounded
pages, unsigned records, existing destinations, USB guard failure after remote
write, offline persistence and skipping acknowledged events without network I/O.

## Limits and next integration

The source was the live first-light **internal** ledger, not physical USB.
USB `/dev/sda1`, UUID `6C1A-C6EA`, remains unmounted. First-light assessment is a
fixture and the actuator is mocked. Automatic reconnect scheduling, owner-integrated
background delivery, semantic reconciliation, evidence blob uploads and enterprise
permissions/baseline publication remain. Technician transport belongs to teammates.
No simulated human Wazuh account was created and no permission grants were altered.
Service credentials and CA material stay in ignored/private local state.
