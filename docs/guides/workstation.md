# ALICE Technician Console in this repository

The existing Technician Console subsystem is integrated under
[`workstation/`](../../workstation/README.md). Start with its README for browser
preview, the native macOS Tauri application, ArcFace enrollment/login/approval,
Ollama configuration, tests and packaging. The standalone checkout is no longer
required to build it.

From the main repository root:

```sh
cd workstation
npm ci
npm run dev
```

The console is a self-contained npm workspace with its own lockfile, Rust crate
and Python service environment. Root Python anomaly dependencies remain separate
from `workstation/services/biometrics/.venv`. There is no root npm workspace.

The preexisting `workstation/backend/`, `workstation/dashboard/` and
`workstation/face_verification/` skeleton files are retained for team review;
the implemented console entry points are `workstation/apps/desktop/` and
`workstation/services/biometrics/`.

## Scope and authority

The [team integration agreement](../integration/technician-console.md) and
[current architecture](../prds/ALICE-DCAMR-Architecture.md) govern whole-system
authority. The [migration assessment](../../workstation/docs/integration/main-repository-migration.md)
records the differences between those requirements and the preserved console,
including anomaly scores, context challenges and ONLINE/OFFLINE control transfer.
The console's [executable contracts and upstream boundary](../../workstation/docs/integration/upstream-alice.md)
remain local to `workstation/packages/contracts/`; no shared core contracts were
replaced or promoted during migration.

Mock events, automatic HOLD clarification, immutable reassessment lineage,
request-bound technician actions, native security, facial identity and local
explanation are preserved. Remote transport still fails closed. The core API,
agent client and enforcement files are placeholders; source colocation does not
connect them or prove protected execution.

## Verification and remaining work

See the [migration verification record](../../workstation/docs/development/verification.md#main-repository-migration-verification)
for commands actually executed and their outcomes, and the
[console handoff](../../workstation/HANDOFF.md) for implemented/planned distinctions.
Previous operator results refer to the original standalone installation unless
explicitly recorded as migration checks.

Remaining cross-system work includes authenticated real transport, schema/version
mapping, control-owner and authority-transfer semantics, remotely verifiable
biometric attestations, execution confirmation, durable delivery/reconnect and
mission-wide audit. Camera/operator acceptance, liveness/deepfake defenses and
distribution/service provisioning are also separate work. The packaged console
does not include Python, ArcFace weights or Ollama.

The native bundle identifier is preserved. Its default macOS Application Support
path may already contain an earlier installation's data; use an explicit fresh
`ALICE_DATABASE_PATH` and private biometric data directory for isolated validation.
No prior runtime database, enrollment, credential or model cache is part of this
source migration.
