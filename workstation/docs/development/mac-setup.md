# macOS setup and packaging

Run these commands from the `workstation/` subsystem root. The migration imports source and locks, not `.env`, toolchains, models, native databases or installed services. See the [main workstation guide](../../../docs/workstation.md).

## Runtime setup

Install Xcode Command Line Tools, Node 22+, Rust stable, and Python 3.11. macOS 14+ is recommended for the locked current Python ONNX Runtime wheels, even though the native Tauri shell declares macOS 12 as its minimum. The checked-in Python lock was resolved on Apple Silicon. Intel Macs should resolve `requirements.txt` in a fresh 3.11 environment and rerun the same checks.

Tauri uses the macOS system webview and a Rust command boundary. See [official prerequisites](https://v2.tauri.app/start/prerequisites/) and [calling native Rust commands](https://v2.tauri.app/develop/calling-rust/).

The repository launcher detects a standard Rust toolchain or an isolated `.tools/cargo`/`.tools/rustup` installation, if separately provisioned in this checkout. It loads `.env` as literal key/value data without shell evaluation. Never put secrets in Vite-prefixed variables: Vite values are visible in the renderer. Bootstrap admin password is hashed when the selected database has zero administrators and both bootstrap values are configured, then removed from the native process environment; remove it from your `.env` after successful setup.

Native default data lives under the app's macOS Application Support directory. Mock state uses `console-mock.sqlite3`; real mode uses `console.sqlite3`. `ALICE_DATABASE_PATH` can override it. Point overrides at a private, dedicated directory. Do not use a shared world-readable volume for identity or audit data.

## Camera

The bundle includes `NSCameraUsageDescription` and the camera entitlement. Camera capture requests video only, never microphone input. macOS should show its normal privacy prompt when the operator begins enrollment/login/step-up. A denied/unavailable camera shows an explicit failure. Multiple available cameras can be selected in the capture view. Camera tracks stop when leaving it.

If permission was denied, enable ALICE in System Settings → Privacy & Security → Camera and retry. Real camera permission and live technician matching cannot be validated using a browser preview or a static-image smoke test; run them interactively on each demo Mac.

## One-command demo

After `npm ci` and Rust setup, `npm run demo` boots the native console in the configured mode. A running Vite server is reused; otherwise the launcher starts it. Default demo mode uses mock edge and mock biometrics. Real ArcFace uses `ALICE_BIOMETRIC_MODE=arcface`, an enrolled technician, and the separately running service (`npm run biometrics`). This separation means ML/service debugging does not block the first interactive demo.

Ollama is optional. Start `ollama serve` and choose an installed model in Connection settings. `ALICE_LLM_MODEL` configures its startup default. The launcher does not automatically install or start a large model.

## Bundle

`npm run build:app` produces `apps/desktop/src-tauri/target/release/bundle/macos/ALICE.app`. The binary currently is `Contents/MacOS/alice-technician-console`. The shipped React assets and local font files work without the network.

The initial package does not embed Python, ONNX weights, or Ollama. For a reproducible team demo, provision the venv, locked requirements, model, token, and optional Ollama model before disconnecting the network. Start local services separately. Model downloads never run during identity checks.

A later signed distribution can build the FastAPI service as a PyInstaller sidecar per architecture, place pre-provisioned model resources in a read-only bundle, manage a private token over native process launch, and wait for `/health` before accepting identity operations. Validate signing, hardened runtime, native libraries, microphone exclusion, and camera permission after packaging. That sidecar integration is a packaging strategy, not claimed complete in this build.

No Apple Developer signing identity or notarization credential was supplied. The local bundle is for development. Production rollout also needs the team's real transport authentication, attestation protocol, replay behavior, and appropriate biometric model rights.
