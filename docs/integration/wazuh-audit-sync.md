# Pi ledger → Wazuh audit delivery

This slice uploads original, sealed Pi ledger events directly to the enterprise
Wazuh indexer. The technician application is not a relay. The next transition adds
enterprise → USB permissions and baseline publication as a separate authenticated
direction; audit delivery must continue without sharing its service credentials.

## Wireless and enterprise transition

The current Wazuh stack runs on Jared's Mac and remains reachable to the Pi on the
local demo LAN using the existing TLS hostname and dedicated delivery account.
Adding an access point must preserve that path; adding a WAN later may also reach
hosted enterprise services. Local agents and technician browsers do not receive
Wazuh service credentials. Cloud agents authenticate at an enterprise gateway;
they do not call the Pi's loopback runtime or USB-serial controller directly.

Keep these flows distinct:

| Direction | Data | Trust and storage |
| --- | --- | --- |
| Pi → Wazuh | Immutable request, decision, execution and observation events | Existing create-only delivery IDs, exact read-back and USB receipts |
| Enterprise → Pi | Signed permissions, normal baseline and compatible model metadata/artifact | Stage on USB, verify fully, then atomically activate a new generation |
| Pi ↔ technician | Read-only events now; bound HOLD response later | Authenticated workstation channel, separate from Wazuh |

Loss or restoration of Wazuh connectivity changes uploader state only. It never
selects ONLINE/OFFLINE execution ownership. On reconnection, drain retained events
before or alongside cache refresh, preserve original decision-time evidence and
append reconciliation findings rather than rewriting records. The full sequence is
in the [integrated demo runbook](../guides/demo-runbook.md).

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


## Enterprise permissions → USB cache (local follow-up)

The Pi now runs `alice-permissions-cache.timer` every approximately 30 seconds.
Its separate oneshot service only owns enterprise cache files, never AuditLog or
its SQLite connection. `cloud/permissions_cache.py` verifies the actual CURRENT
release from `alice-permissions`: pinned issuer/site/key, Ed25519 signature,
canonical payload hashes, validity interval, generation and revocation epoch.
It rejects rollback and same-generation conflicts and retains the previous cache
on download failure. Each file and the current pointer use fsync/atomic replacement.
The public verification key and rollback anchor are stored outside USB.

Live result: generation **44**, revocation epoch **8**, manifest SHA-256
`35cf7df2f05d57584a3a9c464fbb1a0236849798d918edb8e3e640373ee844f2`.
Files: `/mnt/alice-usb/enterprise-cache/permissions/000044/`.
Pointer: `/mnt/alice-usb/enterprise-cache/permissions/current.json`.
Anchor: `/home/pi/first-light/wazuh-sync/permissions-anchor.json`.
Verification key: `/home/pi/first-light/trust/enterprise-permissions.pk`.
Only the public demo authority key was installed; this is demonstration trust.
The Pi service role now additionally reads the `alice-permissions` index.

```sh
systemctl status alice-permissions-cache.timer --no-pager
journalctl -u alice-permissions-cache.service -n 10 --no-pager
cat /mnt/alice-usb/enterprise-cache/permissions/current.json
```

This is **VERIFIED_CACHE_ONLY**, not runtime activation. The enterprise schema
contains revocations, hard prohibitions and compatibility metadata that the current
first-light resolver does not fully implement. It must not be pointed at this
folder as an incidental configuration change. The active signed light release
remains `/mnt/alice-usb/release`. Normal-behavior/model package download, compatible
activation, expiry enforcement at decision time and SQL permission loading remain
separate work. Expired packages are not newly cached; retaining an old cached file
is not authorization to use expired grants. Offline protection against replacing
both internal storage and USB is outside this checkpoint's threat model.

Component tests cover valid install, idempotence, rollback, expiry, tampered data,
wrong trust and offline retention. Live service returned success and cached the
same hash as Wazuh while `alice-runtime` remained active. No new Markdown files
were added for this increment, and the user requested local work without a push.


## Enterprise presentation (local redesign)

The enterprise page at `http://127.0.0.1:8787/` now opens a security-operations
workspace: severity metrics, detection histogram, searchable threat-hunting queue,
endpoint investigation panels and a distinct actual Pi audit stream. It preserves
the prior architecture, permission, scenario and model views. The operator page
on port 8789 and the Pi services are unchanged.

