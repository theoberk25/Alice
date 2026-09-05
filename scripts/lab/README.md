# Lab commands

Working directory: repository root. Preserve the importable lab package and
its existing python -m lab.* commands.

- [Anomaly fixture replay](../../lab/replay_anomaly_fixtures.py)
- [Feature fixture replay](../../lab/replay_feature_fixtures.py)
- [Contextual ledger replay](../../lab/replay_contextual_ledger.py)
- [Model training](../../lab/train_anomaly_model.py)
- [Calibration comparison](../../lab/compare_anomaly_calibration.py)
- [Enterprise generator](../../lab/enterprise_sim/__main__.py)
- [Enterprise fitting](../../lab/enterprise_sim/fit.py)
- [Enterprise console](../../lab/enterprise_sim/console/__main__.py)

Commands, dependencies and generated outputs are documented in the
[training guide](../../docs/guides/anomaly-training.md),
[enterprise handoff](../../docs/handoffs/enterprise-sim-handoff.md), and
[repository README](../../README.md). Some tools locate fixtures from __file__;
others are imported by tests or package modules. Do not flatten or relocate them
without a separately reviewed code/import migration. New standalone helpers go
here; reusable lab implementation stays in lab/.
