# Integrated demo transition and runbook

Updated: 2026-09-06 UTC (September 5 EDT). Read [AGENTS.md](../../AGENTS.md)
and [current.md](../../current.md) before changing the deployment. This is the
single active runbook for connecting the wireless network, enterprise simulator,
local and cloud agents, Pi, USB ledger, physical lights and technician console.

## Current state and target

The wired first-light path works today:

```text
signed local action
  → Pi runtime → verified permissions + live fan-model assessment
  → protected fan state or USB-serial XIAO light controller
  → ext4 USB ledger → automatic Wazuh upload
  → authenticated read-only technician web app
```

The transition adds a wireless access point, internet/cloud-agent reachability,
enterprise permission and baseline synchronization, and the full native technician
application. Wireless transport does not change decision authority. ONLINE remains
enterprise-controlled execution; OFFLINE permits ALICE execution only after an
explicit control transfer and readiness checks.

| Surface | Current | Next integration |
| --- | --- | --- |
| Pi runtime | `alice-pi-01`, `192.168.50.20`, systemd, light serial controller plus deployed fan model/state controller | General synced permissions and authority state |
| Storage | ext4 USB at `/mnt/alice-usb`; ledger/evidence in `pi-data`; signed release in `release` | Atomic enterprise permissions/baseline activation without replacing audit history |
| Enterprise | Wazuh/Sentinel simulator on Jared's Mac; Pi audit upload works | Publish signed cache releases and reconcile DDIL findings |
| Agents | Provisioned signed terminal client works through an SSH tunnel | Separate local and cloud identities, authenticated gateway and active-mode routing |
| Technician | Native Tauri app shows live Pi events and uses facial identity for request-bound accept/reject | Add local-LLM explanation to the supplied structured fan assessment |
| Physical demo | Eight stable targets blink slowly; signed all-off is available | Grid asset names, telemetry and agreed interlocks |

Focused references are limited to the [technician integration contract](../integration/technician-console.md),
[Pi/Wazuh contract](../integration/wazuh-audit-sync.md),
[release snapshot contract](../integration/release-snapshot.md),
[console wire contract](../integration/upstream-alice.md), and
[hardware runbook](first-light-hardware.md). Detailed progress stays in the
[implementation tracker](../implementation-tracker.md).

## Target story: connected activity to a contextual DDIL hold

This is the agreed integrated demonstration. The fan model/runtime and native
review contract are implemented; agent triggers, general control transfer, real
sensors and the final local-LLM explanation still need integration.

| Device | Demo address / attachment |
| --- | --- |
| Opal | `192.168.50.1`; DHCP `.100-.199` while powered |
| Pi | Static `192.168.50.20`; wired switch |
| Theo technician workstation | Suggested static `192.168.50.30`; wired switch |
| Jared enterprise/Wazuh Mac | Reserved/static `192.168.50.50`; Opal Wi-Fi only |
| Local-agent laptop | Suggested static `192.168.50.60`; wired switch; two agent keys are allowed |

Confirm each address is unused before assignment. If two physical agent laptops
are used, assign the second `.61`. Keep `.50` reserved while enterprise is absent.

### ONLINE scene

1. Keep the Opal powered in Router/Repeater mode. Connect its LAN port to the
   switch and its wireless uplink to the venue Wi-Fi.
2. Connect Jared's enterprise Mac only to `ALICE-NETWORK`; forget/disable its
   direct `DNHacks` profile and remove its switch cable. Reserve `.50` for this
   Mac so the Pi's verified Wazuh endpoint remains stable.
3. A separately authenticated cloud-agent simulator joins `ALICE-NETWORK` and
   submits an ordinary action to the enterprise gateway on Jared's Mac. Label this
   as a simulated cloud source; a true internet-hosted agent needs the unfinished
   authenticated public gateway. The Pi is never exposed directly to the internet.
   **Target:** enterprise controls execution and emits one authenticated activity
   stream with the same agent/request identity.
4. Show the request, authorization/result and responsible identity in the SIEM.
   Show the same correlated activity and context in the technician console.
5. Record the current cache generation and a known audit backlog before outage.

### Physical transition to OFFLINE/DDIL

1. Unplug power from the Opal. This removes the wireless cloud path and Jared's
   Wi-Fi-only enterprise Mac while leaving the Ethernet switch operational.
2. Theo's technician workstation, the Pi and the local-agent laptop remain wired
   with static `192.168.50.0/24` addresses. DHCP is unavailable while the Opal is
   off. Keep `.20` for the Pi and `.50` unused until enterprise returns.
