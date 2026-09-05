"""Relocation checks use a second checkout and an unrelated working directory."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScriptLocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='alice relocated ')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name) / 'checkout with spaces'
        cls.root.mkdir()
        for name in ('common', 'dcamr', 'lab', 'scripts/lab', 'tests/fixtures'):
            shutil.copytree(ROOT / name, cls.root / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for file in ROOT.glob('requirements-*.txt'):
            shutil.copy2(file, cls.root / file.name)

    def run_tool(self, command, *args):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/lab/run.py'), command, *args],
                                cwd=self.temp.name, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_replay_resolves_package_schemas_and_fixtures_after_relocation(self):
        self.assertIn('Verified 8 result fixtures', self.run_tool('replay_anomaly_fixtures'))
        self.assertIn('Verified 5 feature vectors', self.run_tool('replay_feature_fixtures'))

    def test_training_provenance_uses_moved_source_paths(self):
        import json
        output = Path(self.temp.name) / 'training'
        self.run_tool('train_anomaly_model', '--prepare-only', '--output', str(output))
        manifest = json.loads((output / 'dataset-manifest.json').read_text())
        paths = manifest['source_sha256']
        self.assertIn('scripts/lab/train_anomaly_model.py', paths)
        self.assertNotIn('lab/train_anomaly_model.py', paths)

    def test_enterprise_defaults_and_console_asset_are_checkout_local(self):
        code = '''
from pathlib import Path
from lab.enterprise_sim import fit
from lab.enterprise_sim.console import server
from common.repository_paths import repository_root
root = repository_root()
assert fit.OUT == root / 'artifacts/enterprise-sim'
assert server.ARTIFACTS == fit.OUT
assert (server.HERE / 'index.html').is_file()
assert str(root) in str(__import__('lab.contextual_training', fromlist=['x']).__file__)
'''
        result = subprocess.run([sys.executable, '-c', code], cwd=self.root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_enterprise_generator_preserves_published_payloads(self):
        from hashlib import sha256
        output = Path(self.temp.name) / 'enterprise'
        self.run_tool('enterprise_sim', '--out', str(output))
        original = ROOT / 'artifacts/enterprise-sim'
        checked = 0
        for source in original.rglob('*'):
            relative = source.relative_to(original)
            if not source.is_file() or relative.parts[0] in ('datasets', 'reports') or source.suffix == '.sk':
                continue
            self.assertEqual(sha256(source.read_bytes()).digest(),
                             sha256((output / relative).read_bytes()).digest(), str(relative))
            checked += 1
        self.assertEqual(checked, 28)
