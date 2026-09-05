# Enterprise SIEM simulation — team handoff

**Status:** working simulation, runnable end to end. **Not** a Pi deployment.
**Owner of this increment:** Jared (anomaly model + permissions tracker).
**Scope:** self-contained enterprise simulation handoff. The Pi runtime and
technician console remain separate integrations.

Everything here is invented for a demonstration: every person, unit, address,
asset, credential and measurement. Nothing is real base data, an approved
permissions release, or an agreed electrical operating limit.

---

## 1. Where each piece sits

```text
Enterprise SIEM (Wazuh)                     authoritative, cloud side
  |   publishes permissions, baselines and model releases   (downstream)
  v   receives DDIL audit, findings and discrepancies       (upstream)
ALICE Pi                                    edge decision node
  ^   caches the last accepted releases for offline use, governs local
  |   agent actions while disconnected, reports on reconnection
  |   <-- data and decisions -->
ALICE technician software (Mac)             operator surface, talks to the Pi
```

The Wazuh deployment is **not** ALICE. It is the enterprise cybersecurity
platform ALICE synchronizes with while online. It never observes an offline
request as it happens — it holds the release it published and the record the edge
node returned when connectivity came back. The ALICE technician software runs on
the technician's Mac and connects to the Pi for state and decisions; it is not an
enterprise client.

Every artifact below is either something the enterprise sends **down**, or
something the edge sends **up**. Keeping that straight is the main thing this
increment is trying to protect.

---

## 2. What is in the repository

| Path | What it is | Commit? |
|---|---|---|
| `scripts/lab/enterprise_sim/` | Generator: scenario, permissions releases, baselines, datasets, Wazuh assets, activity | **yes** |
| `scripts/lab/enterprise_sim/console/` | Enterprise SIEM console (local read-only server + UI) | **yes** |
| `artifacts/enterprise-sim/usb/` | 60 KB, 11 files — the Pi's storage image | **yes** |
| `artifacts/enterprise-sim/wazuh/` | 136 KB, 12 files — rules, decoders, templates, RBAC, agent.conf, inventory | **yes** |
| `artifacts/enterprise-sim/logs/` | 56 KB, 2 files — returned audit + simulated IT activity | **yes** |
| `artifacts/enterprise-sim/reports/` | 12 KB — model fitting experiment results | **yes** |
| `artifacts/enterprise-sim/keys/*.pk` | Ed25519 **public** verifying key + README | **yes** |
| `artifacts/enterprise-sim/keys/*.sk` | Ed25519 **private** key | **NO — never commit a signing key** |
| `artifacts/enterprise-sim/datasets/` | 21 MB, 8 files — contextual training data | **no** — regenerates deterministically |

### Integration note on `.gitignore`

The repository now shares the generated release set while excluding datasets
and private-key files. These are the applied `.gitignore` rules:

```gitignore
# Generated enterprise simulation. The USB image, Wazuh configuration, returned
# audit and experiment reports are committed so everyone shares one release set.
# The contextual datasets are 21 MB and regenerate deterministically from seed
# 1729, so they stay out of the repository.
artifacts/enterprise-sim/datasets/
# Never commit signing keys, even demonstration ones.
artifacts/enterprise-sim/keys/*.sk
```

The generator's private key is deterministically derived from a public literal
in its source. Excluding the `.sk` file does **not** make that demo key secret:
anyone with the generator can recreate it. These signatures exercise mechanics
only. A real issuer must use separately provisioned secret key material and a
separately trusted public key; never trust this public demo key for real releases.

---

## 3. Regenerate everything

```bash
cd ~/Desktop/Alice && python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements-anomaly-training.txt cryptography
```

Use **Python 3.12**. The pins in `requirements-anomaly-training.txt`
(`numpy==1.26.4`) have no wheels for 3.13+, and 3.12.6 is what the README
already documents.

```bash
cd ~/Desktop/Alice && .venv/bin/python -m lab.enterprise_sim
```

Deterministic for seed 1729. The run validates what it wrote against the real
loaders — `load_baseline`, `load_context_profile`, `parse_context_observation` —
and against the audit hash chain, and exits nonzero if any contract rejects the
data. Two generator runs produce byte-identical trees in the verified Python 3.12
environment. The fitting report is a separate output; run the fit command to
regenerate it. Run `.claude/launch.json` from the repository root after setup; its
launcher now uses repository-relative paths.

