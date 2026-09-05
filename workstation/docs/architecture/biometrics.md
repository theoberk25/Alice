# Facial identity and future liveness

The frontend asks for a specific username, then captures the local camera. It never searches the enrollment roster to guess an identity. Enrollment requires five distinct JPEG frames. The service decodes bounded images, detects exactly one face, checks face size/detection confidence/brightness/sharpness, uses landmark alignment in InsightFace, produces ArcFace embeddings, checks sample consistency, and saves the normalized mean embedding.

`/verify` compares each supplied capture with the claimed technician's reference using cosine similarity. A configurable threshold initially defaults to 0.45. This value is a demo configuration, not a measured false-accept-rate guarantee. Model/threshold changes need representative local evaluation and potentially re-enrollment.

Embeddings are encrypted with Fernet before being written to SQLite. The service directory is mode 0700; the database and encryption-key file are 0600. The key is separate from the database but accessible to the same OS user, so this does not protect against compromise of that user. No raw frames or vectors are returned to normal UI screens. Camera tracks stop when their view unmounts. Transport is loopback HTTP with a shared random bearer token known only to the native backend and service; never expose the service beyond loopback.

The service is an identity signal, not an action authority. Rust binds fresh step-up results to the logged-in technician, exact decision/request, issuance time, and expiry. A login success does not issue a step-up grant. Failure, model unavailability, missing enrollment, permission denial, no face, multiple faces, low-quality image, and submission errors all block approval visibly.

`BiometricVerifier.verifyAuthenticity` and the Python `AuthenticityVerifier` protocol reserve a separate anti-spoof extension. **Liveness and deepfake detection are not implemented.** ArcFace cannot distinguish a live technician from a convincing photo or replay. The UI says so.

The model is provisioned explicitly by `scripts/setup-model.py`, never downloaded during login or an outage. The service can boot with missing models and report UNAVAILABLE. Only detection and recognition modules are loaded. `buffalo_l` comes from the [official InsightFace project](https://github.com/deepinsight/insightface/tree/master/python-package); pretrained model usage is restricted separately from the MIT-licensed code (the project describes non-commercial research use). Obtain appropriate rights before redistribution or commercial deployment.

`scripts/smoke-arcface.py` performs real inference against scikit-image's public astronaut test image and checks blank/multiple-face rejection. It is not a live camera or anti-spoof test. Real technician enrollment and macOS camera permission must be exercised by the operator.
