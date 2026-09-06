"""Local native review rehearsal: signed fixture release, real ledger, mock ESP.

Uses the existing biometric service and enrollment when --launch-app is selected.
Never connects to a physical Pi, provisions remote trust, or relaxes face policy.
All runtime trust, requests and ledger files belong to a new private directory.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
from urllib.parse import urlsplit
import uuid

from dcamr.main import FirstLightRuntime, make_server as runtime_server
from common.repository_paths import repository_root
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from scripts.console.provision_review_key import provision
from services.runtime_feed import make_server

ROOT = repository_root()
REHEARSAL_SOURCE = "LOCAL REHEARSAL / SIGNED FIXTURE RELEASE / FIXTURE ASSESSMENT / MOCK ESP"


class ResumeError(ValueError):
    """Bounded diagnostic: private descriptors and key contents stay private."""


def resume_configuration(session_file):
    """Validate the complete existing rehearsal before opening any runtime."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from dcamr.audit.event_contract import MAX_EVENT_BYTES, parse_json
    from dcamr.packages.package_verifier import RELEASE_DOCUMENTS, load_release
    from dcamr.technician_review import load_trust
    from lab.first_light.send_native_hold import _private_file, load_rehearsal
    try:
        runtime_url, _, feed_url, token = load_rehearsal(session_file)
        root = Path(session_file).resolve(strict=True).parent
        info = parse_json(_private_file(root / "session.json", MAX_EVENT_BYTES))
        settings = info["environment"]
        required_settings = {"ALICE_TRANSPORT_MODE", "ALICE_BIOMETRIC_MODE", "ALICE_FEED_URL",
                             "ALICE_FEED_TOKEN", "ALICE_CONSOLE_ID", "ALICE_REVIEW_KEY_FILE"}
        if not required_settings <= set(settings) <= required_settings | {"ALICE_DATABASE_PATH"}:
            raise ValueError
        endpoints = [urlsplit(value) for value in (runtime_url, feed_url)]
        if any(endpoint.hostname != "127.0.0.1" or not 0 < endpoint.port < 65536
               for endpoint in endpoints) or endpoints[0].port == endpoints[1].port:
            raise ValueError
        directories = ("runtime", "runtime/evidence", "bundle", "bundle/release",
                       "bundle/trust", "bundle/client", "console")
        files = ["runtime/ledger.sqlite", "runtime/ledger_key.seed",
                 "bundle/trust/manifest_public.hex", "bundle/client/term-agent-01-k1.seed",
                 "console/console.seed", "console/console-trust.candidate.json"]
        files.extend(f"bundle/release/{name}" for name in RELEASE_DOCUMENTS)
        # FirstLightRuntime can provision absent local files. Resume must never
        # enter that creation path, or follow a replacement into another store.
        for relative in directories:
            path = root / relative
            if not path.is_dir() or path.resolve(strict=True) != path:
                raise ValueError
        for relative in files:
            path = root / relative
            if not path.is_file() or path.resolve(strict=True) != path:
                raise ValueError
        ledger_seed = bytes.fromhex(_private_file(root / "runtime/ledger_key.seed", 128)
                                    .decode("ascii").strip())
        manifest_key = bytes.fromhex((root / "bundle/trust/manifest_public.hex")
                                    .read_text().strip())
        console_seed = _private_file(root / "console/console.seed", 32)
        if (len(ledger_seed) != 32 or len(manifest_key) != 32 or len(console_seed) != 32
                or settings["ALICE_REVIEW_KEY_FILE"] != str(root / "console/console.seed")):
            raise ValueError
        trust_file = root / "console/console-trust.candidate.json"
        trust = load_trust(trust_file)
        trusted = trust[settings["ALICE_CONSOLE_ID"]][0]
        public = Ed25519PrivateKey.from_private_bytes(console_seed).public_key()
        if trusted.public_bytes(Encoding.Raw, PublicFormat.Raw) != public.public_bytes(Encoding.Raw, PublicFormat.Raw):
            raise ValueError
        load_release(root / "bundle/release", manifest_key)
        return {"root": root, "runtime_port": endpoints[0].port, "feed_port": endpoints[1].port,
                "token": token, "manifest_key": manifest_key, "trust_file": trust_file}
    except Exception:
        raise ResumeError("INVALID_EXISTING_LOCAL_REHEARSAL; no new state was created") from None


