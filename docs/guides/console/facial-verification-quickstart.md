# Set up live facial verification

Updated September 6, 2026 for the main-based `alice.live-face.v3` integration.
Follow [working rules](../../../AGENTS.md) and the [workstation guide](../workstation.md).
This guide describes the implemented native flow. Physical camera acceptance must
be repeated on each teammate's Mac; automated component tests do not establish it.

## Install and provision

Use Node 22+, Python 3.11, Rust stable and Xcode Command Line Tools on macOS.
From the repository root, install `npm ci` and the biometric environment described
in the [console guide](../technician-console.md). Then install the live additions:

```sh
services/biometrics/.venv/bin/python -m pip install --no-deps -r services/biometrics/requirements-live.txt
services/biometrics/.venv/bin/python scripts/biometrics/setup_model.py
services/biometrics/.venv/bin/python scripts/biometrics/setup_live_models.py
```

Models are explicitly provisioned and checksum checked. Authentication does not
download models. Existing models, enrollment stores, keys and environment settings
must be preserved. No model weights or private biometric data are distributed in Git.
See [third-party notices](../live-face-third-party-notices.md).

Edit the existing private root `.env`, or copy `.env.example` only if none exists:

```dotenv
ALICE_TRANSPORT_MODE=mock
ALICE_BIOMETRIC_MODE=arcface
ALICE_ADMIN_USERNAME=<bootstrap username for a new database>
ALICE_ADMIN_PASSWORD=<unique password of at least 12 characters>
ALICE_BIOMETRIC_SERVICE_URL=http://127.0.0.1:8765
ALICE_BIOMETRIC_TOKEN=<random private token of at least 32 characters>
```

Generate a token locally with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
Use the same token and service URL for both native app and service. Keep `.env`
private (`chmod 600 .env`). Existing administrator accounts are not overwritten by
bootstrap values. `ALICE_DATABASE_PATH`, `ALICE_BIOMETRIC_DATA_DIR` and
`ALICE_INSIGHTFACE_ROOT` retain their existing meanings; do not reset them to
work around missing enrollment or key errors.

Start `npm run biometrics` in one terminal. In another run `npm run demo`, or build
with `npm run build:app` and run `npm run launch:app`. A built checkout-local app
can also be opened from Finder; it loads its checkout's allowed native settings.
The local Python service must remain running. Browser preview cannot enroll or
verify identity. Allow macOS camera access and keep ALICE foreground during capture.

For the team's live read-only feed, use `ALICE_TRANSPORT_MODE=remote` and the
existing `ALICE_FEED_URL` / `ALICE_FEED_TOKEN` configuration from the
[live dashboard guide](../demo-runbook.md). Live HOLD approval
and rejection remain explicitly unavailable in this delivery. Mock transport is
only for fixture decisions; it does not command physical devices.

## Enroll once, then sign in automatically

1. Open Administration and authenticate with the database's administrator account.
2. Add/update a technician, then select **Save identity & enroll face** or **Re-enroll**.
3. The native camera starts automatically. Face it briefly to establish neutral,
   then look around gently to fill the seven-region meter. Angles may be completed
   in either order after center. There is no shutter button or timed manual capture.
4. Keep the face visible; ordinary quality/position interruptions pause collection
   without deleting accepted angles. Enrollment collects two samples per region.
5. Wait for successful encrypted-generation activation and the enrolled status.
   If saving was interrupted, use the recovery control; do not delete the store.
6. Open Technician identity, enter the technician username and continue. A short
   automatic scan matches the saved pose gallery. Login does not repeat enrollment
   rotations. Slight angles are supported within the implemented pose limits.
7. A brief checkmark/fade acknowledges success. Failure, cancellation and stale
   sessions cannot sign in. Restarting the app/service retains active enrollment.

V1 identity-only enrollments are retained but require multi-pose re-enrollment.
Saved compatible V2/V3 galleries are reused. Native and service generation checks
prevent an interrupted re-enrollment from silently replacing the active identity.
Raw camera frames stay in memory; encrypted embeddings and metadata persist locally.

## Local fresh approval and evidence limits

In the native app with mock transport and real ArcFace enabled, **Approve once** on
a reviewable fixture HOLD starts a fresh automatic facial verification. Login alone
cannot satisfy it. The native one-use grant binds the technician, decision and request
and expires after 60 seconds. Failed/cancelled/superseded attempts cannot submit.
The fixture receipt is not physical execution confirmation. Live Pi approval and
rejection are separate unfinished work, retained only on a local WIP branch.

`npm run check`, `npm run test:rust`, and `npm run test:python` exercise the UI,
session authority, gallery persistence, cancellation and negative paths.
`services/biometrics/.venv/bin/python scripts/biometrics/smoke_native_identity.py`
checks actual public-image ArcFace inference and confirms retired renderer-frame
IPC cannot mint native authority; it does not test live capture or PAD accuracy.

The five controls are identity, image quality, capture integrity, pose and MiniFAS
presentation checks. There is no deepfake detector, forged-media fallback, or
randomized head/blink challenge. This webcam implementation is not Apple's depth
sensor system. User-reported success and rejection on the original branch are
historical evidence; the integrated build still needs a person to enroll, restart,
log in and exercise a fresh local approval on their own Mac.
