# Joint Pi, USB, Wazuh and live technician acceptance

Follow [AGENTS.md](../../AGENTS.md) and Jared's
[ESP/technician handoff](esp-technician-handoff.md). This guide prepares a joint
operator test; none of these physical checks ran on Merek's disconnected Mac.

## What the data paths mean

Current implemented paths are **Pi → USB ledger → Wazuh** and **Pi → authenticated
workstation bridge → technician dashboard**. They share original request/event
identities. SIEM → Pi permissions/baseline synchronization is a separate unfinished
input direction. Do not mistake successful audit upload for permissions download.
The dashboard already supports history, automatic updates and reconnect recovery.
Its remote controls remain read-only; fixture assessment and mock controller labels
must remain until those producers are replaced and verified.

The technician Mac needs a route to the demo LAN (`192.168.50.x`), normally its
configured Ethernet connection, or an explicitly configured routed/VPN connection.
A direct cable to the Pi is not mandatory. Merek's inspected Mac was on
`192.168.10.17`, with inactive Ethernet interfaces; SSH to `192.168.50.20` timed out.
No network settings were changed. Have Theo provision the Mac's SSH public key,
and verify the fingerprint in Jared's handoff. Do not bypass host-key checking.

## Physical controller selection

Xavier's `290699b` adds the XIAO ESP32-S3 over **USB serial**, with no ESP network
address. His development-Mac hardware test is reported in the [hardware guide](../guides/first-light-hardware.md);
the same deployment on the Pi remains to verify. Do not assume the existing
systemd unit has switched from its HTTP mock. In a coordinated stop/restart,
Jared/Xavier select `--esp-serial /dev/serial/by-id/<actual-device>` in place of
`--esp-url`, retaining every storage, trust, signing-key and Wazuh argument.
Never run a serial monitor beside the runtime or launch another ledger writer.
The merge also hardens firmware parsing; Xavier must compile/flash and reverify
that updated firmware separately. No board was flashed by this integration.

Keep the bridge's `--controller mock` for the HTTP mock. With confirmed physical
serial deployment, omit that flag; controller verification stays unavailable, and
`ACTUATOR_FEEDBACK` is the output reported by the board, not measured illumination.
No dashboard/contract redesign is required for the serial receipt or observation.

## Jared: verify existing data first, without a new action

After the integration is published, preserve local changes and private state before
pulling on Jared's checkout and the Pi checkout. The current systemd process owns
its ledger; **do not initialize, replace, format or start another runtime**. A git
pull does not reload running Python modules. Apply worker fixes in a coordinated
service restart only after recording current status; preserve the installed service
arguments/config, including its current JSON release. Do not replace it with a
snapshot or the checked-in unit just to run this check.

On the Pi, from `/home/pi/Alice`:

```sh
systemctl is-active alice-runtime
findmnt /mnt/alice-usb
curl -fsS --max-time 5 http://127.0.0.1:8080/sync-status
.venv/bin/python -m lab.first_light.check_pipeline \
  --request-id 2ba62d25-7da7-47f2-a775-e126ac46e7d3 --expect ALLOW \
  --usb-root /mnt/alice-usb --data-dir /mnt/alice-usb/pi-data \
  --wazuh-config /home/pi/first-light/wazuh-sync/config.json --wait-seconds 60
```

That request ID comes from Jared's earlier seven-event USB proof. If it is absent,
the checker fails; choose another known request, never fabricate history or
reinitialize to make the check pass. The supplied credential file stays private;
only read-only Wazuh GET requests use it. No credentials or raw events are printed.

A successful report includes `runtime_sql: EXACT_MATCH`, `storage: MOUNTED_USB`,
`wazuh: EXACT_MATCH`, and seven verified events for a completed allowed request.
It checks the runtime's event hashes/continuity and compares exact canonical bytes
with read-only SQL and the original Wazuh documents. This is not independent
checkpoint-signature verification, power-loss durability or semantic reconciliation.
`worker_state` is a snapshot, not proof of current enterprise connectivity.
`dashboard: NOT_CHECKED`, `physical_effect: NOT_VERIFIED` and
`replay_execution_count: NOT_CHECKED` deliberately require separate observation.