def resume(session_file):
    """Reopen existing history at its original endpoints until an explicit signal."""
    config = resume_configuration(session_file)
    root = config["root"]
    servers, started, runtime = [], [], None
    stopped = threading.Event()
    previous_handlers = {}
    try:
        controller, esp = mock_esp.make_server()
        servers.append(controller)
        runtime = FirstLightRuntime(
            release_dir=root / "bundle/release", trusted_manifest_key=config["manifest_key"],
            data_dir=root / "runtime", esp_base_url=f"http://127.0.0.1:{controller.server_port}",
            console_trust_file=config["trust_file"])
        pi = runtime_server(runtime, "127.0.0.1", config["runtime_port"])
        servers.append(pi)
        bridge = make_server(upstream=f"http://127.0.0.1:{pi.server_port}", token=config["token"],
                             source="local-runtime", controller="mock", port=config["feed_port"])
        servers.append(bridge)
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, lambda *_: stopped.set())
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            started.append(server)
        print(json.dumps({"ready": True, "resumed": True, "source": REHEARSAL_SOURCE,
                          "session_file": str(root / "session.json"),
                          "events": sum(1 for _ in runtime.iter_events()),
                          "mock_controller_reset": True, "mock_state": esp.state,
                          "mock_commands": esp.commands}), flush=True)
        # Packaged-app use must survive a closed launch terminal/stdin. No
        # requests are generated and no historical controller action is replayed.
        stopped.wait()
    finally:
        for server in reversed(started):
            server.shutdown()
        for server in reversed(servers):
            server.server_close()
        if runtime is not None:
            runtime.close()
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--directory", type=Path,
                      help="New absolute directory outside Git for this rehearsal")
    mode.add_argument("--resume", type=Path,
                      help="Existing absolute private session.json; reopen history until SIGINT/SIGTERM")
    parser.add_argument("--technician-id", action="append",
                        help="Exact existing enabled technician ID, not username")
    parser.add_argument("--launch-app", action="store_true",
                        help="Launch already-built native app using real existing ArcFace settings")
    parser.add_argument("--database", type=Path,
                        help="Explicit existing native database to reuse, e.g. the prior console-mock.sqlite3")
    parser.add_argument("--integration-test-ids", action="store_true",
                        help="Fixed request IDs for the opt-in Rust test with its isolated database only")
    args = parser.parse_args()
    if args.resume is not None:
        if args.technician_id or args.launch_app or args.database or args.integration_test_ids:
            parser.error("--resume uses its existing configuration; creation/launch options are not accepted")
        try:
            resume(args.resume)
        except ResumeError as exc:
            parser.exit(1, f"{exc}\n")
        except (OSError, RuntimeError):
            parser.exit(1, "EXISTING_LOCAL_REHEARSAL_UNAVAILABLE; check saved state, ownership and loopback ports\n")
        return
    if not args.technician_id:
        parser.error("--technician-id is required when creating a rehearsal")
    if args.database is not None and not args.database.expanduser().resolve().is_file():
        parser.error("--database must name an existing native database; no new identity store is created")
    root = args.directory.expanduser().resolve()
    if ROOT == root or ROOT in root.parents:
        parser.error("Use a new private rehearsal directory outside the checkout")
    root.mkdir(mode=0o700, exist_ok=False)
    console_id = "local-rehearsal-" + uuid.uuid4().hex[:12]
    keys = provision(root / "console", console_id, args.technician_id)
    release = build_release.build(root / "bundle", approval_required=True)
    manifest_key = bytes.fromhex((root / "bundle/trust/manifest_public.hex").read_text().strip())
    agent_key = root / "bundle/client/term-agent-01-k1.seed"
    agent_key.chmod(0o600)
    agent_seed = bytes.fromhex(agent_key.read_text().strip())
    servers, runtime, app = [], None, None
    try:
        controller, esp = mock_esp.make_server()
        servers.append(controller)
        threading.Thread(target=controller.serve_forever, daemon=True).start()
        runtime = FirstLightRuntime(
            release_dir=release, trusted_manifest_key=manifest_key,
            data_dir=root / "runtime", esp_base_url=f"http://127.0.0.1:{controller.server_port}",
            console_trust_file=keys["trust_candidate"])
        pi = runtime_server(runtime, "127.0.0.1", 0)
        token = secrets.token_urlsafe(48)
        bridge = make_server(upstream=f"http://127.0.0.1:{pi.server_port}", token=token,
                             source="local-runtime", controller="mock", port=0)
        for server in (pi, bridge):
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
        settings = {"ALICE_TRANSPORT_MODE": "remote", "ALICE_BIOMETRIC_MODE": "arcface",
                    "ALICE_FEED_URL": f"http://127.0.0.1:{bridge.server_port}",
                    "ALICE_FEED_TOKEN": token, "ALICE_CONSOLE_ID": console_id,
                    "ALICE_REVIEW_KEY_FILE": keys["key_file"]}
        if args.database is not None:
            settings["ALICE_DATABASE_PATH"] = str(args.database.expanduser().resolve())
        info = {"source": REHEARSAL_SOURCE, "directory": str(root),
                "runtime_url": f"http://127.0.0.1:{pi.server_port}", "environment": settings}
        descriptor = os.open(root / "session.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(info, stream, indent=2)
        def hold(request_id):
            code, result = runtime.handle_request(build_envelope(
                agent_seed, state="on", request_id=request_id))
            if code != 202 or result.get("decision") != "CHALLENGE":
                raise RuntimeError("Rehearsal did not produce a signed-permission HOLD")
            return request_id
        suffix = "" if args.integration_test_ids else "-" + uuid.uuid4().hex[:12]
        requests = [hold("native-test-approve" + suffix), hold("native-test-reject" + suffix)]
        print(json.dumps({"ready": True, "source": info["source"], "requests": requests,
                          "session_file": str(root / "session.json"),
                          "mock_commands": esp.commands}), flush=True)
        if args.launch_app:
            app = subprocess.Popen(["node", "scripts/console/desktop.mjs", "launch"],
                                   cwd=ROOT, env={**os.environ, **settings},
                                   stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr)
        for line in sys.stdin:
            command = line.strip()
            if command == "stop":
                break
            if command == "hold":
                print(json.dumps({"request_id": hold("native-test-" + uuid.uuid4().hex[:12])}), flush=True)
            elif command == "status":
                print(json.dumps({"mock_commands": esp.commands,
                                  "events": sum(1 for _ in runtime.iter_events())}), flush=True)
    finally:
        if app is not None and app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        for server in reversed(servers):
            server.shutdown()
            server.server_close()
        if runtime is not None:
            runtime.close()


if __name__ == "__main__":
    main()
