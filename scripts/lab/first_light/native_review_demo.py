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
import subprocess
import sys
import threading
import uuid

from dcamr.main import FirstLightRuntime, make_server as runtime_server
from common.repository_paths import repository_root
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from scripts.console.provision_review_key import provision
from services.runtime_feed import make_server

ROOT = repository_root()
REHEARSAL_SOURCE = "LOCAL REHEARSAL / SIGNED FIXTURE RELEASE / FIXTURE ASSESSMENT / MOCK ESP"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True,
                        help="New absolute directory outside Git for this rehearsal")
    parser.add_argument("--technician-id", action="append", required=True,
                        help="Exact existing enabled technician ID, not username")
    parser.add_argument("--launch-app", action="store_true",
                        help="Launch already-built native app using real existing ArcFace settings")
    parser.add_argument("--database", type=Path,
                        help="Explicit existing native database to reuse, e.g. the prior console-mock.sqlite3")
    parser.add_argument("--integration-test-ids", action="store_true",
                        help="Fixed request IDs for the opt-in Rust test with its isolated database only")
    args = parser.parse_args()
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
