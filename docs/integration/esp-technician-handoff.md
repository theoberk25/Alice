# ESP grid demo and technician integration handoff

Updated 2026-09-06 UTC. Read [AGENTS.md](../../AGENTS.md) and
[current.md](../../current.md). This guide joins the implemented interfaces;
recommendations below are not claims that remote approval or grid control exists.

## Current connection map

| Component | Address / configuration | Verified scope |
| --- | --- | --- |
| Pi | `alice-pi-01`, SSH `pi@192.168.50.20` | Runtime service and ext4 USB active |
| Pi runtime | Port 8080; `/request`, `/events`, `/sync-status` | Signed first-light requests and read-only history/status |
| USB | `/mnt/alice-usb/pi-data/ledger.sqlite`, sibling `evidence/` | Real new events stored and automatically uploaded |
| Signed release | `/mnt/alice-usb/release/` | Existing first-light JSON grants, not general enterprise SQL permissions |
| Current controller | Pi loopback `http://127.0.0.1:8090` | Mock ESP; real ESP address/port must be supplied by hardware owner |
| Wazuh indexer | Jared Mac `192.168.50.50:9200`, TLS name `wazuh.indexer` | 83 records at last observed test, including seven from USB |
| Technician | Theo's Mac; use the SSH tunnel below | Dashboard transport setup is separate from Wazuh credentials |

Pi host ED25519 fingerprint supplied by Theo:
`SHA256:uFZ6XoYVJ6PevSXSi2kyGQeM9XV/P6pks125tDddPEY`.
Verify it before trusting a new host entry; never suppress host-key verification.
Have Theo provision each teammate's SSH public key. Terminal signing seeds are
separate private credentials: a clone does not grant agent identity or permissions.
Do not regenerate a shared release merely to recover a missing private seed.

## Get the shared code

From an existing clean Alice checkout, `git pull --ff-only origin main` after this
checkpoint is published. Preserve local changes and private `.env`/keys. Use the
existing Python environment; a fresh Python 3.12 setup can install
`requirements-audit.txt`. ML training dependencies are unnecessary for this transport
slice. Dashboard setup uses Node 22+, `npm ci`, and its own biometric/native tools.

The Pi is already provisioned. **Do not format its USB, initialize another ledger,
copy a database over it, or launch another writer.** `alice-runtime.service` owns
its ledger and uploader. Inspect with:

```sh
ssh pi@192.168.50.20 'systemctl status alice-runtime --no-pager; findmnt /mnt/alice-usb'
ssh pi@192.168.50.20 'curl -fsS http://127.0.0.1:8080/sync-status'
```

## Connect the ESP owner

The current adapter is [LightController](../../dcamr/enforcement/enforcement_gateway.py).
For the first physical light test the firmware must implement:

| Method | Path | Body / response |
| --- | --- | --- |
| POST | `/light` | Request `{"state":"on"}` or `{"state":"off"}`; successful HTTP response with a JSON object, e.g. `{"ok":true,"state":"on"}` |
| GET | `/light` | Response `{"state":"on"}` or `{"state":"off"}` representing observed state |

A successful POST is only a transport receipt. GET readback is recorded separately;
it must not invent a physical observation. The mock's `/stats` command counter is
only a test aid, not a required physical-device API.

1. Hardware owner supplies the actual ESP LAN IP, port and the agreed low-voltage
   demonstration wiring. No ESP IP or feeder voltage range is assumed here.
2. Confirm read-only `GET /light` from the Pi before replacing the mock endpoint.
3. In a coordinated pause, update only `--esp-url` in the deployed
   `/etc/systemd/system/alice-runtime.service` (retain its other arguments), then
   `sudo systemctl daemon-reload` and `sudo systemctl restart alice-runtime`.
   The checked-in [demo unit](../../services/systemd/alice-runtime.service) still
   points at the mock and must be adapted for the physical ESP.
4. Submit the signed request below through ALICE and verify one physical state
   change, matching USB events, dashboard observation and Wazuh delivery.

The existing transport is plain HTTP without device authentication. Recommend a
restricted demo LAN/endpoint access limited to the Pi until authenticated controller
commands and device-side idempotency are implemented. Do not let the agent or
technician browser directly call `/light` to bypass ALICE during governance tests.

