# Pi ledger → Wazuh audit delivery

This slice uploads original, sealed Pi ledger events directly to the enterprise
Wazuh indexer. The technician application is not a relay. Teammates continue to
own Pi ↔ technician transport and enterprise → USB cache publication.

## Integration boundary

The automatic runtime path is `cloud/wazuh_worker.py::WazuhWorker`, enabled by
`dcamr.main --wazuh-sync-config <private config>`. It shares the runtime's existing
`AuditLog` and owner lock. SQL preparation/acknowledgement happens under that lock;
HTTPS requests happen outside it. There is no second database connection or writer
service. The worker seals low-volume records, including isolated rejections.

The worker scans at most 64 records at a time and uploads one event per step.
It yields between steps, polls every five seconds when caught up, and backs off
60/120/240/300 seconds on delivery errors. After a failure, authenticated TLS
reachability probes do not spend further ledger attempts during a sustained outage.
This avoids exhausting each event's 64-attempt budget simply because Wazuh is down.
Exhausted/conflicting records remain retained; inspection is required for those
exceptional cases. The scan continues past a failed event so it cannot permanently
starve later records, wraps to zero, and resumes from zero after process restart.
Already acknowledged records cause no duplicate writes.

Shutdown stops the worker before closing the shared ledger. A local storage/signing
failure stops delivery and surfaces `STOPPED_ERROR`; USB guard failure remains
latched and local action admission fails closed. Network failure alone does not
block local action handling. Uploader reachability **does not switch execution
authority**: the current first-light runtime still labels itself OFFLINE/fixture.

`GET /sync-status` exposes non-secret worker status: `state`, process-local
`delivered`, `last_event_id`, `last_error`, and configured `retry_in_seconds` delay
(not a countdown). `IDLE` means a scan found no work; it does not assert that the
enterprise is reachable. There is no approval or permission-changing verb here.

`cloud/wazuh_audit.py` retains the bounded `sync_once` maintenance API and
`python -m lab.wazuh_sync` CLI. **Never run that CLI while the runtime/worker owns
the ledger.** Its `next_after` cursor is a scan position, not durable acknowledgement;
restart at zero after a failed pass. Existing outbox destinations are not reassigned.
Multi-destination delivery, evidence reconciliation, and permission/baseline
downloads remain separate integration work.

All delivery uses HTTPS certificate and hostname verification, five-second network
timeouts and responses capped at 128 KiB. No environment proxies or redirects.

## Automatic Pi deployment

The checked-in `services/systemd/alice-runtime.service` is the current **demo Pi
configuration**, with explicit deployment paths; adapt them for another machine.
It runs the existing runtime with automatic delivery, `Restart=on-failure`, private
file creation, and `RequiresMountsFor=/mnt/alice-usb`. On this Pi it is installed
and enabled as `alice-runtime.service`. Mount configuration is persisted by UUID.

Current physical layout (provisioned with explicit user approval):

- USB: ext4, `/mnt/alice-usb`, UUID `0742aa3f-38fe-44aa-a382-9be9c4d9bb52`.
- Ledger/evidence: `/mnt/alice-usb/pi-data/`.
- Verified signed release: `/mnt/alice-usb/release/`.
- Private ledger key: `/home/pi/first-light/pi-data/ledger_key.seed` (internal).
- Private service configuration: `/home/pi/first-light/wazuh-sync/config.json`.
- Original internal ledger remains an inactive backup, **not a fallback writer**.
- Migration backup: `/home/pi/first-light/pre-auto-sync-backup/` (private).

```sh
sudo systemctl status alice-runtime
journalctl -u alice-runtime --since '10 minutes ago'
curl http://127.0.0.1:8080/sync-status
findmnt /mnt/alice-usb
```

Stop the service before any maintenance writer. Restart it with
`sudo systemctl restart alice-runtime`, not a second tmux runtime. Reboot and
physical unplug/power-loss acceptance have not been performed. The mock ESP is
still in its previous tmux session and is not boot-persistent; replace it with
the team's real controller endpoint before claiming automatic action execution
across a reboot. Audit uploading itself does not require a controller response.

## Enterprise contract

- Index: `alice-ledger-v1`; outbox destination: `wazuh-ledger-v1`.
- Document ID: SHA-256 of canonical JSON `[node_id, ledger_id, event_id]`.
- Wrapper fields: `schema_version=alice-ledger-delivery-v1`, `node_id`, `ledger_id`,
  `event_id`, `event_hash`, `sequence`, `event_type`, `request_id`, `event`.
- `event` is the complete original canonical ledger object. Neither event content
  nor event hashes are rewritten. Evidence references survive; evidence blobs
  and independent checkpoint verification are not uploaded by this slice.
