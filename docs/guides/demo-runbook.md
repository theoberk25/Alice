# Integrated demo transition and runbook

Updated: 2026-09-06 UTC (September 5 EDT). Read [AGENTS.md](../../AGENTS.md)
and [current.md](../../current.md) before changing the deployment. This is the
single active runbook for connecting the wireless network, enterprise simulator,
local and cloud agents, Pi, USB ledger, physical lights and technician console.

## Current state and target

The wired first-light path works today:

```text
signed local action
  → SSH tunnel → Pi runtime → permissions check / fixture assessment
  → USB-serial XIAO → one of eight blinking lights
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
| Pi runtime | `alice-pi-01`, `192.168.50.20`, systemd, physical serial controller | Full synced permissions, real anomaly inference and authority state |
| Storage | ext4 USB at `/mnt/alice-usb`; ledger/evidence in `pi-data`; signed release in `release` | Atomic enterprise permissions/baseline activation without replacing audit history |
| Enterprise | Wazuh/Sentinel simulator on Jared's Mac; Pi audit upload works | Publish signed cache releases and reconcile DDIL findings |
| Agents | Provisioned signed terminal client works through an SSH tunnel | Separate local and cloud identities, authenticated gateway and active-mode routing |
| Technician | Authenticated LAN web app shows live Pi events, read-only | Native Tauri app with local LLM, facial identity and request-bound accept/reject |
| Physical demo | Eight stable targets blink slowly; signed all-off is available | Grid asset names, telemetry and agreed interlocks |

Focused references are limited to the [technician integration contract](../integration/technician-console.md),
[Pi/Wazuh contract](../integration/wazuh-audit-sync.md),
[release snapshot contract](../integration/release-snapshot.md),
[console wire contract](../integration/upstream-alice.md), and
[hardware runbook](first-light-hardware.md). Detailed progress stays in the
[implementation tracker](../implementation-tracker.md).

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

Configure the wireless router as an **access point or bridge** and connect one of
its LAN ports to the Ethernet switch. Keep the existing `192.168.50.0/24` network
so the Pi stays `192.168.50.20` and Jared's host stays `192.168.50.50`. Use exactly
one DHCP server. Reserve the existing static addresses or keep DHCP away from them.
Do not connect the WAN/uplink until local wired and wireless checks pass.

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
