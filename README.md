# ALICE / DCAMR

ALICE synchronizes trusted enterprise context while connected, governs local
agent actions during DDIL outages, and reports disconnected activity when
enterprise services return.

| Mode | Who controls execution | What ALICE does |
| --- | --- | --- |
| **ONLINE** | Enterprise systems directly | Refresh bounded permissions, normal-behavior and relevant evidence caches; consume authenticated activity feeds; send audit and findings upstream. |
| **OFFLINE / DDIL** | ALICE, after a controlled transfer | Evaluate local requests using trusted caches, anomaly models and technician review; preserve an audit trail for every action. |

Reconnection is a workflow between these two modes. The Pi communicates directly
with enterprise interfaces for synchronization and reporting. Transferring
execution authority safely is required integration work, not implemented failover.

Development targets a **Raspberry Pi 4 Model B with 2 GB RAM and OS Lite**.
Model training, the explanatory LLM and facial verification belong on the Mac.

- [Architecture and authority boundaries](docs/prds/ALICE-DCAMR-Architecture.md)
- [Product PRD](docs/prds/ALICE-DCAMR-PRD.md)
- [Teammate handoff and integration responsibilities](docs/prds/ALICE-DCAMR-PRD-Handoff.md)
- [Technician console and face-verification integration](docs/technician-console-integration.md)

- [Implementation tracker — all 118 to-dos](docs/implementation-tracker.md)
- [Accepted data direction and remaining decisions](docs/data-direction-2026-09-05.md)
- [Anomaly output PRD](docs/prds/anomaly-model-prd.md)
- [Output contract and fixtures](docs/anomaly-contract.md)
- [Web-01 feature builder](docs/anomaly-features.md)
- [Mac synthetic training lab](docs/anomaly-training.md)
- [General before/after behavior model](docs/contextual-behavior-model.md)
- [Pi assessment for the technician application](docs/decision-assessment.md)
- [Local Decision Evidence Ledger](docs/decision-evidence-ledger.md)
- [Enterprise SIEM simulation and Wazuh setup](docs/enterprise-sim-handoff.md)
- [WIP integration handoff for workflow development](docs/core-workflow-wip-handoff.md)

**WIP integration checkpoint:** analysis, ledger, workstation and enterprise
simulation components are available for team integration. This is not a complete
live request-to-execution system. See the workflow handoff for existing entry points,
contract differences and remaining work before adding parallel implementations.

The anomaly contract, cyber feature builder, Mac training lab and general
context-conditioned Isolation Forest interface and durable local ledger are
implemented components. The
new interface supports separate before/after assessments; real ESP operating data
and its sensor/action adapter remain to be supplied. Permissions evaluation, decision fusion, package
verification, enterprise synchronization, authority transfer, live mission-audit coverage,
motor execution and Pi deployment remain integration work. The separate console
handoff reports real face enrollment/login with mock edge transport; it is not yet
connected to this core. See the tracker for evidence and scope.

The enterprise simulation supplies Wazuh configuration, demonstration permissions
releases and synthetic behavioral data. Pi permission resolution, trusted cache
synchronization and durable audit adapters remain unimplemented. The
likely physical demo now uses an ESP with lights and a voltage sensor; actual
measurements, units and operating ranges still need agreement.

“Permissions” is the current product term. Existing `policy` paths and wire keys
remain unchanged until a coordinated contract migration.

For contract and feature work, start from the repository root with Python 3.11+
(latest core suite tested with Python 3.13):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-audit.txt
.venv/bin/python -m lab.replay_anomaly_fixtures
.venv/bin/python -m lab.replay_feature_fixtures
.venv/bin/python -m unittest discover -v
```

The audit requirements include the contract/feature requirements and Ed25519
dependency. For contract/feature work alone, `requirements-anomaly.txt` remains
sufficient; running the full suite also requires the audit dependencies.

For the Mac training lab and its real-estimator tests, also install
`.venv/bin/python -m pip install -r requirements-anomaly-training.txt`.
Those tests skip when training dependencies are absent. See the training guide
for experiment commands and the [published experiment evidence](docs/reports/anomaly-lab/README.md).

With both audit and training dependencies installed, run
`.venv/bin/python -m lab.replay_contextual_ledger` to verify synthetic PRE/POST and
failure assessments through ledger sealing, restart and duplicate retry.

See the [demo runbook](docs/demo-runbook.md) for the distinction between runnable
component checks and planned end-to-end acceptance, and the
[threat model](docs/threat-model.md) for trust boundaries that integration must enforce.

## Technician Console

The macOS ALICE Technician Console lives under [`workstation/`](workstation/README.md).
Run `cd workstation && npm ci && npm run dev` for the independent mock dashboard.
See its README for native Tauri operation, biometric setup, Ollama, tests and
`ALICE.app` packaging, and the [repository integration guide](docs/workstation.md)
for scope and shared-contract boundaries. Remote core transport remains fail-closed.

## Enterprise Simulation

For the enterprise simulation, use **Python 3.12 on the development Mac** and
regenerate the ignored datasets once after cloning, before running its fit command:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-anomaly-training.txt cryptography
.venv/bin/python -m lab.enterprise_sim
```

See the [enterprise handoff](docs/enterprise-sim-handoff.md) for fitting, console
startup and trust boundaries. Generated signing material is demonstration-only.