3. The enterprise console remains visible locally on Jared's disconnected Mac and
   displays **ALICE EDGE OFFLINE**, last successful contact, stale duration and
   paused synchronization. It reports authority as unknown until a separate
   handover signal establishes ALICE ownership.
4. Complete the explicit authority-transfer step. Power loss, a failed heartbeat
   or an offline banner cannot authorize the Pi by itself.

### Sequential local-agent scene

Use two authenticated signing identities even if one wired laptop runs both clients.
The synthetic normal-behavior package explicitly contains small `+10%` fan-speed
adjustments under overheating conditions. Mark this data as demo-generated; it is
not a learned production safety envelope.

1. `cooling-agent-01` submits `set_fan_speed` with the current value plus 10.
2. The Pi verifies permission, scores it against the normal sequence and emits
   ALLOW. Execute and record the resulting fan level.
3. Repeat with two new signed request IDs, waiting for each prior result. All three
   requests should receive ALLOW and raise the fan setting by a total of 30 points.
4. The resulting power observation crosses the configured demo wake threshold for
   `power-agent-01`. Keep the exact threshold in the signed fixture/package rather
   than inventing a production electrical limit in the UI.
5. `power-agent-01` submits `set_fan_speed` with `parameters.value=0` to reduce power.
6. Although this agent is permitted to request fan control, the Isolation Forest
   classifies the abrupt shutdown as `HIGH` relative to the learned
   small-step sequence and fresh overheating telemetry. The Pi assessment adds the
   matching `ANOMALY_REVIEW_REQUIRED` reason; the technician application presents
   HOLD. The compact native payload includes the exact request, decision reasons,
   model ID/fingerprint, calibrated score and model reason codes. Detailed factors
   remain retained Pi evidence and are not yet rendered by the console.
7. The local LLM explains those supplied facts and recommends rejecting shutdown
   while temperature remains too high. It cannot change HOLD or authorize action.
8. The technician reviews the single HOLD and chooses REJECT. The Pi records the
   bound rejection; it sends no fan-off command and confirms the fan remains at
   the last approved level. Audit all four requests and their outcomes to USB.

A hard prohibition would produce DENY rather than HOLD. The demo permissions and
threshold fixtures must deliberately make fan-off eligible for review so the human
rejection path is exercised without weakening hard-deny precedence.

### Return ONLINE

Power the Opal back on, restore its venue Repeater connection, and reconnect
Jared's enterprise Mac to `ALICE-NETWORK` as `.50`. Confirm the Pi authenticates
Wazuh, uploads every queued DDIL event without duplicates and preserves the three
ALLOW decisions, the shutdown HOLD, technician rejection, unchanged fan state and
later reconciliation as separate records.

## Preserve the working deployment before pulling

Do not copy a teammate's directory over this checkout. Each contributor should
commit or stash tracked changes, inspect `git status`, and pull with
`git pull --ff-only origin main` after the new checkpoint is published. Resolve a
real branch divergence by merging reviewed changes; never discard `apps/desktop`,
`dcamr`, `cloud`, firmware or local service work to make Git appear clean.

Git does not carry `.env*`, signing seeds, service credentials, biometric stores,
model files, USB data or installed systemd overrides. Preserve those separately.
On the Pi, a pull does not reload the running process. Coordinate any service
restart, retain its full installed arguments, and never launch a second runtime or
ledger writer beside `alice-runtime.service`.

Before a Pi maintenance window:

```sh
ssh pi@192.168.50.20 'systemctl is-active alice-runtime; findmnt /mnt/alice-usb'
ssh pi@192.168.50.20 'curl -fsS http://127.0.0.1:8080/sync-status'
```

## Add wireless without breaking the wired LAN

The deployed GL.iNet Opal uses **Router mode with a wireless Repeater uplink**.
Its LAN is `192.168.50.1/24`, DHCP is `.100-.199`, AP isolation is disabled and
one LAN port connects to the Ethernet switch. Keep the Pi at `192.168.50.20` and
Jared's host at `192.168.50.50`; do not use Access Point/WDS mode or connect the
physical WAN port to the ALICE switch. The venue Wi-Fi is the Opal's wireless WAN.

Observed September 6: a wireless Mac on `ALICE-NETWORK` authenticated to the wired
Pi; Pi-to-router and Pi-to-public-IP checks had zero loss. The Pi's persistent
default route is now `192.168.50.1` on `eth0`, and its direct venue Wi-Fi profile
has autoconnect disabled. ALICE remained active and `/sync-status` remained healthy.

