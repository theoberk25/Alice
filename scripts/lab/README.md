# ML, assessment and enterprise development tools

The implemented lab tools now live here. The reusable Pi anomaly and assessment
runtime stays in `dcamr/`; the ledger stays in `dcamr/audit/`. No implementation
is duplicated. `lab/__init__.py` provides the existing import/command namespace.

From the repository root, existing commands still work:

```sh
python3 -m lab.replay_anomaly_fixtures
python3 -m lab.replay_feature_fixtures
python3 -m lab.replay_contextual_ledger
python3 -m lab.train_anomaly_model --output /tmp/alice-training-run
python3 -m lab.enterprise_sim --out /tmp/alice-enterprise-run
python3 -m lab.enterprise_sim.fit
python3 -m lab.enterprise_sim.console
```

From **any working directory**, use the single launcher (replace the checkout
path with yours; no installation or PYTHONPATH setup is needed):

```sh
python3 /path/to/Alice/scripts/lab/run.py replay_anomaly_fixtures
python3 /path/to/Alice/scripts/lab/run.py enterprise_sim --out /tmp/alice-enterprise-run
```

Use `run.py --help` to list commands. Remaining arguments are passed through.
Do not run individual implementation files directly or import them under a
second `scripts.lab` namespace; relative imports and monkeypatches use `lab.*`.
Paths to default fixtures/artifacts come from a shared checkout-root resolver,
not the process working directory or hard-coded parent counts. Relative explicit
output paths still mean relative to the caller's working directory.

- [Training](train_anomaly_model.py), [calibration comparison](compare_anomaly_calibration.py)
- [Contextual fitting](contextual_training.py), [ledger replay](replay_contextual_ledger.py)
- [Enterprise generator](enterprise_sim/__main__.py), [fit](enterprise_sim/fit.py), [console](enterprise_sim/console/server.py)
- [Assessment API](../../dcamr/decision_model.py) and [contract](../../docs/contracts/decision-assessment.md)

Use Python 3.12 and `requirements-anomaly-training.txt` plus `cryptography` for
enterprise generation/fitting; ledger replay also needs `requirements-audit.txt`.
See [training](../../docs/guides/anomaly-training.md) and
[enterprise setup](../../docs/handoffs/enterprise-sim-handoff.md). Generated
artifacts, datasets, keys and existing environments remain in their original
locations. This migration does not regenerate or activate them.
