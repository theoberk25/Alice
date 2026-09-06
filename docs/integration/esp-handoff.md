# ESP handoff — eight-light power-grid demo

Updated 2026-09-06 UTC. Read [AGENTS.md](../../AGENTS.md) and
[current.md](../../current.md). This guide joins the implemented interfaces;
recommendations below are not claims that remote approval or grid control exists.

Renamed from `docs/integration/esp-technician-handoff.md` at Jared's request.
Existing technician integration notes are retained below for interface continuity;
the technician team owns that implementation.

## Power-grid team: start here

All eight LEDs were individually selected and visually identified by Jared.
The pin/color mapping below is verified. Suggested grid roles are **proposals**,
not active permissions, electrical wiring or simulated voltage measurements.

| Channel | Board pin | GPIO | Verified label | Suggested simulated role |
| --- | --- | --- | --- | --- |
| 1 | D0 | 1 | Yellow 1 | Primary utility feed |
| 2 | D3 | 4 | Blue 1 | Server rack A supply |
| 3 | D5 | 6 | Red 1 | Cooling plant supply |
| 4 | D6 | 43 | White 1 | Communications rack supply |
| 5 | D10 | 9 | Yellow 2 | Backup generator feed |
| 6 | D9 | 8 | Blue 2 | Server rack B supply |
| 7 | D8 | 7 | Red 2 | Auxiliary maintenance load |
| 8 | D7 | 44 | White 2 | Security monitoring rack supply |

Keep these stable channel/pin/color identities when assigning your own asset names.
Use ON to mean a simulated circuit is energized and OFF to mean disconnected;
color identifies the LED, not alarm severity. Show alarm state separately in UI.
Suggested topology: utility and generator feed a transfer switch, then a bus
supplies the six loads. Model interlocks in software; these LEDs do not physically
switch utility power. Define whether transfer permits an interruption and which
loads are critical before making demo scenarios.

### What to implement next

1. Current production supports only D0 through the signed single-light contract.
   Extend the request schema, signed grants, permission resolution, controller,
   firmware and operator UI together. Use stable target IDs for each circuit;
   never infer permission from a color or send arbitrary GPIO numbers from a client.
2. Version the multi-channel serial contract. Bind SET, GET and acknowledgments to
   the selected channel; reject unknown channels, preserve the bounded parser,
   and do not retry an uncertain SET automatically. Keep all outputs LOW at boot.
   D6/D7 are UART pads: keep hardware UART disabled when using them for these LEDs.
3. Carry the same target through decision, execution receipt, observation, USB
   ledger and Wazuh records. Remove hardcoded ESP-LIGHT-01 provenance only as part
   of that coordinated change. The technician team consumes these same IDs.
4. Keep permissions and grid rules explicit: approved circuit actions may execute;
   HOLD waits for an authenticated, request-bound human response; DENY never writes
   to the device. A simulated transfer interlock needs its own defined rules.
5. Represent sensor values with units, timestamp, source and freshness. Label
   generated voltages as simulated; LED output readback is not measured voltage.
   Preserve the PRE/POST assessment split. The current live demo uses fixture
   assessment, not the trained Isolation Forest.
6. Test each channel alone, no change to other channels, invalid channel rejection,
   signed permission denial, request replay, device disconnect and restart-to-OFF.
   Then verify one approved circuit action across the USB ledger and Wazuh before
   adding the technician workflow. Do not expand the existing live release silently.

### Current deployed state

The production sketch now holds the other seven LED outputs LOW; White 2's dim
idle glow was fixed and visually confirmed. All eight can be selected with the
separate bench-identification sketch, but **the operator application still controls
only D0**. The Pi service is running with production firmware; bench mode is over.
The full original flash backup is historical recovery material and predates the
idle-low fix. For normal deployment, build the current production source instead
of restoring that backup. Never flash while alice-runtime owns the serial port.

## Current connection map

| Component | Address / configuration | Verified scope |
| --- | --- | --- |
| Pi | `alice-pi-01`, SSH `pi@192.168.50.20` | Runtime service and ext4 USB active |
| Pi runtime | Port 8080; `/request`, `/events`, `/sync-status` | Signed first-light requests and read-only history/status |
| USB | `/mnt/alice-usb/pi-data/ledger.sqlite`, sibling `evidence/` | Real new events stored and automatically uploaded |
| Signed release | `/mnt/alice-usb/release/` | Existing first-light JSON grants, not general enterprise SQL permissions |
| Available physical controller | XIAO ESP32-S3 via `--esp-serial` | Pi deployed and external LED visually confirmed by Jared; see physical acceptance below |
| Wazuh indexer | Jared Mac `192.168.50.50:9200`, TLS name `wazuh.indexer` | 104 records at physical light-on checkpoint, including seven new events |
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
outage/reboot/unplug acceptance remain separate. This was local acceptance before the ESP handoff publication.

## Eight-LED bench identification (colors confirmed)

Jared supplied this wiring order and visually confirmed every color:

| Test | Pin | Color label |
| --- | --- | --- |
| 1 | D0 | Yellow 1 (visually confirmed) |
| 2 | D3 | Blue 1 (visually confirmed) |
| 3 | D5 | Red 1 (visually confirmed) |
| 4 | D6 | White 1 (visually confirmed) |
| 5 | D10 | Yellow 2 (visually confirmed on retest) |
| 6 | D9 | Blue 2 (visually confirmed) |
| 7 | D8 | Red 2 (visually confirmed on retest) |
| 8 | D7 | White 2 (visually confirmed on retest) |

Temporary sketch: `firmware/xiao_light_identify/xiao_light_identify.ino`.
ASCII digits 1–8 select exactly one LED; 0 clears all outputs.
This is a direct bench identification test, not an authorized ALICE request and
not evidence of an audit or SIEM decision. Pause alice-runtime during this mode.
Restore current production firmware before resuming normal signed light commands;
the old full-flash backup predates the idle-low fix.
The teammate owns grid semantics; retain the pin/color map independently of
future asset titles. Firmware backup location:
`/home/pi/first-light/pre-identify-backup/esp-flash.bin`.

Identification sketch compiled with Arduino ESP32 core 3.3.11 and flashed at
0x10000 with device hash verification. First command acknowledged `IDENTIFY D0`;
That was the initial identification checkpoint; all labels are now confirmed and
the production runtime has resumed.
Original full-flash SHA-256:
`e1a4be6ae9053036dbf095e13894a6d229bbc5048b158fa5fa5bc627c43ea324`.
Second backup: ignored `artifacts/local-state/esp-identify/esp-flash-before.bin`
on Jared's Mac. No normal ledger data or permissions were changed.

Identification completed: all eight colors visually confirmed. All outputs were
commanded OFF, then the original full flash was restored with device hash
verification. Pi alice-runtime resumed. Normal operator control remains the
original D0-only contract; the grid teammate owns multi-channel integration.

After restoring the original firmware, Jared reported White 2 (D7) glowing dimly.
The production sketch now explicitly drives all seven unused LED pins LOW at
startup. Compiled, flashed with hash verification; D0 readback reports OFF and
runtime resumed. Two firmware tests plus six subtests passed. Jared visually confirmed White 2 is now completely dark. Floating input remains
a hypothesis, not a measured electrical diagnosis.

Publication verification: 31 serial/firmware tests plus 24 subtests passed.
Changed documentation links resolve; current.md meets both size limits. The
authorized rename preserves prior handoff material and all tracker IDs. Generated
Arduino build directories and private local artifacts are excluded from Git.
