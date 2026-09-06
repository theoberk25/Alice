# Native live runtime review

Follow [working rules](../../AGENTS.md), the [review contract](../contracts/technician-runtime-review.md),
and [facial setup](console/facial-verification-quickstart.md). The Pi remains the
authoritative policy, audit and execution owner. The browser remains read-only.

## Existing local configuration

Use `/Users/alexdaoud/Documents/Alice` on `codex/native-live-backend`.
Preserve `.env`, `ALICE_DATABASE_PATH`, model paths, encrypted enrollment stores
and existing administrator accounts. Root is the only development checkout;
[recovery storage](../handoffs/2026-09-06-native-live-backend-workspace.md) is inactive.

The native app uses `ALICE_TRANSPORT_MODE=remote`, `ALICE_BIOMETRIC_MODE=arcface`,
and the existing authenticated loopback `ALICE_FEED_URL` / `ALICE_FEED_TOKEN`.
Both app and biometric service must use the same private biometric token and URL.
Review needs additional explicit console trust; a feed token or web viewer login
alone cannot authorize an action. Missing review setup leaves live viewing usable.

## Explicit local key creation

The helper creates a **new** private directory outside Git and refuses existing
directories, symlinks, invalid IDs or overwrite. Its parent must already exist.
Use actual enabled native technician IDs, which may differ from display usernames.

```sh
.venv/bin/python scripts/console/provision_review_key.py \
  --output-dir "$HOME/Library/Application Support/ALICE-review" \
  --console-id YOUR-CONSOLE-ID --technician-id YOUR-TECHNICIAN-ID
```

Output contains a raw 32-byte `console.seed` and `console-trust.candidate.json`,
both mode 0600 inside a mode 0700 directory. The tool prints only paths, console ID
and public-key fingerprint. It never edits `.env`, sends a network request,
installs runtime trust or starts execution. Never commit or share the seed.

Set private native settings `ALICE_CONSOLE_ID` and `ALICE_REVIEW_KEY_FILE` to the
chosen ID and absolute seed path. A separately authorized operator must review
the public candidate's console/technician scope and configure the Pi's explicit
`--console-trust-file` setting. Do not copy a candidate to a Pi or restart its
runtime merely to test the UI. Trust installation and physical operations require
separate authorization; neither was performed during this local integration.

## Operator acceptance sequence

For a local rehearsal with the built app and your existing enrollment:

```sh
.venv/bin/python -m lab.first_light.native_review_demo \
  --directory /absolute/new-private-rehearsal --technician-id YOUR-TECHNICIAN-ID \
  --launch-app
```

If your previous enrollment used mock request transport, the app's default native
store is `console-mock.sqlite3`; remote mode normally selects `console.sqlite3`.
Add `--database "/absolute/path/to/existing/console-mock.sqlite3"` to explicitly
reuse that enrolled database. Preserve it first; never copy or reset enrollment
to work around the mode distinction. An existing `.env` database override remains
effective when no `--database` argument is supplied.

Keep `npm run biometrics` running with the existing `.env`. The rehearsal starts
only local mock-controller/runtime/bridge processes and uses ephemeral local trust.
It creates two HOLDs from an actually signed approval-required fixture release.
The UI labels the controller as mock; request IDs begin `native-test-`. It uses
real ArcFace settings and does not replace your native database or enrollment.
Type `hold` for another synthetic request, `status` for mock-command counts, and
`stop` to stop the rehearsal/app. Runtime data stays in its private directory.
`session.json` contains private session configuration and must not be shared.

From a second terminal in the repository root, add another HOLD to a running
rehearsal with:

```sh
npm run demo:hold -- --session /absolute/new-private-rehearsal/session.json
```

Each run signs a new test-agent `set_light_state` request and submits it through
the existing local runtime's `/request` endpoint. It prints the new request ID,
`CHALLENGE` and `NOT_EXECUTED`; the HOLD appears in the live native feed. The
command refuses nonlocal or non-rehearsal configuration and checks that the
authenticated bridge identifies the controller as mock. It does not approve the
HOLD or send a controller command. Keep the rehearsal running while using it.

1. Start the configured biometric service, then build/launch `npm run build:app`
   and `npm run launch:app`. Sign in with the existing enrolled technician.
2. Confirm feed source, controller label, connection freshness and history. The
   feed represents collected ALICE requests/audit, not every network packet.
3. Select a new eligible HOLD. Inspect the supplied exact request, action, target,
   parameters, immutable decision and authority binding. Missing historical bytes
   or unconfirmed/enterprise ownership must leave review unavailable.
4. Select approve once; obtain a fresh automatic face scan with no enrollment
   rotation. Confirm acknowledgment separately from execution and observation.
5. Reject another HOLD using another fresh scan; verify no controller execution.
6. Cancel a scan and a completed-but-unsubmitted scan. Change requests, sign out,
   and refresh stale state; those grants must not submit.
7. Interrupt delivery after submission. Reconcile the same saved action against
   the runtime; an unknown outcome is never a reason to create a new execution.

Automated tests use temporary ledgers, ephemeral keys, synthetic face-session
states and mock controllers. They do not establish real camera matching quality,
physical-Pi review, hardware effects, enterprise ownership transfer or network-wide
visibility. Real camera and physical acceptance must be recorded independently.
