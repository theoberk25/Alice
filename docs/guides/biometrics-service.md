# ALICE live face identity service

Run from the repository root with `npm run biometrics` after following the
[live facial setup](console/facial-verification-quickstart.md). The loopback
`ALICE_BIOMETRIC_SERVICE_URL` and private `ALICE_BIOMETRIC_TOKEN` must match the
native app. No permissive browser CORS or model download runs during authentication.

The native Swift camera owns acquisition; Rust owns operation intent, session IDs,
nonces, epochs, cancellation and final authority. Preview frames are display-only.
The Python service performs ArcFace identity, quality, MediaPipe pose and MiniFAS
presentation checks under `alice.live-face.v3`. No deepfake detector is included.

| Route | Purpose |
| --- | --- |
| GET `/live/readiness` | Policy, epoch, model readiness for live capture |
| POST `/live/begin` | Exact native operation/generation binding |
| POST `/live/observe` | Bounded native frame with matching session/nonce/epoch/sequence |
| POST `/live/cancel` | Release the service session |
| POST `/generation/activate` | Compare-and-swap activation of an encrypted staged generation |
| POST `/generation/remove` | Idempotent generation-bound removal and recovery |
| GET `/health`, `/model-info` | Service and identity-model diagnostics |
| POST `/enroll`, `/verify`, `/remove` | Legacy service compatibility/inference tests; no native login or grant authority |

All routes require bearer authentication. Unknown fields, invalid bindings, oversized
bodies, concurrent inference, stale/replayed sessions and unusable models fail closed.
Only embeddings/metadata persist in encrypted, versioned enrollment generations;
raw camera images are not retained. V1 data remains intact until explicit migration
or removal; compatible V2/V3 multi-pose galleries persist across service restarts.

Enrollment uses seven pose regions after brief neutral calibration. Later login and
local fresh approval use a short automatic gallery match, without repeating head
rotations. Native approval grants do not deliver live Pi decisions in this release.
Automated fixtures establish behavior, not live PAD accuracy or physical acceptance.
