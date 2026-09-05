# Set up and test local facial verification

Updated for source migration: September 5, 2026. Run commands from `workstation/` in the main ALICE repository. Follow the [main workstation guide](../../../docs/guides/workstation.md) and [Mac setup](mac-setup.md) to provision dependencies first.

## Implemented behavior and historical evidence

Real InsightFace/ArcFace inference is implemented. The standalone source's automated tests exercised enrollment, username-based login, failed capture, fresh approval verification, one-use request binding, native audit and enrollment removal through Rust and the real Python service.

**Historical standalone evidence:** the original operator confirmed live enrollment and facial login on September 5, 2026, corroborated by native audit records. See the [historical verification record](verification.md). This source migration does not install dependencies, configure credentials, copy enrollment data or certify camera readiness in this checkout. Fresh live approval step-up and negative cases still need operator acceptance. The instructions below support new setup and repeat testing; preserve any existing private credentials and enrolled identities.

ArcFace answers whether a captured face matches one claimed identity. It does not prove that the face is live or detect a photo, screen replay or deepfake. The application correctly displays liveness as not configured.

## Fastest check without using the camera

After separately installing the Python environment, Rust toolchain and model according to the subsystem [README](../../README.md), run:

```sh
services/biometrics/.venv/bin/python scripts/smoke-native-identity.py
```

This starts a temporary authenticated local biometric server, uses a public test image, and runs the real Rust → FastAPI → ArcFace enrollment/login/approval path. It should exit successfully with a message beginning `Real ArcFace service → native enrollment` and a passing Rust test result. It also checks that a blank capture blocks verification and that disabling the identity revokes its session.

It supplies its own temporary administrator, token and enrollment store and removes them afterward. It does not configure your normal app or enroll you. This is the easiest inference/integration check; the next steps test the actual camera.

## Configure the real camera test once

1. Quit the currently running ALICE app and stop its `npm run demo` terminal with Ctrl+C. Stop an existing biometric-service terminal too if one is running. The native processes need a restart to read changed environment settings.
2. Use `workstation/.env` for this subsystem. On first setup, copy `.env.example` only if `.env` is absent; otherwise edit the existing private file without overwriting working settings. Configure bootstrap credentials only for a database without an administrator. Set the following keys, replacing both angle-bracket values with your own values:

   ```dotenv
   ALICE_TRANSPORT_MODE=mock
   ALICE_BIOMETRIC_MODE=arcface
   ALICE_ADMIN_USERNAME=admin
   ALICE_ADMIN_PASSWORD=<choose-a-unique-password-of-at-least-12-characters>
   ALICE_BIOMETRIC_SERVICE_URL=http://127.0.0.1:8765
   ALICE_BIOMETRIC_TOKEN=<paste-a-random-token-of-at-least-32-characters>
   ```

   `admin` is a proposed username for you to create, not an existing account. Do not use the placeholder password/token literally. Generate a token locally with:

   ```sh
   python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```

   Paste that output as the literal token value in `.env`. The launcher does not evaluate shell expressions placed inside `.env`. The file is ignored by Git; keep it private and do not paste credentials into a shared handoff or chat. `chmod 600 .env` keeps its filesystem permissions private.

3. Confirm the configured model paths point to the separately provisioned `buffalo_l` assets and this checkout has its Python virtualenv. Keep existing working paths. Ollama is optional for facial verification and does not need to be running for this test.
4. Start the service in one terminal:

   ```sh
   npm run biometrics
   ```

   Leave it running. It binds to the loopback URL configured above. If that port is occupied, choose an available loopback port and configure the same `ALICE_BIOMETRIC_SERVICE_URL` for both service and native app. A separate unauthenticated browser/curl visit to `/health` is expected to return 401; do not remove service authentication to make that visit work.

5. Start the native app in a second terminal:

   ```sh
   npm run demo
   ```

   The dashboard should now require technician identity. The edge is still deliberately simulated, allowing you to test real facial verification before upstream integration. Use this native app, not the browser started by `npm run dev`.

