# Live technician dashboard and USB SQL configuration

Status: local runtime/browser slice, 2026-09-06 UTC (September 5 EDT).
Follow [AGENTS.md](../../AGENTS.md). Built on architecture checkpoint `417b9de`
and merged teammate updates through `7081b6a`, on local `codex/live-dashboard`.
The user authorized publishing this reviewed slice to main. Deployment and physical
Pi/USB acceptance remain separate.

## Approved storage lifecycle

The user confirmed that the USB carries the latest consistent synchronized SQL
snapshot into DDIL. The Pi reads it and durably writes new offline audit events
back to that USB. On reconnection, the Pi delivers those events to SIEM, tracks
acknowledgements, and appends reconciliation findings. Original events are never
rewritten, renumbered or deleted to make the histories agree.

The implemented runtime database is SQLite: `<usb-data-dir>/ledger.sqlite`, with
canonical events, Ed25519 checkpoints and delivery bookkeeping. Evidence files
live in `<usb-data-dir>/evidence/`. Reuse this ledger rather than creating another
backend database or logger. Signing private keys stay on the Pi outside USB.
The workstation bridge owns no database; the dashboard receives read-only events.
The desktop's existing local identity database is separate from the runtime ledger.

**Scope limit:** enterprise snapshot publishing/atomic activation, loading general
enterprise policy data from SQL, whole-store rollback protection using independent
anchors, automatic authority transfer, and SIEM upload/reconciliation workers are
not implemented by this slice. First-light still loads its existing signed JSON
permissions release. The USB SQL runtime configuration implements the offline
recording/display part of the approved lifecycle, not a completed snapshot service.

For a real Pi, provision a locally mounted filesystem supporting SQLite locking,
atomic rollback-journal writes and fsync (for example an appropriately provisioned
Linux filesystem on the USB). Use one Pi writer. Do not copy a database file while
its writer is running: stop/seal/close first, or use a coordinated SQLite backup
and activation process. Never replace a ledger containing undelivered DDIL events
with a newer enterprise snapshot. Snapshot inputs and offline history must coexist.

`--usb-root` must already be mounted. The runtime checks the mount identity,
writability and data-path containment at startup, before appends and before the
controller command. Missing/replaced/read-only storage latches unavailable until
restart/revalidation. No fallback directory is created in place of the USB.
An existing USB ledger is required unless first provisioning is explicitly
requested with `--initialize-ledger`. I/O failure returns unavailable; when a
command may already have begun, the response does not claim a new DENY or success.
Physical removal/power-loss durability and the real filesystem require acceptance.

## Data and trust boundary

```text
USB SQLite ledger → existing Pi GET /events
  → SSH forwarding to Mac (physical Pi; host-key and user authentication)
  → authenticated loopback Python feed bridge
  → native Rust command OR same-origin Vite development proxy
  → RemoteAliceTransport → existing console store/layout/panels
```

Both workstation entry points keep `ALICE_FEED_TOKEN` outside renderer code and
only contact a configured loopback bridge. The bridge binds `127.0.0.1`, requires
a bearer token, accepts only read-only `/events?after=N`, disables redirects and
proxy-environment routing, and connects only to an explicit loopback runtime URL.
For a physical Pi that URL is an SSH tunnel. Do not expose the unauthenticated
first-light HTTP runtime on the LAN: bind it to loopback and access it through SSH.
`--source ssh-tunnel` records the operator's configuration; it cannot verify that
an arbitrary loopback listener actually belongs to SSH. Manage the tunnel and
verify the Pi's SSH host key through your provisioning process.

The bridge reuses `dcamr.audit.event_contract.validate_event`: strict schema,
semantic bindings and event-hash checks. It validates predecessor hashes and
sequence continuity. These checks do not claim ledger checkpoint signature
verification or physical sensor verification in the dashboard.

## Mapping for Alex

The rich `alice.decision` fixture contract remains unchanged. Live mode uses the
separate versioned `alice-runtime-feed-v1` schema in
[packages/contracts](../../packages/contracts/src/alice/runtime.ts) and the
[request/event reducer](../../packages/domain/src/runtime-feed.ts). It never
populates required fixture fields using guesses. Existing operations/history,
agent, evidence and status areas now display runtime records in the same layout.

