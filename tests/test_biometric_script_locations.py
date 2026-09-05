"""Provisioning entry-point checks without InsightFace downloads or private data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BiometricProvisioningLocationTests(unittest.TestCase):
    def check_provisioning(self, override):
        with tempfile.TemporaryDirectory(prefix="alice model setup ") as directory:
            temp = Path(directory).resolve()
            checkout = temp / "checkout with spaces"
            scripts = checkout / "scripts/biometrics"
            scripts.mkdir(parents=True)
            (checkout / "package.json").write_text(
                json.dumps({"name": "alice-technician-console"}))
            for name in ("setup_model.py", "console_paths.py"):
                shutil.copy2(ROOT / "scripts/biometrics" / name, scripts / name)
            stub = temp / "stubs/insightface"
            stub.mkdir(parents=True)
            (stub / "__init__.py").write_text("")
            (stub / "app.py").write_text('''
import json
import os
from pathlib import Path
class FaceAnalysis:
    def __init__(self, **kwargs):
        self.options = kwargs
    def prepare(self, **kwargs):
        Path(os.environ["ALICE_TEST_CAPTURE"]).write_text(
            json.dumps({"options": self.options, "prepare": kwargs}))
''')
            capture = temp / "result.json"
            env = os.environ.copy()
            env.pop("ALICE_INSIGHTFACE_ROOT", None)
            env["PYTHONPATH"] = str(stub.parent)
            env["ALICE_TEST_CAPTURE"] = str(capture)
            expected = checkout / "services/biometrics/models"
            if override:
                expected = temp / "custom model directory"
                env["ALICE_INSIGHTFACE_ROOT"] = str(expected)
            result = subprocess.run(
                [sys.executable, str(scripts / "setup_model.py")],
                cwd=temp, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            recorded = json.loads(capture.read_text())
            self.assertEqual(recorded["options"], {
                "name": "buffalo_l", "root": str(expected),
                "allowed_modules": ["detection", "recognition"],
                "providers": ["CPUExecutionProvider"],
            })
            self.assertEqual(recorded["prepare"], {"ctx_id": -1, "det_size": [640, 640]})
            self.assertIn("Liveness: NOT CONFIGURED", result.stdout)
            self.assertFalse(expected.exists(), "The stub must not provision model files")

    def test_default_models_follow_copied_checkout_from_unrelated_cwd(self):
        self.check_provisioning(override=False)

    def test_explicit_model_root_is_preserved_after_relocation(self):
        self.check_provisioning(override=True)