- Delivery uses `PUT /alice-ledger-v1/_create/<id>`, then real-time `GET /.../_doc/<id>`.
  A 201 or 409 is insufficient: acknowledgement requires an exact canonical match
  of the entire returned document. Conflicting content remains pending.
- Receipt binds destination, index, document ID, event hash and document digest.
  Delivery acknowledgement does **not** mean semantic reconciliation, execution
  approval, detection of a security incident or independent signature verification.

Pre-create the index with one shard and zero replicas for the single-node demo.
Use `dynamic: strict`; keyword mappings for the wrapper's strings, `long` for
`sequence`, and `event: {type: object, enabled: false}`. This retains raw evidence
without dynamic field explosion. Search/filter by wrapper fields; `_source` retains
all event fields. Production retention, replication and access controls remain
separate from this demo configuration.

A dedicated service role, `alice_ledger_sync`, is installed on this demo stack:

```json
{
  "cluster_permissions": [],
  "index_permissions": [{
    "index_patterns": ["alice-ledger-v1"],
    "allowed_actions": ["indices:data/read/get", "indices:data/write/index", "indices:data/write/bulk[s]"]
  }],
  "tenant_permissions": []
}
```

The Wazuh 4.14.7 write path required the shard bulk action even for single-document
create. This account has no permissions-publication, human dashboard, delete or
index-management role. The client uses create-only requests; index write privilege
is not a server-enforced WORM guarantee. Provision the index/role through the
enterprise administrator and retain credentials outside source control and USB.
This service is separate from the simulated operator `ssgt.a.okafor`/`elec-agent-01`.

## Pi maintenance command

Install the ledger dependencies (`cryptography`; see `requirements-audit.txt`).
Store a private mode-0600 configuration outside USB, with an absolute CA path:

```json
{
  "url": "https://wazuh.indexer:9200",
  "username": "alice_ledger_sync",
  "password": "<provisioned service secret>",
  "ca_file": "/home/pi/first-light/wazuh-sync/root-ca.pem"
}
```

Stop the runtime and establish exclusive ledger ownership first. The
`--runtime-stopped` flag is an operator assertion, not a process lock. Back up
and use the actual deployment paths; do not initialize or replace its ledger.

```sh
python -m lab.wazuh_sync \
  --usb-root /mnt/alice-usb \
  --data-dir /mnt/alice-usb/pi-data \
  --ledger-key-file /home/pi/first-light/pi-data/ledger_key.seed \
  --config /home/pi/first-light/wazuh-sync/config.json \
  --runtime-stopped --limit 16
```

USB mode uses the new mount guard, keeps credentials/signing key outside USB and
fails on lost storage without fallback. The sample data path must be coordinated
with the storage owner. For the existing internal-storage first-light test only,
replace `--usb-root ...` with `--local-test-storage` and use its existing data dir.
Always restart the original runtime afterward, including after failed delivery.
Do not run this CLI beside `dcamr.main` or an owner-integrated delivery worker.

## Current demo network and evidence

Pi `pi@192.168.50.20` maps `wazuh.indexer` to Jared's wired Mac `192.168.50.50`.
The indexer's leaf certificate names `wazuh.indexer`, not that IP. Python 3.13
rejected the demo CA's missing key-usage extension. The Pi trust bundle now uses
a CA certificate reissued locally with the existing CA key/identity and correct
critical CA/key-signing constraints. The Docker certificate/key files were not
changed. No private CA key was sent to the Pi and delivery verification remains
strict. Replace demo PKI with the deployment's managed CA when provisioning it.

[Live proof](../reports/2026-09-06-wazuh-ledger-sync.md): 76 real Pi records delivered,
76 replayed without duplicate writes; original runtime restored. That first proof used internal storage. The subsequent
[automatic USB proof](../reports/2026-09-06-automatic-usb-wazuh-sync.md) demonstrates
a new action automatically uploaded from ext4 USB. Power-loss durability, automatic
execution-authority handoff and semantic evidence reconciliation remain unverified.

The enterprise console's existing simulation audit cards and direct live-Pi feed
are different sources. Inspect `alice-ledger-v1` in Wazuh/OpenSearch to see this
synced stream; do not interpret the older 48 simulation records as Pi uploads.

## Integrated snapshot and acceptance continuation

The worker also passes local integration checks alongside the explicit signed
first-light SQL snapshot input, preserving original events and restart replay.
HTTP protocol/truncated-body errors now enter delivery retry rather than stopping
the worker as a local failure; malformed nested create receipts are rejected.
The shared `verify_stored(event)` method performs only exact-content GET verification.
The [joint acceptance helper](pi-technician-acceptance.md) uses it without uploading
or mutating delivery state. Existing physical service deployment remains unchanged
until the operator pulls and performs a coordinated restart.
