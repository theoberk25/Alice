# Biometrics scripts

Use Python 3.11 and the environment at services/biometrics/.venv. Install the
pinned services/biometrics/requirements-lock.txt dependencies. These scripts can
be invoked by absolute path from any working directory. Paths are resolved from
the checkout package manifest, not the current directory or a fixed parent count.

| Tool | Purpose |
| --- | --- |
| [biometrics.mjs](../../scripts/biometrics/biometrics.mjs) | `npm run biometrics` from root; loads .env and starts the local service |
| [setup_model.py](../../scripts/biometrics/setup_model.py) | Explicit InsightFace model provisioning; never runs implicitly during login |
| [smoke_arcface.py](../../scripts/biometrics/smoke_arcface.py) | Public-image inference check using a temporary encrypted store |
| [smoke_native_identity.py](../../scripts/biometrics/smoke_native_identity.py) | Isolated public-image Rust/service identity integration |

The launcher keeps models under services/biometrics/models and private enrollment
data under services/biometrics/data by default. ALICE_INSIGHTFACE_ROOT and
ALICE_BIOMETRIC_DATA_DIR overrides are retained. Reusable service code stays in
services/biometrics/app. These checks do not establish live camera acceptance.
See the [quick start](../guides/console/facial-verification-quickstart.md)
and [console guide](../guides/technician-console.md).
