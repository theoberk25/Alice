# Demo runbook and acceptance plan

Updated: 2026-09-05. Read the [architecture](prds/ALICE-DCAMR-Architecture.md)
and [console integration guide](technician-console-integration.md) first.
The commands below run existing components; the lifecycle demo is a **planned
integration test**, not a working startup procedure. There is no implemented
Pi server, enterprise connector or motor executor to launch from this checkout.

## Runnable component checks

From the repository root, use Python 3.11+ (previously tested with 3.12.6):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-anomaly.txt
.venv/bin/python -m lab.replay_anomaly_fixtures
.venv/bin/python -m lab.replay_feature_fixtures
.venv/bin/python -m unittest discover -v
```

Install the training dependencies on the Mac to include real-estimator tests:

```sh
.venv/bin/python -m pip install -r requirements-anomaly-training.txt
.venv/bin/python -m unittest discover -v
```

The published implementation passed 103 tests and both replays. Training-dependent
cases skip without those dependencies. Record the actual pass/skip counts in each
new run; that earlier result is not a Pi benchmark or an end-to-end acceptance.
See [training commands and evidence](anomaly-training.md) before repeating a model
experiment. No model artifact is currently saved or loaded on Pi boot.

The separate console handoff reports native Mac checks and live face enrollment/
login. Its repository and exact setup must come from the console team. Cloning
this core does not install its Tauri app, biometric assets, local identities or
Ollama model. Mock edge events must remain visibly distinguished from real feeds.

## Prerequisites for the future lifecycle demo

Agree these before claiming a live ONLINE → OFFLINE → ONLINE demonstration:

- A protected controller that enforces one authenticated execution authority,
  stable command IDs and the agreed handover protocol. Define in-flight command
  recovery and behavior when authority cannot be established.
- Enterprise or clearly labelled simulated interfaces for authorized cache
  releases, activity feeds, audit acknowledgements and evidence reconciliation.
  Record the required-service health criteria and feed coverage.
- A compatible accepted permissions/baseline/model set, trusted agent-to-user
  mappings, local identity provisioning and an offline-validity policy.
- Native console/Pi transport, full exchanged schemas, remote approval proof,
  durable delivery and distinct submission/execution reporting.
- Durable Pi audit/outbox with bounded storage and specified USB/disk failure
  behavior. Keep local LAN addressing and credentials usable without the router.
- Agreed motor request semantics, limits and actual feedback capabilities. Begin
  with a simulated executor until the controller contract has been reviewed;
  identify simulated telemetry explicitly.
- Pi resource measurements with actual concurrent services. Keep training,
  language-model inference and face processing on the Technician Mac.

## Demonstration sequence

### 1. ONLINE: enterprise control and cache synchronization

Show enterprise authorizing and executing a request directly at the controller.
ALICE receives the authenticated activity/result feed and displays its source,
coverage and cursor; it does not present a local ALLOW as authority for that action.
Show current permissions, normal-behavior and relevant evidence cache identities,
last accepted update and unavailable/stale sources. A missing feed appears as a
gap, not as proof that no activity occurred.

Attempt an ALICE offline approval while enterprise owns execution. It must not
execute through the local path. A reachable router or successful facial login
cannot bypass that ownership restriction.

### 2. Lose enterprise connectivity and transfer authority

Remove the router uplink while retaining the local LAN. Show required-service
failure and the controller's confirmed transfer to ALICE. Preserve readiness and
ownership uncertainty visibly while transfer is incomplete; no ambiguous command
path is enabled. Try a delayed enterprise command from the retired authority
interval and confirm rejection.

Confirm OFFLINE operation uses accepted cache generations and records their
age/validity. Unusable required data, missing execution authority or failed required
audit persistence must produce the agreed blocked behavior, not a fabricated score.

### 3. Exercise local decisions and review

| Scenario | Expected evidence |
| --- | --- |
| Normal permitted request | Local assessment and authorized execution, with separate result/available observed state and durable audit. |
| Authenticated new agent | Trusted identity and responsible user mapping; role/mission baseline fallback retains novelty; permissions decide whether context/review is available. |
| Slight anomaly | Bounded exact-request context challenge, authenticated response and verified evidence; original assessment preserved. |
| Hard prohibition | DENY without a model, prose or technician override; dangerous request recorded as blocked, not executed. |
| High anomaly | HOLD under the agreed fusion rules; a low independent factor or face match cannot silently resolve it. |
| Technician review | Latest eligible assessment, fresh request-bound facial grant and Pi verification; submission acceptance remains distinct from execution. |
| Superseded review | New immutable assessment invalidates the old grant/dialog; late receipts stay historical. |
| Failed/uncertain execution | Failure/unknown result is recorded honestly; no automatic new command ID and no invented position reading. |

The console's current automatic push-back starts only for HOLD with
`context_challenge.required=true`; agree its adapter to core `REQUEST_CONTEXT`
before running this sequence. Agent prose alone cannot trigger a locally invented
reassessment. Show the authoritative successor event and its lineage.

Use consenting enrolled technicians for live camera acceptance. A live enrollment/
login success is separate from the still-pending live approval step-up and wrong
identity, unavailable-camera, revoked-user and replay/expiry negative cases.

### 4. Restore connectivity and reconcile

Reauthenticate enterprise services. Show the Pi directly delivering the DDIL
outbox and refreshing trusted context. Prioritize high-risk or unresolved findings
while preserving reliable delivery of every ordinary allowed/blocked event too.
Distinguish requested, approved, attempted, executed and observed effects in alerts.

Fetch delayed evidence and append linked findings/discrepancies. Keep original
decision-time scores, cache versions and evidence availability unchanged. Show
accepted new cache versions or an explicit rejection retaining an allowed prior
generation. Never label a self-computed digest as signature verification.

Transfer execution back to enterprise under the agreed controller protocol;
reject late ALICE commands/approvals from the previous authority. Retained audit
backlog may drain after transfer. Show ONLINE ownership, upload acknowledgements,
reconciliation progress and cache freshness separately.

### 5. Failure and recovery acceptance

Repeat targeted failures: flapping uplink, optional evidence service loss, expired/
revoked permissions, tampered or rolled-back package, full/unavailable storage,
USB removal, lost acknowledgement, duplicate event, crash/restart and stale face
proof. Required results are one control owner, no duplicate execution, honest
unknown states, preserved history and recoverable unacknowledged delivery.

Record request/event/command IDs, captured source versions, mode/ownership evidence,
expected versus observed outcomes, simulation boundaries and resource measurements.
Exclude credentials, biometric material and private model reasoning. Track failures
and unimplemented checks in the [implementation tracker](implementation-tracker.md);
none of this planned sequence is marked passed by a fixture replay.
