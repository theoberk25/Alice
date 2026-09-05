# ALICE / DCAMR

Local decision and enforcement platform for agent action requests. Development
targets a Raspberry Pi 4 with 2 GB RAM; model training and the explanatory LLM
belong on the workstation.

- [Implementation tracker — all 118 to-dos](docs/implementation-tracker.md)
- [Latest motor/USB data direction](docs/data-direction-2026-09-05.md)
- [Anomaly output PRD](docs/prds/anomaly-model-prd.md)
- [Output contract and fixtures](docs/anomaly-contract.md)
- [Web-01 feature builder](docs/anomaly-features.md)
- [Mac synthetic training lab](docs/anomaly-training.md)

The anomaly contract, feature builder and Mac training lab are implemented
components. Policy, fusion, package verification, enforcement, motor support and
Pi deployment remain integration work. See the tracker for evidence and scope.

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
