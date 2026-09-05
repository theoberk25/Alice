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

The anomaly contract, cyber feature builder, Mac training lab and general
context-conditioned Isolation Forest interface are implemented components. The
new interface supports separate before/after assessments; real ESP operating data
and its sensor/action adapter remain to be supplied. Permissions evaluation, decision fusion, package
verification, enterprise synchronization, authority transfer, durable mission audit,
motor execution and Pi deployment remain integration work. The separate console
handoff reports real face enrollment/login with mock edge transport; it is not yet
connected to this core. See the tracker for evidence and scope.

Wazuh is the planned integration for permissions-related context and some auditing.
Its ALICE action-permission mapping and audit adapters are not implemented. The
likely physical demo now uses an ESP with lights and a voltage sensor; actual
measurements, units and operating ranges still need agreement.

“Permissions” is the current product term. Existing `policy` paths and wire keys
remain unchanged until a coordinated contract migration.

For contract and feature work, start from the repository root with Python 3.11+
(tested with Python 3.12.6):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-anomaly.txt
.venv/bin/python -m lab.replay_anomaly_fixtures
.venv/bin/python -m lab.replay_feature_fixtures
.venv/bin/python -m unittest discover -v
```

For the Mac training lab and its real-estimator tests, also install
`.venv/bin/python -m pip install -r requirements-anomaly-training.txt`.
Those tests skip when training dependencies are absent. See the training guide
for experiment commands and the [published experiment evidence](docs/reports/anomaly-lab/README.md).

See the [demo runbook](docs/demo-runbook.md) for the distinction between runnable
component checks and planned end-to-end acceptance, and the
[threat model](docs/threat-model.md) for trust boundaries that integration must enforce.