```bash
cd ~/Desktop/Alice && .venv/bin/python -m lab.enterprise_sim.fit
```

Fits both contextual models in memory and scores the held-out normals and
labelled challenges. Writes `artifacts/enterprise-sim/reports/`. Saves no model.

---

## 4. The simulated base

**Sentinel Air Force Base (SEN)**, three enclaves: `10.42.10.0/24` ALICE and
management, `10.42.20.0/24` OT/SCADA, `10.42.30.0/24` IT services.

### People

| User | Unit | Role | Deploys agents | Console | Ceiling |
|---|---|---|---|---|---|
| MSgt D. Reyes | 899 CES/Power Pro | Power production supervisor | yes | yes | $5,000 |
| SSgt A. Okafor | 899 CES/Power Pro | Electrician | yes | yes | $1,000 |
| A1C R. Delgado | 899 CES/Power Pro | Apprentice electrician | yes | no | $0 |
| TSgt M. Lindqvist | 899 CS | Cyber defense operator | yes | yes | $0 |
| Capt J. Whitfield | 899 CES/Energy | Base energy manager | yes | yes | $2,500 |
| K. Tran, GS-12 | 899 CES/Ops Eng | Facility manager | yes | yes | $2,500 |
| P. Osei (contractor) | Meridian Grid Systems | Vendor support | yes | no | $0 |
| Col S. Hargrove | 899 MSG | Squadron commander | **no** | yes | $50,000 |
| `svc.alice-sync` | 899 CS | Pi sync principal | no | no | — |

The commander approves but deploys nothing; the vendor deploys an agent granted
no state change at all. Both exist so the permissions tracker has to prove it
separates *who may approve* from *who may act*.

### AI agents

| Agent | Type | Responsible user | Targets |
|---|---|---|---|
| `elec-agent-01` | electrician | SSgt Okafor | Feeder A/B RTU, metering GW |
| `elec-agent-02` | electrician | MSgt Reyes | Feeder A/B RTU, BESS |
| `elec-agent-07` | electrician | SSgt Okafor | Feeder B RTU — deployed *after* the cached baseline |
| `microgrid-agent-01` | microgrid dispatch | MSgt Reyes | SPIDERS MGC, BESS |
| `dr-agent-01` | demand response | Capt Whitfield | Metering GW |
| `maint-agent-01` | facility maintenance | K. Tran | BUILDER, WO API, TRIRIGA |
| `cyber-agent-04` | cyber defense | TSgt Lindqvist | SCADA HMI, TRIRIGA |
| `appr-agent-01` | apprentice read-only | A1C Delgado | Feeder A RTU |
| `vendor-agent-01` | vendor support | P. Osei | SCADA HMI, time-boxed |

`elec-agent-07` is the novelty case: no personal baseline profile, so it resolves
to the `electrician / power_distribution` cohort and keeps an explicit
`NO_AGENT_BASELINE` flag that a low anomaly score does not clear. The generator
asserts this fallback on every run.

### Protected systems

Ten, spanning the four base-ops workflows: `SPIDERS-MGC-01`, `SPIDERS-RELAY-03`,
`BESS-CTRL-02`, `FEEDER-A-RTU`, `FEEDER-B-RTU`, `METER-GW-01`, `SCADA-HMI-02`,
`TRIRIGA-APP-01`, `BUILDER-SVC-01`, `WO-API-01`.

### Workflows, mapped to the base-ops columns

| Workflow | Consequential action an agent proposes | What gates it |
|---|---|---|
| Microgrid control (SPIDERS) | `dispatch_generator`, `set_load_shed_priority`, `close_switchgear` | `P-GEN-ENVELOPE`, `P-PROTECTED-LOAD`; dispatch always needs technician step-up |
| Facility maintenance (BUILDER/TRIRIGA) | `create_work_order`, `order_parts`, `update_asset_record` | `order_parts` capped at the **user's** ceiling with step-up; `P-OFFLINE-PURCHASE` blocks it entirely while disconnected |
| Utility metering / demand response | `curtail_load` | `P-PROTECTED-LOAD`; needs a verified utility signal; keeps working offline |
| TRIRIGA system of record | `update_asset_record` | Step-up gated; every write lands in the tamper-evident chain |
| Power distribution (the demo) | `set_voltage_setpoint` | Grants bound 468–492 V; `P-VOLTAGE-ENVELOPE` hard-denies outside 456–504 V; PRE/POST anomaly assessment |