| Dashboard information | Actual producer / mapping | Missing-data behavior |
| --- | --- | --- |
| Request identity and digest | Event `correlation.request_id/request_sha256` | Uncorrelated rejections remain visible in the audit trail. |
| Agent / responsible user | Event attribution, retained in raw record | No invented agent health, activity or connectivity. |
| Decision | `DECISION.detail.outcome` or `REJECTION` | Exact runtime outcome; CHALLENGE is not silently renamed HOLD. |
| Classification | `ASSESSMENT.detail.result/status/kind` | Missing assessment is unavailable; retained `fixture_mode=true` is labelled FIXTURE ASSESSMENT. |
| Numeric risk / confidence | Not exposed by the compact audit projection | Unavailable; no 0, 8/60/90 mapping or 100% confidence. |
| Action/target | Retained contextual assessment metadata when supplied | Labelled assessment context, not a recovered signed request. Full request parameters/mission are unavailable. |
| Execution | Separate attempt, controller receipt, execution result, observation | Receipt acceptance does not verify physical effect. Late results update the request without modifying decision events. |
| Observed state | `OBSERVED_STATE.detail.value/unit/quality/origin/source` | Preserve nulls, original numeric string and unit. Mock controller label is independent of feed connectivity. |
| Time | Recorded timestamp, clock confidence, boot and monotonic metadata | No replacement with browser time; monotonic nanoseconds cross JSON as a decimal string to avoid JavaScript precision loss. |
| Evidence / packages | Original refs, hashes and source verification/freshness | No verification inferred from presence or valid schema. |
| Feed connection | Successful polling, errors, timeout and local receipt time | Connecting/live/disconnected/stale/unavailable; not cloud, model or hardware readiness. |
| Authority | Original event authority owner/interval/confirmation | Historical reported metadata, not a new authority handshake. |

Jared's enterprise simulator uses distinct generated formats and fictional site,
identity, voltage and audit examples. `artifacts/enterprise-sim/` is not imported by
this transport. First-light's fixture assessment and mock ESP remain explicit.
The first-light runtime itself has no held-action/biometric response path yet.
The existing `AliceTransport` action interface is preserved but remote methods
throw unavailable. No action receipt or successful execution is simulated.

History starts at cursor zero. Incremental reads overlap the acknowledged head,
which detects lost/reset/replaced ledgers even when no new request arrives.
Exact duplicate events are ignored; conflicting IDs, request digests, source
changes, gaps and malformed batches are rejected atomically. Events are ordered
by ledger sequence, not uncertain wall-clock time. Reconnect reloads history and
compares it with retained events before advancing. Errors retain the last data;
no live failure loads fixtures. Polling is every 1.5 seconds, bounded by a timeout;
a feed without a successful response for 10 seconds is stale. An idle feed with
successful empty/overlap polls remains live; reading freshness is separate.
The Settings reconnect button explicitly clears the display and reloads history.

## One-command synthetic session

Run `npm run demo:live` from the repository root. It creates a new private temporary
folder, test-only keys, real SQLite ledger, real first-light runtime, mock ESP,
authenticated bridge and Alex's dashboard at `http://127.0.0.1:1422`. It prints the
SQLite path, never the token. Initial history contains one allowed and one denied
request. Type `on`, `off` or `deny` in that terminal and press Enter to submit a
new signed request; it appears in the dashboard automatically. Type `stop` to end.
Data remains in the printed temporary directory for inspection. No existing data
or keys are overwritten. This is explicitly synthetic input to a real pipeline,
not a live-mode fallback and not physical USB acceptance.

The local viewer session demonstrated 16 persisted events across three requests,
including a new `off` request added while the browser was open. SQL and dashboard
both showed its seven correlated events and observed value `0 bool`.

## Local runnable setup

Run commands from the Alice repository. Use Node 22+ and Python with
`requirements-audit.txt`; existing lab requirements supply other runtime imports.
The examples use `.venv/bin/python` if that environment already has dependencies.
Use a new temporary directory so existing private data and keys remain untouched.

```sh
export ALICE_LIVE_TEST_DIR="$(mktemp -d /tmp/alice-live.XXXXXX)"
.venv/bin/python -m lab.first_light.build_release "$ALICE_LIVE_TEST_DIR/bundle"
.venv/bin/python -m lab.first_light.mock_esp --host 127.0.0.1 --port 8090
```

In a second terminal (set the same `ALICE_LIVE_TEST_DIR` path):

```sh
.venv/bin/python -m dcamr.main \
  --release "$ALICE_LIVE_TEST_DIR/bundle/release" \
  --trust-key "$ALICE_LIVE_TEST_DIR/bundle/trust/manifest_public.hex" \
  --data-dir "$ALICE_LIVE_TEST_DIR/usb-test-data" --local-test-storage \
  --esp-url http://127.0.0.1:8090 --host 127.0.0.1 --port 8080
```