Design references: [Wazuh dashboard capabilities](https://documentation.wazuh.com/current/getting-started/components/wazuh-dashboard.html)
for threat hunting and endpoint security; [Defender incident investigation](https://learn.microsoft.com/en-us/defender-xdr/investigate-incidents)
for asset pivots and evidence timelines. This is our demo presentation over Wazuh,
not a replica claiming their full capabilities or an independently implemented EDR.
Response actions are explicitly unconnected. No isolation/scan/kill command is sent.

`/api/soc` reads `wazuh-alerts-*` and `alice-ledger-v1` independently, returns at
most 100 records per stream, reports unavailable sources without fake zeros, and
preserves large integers as decimal strings for browser display. Alert metrics and
histograms use server-side aggregation over the chosen interval; the loaded search
sample is bounded to 100. Ledger counts are explicitly all-history. The 13-asset
inventory is labelled scenario data, not verified agent enrollment. Index presence
alone does not prove that an alert describes a real attack rather than demo input.

Live query observed 259 indexed alerts, 8 critical-level detections and 97 Pi
records. Browser checks passed: overview loads; search for authentication failed
shows 5/100 results; alert detail includes actual MITRE mappings/raw evidence;
endpoint detail and audit stream navigation work. Five backend tests cover source
failure, independent streams, range validation and integer precision; JS syntax
check passed. Changes remain local and no new Markdown file was created.

Final regression after the presentation changes: **310 passed, 226 subtests passed**
in 21.41 seconds. No push or Pi deployment was performed for this UI increment.

## Integrated snapshot and acceptance continuation

The worker also passes local integration checks alongside the explicit signed
first-light SQL snapshot input, preserving original events and restart replay.
HTTP protocol/truncated-body errors now enter delivery retry rather than stopping
the worker as a local failure; malformed nested create receipts are rejected.
The shared `verify_stored(event)` method performs only exact-content GET verification.
The [integrated acceptance flow](../guides/demo-runbook.md#acceptance-sequence) uses it without uploading
or mutating delivery state. Existing physical service deployment remains unchanged
until the operator pulls and performs a coordinated restart.

## Physical ESP delivery acceptance

September 5 EDT / September 6 UTC: operator request
`4bc40a85-4c49-4a52-842c-5f6171f41af2` ran through the USB-backed Pi to
the physical serial XIAO. Jared visually confirmed the external LED on.
Seven events automatically reached Wazuh; worker reported IDLE, delivered 7,
last event ending `.observed`, and no error. USB ledger total: 104.
All 97 predeployment canonical events were byte-identical to the backup.
See the [hardware runbook](../guides/first-light-hardware.md) for configuration,
backup and validation. This does not activate cached generation 44 permissions
or establish technician approval transport.

## Signed enterprise LAN ingress (2026-09-06)

`services.enterprise_ingress` listens on `192.168.50.50:8790`, POST `/request`.
GET `/health` proves only listener availability. Clients send the existing signed
first-light envelope (`request`, `key_id`, `signature`); no Wazuh credentials or
Mac signing key are served. Signature, agent binding, strict request schema and
freshness (300 seconds, five seconds future tolerance) are checked before writes.
Requests remain the eight-light contract; fan requests are not yet admitted.

A dedicated create-only index `alice-enterprise-ingress-v1` stores the original
signed envelope. The dedicated `alice_enterprise_ingress` account can create/read
that index only. Exact readback precedes forwarding the original request bytes
to Pi `/request`. Identical retries reconcile receipts; changed content under the
same request ID conflicts. Pi deduplication prevents repeat execution. Wazuh
unavailability returns 503 without forwarding; uncertain Pi response returns 502
with the verified enterprise receipt, requiring history reconciliation. A fresh
ID is not an automatic retry. No background forwarding queue was added.

Launch from the checkout:

```sh
.venv/bin/python -m services.enterprise_ingress \
  --release artifacts/local-state/merek-hold-release/candidate \
  --trust-key artifacts/local-state/merek-hold-release/public.hex \
  --wazuh-config artifacts/local-state/enterprise-ingress/wazuh.json
```

This demo config is private/ignored. Local Docker traffic connects to loopback
while verifying the TLS certificate against `wazuh.indexer` and the pinned CA;
no TLS verification bypass or global hosts change. LAN ingress is HTTP with
signed bodies, not encrypted transport; use an authenticated encrypted gateway
before Internet exposure. No WAN port forwarding is configured. The listener
runs as a session process, not a boot-persistent service.

Verified local/LAN test `enterprise-wireless-hold-001`: Wazuh verified receipt,
Pi CHALLENGE, eligible READY/NOT_EXECUTED; identical retry produced one receipt
and Pi idempotent replay. Pi reached Mac health over the switch. Five ingress
tests passed. Actual wireless laptop test is pending. Index receipt is ingestion,
not a Wazuh detection-rule alert. Technician visibility comes from the Pi's ledger
feed; this does not automatically activate enterprise permissions or model caches.

The operator source now routes through ingress by default (`--enterprise-url`).
The already-running localhost:8789 process still uses old direct-to-Pi code:
this session could not terminate that process due to OS permissions. Its owner
must restart it with the same private key/credentials and controller settings
before claiming the existing page is enterprise-first. Do not expose that page's
local signing controls to LAN clients; use the signed-only 8790 endpoint.

Receipt retention now additionally uses authenticated, host-verified SSH to run
`dcamr.enterprise_receipts` on the Pi. It validates the existing agent signature
against the active signed release, then atomically creates an immutable receipt
under `/mnt/alice-usb/enterprise-cache/ingress-receipts/<document-id>.json`.
Original envelope and enterprise readback metadata are retained, with fsync and
exact-content replay checks. USB mount checks fail closed. This is a separate
cache, never a second ledger writer; Pi does not independently contact Wazuh to
verify the gateway's receipt claim. Forwarding waits for cache hash acknowledgement.
Seven ingress/cache tests passed. Runtime restart was not required. Receipt-cache
fields are returned by ingress; native receipt-specific presentation is not added.
