# ML, assessment and enterprise development tools

The implemented lab tools live in `scripts/lab/` at the repository root. The reusable Pi anomaly and assessment
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
python3 -m lab.enterprise_sim.soc_seed --apply
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

- [Training](../../scripts/lab/train_anomaly_model.py), [calibration comparison](../../scripts/lab/compare_anomaly_calibration.py)
- [Contextual fitting](../../scripts/lab/contextual_training.py), [ledger replay](../../scripts/lab/replay_contextual_ledger.py)
- [Enterprise generator](../../scripts/lab/enterprise_sim/__main__.py), [fit](../../scripts/lab/enterprise_sim/fit.py), [console](../../scripts/lab/enterprise_sim/console/server.py)
- [Energy-infrastructure SOC seed](../../scripts/lab/enterprise_sim/soc_seed.py) writes
  an idempotent, internally labelled DN-Hacks scenario to the configured local
  Wazuh indexer. Omit `--apply` for a read-only count before loading it.
- [Assessment API](../../dcamr/decision_model.py) and [contract](../contracts/decision-assessment.md)

Use Python 3.12 and `requirements-anomaly-training.txt` plus `cryptography` for
enterprise generation/fitting; ledger replay also needs `requirements-audit.txt`.
See [training](../guides/anomaly-training.md) and
[integrated demo setup](../guides/demo-runbook.md). Generated
artifacts, datasets, keys and existing environments remain in their original
locations. This migration does not regenerate or activate them.

## First-light integration tools

`first_light/` now contains the demo release builder, labelled assessment fixture,
mock ESP, signed terminal client, read-only technician view and verified USB export.
Run these as `python -m lab.first_light.<module>` from the repository root; the
existing `scripts/lab/run.py` command allowlist does not include them. The runtime
is `python -m dcamr.main`; its verifier, exact permissions, light client and
data-only fan scorer stay in `dcamr/`.

Use temporary or ignored local-state directories for generated release/private-key,
ledger and export outputs. See the [first-light test report](../reports/2026-09-05-first-light-test-log.md)
and [backend scope](../reports/2026-09-05-pi-backend-status.md). First-light fan
scoring and signed native review are now integrated; general authority transfer,
real fan sensors/actuation and production model validation remain.

The first-light `publish_snapshot` command packages an already signed release as
a new immutable SQL input artifact. See [snapshot commands and limits](../integration/release-snapshot.md).

## Local native review rehearsal

`python -m lab.first_light.native_review_demo --directory /absolute/new-private-dir
--technician-id TECH-ID --launch-app` runs the existing first-light runtime, bridge
and mock ESP locally. It generates an explicitly signed approval-required test
release and two held requests. The native app still requires its configured real
ArcFace service and existing enrollment; the helper does not alter private settings
or install physical-Pi trust. See [operator steps](../guides/native-runtime-review.md).
All synthetic ledger/keys remain in the new private directory; `stop` on stdin
shuts down only this rehearsal and its launched app. No physical action is implied.

`npm run demo:hold -- --session /absolute/new-private-dir/session.json` invokes
`python -m lab.first_light.send_native_hold` to send another uniquely signed HOLD
through that rehearsal's existing runtime. It requires the private local session
and authenticated mock source; it neither approves nor commands the controller.

## Wazuh maintenance

`python -m lab.wazuh_sync` is implemented under `scripts/lab/`. It requires
exclusive ledger ownership with `alice-runtime.service` stopped; use the
[automatic runtime worker](../integration/wazuh-audit-sync.md) during normal operation.
The generic `run.py` allowlist does not include this maintenance command.

## Read-only deployed pipeline acceptance

`python -m lab.first_light.check_pipeline` compares an existing request in the
loopback runtime, read-only USB SQL and optional Wazuh GET. It never submits or
uploads events and may run beside the runtime owner. Follow the
[integrated demo acceptance guide](../guides/demo-runbook.md#acceptance-sequence).

Fan demo data: `python -m lab.fan_demo_data --output /absolute/new-directory`;
see [corpus contract and usage](../guides/anomaly-training.md#fan-demo-jsonl-corpus-2026-09-06).

Fan candidate fitting: `python -m lab.train_fan_demo --data /path/to/corpus --output /new/model-directory`.
Workstation experiment only; [measured limits](../guides/anomaly-training.md#first-fitted-fan-candidate).

`python -m lab.refine_fan_model --output /new/model-directory --demo-data
/path/to/demo.jsonl` exports the bounded hybrid data-only candidate used by the
first-light Pi scorer. `python -m lab.first_light.extend_fan_release` extends an
existing signed release while preserving all prior grants and terminal keys. Both
commands write generated models or private keys only to a new ignored/private
directory; neither activates a release.
