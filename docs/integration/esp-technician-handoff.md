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
| Available physical controller | XIAO ESP32-S3 via `--esp-serial` | Pi deployed and external LED visually confirmed by Jared; see physical acceptance below |
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

**The physical light node is USB-serial, not a network endpoint.** It has no
Wi-Fi, no Ethernet and no IP address, and serves no HTTP. Do not assign it a LAN
address, do not attach a USB-to-Ethernet adapter, and do not expect `curl` to
reach it. The adapter is
[SerialLightController](../../dcamr/enforcement/serial_light_controller.py);
[LightController](../../dcamr/enforcement/enforcement_gateway.py) is retained
unchanged for the mock and any future networked node.

Hardware: a Seeed XIAO ESP32-S3 on a USB data cable to the Pi, LED on D0 (GPIO1)
through a 270 ohm resistor to the anode, cathode to GND, active HIGH. Firmware,
wiring and the full bring-up are in the
[hardware runbook](../guides/first-light-hardware.md); the wire format is the
[serial protocol](../contracts/esp-serial-protocol.md).

1. Hardware owner flashes the board once with
   `arduino-cli upload -p <PORT> --fqbn esp32:esp32:XIAO_ESP32S3 firmware/xiao_first_light`.
   Firmware persists, so the board can then be moved to the Pi.
2. On the Pi, install the optional serial tier (`pip install -r requirements-hardware.txt`),
   add the runtime user to `dialout`, and identify the node with
   `ls -l /dev/serial/by-id/`. Close any serial monitor first: the port is exclusive.
3. In a coordinated pause, replace `--esp-url <URL>` with
   `--esp-serial /dev/serial/by-id/<node>` in the deployed
   `/etc/systemd/system/alice-runtime.service` (retain its other arguments), then
   `sudo systemctl daemon-reload` and `sudo systemctl restart alice-runtime`.
   The two flags are mutually exclusive and one is required, so a mistake fails
   closed at startup instead of silently commanding the wrong endpoint. The
   checked-in [demo unit](../../services/systemd/alice-runtime.service) still
   points at the mock and must be adapted.
4. Submit the signed request below through ALICE and verify one physical state
   change, matching USB events, dashboard observation and Wazuh delivery.

The serial link carries no device authentication: a command id is correlation
only, and the node trusts whichever host owns its USB port. That is a narrower
exposure than the previous LAN plan, since the cable is the only path in, but it
is no protection against a compromised Pi. Do not let the agent or technician
browser drive the node directly and bypass ALICE during governance tests.

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
retry causing no extra actuation. Mock retry acceptance passed previously. Physical light-on acceptance now passed below; a physical replay test remains.
Then: denied action causes no actuation; authenticated human resolves a held action;
Wazuh-only outage preserves local decisions and pending events; reconnect uploads
without duplicates; restart preserves outcomes; missing USB refuses execution.

The automatic worker passed simulated outage/restart tests. The staged **live**
outage test was blocked by tool usage limits and did not run. Reboot/unplug/power-loss
acceptance remains. The mock ESP tmux session does not survive reboot. See the
[automatic USB evidence](../reports/2026-09-06-automatic-usb-wazuh-sync.md) and
[Wazuh contract/runbook](wazuh-audit-sync.md) for exact scope and recovery instructions.

## Joint verification after integration

Use the [Pi/USB/Wazuh/technician acceptance sequence](pi-technician-acceptance.md)
and read-only `python -m lab.first_light.check_pipeline` from the Pi checkout.
It compares an existing request across the runtime, USB SQL and optional Wazuh
without submitting, uploading or opening another ledger writer. Dashboard arrival
and physical/replay actuation counts remain separate operator checks.

## Physical acceptance — September 5 EDT / September 6 UTC

Merged main `d3502e3` into Jared's preserved local branch at `bf6fee0`.
Sentinel operator at http://127.0.0.1:8789 submitted request
`4bc40a85-4c49-4a52-842c-5f6171f41af2`: HTTP 200, ALLOW,
PERMITTED_NORMAL_AUTO, COMPLETED, observed state `on`.
**Jared confirmed the external D0 LED visibly lit.** The LED was left on.
All seven request events reached Wazuh; the USB ledger now has 104 events.
The 97 original canonical event blobs were compared with the stopped-service
backup and are byte-identical.

The live Pi uses pyserial 3.5 and
`/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_A4:CB:8F:D2:6E:EC-if00`.
The systemd override
`/etc/systemd/system/alice-runtime.service.d/60-physical-esp.conf`
replaces the base ExecStart's HTTP mock flag with `--esp-serial <by-id path>`,
retaining all storage, trust and Wazuh arguments. It adds the dialout group.
The base unit remains intact. The old mock process is idle and unused.
Existing firmware responded with boot ID `b3f47bd1`; it was not reflashed,
so this does not certify it matches the latest hardened firmware source.

Before deployment, the stopped Pi's source, release, ledger and unit were backed
up in `/home/pi/first-light/pre-serial-backup/`. Do not restore that ledger over
new events. For a transport rollback, stop the runtime, move only the named
override outside the unit directory, reload systemd and restart with the known
mock available. Do not use a blanket systemctl revert that removes other overrides.

The operator accepts `--controller-label 'Physical XIAO ESP32-S3 via Pi USB serial'`;
this label describes configuration and is not hardware attestation.
Combined Python verification: 357 tests plus 261 subtests passed.
`npm ci && npm run check` passed typecheck, lint, 73 frontend tests,
5 script tests and production build. Native biometric checks were not rerun.
Remote technician accept/prevent transport, real ML integration and live
outage/reboot/unplug acceptance remain separate. Changes remain local, not pushed.