The optional Wazuh flag can be omitted for runtime/SQL diagnosis, but the report
then says `wazuh: NOT_CHECKED`; that is not end-to-end Wazuh acceptance. The helper
waits for missing request chains or remote documents, bounded by `--wait-seconds`
(0–300) plus current network-call timeouts. Conflicts/invalid data fail immediately.
For isolated local fixtures use `--local-test-storage`, never to conceal absent USB.
A DENY check accepts either REQUEST/REJECTION or REQUEST/ASSESSMENT/DECISION(DENY),
and refuses any chain containing an execution attempt. It checks a recorded denial,
not an inferred physical device command count.

## Technician Mac: make the actual dashboard live

Use the same updated checkout and Node 22+. Follow existing dependency setup rather
than replacing private `.env`, identity stores or environments. In one terminal:

```sh
ssh -N -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 -L 127.0.0.1:18080:127.0.0.1:8080 pi@192.168.50.20
```

In a second terminal at the Alice root, run the bridge and browser preview with
the same process environment. Port 8788 avoids Jared's enterprise console; 1424
avoids earlier local demo/browser test ports. Inspect existing listeners before use.

```sh
export ALICE_FEED_TOKEN="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
export ALICE_FEED_URL=http://127.0.0.1:8788
.venv/bin/python -m services.runtime_feed \
  --upstream http://127.0.0.1:18080 --source ssh-tunnel --controller mock --port 8788 &
ALICE_ACCEPTANCE_BRIDGE_PID=$!
VITE_ALICE_PREVIEW_MODE=remote npm run dev -- --host 127.0.0.1 --port 1424 --strictPort
# After stopping Vite, stop only the bridge started by this terminal:
kill "$ALICE_ACCEPTANCE_BRIDGE_PID"
unset ALICE_FEED_TOKEN
```

Open `http://127.0.0.1:1424`. This is the existing technician layout with real Pi
history, not the enterprise simulator's live-edge tab. No token belongs in a
`VITE_*` variable or renderer code. Keep `--controller mock` while the Pi's endpoint
is still mock ESP. For native identity setup follow the existing console runbook;
browser preview does not implement biometric approvals.

## One new request across all outputs

With the dashboard visible, Jared uses an already provisioned permitted terminal
seed. Do not regenerate release/key files to obtain an identity. From a requesting
Mac with the tunnel (or on the Pi using its loopback URL and a provisioned seed):

```sh
ALICE_ACCEPTANCE_REQUEST_ID="$(.venv/bin/python -c 'import uuid; print(uuid.uuid4())')"
.venv/bin/python -m lab.first_light.terminal_client \
  --url http://127.0.0.1:18080 --key-file /absolute/private/path/elec-agent-01-k1.seed \
  --agent elec-agent-01 --state on --request-id "$ALICE_ACCEPTANCE_REQUEST_ID" --repeat 2
```

Use the printed nonsecret request ID with `check_pipeline` on the Pi, replacing
the historical ID above. Select `on`/`off` only for the agreed demonstration device.
The supplied path is a placeholder; the repo does not contain a usable private seed.
Record the controller's before/after command count while it is mock, or obtain the
hardware owner's physical observation when using the real ESP. The replay flag alone
is not an independent count of physical commands.

Confirm all of the following for that same request ID:

1. The first response succeeds; the identical envelope reports replay. There is
   exactly one new controller actuation, observed independently.
2. The technician dashboard adds the request automatically without manual refresh,
   retaining separate decision, receipt, completion and observation events.
3. The Pi helper verifies seven exact runtime/USB/Wazuh records. The earlier history
   remains; there are no duplicate request events or rewritten decisions.
4. A separately provisioned ungranted identity produces DENY with no actuation;
   its chain appears in the dashboard and passes `--expect DENY`. Do not edit the
   production release merely to manufacture this case.
5. Disconnect only the technician SSH tunnel, observe retained/disconnected history,
   restore the tunnel and observe automatic recovery without fixture fallback.

Run Wazuh-only outage/recovery, service restart, and missing-USB/power-loss tests
later in a coordinated maintenance window using the [sync runbook](wazuh-audit-sync.md).
This script intentionally cannot stop services, alter routing, unmount USB or send
commands. Keep those disruptive operations separate from the read-only check.

Save the request ID, nonsecret checker JSON, observed dashboard result and controller
count/readback in a dated report. Do not include tokens, signing seeds, biometric
material or service credential contents. After this connected read-only flow passes,
prioritize authenticated request-bound technician responses and enterprise input sync.