The admin is created at native startup if the selected database has zero admins and both credentials are configured. If an administrator already exists, that account is retained and environment changes do not replace it. Once created, its Argon2id hash is stored in SQLite. You can remove `ALICE_ADMIN_PASSWORD` from `.env` after confirming bootstrap/login and keep the password in your password manager; restarting the app does not require that bootstrap value again. Changing `.env` later does not change the stored password, and no password-reset UI exists yet.

## Set a user's face through Administration

1. Open **Administration** from the top navigation. This remains available while the technician dashboard is locked.
2. Enter the admin username/password you just configured and click **Authenticate administrator**. This creates an admin session; it is separate from technician face login.
3. In **Add or update technician**, enter an identity. For example:

   | Field           | Example      |
   | --------------- | ------------ |
   | `technician_id` | `TECH-001`   |
   | `username`      | `alex`       |
   | `display_name`  | `Alex`       |
   | `role`          | `Technician` |

   Use a unique technician ID and username. IDs allow letters, digits, hyphens and underscores. Use the same technician ID when updating an existing identity.

4. Click **Save identity & enroll face**. This saves metadata and opens camera enrollment.
5. Allow ALICE to use the camera when macOS asks. Select the desired camera if more than one is listed. Keep only your face in view, with even front lighting.
6. Click **Capture 5 samples**. The UI collects five frames about 450 ms apart. Move your head slightly while remaining centered so the frames are distinct. The service checks exactly one face, usable quality and consistent identity, then stores the reference embedding.
7. Confirm the technician row shows **ENABLED** and **ENROLLED**. Captured photos are not stored; an encrypted face embedding and enrollment metadata are stored locally.

For another person, repeat with another unique technician ID and username. Existing rows provide **Edit**, **Enroll face / Re-enroll**, **Enable / Disable**, and **Remove face**. Re-enrollment replaces the reference for that ID. Removing a face removes the enrollment but leaves technician metadata. Disable, removal and re-enrollment invalidate applicable native grants; disable/removal/re-enrollment also revoke the affected active native session.

## Test actual face login

1. Open **Technician identity** using the user icon/sign-in control, or **Technician sign in** on the locked screen.
2. Enter the technician username you created, such as `alex`. Do not enter the admin username unless you separately created a technician with that username.
3. Click **Continue to facial login**, then **Capture and verify** with your face centered.
4. A successful comparison opens the technician dashboard and shows your enrolled display name. If verification fails, the app stays locked and displays the reason.

For a simple negative check, sign out and try a capture pointed at a blank wall. It should report no face and remain logged out. If another consenting person is available, have them attempt your claimed username: identity matching should fail. A blank-wall test checks face detection; the other-person test checks identity discrimination.

## Test fresh face verification before approval

1. Log in successfully as your technician.
2. Select the supplied HOLD `allow_outbound` request, with risk 94 and request `REQ-88291`.
3. Click **Approve once**. The modal should show **LOCAL FACE IDENTITY** and a real camera preview. **Simulate pass/fail** buttons mean the app is still in mock biometric mode; revisit `.env` and restart the launcher.
4. First capture a blank wall or have no face in frame. The modal should say **Approval blocked** and the original request should remain HOLD. No approval is submitted from that failure.
5. Retry with your own face and click **Capture and verify**. A match creates a new grant and submits the one-request approval. Expect **Approval submitted / APPROVED ONCE** and a cosine similarity/threshold display.
6. The original upstream result should still say **HOLD**, with execution unconfirmed. That is correct: this is a mock edge acknowledgement, and the console does not execute the protected action.

Login does not satisfy this approval check. Step-up issues a separate native grant bound to the decision, request, technician and time, valid for 60 seconds and consumed by a successful submission.

