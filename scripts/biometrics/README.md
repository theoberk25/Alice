# Biometrics scripts

Working directory: workstation/. Existing source:

- [setup-model.py](../../workstation/scripts/setup-model.py): explicit model provisioning.
- [smoke-arcface.py](../../workstation/scripts/smoke-arcface.py): real inference smoke check.
- [smoke-native-identity.py](../../workstation/scripts/smoke-native-identity.py): isolated native identity check.
- [biometrics.mjs](../../workstation/scripts/biometrics.mjs): local service launcher.

Use the commands and prerequisites in the [quick start](../../workstation/docs/development/facial-verification-quickstart.md)
and [workstation README](../../workstation/README.md). These tools derive service,
model and environment paths from their source location; retain their current paths.
New independent biometric helpers belong here; reusable service code belongs in
workstation/services/biometrics/.
