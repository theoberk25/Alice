# Local agent/main integration — 2026-09-06

Follow [AGENTS.md](../../AGENTS.md). The user authorized fetching the main GitHub
repository, preserving the local setup, merging and opening a pull request.

## Integration

- Main repository: `theoberk25/Alice`; publication fork: `Adaoud03/Alice`.
- Original baseline: `11ccd6aaa340742796cb2fb350f4db847d1a3f6f`.
- Preserved all nine modified/untracked setup files in commit `5282f13`.
- Merged `upstream/main` at `2aa5c343a51eba63de86726490ed61a8cba0989f`
  through merge commit `3dd14ee33443777e600bad0dea481a719dd1351b`.
- Upstream adds feed-staleness correction and audited plant/agent telemetry.
  Merge completed automatically with no conflicts. All upstream implementation
  files remain unchanged by this branch; dependency manifests and lockfiles match main.
- Private profiles, tokens, model weights, environments, saved console settings,
  enrollment data and Pi services were preserved. No installation or deployment
  was needed. The current setup snapshot is preserved in the
  [pre-integration handoff](../handoffs/2026-09-06-before-agent-main-integration.md).

## Fresh verification

Commands below were actually run against the merged source.

- `npm ls --depth=0`: passes with all workspace dependencies resolved.
- `npm run check`: passes typecheck, lint, frontend tests, script tests and build.
  Non-fatal motion-test, annotation and bundle-size warnings remain.
- `.venv/bin/python -m pip check`: passes, no broken requirements.
- `.venv/bin/python -m pytest -q -p no:cacheprovider tests`:
  **562 passed, 266 subtests passed, 1 failed**, 12 MCP deprecation warnings.
- The failure is
  `tests/test_script_locations.py::ScriptLocationTests::test_enterprise_generator_preserves_published_payloads`.
  Reproduced the identical MANIFEST.json mismatch from an unmodified
  `git archive upstream/main` export of the relevant source/test/fixture paths in
  a temporary directory. No archived documentation was opened. The generator now
  names DN-Hacks Energy Infrastructure Testbed with 12 endpoints/9 groups; the
  published manifest still names Sentinel Air Force Base with 13 endpoints/6 groups.
  This pre-existing fixture drift is unrelated to the launcher and remains visible;
  published historical artifacts were not overwritten to suppress the failure.
- `services/biometrics/.venv/bin/python -m pytest -q -p no:cacheprovider services/biometrics/tests`:
  **177 passed** with three warnings.
- `services/biometrics/.venv/bin/python -m pip check`: reports MediaPipe's absent
  `opencv-contrib-python` distribution. The existing `requirements-live.txt`
  explicitly installs with `--no-deps` and uses the single headless OpenCV provider.
  Preserved that intentional arrangement; this is not a clean pip metadata check.
- `services/biometrics/.venv/bin/python scripts/biometrics/smoke_arcface.py`:
  real public-image enrollment/match pass; absent/multiple faces rejected.
  OpenCV 4.14.0, MediaPipe 0.10.35 and MediaPipe vision task imports also pass.
- Launcher `--help` passes. `--check` passes for cooling, power and observer using
  their existing private tokens. All read the existing RUNNING simulation,
  revision 1, target 70%, battery 80%, one existing request.
- Observer `--text 'Read get_metrics once and report the plant status, fan target and battery.'`:
  Goose/Qwen calls `get_metrics`, reports target/battery and labels simulation;
  exits 0. Its prose is not runtime acceptance or a safety assessment.
- `git diff --check`, empty unmerged-index check, current snapshot size/link
  validation and private-token absence checks pass.

## Limits and follow-up

The code merge is conflict-free; the complete Python suite is not wholly green
because of the independently reproduced upstream fixture mismatch. Biometric pip
metadata has the intentional provider exception described above. No new dependency
regression was observed. Full physical camera/technician/actuation acceptance,
Pi deployment, native bundle rebuild and browser end-to-end tests were not run.
The local merge does not update the running Pi or installed desktop bundle.
