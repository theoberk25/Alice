# Runtime bridge recovery

2026-09-06 EDT. Branch `codex/dashboard-visual-refinements`, baseline `5bb092a`.
Available refs at session start: origin/main `e1e7506`, upstream/main `237c307`.
Follow [working rules](../../AGENTS.md). User asked why the Dock app showed
Runtime bridge unavailable and requested a fix unless it was intentionally gone.

## Diagnosis

The native error originates from a failed HTTP transport to the configured
loopback bridge, before any response status is received. No process listened on
configured bridge port56256 or its runtime port56255. Root `.env` still matched
the private descriptor in `/private/tmp/alice-native-personal-20260906-01/` for
feed URL/token, console identity and review-key path; no credential was printed.

The [earlier delivery](../handoffs/2026-09-06-native-live-backend-ready.md) identifies
that endpoint as a personal **local rehearsal / fixture assessment / mock controller**.
It was not a physical-Pi connection. The original launcher exits its stdin loop on
EOF or `stop`, then closes runtime, bridge and mock controller. The processes had
ended; this session could not establish who/what ended the original terminal.
There was no evidence of a deliberate configuration removal. The warning was
correct; it was not caused by missing dashboard rendering or hidden fixture data.

## Restoration and durable helper

`lab.first_light.native_review_demo --resume /absolute/existing/session.json`
reopens the exact existing private rehearsal, validates stored source, loopback
URLs/ports, required artifacts, signed release and matching console trust/seed,
and refuses absent state rather than initializing replacements. It reuses the
saved ports/token, runtime ledger and trust; it creates no new HOLDs, requests or
keys. The runtime's existing exclusive owner lock remains enforced. It waits for
SIGINT/SIGTERM independently of stdin. New-rehearsal interactive behavior remains.

The mock controller starts fresh in memory (`off`, zero commands). Historical
commands are not replayed, and retained observations remain historical. No
physical hardware, remote trust, SSH tunnel or enterprise setting was changed.

Before restoration, SQLite backup and the private descriptor were preserved in
`/private/tmp/alice-runtime-recovery-20260906/`. Ledger quick_check was OK and the
22 original event rows were digested privately for after-recovery comparison.

Actually launched:

```sh
.venv/bin/python -m lab.first_light.native_review_demo \
  --resume /private/tmp/alice-native-personal-20260906-01/session.json \
  </dev/null > /tmp/alice-runtime-resume-20260906.log 2>&1
```

The process remains running for the user's existing Dock app. No `.env`, native
identity store or session descriptor was changed. No native app rebuild/restart
was needed; the existing renderer automatically retries the bridge.

## Verification

- `.venv/bin/python -m pytest tests/test_native_review_demo.py -q`: **15 passed**
  (final7.05s). New tests cover exact event/key/descriptor preservation, closed stdin,
  safe missing/invalid-state refusal and occupied ports. Initial sandbox run could
  not bind local ports; the same tests passed with authorized local-server access.
- Python compilation and `git diff --check` passed.
- Authenticated read-only `/events?after=0` returned HTTP200, source `local-runtime`,
  controller `mock`,22 events. All22 event rows matched the pre-recovery digest,
  quick_check stayed OK, and descriptor bytes matched the private backup.
- At04:37 native accessibility showed **FEED LIVE**,1 observed identity,4 retained
  requests, ledger sequence22, local-runtime source and MOCK CONTROLLER provenance.
  The error banner cleared automatically and the existing user stayed signed in.

No test request, review approval or controller command was submitted during
recovery. Physical-Pi availability was not tested because the configured feed is
local. A Mac restart/process termination still requires resuming this development
backend; no login item or system service was installed.

[Resume guide](../guides/native-runtime-review.md#resume-a-stopped-local-rehearsal)
· [Previous checkpoint](../handoffs/2026-09-06-before-runtime-recovery.md)
