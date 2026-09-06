"""Public-image ArcFace regression plus rejection of retired native image IPC.

This cannot create a production enrollment, login session or approval grant.
"""
from console_paths import REPOSITORY_ROOT, CONSOLE_ROOT
import os
import subprocess
import sys

env = {**os.environ, "NO_ALBUMENTATIONS_UPDATE": "1"}
subprocess.run([sys.executable, str(CONSOLE_ROOT / "scripts/biometrics/smoke_arcface.py")],
               cwd=CONSOLE_ROOT, env=env, check=True)
subprocess.run(["node", str(REPOSITORY_ROOT / "scripts/console/rust.mjs"), "test",
                "commands_tests::retired_frame_ipc_never_mints_enrollment_login_or_approval",
                "--", "--exact"], cwd=CONSOLE_ROOT, env=env, check=True)
print("Public-image identity regression exercised; retired renderer IPC rejected. No live authorization tested.")