For another run after approval or rejection, use the development sliders → **Reset scenario**. This deliberately clears mock actions and annotations so the same fixture can be reviewed again; it retains original decisions and audit history. Keep remote transport disabled until its real integration exists.

## Troubleshooting

| Symptom                                           | What to check                                                                                                                                                         |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Administration button disabled for authentication | You are probably in browser preview. Run the native `npm run demo` app.                                                                                               |
| Admin credentials rejected                        | Check that you restarted after setting both values and are using the selected database's existing admin credentials. The example `admin` account is not preinstalled. |
| Startup rejects admin password                    | Use at least 12 characters.                                                                                                                                           |
| No camera prompt / denied camera                  | Begin capture in native ALICE; check System Settings → Privacy & Security → Camera. Allow ALICE, then reopen the capture view or restart the app.                     |
| Camera unavailable                                | Check the selected device, another application's camera use, and whether a camera is actually connected.                                                              |
| Biometric token not configured                    | Set the same `.env` token for both launchers and restart them. It must be at least 32 characters.                                                                     |
| UNAUTHORIZED_LOCAL_CLIENT                         | The service and native app are using different tokens. Exported shell values can override `.env`.                                                                     |
| Service unavailable                               | Keep `npm run biometrics` running and verify the configured loopback URL/port.                                                                                        |
| MODEL_FILES_MISSING / MODEL_LOAD_FAILED           | Check the installed venv, provisioned model path and service terminal; see the main README for setup.                                                                 |
| CAPTURE_FIVE_DISTINCT_FRAMES                      | Keep the camera live and move your head slightly while the five samples are captured.                                                                                 |
| MULTIPLE_FACES_DETECTED                           | Remove other faces from the camera view.                                                                                                                              |
| LOW_QUALITY_*                                     | Improve lighting, face size or sharpness, then retry.                                                                                                                 |
| Identity not enrolled / model mismatch            | Ensure the technician row is ENROLLED and use its username; re-enroll if the model/reference changed.                                                                 |
| Too many failed attempts                          | Wait 30 seconds and retry with a usable capture.                                                                                                                      |
| Still seeing Alex Morgan or simulate controls     | The active native process is still using mock biometrics. Fully restart with `ALICE_BIOMETRIC_MODE=arcface`.                                                          |
| Account missing after changing transport mode     | Mock and remote modes use different native databases by default. Their admin/technician metadata is not automatically shared.                                         |

Do not use a photo or replay rejection as an acceptance criterion for this initial ArcFace-only implementation: liveness/anti-spoof is future work. Identity threshold calibration, live approval step-up and broader negative-case acceptance are still required; basic live enrollment/login were confirmed only in the historical standalone audit. Record new outcomes as separately dated operator evidence linked from the [main workstation guide](../../../docs/guides/workstation.md); retain the [standalone verification record](verification.md) as historical evidence.

## On a new teammate's Mac

Follow the subsystem [README](../../README.md) and [Mac setup](mac-setup.md) to install npm/Rust/Python dependencies and provision the model first. The venv, model, `.env`, databases and ALICE.app are ignored build/runtime artifacts and are not included in a Git clone or this source migration.

## Reassessment demo and face binding

For the full current flow, select Development scenarios → `04_hold_context_rejustification`. Wait for the agent response, REASSESSMENT PENDING, then DEC-20260905-000185 as CURRENT ASSESSMENT. Its risk is 62 and verified evidence is 2/3, compared with the preserved original's 94 and 1/3. These are simulated upstream decisions even when the face check is real ArcFace.

Choose Approve once on DEC-185 and confirm the modal displays DEC-185 / REQ-88291 before the fresh capture. A prior login or DEC-184 approval verification does not authorize DEC-185. If a reassessment arrives while an old approval dialog is open, close it and reopen approval on the current assessment; the old capture cannot be reused. Native restart retains DEC-185 once seen. Do not delete the enrolled operator's database to replay the original timeline; use browser preview for a fresh simulated sequence. See the mock scenario guide for isolated native replay options.