Recommended demo firewall exposure:

| Port | Host | Current exposure | Purpose / transition |
| --- | --- | --- | --- |
| 22 | Pi `192.168.50.20` | LAN, provisioned keys | Authenticated SSH tunnel and maintenance |
| 1420 | Jared `192.168.50.50` | Authenticated LAN web | Interim read-only technician dashboard |
| 8787 | Jared | Loopback only | Enterprise SIEM console; add authenticated TLS web ingress before LAN exposure |
| 8789 | Jared | Loopback only | Presenter operator; agents use signed requests instead of this UI |
| 9200 | Jared | Pi only | TLS Wazuh indexer API; do not expose to browsers or agents |

Keep Pi port 8080 and the runtime-feed bridge on loopback. Agents and browsers
must not bypass the signed request path by directly reaching the ESP or an
unauthenticated Pi endpoint. After Wi-Fi joins the same subnet, check from a new
device:

```sh
ping -c 3 192.168.50.20
ping -c 3 192.168.50.50
ssh -o BatchMode=yes pi@192.168.50.20 true
```

Verify the supplied Pi ED25519 fingerprint during first connection:
`SHA256:uFZ6XoYVJ6PevSXSi2kyGQeM9XV/P6pks125tDddPEY`.
Provision each person's public SSH key; never disable host-key checking.

Once local checks pass, connect the router WAN and verify DNS, time and the
specific enterprise/cloud endpoints. A working internet connection does not by
itself switch ALICE to ONLINE or grant a cloud agent execution rights.

The complete scenario above powers off the Opal and therefore uses static wired
addresses for every DDIL participant. A less disruptive network-only test may
disconnect the Repeater while leaving local Wi-Fi and DHCP running, but that does
not remove a Wazuh host still attached to the switch. Theo's technician app must
run independently before Jared's enterprise Mac leaves; the interim web server on
Jared's Mac disappears with it.

## Start the current presentation services

The enterprise SIEM (`http://127.0.0.1:8787`) and signed operator
(`http://127.0.0.1:8789`) run on Jared's Mac. Their credentials and agent keys stay
in ignored local configuration. The Pi service owns the USB ledger and uploads
new canonical events to Wazuh automatically. Both enterprise/operator development
servers currently bind to loopback. Keep them there until an authenticated TLS
reverse proxy or equivalent server-side login is configured for wireless browsers;
screen sharing is the current presentation path. Do not make either public by
changing a bind address alone.

For the interim technician web app, create an ignored `.env.web-dashboard`:

```dotenv
ALICE_FEED_TOKEN=<random value of at least 32 characters>
ALICE_FEED_URL=http://127.0.0.1:8788
ALICE_WEB_USERNAME=<technician web username>
ALICE_WEB_PASSWORD=<password of at least 12 characters>
ALICE_WEB_PUBLIC_HOST=192.168.50.50:1420
ALICE_WEB_LISTEN=lan
VITE_ALICE_WEB_LOGIN=enabled
VITE_ALICE_PREVIEW_MODE=remote
```

Run these in separate terminals from the repository root:

```sh
ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -L 127.0.0.1:18080:127.0.0.1:8080 pi@192.168.50.20
```

```sh
set -a
. ./.env.web-dashboard
set +a
.venv/bin/python -m services.runtime_feed \
  --upstream http://127.0.0.1:18080 --source ssh-tunnel \
  --controller physical-serial --port 8788
```

```sh
set -a
. ./.env.web-dashboard
set +a
npm run dev
```

Connected devices open `http://192.168.50.50:1420`. Web sessions are server-side,
expire after eight hours and have a logout control. This HTTP service is for the
isolated demo network. Use TLS before placing it on a routed or shared network.
The web app is read-only and never receives the feed token, SSH keys, Wazuh
credentials or ledger key.

## Connect local and cloud agents

Every agent gets its own ID, private signing key and permissions binding. A web
login name or source IP is not an agent identity. Keep seeds out of Git and chat.
The current local client submits through the SSH tunnel:

```sh
.venv/bin/python -m lab.first_light.terminal_client \
  --url http://127.0.0.1:18080 \
  --key-file /absolute/private/path/elec-agent-01-k1.seed \
  --agent elec-agent-01 --target ESP-LIGHT-01 --state on --repeat 2
```

The repeated envelope must return the stored result without another actuation.
Use `--state off` to stop that light or the operator's **All lights off** control,
which sends eight separately signed and audited requests.

