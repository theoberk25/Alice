# First-light test log and network runbook (2026-09-05)

Evidence record per [AGENTS.md](../../AGENTS.md). Companion to the
[Pi backend status report](2026-09-05-pi-backend-status.md) and the
[implementation handoff](../handoffs/2026-09-05-first-light-test.md).
Everything below was actually executed this session; nothing is projected.

## 1. Automated test suites

| Where | Command | Result |
| --- | --- | --- |
| Mac (workstation) | `.venv/bin/python -m unittest tests.test_first_light -v` | 6/6 OK (re-run after every change; final run green) |
| Mac | `.venv/bin/python -m unittest discover -v` | 263 tests OK, 30 pre-existing skips |
| **Raspberry Pi (alice-pi-01)** | `ssh alice-pi "cd ~/Alice && .venv/bin/python -m unittest tests.test_first_light -v"` | 6/6 OK on hardware (6.2s) |
| Mac | `npm run typecheck` (technician console) | clean |

The 6 first-light tests assert the acceptance checklist: bad signature →
REJECTION with no execution; key/agent binding mismatch rejected; authenticated
request without a grant → NO_PERMISSION (REQUEST + REJECTION chain); happy path
with the full 7-event correlated chain and evidence-hash binding; identical
request_id retried → exactly one ESP command and a replayed outcome
(request_id reuse with different content → 409); `validate()` after seal +
reopen; USB export records match ledger `event_hash`es.

## 2. Live integration runs (Mac → switch → Pi → mock ESP)

All requests were Ed25519-signed on the Mac and decided/executed/ledgered on
the Pi at `192.168.50.20:8080`, mock ESP on the Pi at `127.0.0.1:8090`.

| Request | Agent (responsible user) | Action | Outcome |
| --- | --- | --- | --- |
| `b639ad34…` | term-agent-01 (theo-test) | state on, `--repeat 2` | ALLOW/COMPLETED; retry replayed; ESP commands = 1 |
| `f08339e8…` | term-agent-01 | state on | ALLOW/COMPLETED, watched live in technician_view |
| `2323efa6…` | elec-agent-01 (SSgt A. Okafor) | state on | ALLOW/COMPLETED — first SIEM-identity run |
| `8ea18938…`, `0002b431…`, `4c604050…` | elec-agent-01 | off / on / on | ALLOW/COMPLETED, rendered live on the workstation console |
| `2a4b221d…` | elec-agent-02 (MSgt D. Reyes) | state off | ALLOW/COMPLETED — second user, key of its own |
| `f766e2c7…` | appr-agent-01 (A1C R. Delgado, training account) | state on | **DENY 403 NO_PERMISSION**, execution BLOCKED, ESP command count unchanged (8) |

Additional verifications: ledger `validate()` clean after reopen
(`event_count=7, covered_sequence=7` on the dry-run ledger); USB export
queue → NDJSON → hash-verify → acknowledge succeeded (Mac dry run); the
workstation console and the SIEM console's "Live edge" tab both rendered every
chain within ~2s of the Pi committing it (1.2–1.5s polling).

## 3. Network runbook — connecting to the Pi from any device

Current state of the network and the Pi:

- Unmanaged switch, **no DHCP**. Static subnet `192.168.50.0/24`.
- Pi `alice-pi-01`: ethernet `192.168.50.20/24` (persistent, auto-connect),
  Wi-Fi `192.168.8.202` (venue Wi-Fi, used only for package installs; also
  reachable as `alice-pi-01.local` via mDNS).
- Assigned addresses: Theo's Mac `.10`, Pi `.20`, technician laptop `.30`,
  ESP (future) `.40`.
- SSH: user `pi`, **public-key auth** — currently only Theo's Mac key is
  installed. A new device needs its key added (from an authorized machine:
  `ssh-copy-id -i ~/.ssh/id_ed25519.pub pi@192.168.50.20`) or the password
  set at flash time.

### 3a. Any new device (developer)

1. Ethernet into the switch. Set IPv4 **manually**: address `192.168.50.x`
   (pick a free host, avoid .10/.20/.30/.40), mask `255.255.255.0`, router
   blank. macOS: System Settings → Network → adapter → Details → TCP/IP.
2. Verify: `ping 192.168.50.20` (expect ~1ms).
3. Shell access (after key provisioning): `ssh pi@192.168.50.20`.
4. Runtime health: `curl http://192.168.50.20:8080/events?after=0`.
5. The Pi processes run in tmux sessions `esp` (mock ESP) and `runtime`
   (`dcamr.main`); `tmux attach -t runtime` to watch, `Ctrl+B D` to detach.
   Data lives in `~/first-light/` (release, trust, pi-data ledger, logs);
   code in `~/Alice` (deployed by `rsync` from the Mac checkout — the GitHub
   repo is private and the Pi holds no credentials).

### 3b. IT technician (read-only observer)

The technician needs no SSH and no repository — only IP reachability to port
8080 on the Pi. Three options, lightest first:

1. **CLI viewer** — copy the single stdlib file
   `scripts/lab/first_light/technician_view.py` to the laptop, set the static
   IP (`192.168.50.30/24`), then:
   `python3 technician_view.py --url http://192.168.50.20:8080 --follow`
2. **Standalone web dashboard** — copy
   `scripts/lab/first_light/dashboard/index.html`, serve it locally
   (`python3 -m http.server 8123`) and open
   `http://127.0.0.1:8123/?pi=192.168.50.20:8080`. The Pi's `/events` reply
   carries `Access-Control-Allow-Origin: *`, so the browser polls it directly.
3. **Full ALICE workstation console** — needs Node on the laptop and the repo:
   `npm install`, then
   `VITE_ALICE_PREVIEW_MODE=remote VITE_ALICE_EDGE_URL=http://192.168.50.20:8080 npm run dev`
   and open `http://127.0.0.1:1420/`. (The vite dev server binds localhost;
   each viewer runs their own instance rather than sharing one.)

All three consume the same read-only `GET /events` ledger projection; none can
approve, deny or execute anything — by design in this slice.

### 3c. ESP (future physical step)

Static `192.168.50.40` in firmware; must serve `POST /light`
(`{"state":"on"|"off"}`) and `GET /light`. Verify with curl from the Pi, then
restart the runtime with `--esp-url http://192.168.50.40`.

## 4. Known caveats

- Rebuilding a release regenerates all terminal keys: previously issued seeds
  stop verifying (UNKNOWN_KEY 401). Rebuild + `scp` + runtime restart together.
- Every key in play is demonstration trust only.
- The dashboards' displayed action/target is echoed from the pinned first-light
  contract because the strict ledger REQUEST event carries no action/target
  fields (see improvement roadmap in the status report).