Generate a private token locally and supply the same value to the bridge and
Vite/native process. Do not put it in a `VITE_*` variable, commit it or paste it into
chat. It can be supplied through a locally secured environment file or shell.

```sh
export ALICE_FEED_TOKEN="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
export ALICE_FEED_URL=http://127.0.0.1:8787
.venv/bin/python -m services.runtime_feed \
  --upstream http://127.0.0.1:8080 --source local-runtime --controller mock
```

In a terminal with the same token and `ALICE_FEED_URL`:

```sh
VITE_ALICE_PREVIEW_MODE=remote npm run dev
```

Open **http://127.0.0.1:1420**. This browser mode is a read-only preview, with no
biometric session or remote action capability. `npm run build` builds assets;
the Vite development proxy is not a production web hosting service.
For the native app, retain the existing biometric setup and launch with
`ALICE_TRANSPORT_MODE=remote ALICE_BIOMETRIC_MODE=arcface npm run desktop -- dev`.
Its new `read_runtime_events` Rust command uses the same bridge configuration;
native compilation/camera acceptance is pending in this environment.

Send a real signed runtime request from another terminal:

```sh
.venv/bin/python -m lab.first_light.terminal_client \
  --url http://127.0.0.1:8080 \
  --key-file "$ALICE_LIVE_TEST_DIR/bundle/client/term-agent-01-k1.seed" \
  --state on --repeat 2
```

The request appears automatically; selecting it shows separate decision, receipt,
execution result and observed state. `--repeat 2` replays the identical envelope
and must produce only one mock-controller command.

## Physical Pi configuration

User-supplied connection details: hostname `alice-pi-01`, SSH user `pi`, Ethernet
`192.168.50.20`; device `/dev/sda`, partition `/dev/sda1`, current UUID `6C1A-C6EA`.
The USB is **not mounted yet**; proposed mount `/mnt/alice-usb`. The read-only
`ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 pi@192.168.50.20 lsblk -f`
check timed out from this Mac. Filesystem type, mount and physical readiness are
unverified. No mount, formatting, population or remote deployment was performed.
Device names can change; verify UUID/device identity before mounting. The UUID
alone does not establish filesystem type or SQLite durability.


Use the actual mounted USB path, verified release and separately provisioned
ledger signing key. Example paths below are placeholders for provisioning:

```sh
python -m dcamr.main \
  --usb-root /mnt/alice-usb --data-dir /mnt/alice-usb/alice/runtime \
  --release /mnt/alice-usb/alice/permissions/release \
  --trust-key /etc/alice/manifest_public.hex \
  --ledger-key-file /etc/alice/ledger_key.seed \
  --esp-url http://CONTROLLER:8090 --host 127.0.0.1 --port 8080
```

This requires an existing valid SQLite ledger, or explicit first provisioning
with `--initialize-ledger`. That flag creates an empty first-light ledger; it is
not an enterprise SQL snapshot importer. Never use it to conceal missing history.
Keep the key associated with the existing ledger; replacing it is not migration.

On the Mac, establish the authenticated tunnel (the supplied `pi@192.168.50.20`):

```sh
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -L 127.0.0.1:18080:127.0.0.1:8080 pi@192.168.50.20
```

Then use the same authenticated bridge/dashboard setup, replacing the bridge
arguments with `--upstream http://127.0.0.1:18080 --source ssh-tunnel`.
Add `--controller mock` if still running a mock controller. Without it controller
provenance remains unavailable, not verified hardware. Do not automatically accept
an unknown or changed SSH host key. No SSH credentials are stored in the dashboard.

Physical acceptance requires Pi SSH details, mounted USB path/filesystem,
provisioned release/key, actual controller interface, storage-removal/power-loss
tests and a real device readback. The current local tests do not establish any of
those. Real ML inference, held accept/deny proof delivery, enterprise snapshot
publication and SIEM reconciliation remain separate team integration work.

## Where to keep connection settings

Hostnames, usernames, IPs, device identifiers and mount paths are configuration,
not passwords. The actual values above can be shared for coordination. Keep the
bridge token in the workstation's gitignored `.env` or process environment; both
Vite and the native launcher read `.env`. Merge settings into an existing file
without replacing its private contents. `.env.example` documents the fields.
The Python bridge reads the exported `ALICE_FEED_TOKEN` environment variable;
it does not itself load `.env`. Export the same locally generated token into its
shell without sharing it in chat. SSH private keys remain in the user's existing
SSH setup; ledger private keys stay in the Pi's protected key directory.
No secret needs to be pasted into the dashboard or sent to a teammate.