Hard prohibitions never reach the model. `disable_protective_relay` and
`drop_islanding` are denied for every agent, in every mode, with no override and
no approval path — and the denial does not depend on the model being available.
Nine prohibitions total; the returned audit records `model_invoked: false` on
each one.

### Electrical envelope — **placeholder, needs engineering sign-off**

| | Value |
|---|---|
| Nominal | 480.0 V |
| Grant band | 468.0 – 492.0 V |
| Hard band | 456.0 – 504.0 V (ANSI C84.1 Range A shaped) |
| Step-up delta | > 6.0 V (release 42) / > 4.0 V (release 44) |
| POST settle window | 2,000 ms |

---

## 5. The permissions release set

The enterprise publishes **three** releases; the simulated Pi cached only the
first. That gap is deliberate — it is the condition the permissions tracker
exists to detect.

| Gen | Status | Change |
|---|---|---|
| 42 | superseded | Baseline. What `alice-pi-01` cached before the DDIL window. |
| 43 | superseded | Revoked `vendor-agent-01` and `ctr.p.osei`; support contract ended early. |
| 44 | **current** | Extended `elec-agent-07` to feeder A; tightened step-up from 6.0 V to 4.0 V. |

### Bundle layout

```text
permissions/
  active                          -> generations/000042
  generations/000042/
    manifest.json                 issuer, generation, validity, digests,
                                  compatibility, signature block
    subjects.json                 users, agents, delegation, attribution source
    grants.json                   allow rules, parameter bounds, approval flags
    prohibitions.json             hard DENY, evaluated before grants
    revocations.json              with a monotonic revocation_epoch
    manifest.sig                  detached Ed25519 over canonical manifest
                                  minus its own signature block
  staging/<bundle_id>/            candidate, byte-bounded, deleted on failure
```

### Four properties that matter more than the field names

1. **The trust anchor is not on the USB.** The verifying key belongs in the Pi's
   read-only root filesystem. A key that travels with the data it verifies means
   swapping the drive swaps the trust root.
2. **Anti-rollback.** `generation` is monotonic; `last_accepted_generation` lives
   in Pi-local state, not on the USB. Without it, a USB swap replays an old
   bundle that still granted a revoked agent. The returned audit exercises this:
   a cached generation 41 arrived on reconnect and was refused with
   `STALE_GENERATION`.
