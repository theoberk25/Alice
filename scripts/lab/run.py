"""Run a relocated lab command from any working directory.

Example: python /path/to/Alice/scripts/lab/run.py replay_anomaly_fixtures
"""
from pathlib import Path
import runpy
import sys

COMMANDS = (
    'replay_anomaly_fixtures', 'replay_feature_fixtures', 'replay_contextual_ledger',
    'train_anomaly_model', 'compare_anomaly_calibration', 'enterprise_sim',
    'enterprise_sim.fit', 'enterprise_sim.console',
)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print('Usage: run.py COMMAND [arguments]\nCommands: ' + ', '.join(COMMANDS))
        raise SystemExit(0 if len(sys.argv) == 2 and sys.argv[1] in ('-h', '--help') else 2)
    root = next((p for p in Path(__file__).resolve().parents
                 if (p / 'lab' / '__init__.py').is_file() and
                 (p / 'common' / 'repository_paths.py').is_file()), None)
    if root is None:
        raise SystemExit('ALICE checkout not found')
    sys.path.insert(0, str(root))
    command = sys.argv.pop(1)
    runpy.run_module('lab.' + command, run_name='__main__', alter_sys=True)


if __name__ == '__main__':
    main()