For additional local agents, provision distinct keypairs and signed grants through
the enterprise permissions release process. For cloud agents, terminate internet
authentication at an enterprise-controlled gateway. Do not expose the Pi runtime
directly to the internet. Preserve the cloud agent ID, responsible user, mission,
request ID and signature through the gateway so Wazuh, ALICE and the technician
console correlate the same action.

During ONLINE operation, enterprise systems own execution and ALICE synchronizes
trusted context plus audit observations. During OFFLINE operation, reject cloud
requests that cannot reach the local authenticated boundary; local agents may be
evaluated only after ALICE has confirmed local authority. Do not permit both paths
to command the same protected target concurrently.

## Integrate the native technician application

The current web app remains the viewing surface until the native application is
finished. The native source is already under `apps/desktop/` with shared contracts
in `packages/` and local ArcFace/Ollama services on the technician Mac. Preserve
the current web feed adapter while adding writable native transport.

The native integration must:

1. Receive the same immutable request, assessment, decision, evidence and execution
   events shown by the web app.
2. Send HOLD evidence to the workstation's local LLM for explanation only. The LLM
   does not change permissions, scores or final authorization.
3. Require a fresh facial verification and a short-lived, one-use proof bound to
   the exact current request and assessment before `APPROVE_ONCE`.
4. Send an authenticated accept/reject response to the Pi. The Pi rechecks hard
   prohibitions, currentness, permissions, authority and USB availability.
5. Display submission receipt separately from controller receipt, execution result
   and observed state. Reject stale, replayed or superseded approvals.

Use the executable shapes in [upstream-alice.md](../integration/upstream-alice.md).
Do not add technician writes to the interim browser proxy.

## Enterprise synchronization boundaries

The implemented Pi-to-Wazuh path uploads every canonical USB ledger event with
create-only IDs and exact read-back. The incoming enterprise path must publish
signed, versioned permissions and normal-behavior/model releases. Download to a
staging generation, verify signature, schema, digest, compatibility, validity and
anti-rollback metadata, then atomically activate it. Never replace the audit ledger
or erase queued DDIL events while updating input caches.

On reconnect, the Pi directly drains pending audit events, reports high-risk and
unresolved DDIL actions, fetches delayed evidence, appends reconciliation findings,
and refreshes verified caches. The technician workstation is not the enterprise
relay. See [wazuh-audit-sync.md](../integration/wazuh-audit-sync.md) and
[release-snapshot.md](../integration/release-snapshot.md).

## Acceptance sequence

Use one request ID across each observable surface:

1. Submit a permitted local-agent light request. Confirm one actuation, seven
   correlated USB events, live technician display and exact Wazuh documents.
2. Repeat the identical envelope and confirm no second actuation or event chain.
3. Submit an ungranted identity and confirm denial with no execution attempt.
4. Repeat the normal request from a Wi-Fi client through its authenticated tunnel.
5. Disconnect only the technician tunnel; the Pi must continue and the dashboard
   must retain history, show disconnection and recover without fixture fallback.
6. Disconnect Wazuh; local operation must continue, events remain pending, and
   reconnection must upload without duplicates. This still does not transfer control.
7. After native integration, exercise an unusual permitted request: HOLD, local LLM
   explanation, fresh face proof, human accept/reject, Pi revalidation and one result.
8. Demonstrate ONLINE enterprise ownership, controlled OFFLINE transfer and return
   to ONLINE without simultaneous controllers or reused offline approvals.

For the planned physical machine swap, establish the online checkpoint before
unplugging anything: record the accepted cache generation, empty uploader backlog
and last Wazuh event ID. Disconnect the Opal Repeater and Jared's enterprise Mac,
then connect the separately provisioned local-agent laptop and submit through the
signed client. Verify the action, ESP result, Theo technician display and USB
ledger while Wazuh is absent. Reconnect the original enterprise Mac at `.50`,
restore the Repeater, and verify queued event upload/read-back without duplicates.

The read-only checker can compare an existing request across runtime, USB and Wazuh
without creating another writer:

```sh
.venv/bin/python -m lab.first_light.check_pipeline \
  --request-id <request-id> --expect ALLOW \
  --usb-root /mnt/alice-usb --data-dir /mnt/alice-usb/pi-data \
  --wazuh-config /home/pi/first-light/wazuh-sync/config.json --wait-seconds 60
```

Record request IDs and observed results without credentials, seeds, biometric
material or private LLM reasoning. Remaining live outage, reboot, USB removal,
power-loss, real anomaly, permissions activation, cloud gateway and native approval
checks stay open until their exact acceptance steps pass.