3. **Atomic activation.** Verify the whole staged set, then replace the pointer
   on the same filesystem. ext4 is the proposed Linux ownership/journaling choice,
   pending Xavier's provisioning decision. Atomic name replacement and power-loss
   durability are different guarantees: activation also needs file/directory
   synchronization and recovery tests. Do not infer them from a filesystem name
   or claim FAT/exFAT categorically lacks every atomic rename operation.
   [Linux rename semantics](https://man7.org/linux/man-pages/man2/rename.2.html).
4. **Write isolation by Unix user.** `alice-sync` owns `permissions/` and
   `normal_behavior/`; `alice-decide` gets read-only and can write neither;
   `alice-audit` appends to `audit_logs/`. Mount `nodev,nosuid,noexec`. Folder
   labels enforce nothing.

### Tracker states

`NEVER_SYNCED → CANDIDATE_STAGED → VERIFIED → ACTIVE`, plus `REJECTED(reason)`,
`STALE_WITHIN_GRACE`, `EXPIRED`. Every transition is audited.

On expiry the release says what happens, and it never widens permission:
prohibitions stay `ENFORCED`, grants become `REVIEW_REQUIRED`.

### The resolver interface

```python
resolve(agent_id, action, target, params, now) -> PermissionOutcome
# PERMITTED | PROHIBITED | REVIEW_REQUIRED | UNRESOLVED
# + reason_codes, + generation/digest actually used, + attribution source
```

Pure, side-effect-free, no model call, no network. `PROHIBITED` must be reachable
without touching the anomaly model — which is why `prohibitions.json` is a
separate file with its own evaluation pass.

**Seam with core integration:** this increment owns storage, sync state,
verification and `resolve()`. Fusion — turning a `PermissionOutcome` plus an
anomaly assessment plus evidence into `ALLOW` / `REQUEST_CONTEXT` / `HOLD` /
`DENY` — belongs to Merek and Theo per handoff §2. Keeping `resolve()` pure is
what makes that seam clean. Settle it before either side writes into the empty
`dcamr/policy_engine/`.

---

## 6. Getting the data onto the Pi

The `usb/` tree is the storage image. After the owners approve the proposed
filesystem and provision an **ext4-formatted** drive, the intended copy is:

```bash
sudo cp -a ~/Desktop/Alice/artifacts/enterprise-sim/usb/. /media/alice-usb/
```

Then apply the ownership split the design requires:

```bash
sudo chown -R alice-sync:alice /media/alice-usb/permissions /media/alice-usb/normal_behavior && sudo chown -R alice-audit:alice /media/alice-usb/audit_logs && sudo chmod -R u=rwX,g=rX,o= /media/alice-usb/permissions /media/alice-usb/normal_behavior
```

Install **only** the public key, into the root filesystem, not the drive:

```bash
sudo install -m 0444 -D ~/Desktop/Alice/artifacts/enterprise-sim/keys/permissions-signing.ed25519.pk /etc/alice/trust/permissions-signing.ed25519.pk
```

`normal_behavior/` contains `cyber/baseline.json` (the `ops-sentinel` release for
the fixed five-action contract) and `contextual/sen-feeder-voltage-{pre,post}.json`
(the PRE/POST profiles). `audit_logs/` starts empty with a README explaining that
it is ALICE-generated output, outside the signed input digest set.

**Audit durability caveat.** The Wazuh agent cannot be the DDIL outbox: its client
buffer drops events once full and logcollector does not replay what it never read.
The simulation assumes the authoritative record is on the Pi's internal storage with the USB as the
transportable copy. That is a small shift from a literal reading of "`audit_logs/`
on the USB" and core integration should confirm it.

---

## 7. Standing up the enterprise SIEM

Verify every path against the version you deploy. These follow Wazuh 4.x.

```bash
git clone https://github.com/wazuh/wazuh-docker.git -b v4.14.7 ~/Desktop/sentinel-wazuh && cd ~/Desktop/sentinel-wazuh/single-node && docker compose -f generate-indexer-certs.yml run --rm generator && docker compose up -d
```

Needs roughly 4 GB of images and a few GB of RAM. Ports 443, 9200, 55000, 1514/5,
514/udp.

| Surface | URL | Credentials |
|---|---|---|
| Wazuh dashboard | `https://localhost` | `admin` / `SecretPassword` |
| Wazuh indexer | `https://localhost:9200` | `admin` / `SecretPassword` |
| Manager API | `https://localhost:55000` | `wazuh-wui` / `MyS3cr37P450r.*-` |
| Edge node's own account | — | `alice_pi` / `AlicePiDemo1!` |
| Enterprise SIEM console | `http://localhost:8787` | none, read-only |

These are stock demonstration credentials plus one invented for `alice_pi`. The
repo is private, but rotate them before anything but a laptop can reach the stack.

### 7.1 Index templates

```bash
cd ~/Desktop/Alice/artifacts/enterprise-sim/wazuh && curl -sk -u "admin:$INDEXER_PW" -X PUT "https://localhost:9200/_index_template/alice-permissions" -H 'Content-Type: application/json' -d @indexer/alice-permissions.template.json && curl -sk -u "admin:$INDEXER_PW" -X PUT "https://localhost:9200/_index_template/alice-audit" -H 'Content-Type: application/json' -d @indexer/alice-audit.template.json
```

`alice-permissions` is `dynamic: strict` on purpose: a release carrying
unexpected fields fails to index rather than landing half-understood.

### 7.2 The edge node's identity

```bash
cd ~/Desktop/Alice/artifacts/enterprise-sim/wazuh && curl -sk -u "admin:$INDEXER_PW" -X PUT "https://localhost:9200/_plugins/_security/api/roles/alice_pi" -H 'Content-Type: application/json' -d @indexer/role-alice-pi.json && curl -sk -u "admin:$INDEXER_PW" -X PUT "https://localhost:9200/_plugins/_security/api/internalusers/alice_pi" -H 'Content-Type: application/json' -d "{\"password\":\"$PI_PW\"}" && curl -sk -u "admin:$INDEXER_PW" -X PUT "https://localhost:9200/_plugins/_security/api/rolesmapping/alice_pi" -H 'Content-Type: application/json' -d @indexer/rolemapping-alice-pi.json
```

That role scopes permissions reads to `alice-permissions*` and writes to
`alice-audit-*`. **It is not append-only enforcement:** the current `write` and
`index` action groups also permit document mutation. The sample uploader uses
`create`, but an ALICE ingestion boundary and authorization tests must enforce
immutable events before real deployment.
[OpenSearch action groups](https://docs.opensearch.org/latest/security/access-control/default-action-groups/).

In a Docker deployment, users created through the security API can be lost on a
container rebuild unless `internal_users.yml` is updated too.

> **Wazuh RBAC governs who may call the Wazuh API. It is not the ALICE
> permissions model.** Mapping ALICE action grants onto `/security/policies`
> would make those grants change meaning whenever someone edits API access.
> Authority for bundle contents is `issuer_id` in the manifest; Wazuh is
> distribution and timestamping.

### 7.3 Seed the release set

```bash
cd ~/Desktop/Alice/artifacts/enterprise-sim/wazuh && curl -sk -u "admin:$INDEXER_PW" -X POST "https://localhost:9200/_bulk" -H 'Content-Type: application/x-ndjson' --data-binary @indexer/seed-permissions.bulk.ndjson
```

Each line uses `create` with an explicit `_id`, so a replay returns 409 instead
of writing a second copy. That is the same idempotency the reconnection outbox
will need, with an additional check: 201 acknowledges creation; a 409 is a
conflict, not proof the stored body matches. Verify the existing event/release
digest before treating it as already delivered. Classify permanent authorization/
validation errors separately from retryable transport errors; inspect every bulk
item rather than relying on the HTTP status alone.

If you change the release set, the index must be recreated — `create` will not
overwrite, so an existing generation keeps its old `status`.

### 7.4 Rules and decoders

Copy `rules/local_rules.xml`, `rules/esp_rules.xml` to `/var/ossec/etc/rules/`
and `decoders/local_decoder.xml` to `/var/ossec/etc/decoders/`, `chown
wazuh:wazuh`, then **validate before restarting**:

```bash
docker exec single-node-wazuh.manager-1 /var/ossec/bin/wazuh-analysisd -t
```

The ALICE audit is JSON, so Wazuh's built-in decoder parses it and the rules
match `alice.*` fields directly. The custom decoder is only for the ESP's plain
syslog line.

Rules 100100–100199. The levels that matter most:

| Rule | Level | Fires on |
|---|---|---|
| 100114 | 12 | Hard prohibition blocked an action |
| 100122 | 14 | Older permissions generation refused — possible rollback |
| 100131 | 13 | Current execution authority unknown; execution blocked |
| 100142 | 12 | Commanded value and measured value disagree |
| 100170 | 14 | Audit sequence gap against the last trusted checkpoint |

### 7.5 Enroll the Pi

Create the `alice-pi` group, upload `shared/alice-pi/agent.conf` via
`PUT /groups/alice-pi/configuration` (`Content-Type: application/octet-stream`),
then:

```bash
sudo WAZUH_MANAGER='10.42.10.5' WAZUH_AGENT_NAME='alice-pi-01' WAZUH_AGENT_GROUP='alice-pi' apt-get install wazuh-agent
```

`wazuh/inventory.json` lists all thirteen endpoints and which run an agent — the
relay bank and the two ESP feeder nodes forward syslog instead, because a
microcontroller does not run a Wazuh agent. The pushed `agent.conf` also puts
`syscheck` in realtime on the trusted input directories, to detect changes to
`permissions/`. Do not assume this configuration alone proves which Unix principal
made the change or selectively exempts the updater; actor attribution needs its
own supported collection/configuration and acceptance tests.

The Wazuh agent must share the 2 GB Pi with the scoring worker and other services.
No agent RSS or combined Pi budget has been measured in this integration; measure
the actual configuration before deployment.

### 7.6 Feed the sample activity

```bash
sudo mkdir -p /var/lib/alice/audit && sudo cp ~/Desktop/Alice/artifacts/enterprise-sim/logs/alice-audit.jsonl /var/lib/alice/audit/mission-audit.jsonl
```

Create the monitored files **empty first, then restart the manager, then append**
— logcollector seeks to the end of a file it has already seen, so content written
before it starts is never read.

`logs/it-network-activity.jsonl` carries the surrounding base traffic. It is
JSONL; convert to syslog lines (`<date> <host> <program>[pid]: <message>`) if you
want the ESP decoder to fire on it.

---

## 8. The Enterprise SIEM console

```bash
cd ~/Desktop/Alice && .venv/bin/python -m lab.enterprise_sim.console
```

Serves `http://localhost:8787`. Reads the live indexer when reachable and falls
back to the generated files when not, and the header always says which. Read-only:
it authorizes nothing, executes nothing, and computes no decisions of its own.

Seven tabs, each labelled with its direction (↓ published downstream, ↑ returned
upstream):

| Tab | Shows |
|---|---|
| Overview | Topology, current published release, fleet posture |
| **Edge fleet** ↕ | Per-node sync state and the synchronization delta |
| Identity ↓ | Authoritative users, agents and delegation |
| Published permissions ↓ | Agent × action matrix for the *current* release |
| Returned activity ↑ | What the edge reported, with the generation each decision used |
| Behavior models ↓ | Model releases and the fitting experiment |
| Endpoints & alerts | SIEM telemetry |

Wazuh's own dashboard shows the SIEM plane but renders neither the permissions
releases nor the returned edge record — those live in custom indices it knows
nothing about. That is the gap the console fills.

### The synchronization delta is the point

With the node on generation 42 and the enterprise on 44, the console diffs the
two signed bundles and reports:

- **`G-VENDOR-READ` is still honoured at the edge.** Withdrawn upstream in
  release 43; the node has not seen the withdrawal and keeps applying it until it
  resynchronizes. This is the sharp end of a stale cache, and the reason
  revocation lists, freshness rules and offline grace need explicit answers.
- **Two revocations the node has never seen**, epoch 7 at the node against 8
  upstream.
- **`G-ELEC-SETPOINT-A` changed** in both agent list and parameter bounds; the
  node is applying the looser 6.0 V step-up threshold.

The Published permissions matrix renders generation 44 and carries a banner
saying it is *not* what the Pi is enforcing while disconnected. The Returned
activity tab has a `gen` column recording which cached release each decision
actually used. Conflating those two would be the worst mistake this console could
make.

---

## 9. The two model tracks

Deliberately separate contracts. They must stay that way.

**Cyber — `cyber-behavior-v1`.** `dcamr/anomaly_engine/baseline.py` pins exactly
five actions and their parameter semantics. `usb/normal_behavior/cyber/baseline.json`
reuses that contract unchanged and only swaps in Sentinel's targets, profiles,
agents and cohorts. `set_voltage_setpoint` is **not** in it and must never be
added — the same rule the docs already state for servo angles.

**Physical — `context-behavior-profile-v1`.** Two profiles, PRE and POST, routed
on `feeder_id × operating_mode`, three fitted contexts. Feeder A grid-tied is
tight (480.2 ± 1.6 V); feeder A islanded is loose (478.6 ± 4.2 V) and cycles far
more often; feeder B is quiet. Those disagreeing normals are the whole point of
exact-context routing.

### What the fitting experiment showed

Held-out normals land `LOW` about 93–95% of the time in every context, which is
what 0.95/0.99 band thresholds are built to produce. The challenges:

| Challenge | Phase | Band | Score | Caught by range comparison |
|---|---|---|---|---|
| `actuator_no_response` | POST | **HIGH** | 0.993 | `setpoint_error_v` |
| `overshoot` | POST | ELEVATED | 0.976 | `settled_bus_voltage_v`, `setpoint_error_v` |
| `slow_settle` | POST | ELEVATED | 0.969 | `settle_duration_ms` |
| `load_collapse` | POST | ELEVATED | 0.968 | `settled_load_current_a` |
| `out_of_band_setpoint` | PRE | ELEVATED | 0.972 | `requested_setpoint_v` |
| `quiet_feeder_burst` | PRE | ELEVATED | 0.954 | `changes_last_hour` |
| `rapid_cycling` | PRE | **LOW** | 0.879 | `seconds_since_last_change`, `changes_last_hour` |
| `large_delta_islanded` | PRE | **LOW** | 0.916 | `requested_setpoint_v` |
| `unstable_bus` | PRE | **LOW** | 0.871 | `bus_voltage_stddev_5m_v` |
| `unseen_feeder` / `unseen_mode` | both | UNKNOWN | null | routing refused to score |

**Three constructed challenge requests scored LOW.** This experiment shows that
forest scoring can miss an extreme individual dimension; it does not establish
a universal explanation for every miss. The deterministic `outside_training_range`
comparison caught every one of them, and it is a separate signal fusion has to
weigh on its own — the same finding the existing training docs record for unseen
endpoints. A low percentile must never suppress a range flag or a novelty flag.

`actuator_no_response` is the case worth demoing: the controller returned
`SUCCESS` and the bus never moved. The POST assessment is the only thing that
notices, because a command receipt is not an independent measurement.

The two `UNKNOWN` rows are a refusal to score, not a low score.

### Recommendation for Pi deployment — do not ship a pickle

`joblib.load` of a scikit-learn model is arbitrary code execution, and the
artifact reaches the Pi over a network onto removable media. Export the fitted
forest to a data-only format (per-tree `children_left`, `children_right`,
`feature`, `threshold`, `n_node_samples`) and write a NumPy scorer reproducing
`score_samples`:

$$s(x) = -2^{-\frac{E[h(x)]}{c(n)}}, \quad c(n) = 2H(n-1) - \frac{2(n-1)}{n}$$

with $H(i) \approx \ln(i) + 0.5772156649$, the leaf adding $c(n_{\text{node samples}})$
when it holds more than one sample. At 64 trees × 256 samples the trees are ≤511
nodes. This drops scikit-learn from the Pi entirely (NumPy only) and removes the
dependency on a scikit-learn runtime on the Pi. Numerical compatibility still
requires validation: reproduce float32 input conversion, threshold routing and
scikit-learn's exact `c(1)=0`, `c(2)=1` special cases before its logarithmic
approximation. Proposed acceptance includes absolute error below 1e-9 on held-out
calibration/evaluation and challenge cases, plus threshold boundaries and small/
degenerate leaves. Bind validated trees, profiles and calibration references in
the eventual signed format; this formula is not an export implementation.

**Not yet implemented.** The current fitting stays in memory and saves nothing.

---

## 10. Verification evidence

Publishing review independently regenerated two byte-identical 37-file trees,
matched all 28 generated publishable artifacts (the experiment report is a
separate 29th artifact), verified every dataset row's stored digest/label and
per-phase split lineage, and reproduced both saved model reports. Each phase
uses three contexts and 720 held-out normal evaluation observations. The core
148-test suite passed. Live Wazuh checks below are the creator's recorded results;
they were not rerun during publishing review.

| Check | Result |
|---|---|
| Generator self-validation | Passes: baseline, both profiles, sampled observations, audit chain |
| Determinism | Two clean runs produce byte-identical trees |
| Existing test suite | 148 tests pass; both fixture replays pass |
| Ruleset load | `wazuh-analysisd -t` clean |
| Custom rules firing | 22 distinct rules fired with correct field substitution |
| ESP decoder | Parsed `esp.commanded_v`, `esp.operating_mode` from raw syslog |
| Permissions idempotency | Seed twice → 201 then 409, count unchanged |
| Audit replay idempotency | 48 events → 48× 201, then 48× 409, count 48 |
| Permission matrix | 18 assertions across all nine agents; 10 re-checked against generation 44 |
| Returned chain | Recomputed from event bytes in the console; intact, no sequence gaps |

Two non-findings worth knowing before a demo: **rule 100113 never fires alone**
(every DENY carries a `prohibition_id`, so child rule 100114 supersedes it —
correct Wazuh behaviour), and **rules 100180/100181 did not fire** because their
frequency thresholds were not met and correlation windows use ingest time, not
the timestamps inside the events.

### Bugs this exercise caught

1. **Decoder rejected at load.** `offset="after_prematch"` is only valid when the
   parent uses `<prematch>`; mine used `<program_name>`. Caught by
   `wazuh-analysisd -t` before the manager restarted. Run that before every push.
2. **The permission matrix over-reported denial.** The first resolver compared
   only agent and action, so `P-RELAY-SWITCHGEAR` — scoped to one target —
   rendered `set_voltage_setpoint` as absolutely prohibited for electrician
   agents that plainly held grants for it. A prohibition now denies a whole cell
   only when unscoped: all targets, no parameter match, no mode condition.
   Anything narrower attaches as a caveat. Separately, a cell with no grant reads
   `NOT_GRANTED` rather than borrowing a scoped prohibition's reason code —
   "denied by an explicit safety rule" and "denied because nothing granted it"
   are different facts.
3. **The simulation contradicted itself.** The returned audit reported enterprise
   drift to generation 44 while only 42 was ever published, so the fleet view
   showed a node simultaneously in sync and drifting. Releases 43 and 44 are now
   real signed bundles.

---

## 11. What this does not do

- No Pi-side loader, verifier, activator or `resolve()` implementation.
  `dcamr/policy_engine/` and `dcamr/audit/` are still empty.
- No fusion. No `ALLOW`/`HOLD`/`DENY` orchestration.
- No authority transfer or fencing protocol.
- No controller execution, no GPIO, no real ESP data.
- No deployable model artifact; nothing boots on a Pi.
- No Pi resource acceptance measured.
- The technician console is a separate repository and is not wired to this.

The returned audit stream is **authored** simulation data. It shows the shape a
real record should take; it is not evidence that the Pi produces one.

---

## 12. Open decisions

- **`source_id` semantics.** The current contextual contract intentionally means
  an immutable evidence-event/summary identity, not a device identity. Keep the
  device ID separately. The generator's per-observation IDs suit invented data;
  a real adapter must reuse the original event ID when reusing a reading, and
  partition collection sessions before deriving overlapping windows. PRE/POST
  simulation collections are generated independently, not paired physical
  observations of one actual execution.
- **USB filesystem.** ext4 proposed for Linux ownership; durability/activation protocol and provisioning still need Xavier and core integration.
- **Audit source of truth.** Pi internal storage with USB as transportable copy.
  Needs Merek and Theo.
- **Tracker / fusion seam.** Who owns `resolve()` versus the decision fusion that
  consumes it.
- **Placeholders needing sign-off:** voltage envelope, settle window, alert
  levels, demo credentials, ESP units and sample rate.

## 13. Core integration follow-up

The architecture, developer handoff and tracker now link this simulation as
concrete fixture/schema evidence. The following runtime work is still pending:

| Doc | What needs saying |
|---|---|
| `docs/prds/ALICE-DCAMR-Architecture.md` §5, §11 | Wazuh integration now has a concrete release schema, distribution path and audit contract in simulation. Pi-side implementation is still absent. |
| `docs/prds/ALICE-DCAMR-PRD-Handoff.md` §3 | "What exists now" lists the simulation, generator and console. |
| `docs/implementation-tracker.md` items 004, 006, 010, 012, 093–098, 102, 103 | Status stays **Planned** — the Pi runtime is unimplemented — but each now has a concrete schema and test data to point at. |
| `README.md` | Links this handoff and gives the Python 3.12 first-clone dataset generation command. |

Publishing this branch does not select the USB filesystem, approve the audit
storage assumption or electrical limits, install a key on a Pi, implement sync,
or stop the running Wazuh stack. Those are subsequent integration decisions.

### Additional boundaries confirmed during publishing review

- The console decodes supplied bundles but does not verify their signatures or
  apply the Pi's trust/expiry/anti-rollback rules. Its matrix is a display summary,
  not `resolve()`. Its TLS verification is disabled for the local demo client;
  do not reuse that transport as the Pi's authenticated sync adapter.
- Without the indexer, its release fallback is the cached generation-42 USB
  image, not the latest generation-44 document in the bulk seed. The source label
  must stay visible; offline console fallback does not prove current publication.
- Compatibility metadata currently names baseline/profile identities but does
  not contain a complete cryptographic binding to every baseline/profile/model
  payload. Finish signed compatibility bindings before accepting live updates.
- `fit.py` is a generated-data experiment: it recomputes source digests and uses
  normal labels while loading train/calibration inputs. A real data importer must
  instead verify stored expected digests/labels and evaluate independent lineage.
- Wazuh's reported live rules/API checks above are the creator's recorded
  evidence; publication validation does not claim that a Pi ran those workflows.
