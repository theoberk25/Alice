# ALICE face identity service

Run from the `workstation/` subsystem root with `npm run biometrics` after installing the Python 3.11 environment and provisioning the model as described in the main README. The service binds to the loopback host/port in `ALICE_BIOMETRIC_SERVICE_URL` (default `http://127.0.0.1:8765`); native Rust uses the same setting. Choose another loopback port if the default is occupied; the same configured URL must reach the service from the native app. The historical standalone port choice does not configure this checkout. Set the same random `ALICE_BIOMETRIC_TOKEN` in both process environments. A missing/short token makes requests fail safely.

| Route | Body / response |
|---|---|
| GET `/health` | READY or UNAVAILABLE, model error, liveness NOT_CONFIGURED |
| GET `/model-info` | Model name, readiness, configured threshold |
| POST `/enroll` | `technician_id`, five to ten distinct base64 JPEG `frames`; returns usable sample count |
| POST `/verify` | `technician_id`, one to ten frames; returns PASS/FAIL, cosine similarity, threshold, provider |
| POST `/remove` | `technician_id`; removes encrypted reference |

All routes require `Authorization: Bearer <local-service-token>`. These are not public browser endpoints; there is no permissive CORS. `technician_id` accepts only letters, digits, underscore, and hyphen. Requests are size-bounded and extra schema fields are rejected. Image errors return explicit operational codes.

Modules separate configuration, schemas, image preprocessing/quality, detector/embedding inference, and encrypted persistence. Tests inject a deterministic engine for error/security paths. `scripts/biometrics/smoke_arcface.py` separately checks actual CPU inference on a public sample. The app never persists raw face frames. This is identity matching only: liveness and anti-spoof are not implemented.