**Power-grid extension:** currently only `set_light_state` targeting `ESP-LIGHT-01`
is accepted by this release/adapter. Voltage readings, feeders, relays and setpoints
need an agreed schema (resource ID, unit, timestamp, sensor verification/freshness,
requested vs measured value), signed permissions and a matching adapter. Do not
reuse provisional enterprise-simulator voltage envelopes as hardware safety limits.
Recommend the electrical owner define the simulated units/limits first, then
add PRE_ACTION and POST_ACTION telemetry fixtures before connecting real inference.

## Submit a first-light action

Open an authenticated tunnel on the requesting Mac:

```sh
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -L 127.0.0.1:18080:127.0.0.1:8080 pi@192.168.50.20
```

In another terminal, use your provisioned seed and its bound agent ID. This example
is Jared's existing simulated `elec-agent-01` (responsible user `ssgt.a.okafor`):

```sh
.venv/bin/python -m lab.first_light.terminal_client \
  --url http://127.0.0.1:18080 \
  --key-file /absolute/private/path/elec-agent-01-k1.seed \
  --agent elec-agent-01 --state on --repeat 2
```

The second request reuses the same signed envelope: it should return the recorded
outcome and cause no second execution. A new invocation creates a new request ID.
Do not share signing seeds in Git or chat. The existing runtime binds the verified
key to the agent and checks exact signed grants; changing a UI username grants nothing.

## Connect Theo's technician dashboard

Use the tunnel above on Theo's Mac. Start the authenticated loopback bridge from
his checkout. Port 8788 below avoids collision with the enterprise console on 8787:

```sh
export ALICE_FEED_TOKEN="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
export ALICE_FEED_URL=http://127.0.0.1:8788
.venv/bin/python -m services.runtime_feed \
  --upstream http://127.0.0.1:18080 --source ssh-tunnel --controller mock --port 8788
```

Supply the same token and feed URL to the dashboard process using its private local
environment, without echoing or committing the token. In that configured terminal:

```sh
VITE_ALICE_PREVIEW_MODE=remote npm run dev
```

Keep `--controller mock` while connected to the mock. When switching to a real
controller, omit that label; its provenance remains unverified until implemented.
For native biometric setup and existing remote transport options, follow the
[live dashboard guide](live-dashboard.md) and [console guide](../guides/technician-console.md).
Do not supply Wazuh admin/service credentials to the dashboard renderer.

The deployed runtime currently listens on the demo LAN. Recommend moving it to
loopback once all clients use SSH tunnels, as the live-dashboard guide specifies.
Signed requests authenticate actions, but the raw LAN history/status endpoints
are not access-controlled. Changing the bind address requires coordinating clients.

## Implement technician accept/prevent next

**Current remote UI is read-only.** There is no Pi endpoint accepting a technician
approval, and the Wazuh uploader does not add one. Avoid displaying a successful
approval or execution result until the Pi returns a real bound result.

Recommended implementation sequence for the owning teammates:

1. Agree/version the response contract in `docs/integration/upstream-alice.md`:
   held request ID and digest, original decision ID, authenticated technician ID,
   proof of the verified biometric session, accept/reject intent, expiry, and
   replay protection. A face match or LLM explanation alone is not authorization.
2. Add the Pi handler through the existing runtime owner/lock. Revalidate pending
   HOLD state, technician permission, request binding, freshness, current authority,
   storage availability and hard prohibitions before execution. A stale response
   must not release a changed request or override a hard DENY.
3. Persist the technician response and execution intent through AuditLog. Rejection
   must cause no controller command. Acceptance executes at most once and separately
   records receipt, result and observed state. The uploader automatically transports
   these valid ledger events; it does not interpret them as new permissions.
4. Connect the native transport after that contract exists; preserve unavailable
   behavior until then. Test duplicate/stale/unauthorized responses, device timeout,
   USB loss and responses to already completed requests.

## Acceptance order and remaining checks

First: known-permitted light action → USB ledger → dashboard → Wazuh, with identical
retry causing no extra actuation. This passed against the mock; physical ESP remains.
Then: denied action causes no actuation; authenticated human resolves a held action;
Wazuh-only outage preserves local decisions and pending events; reconnect uploads
without duplicates; restart preserves outcomes; missing USB refuses execution.

The automatic worker passed simulated outage/restart tests. The staged **live**
outage test was blocked by tool usage limits and did not run. Reboot/unplug/power-loss
acceptance remains. The mock ESP tmux session does not survive reboot. See the
[automatic USB evidence](../reports/2026-09-06-automatic-usb-wazuh-sync.md) and
[Wazuh contract/runbook](wazuh-audit-sync.md) for exact scope and recovery instructions.
