"""Synthetic live dashboard session using the real SQLite/runtime pipeline.

No physical Pi or USB acceptance. All keys and data are created in a NEW directory.
The assessment is a fixture and the controller is mock. See AGENTS.md and
 docs/integration/live-dashboard.md. Commands on stdin: on, off, deny, stop.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import uuid

from dcamr.main import FirstLightRuntime, make_server as runtime_server
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from services.runtime_feed import make_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    root = args.directory
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    release = build_release.build(root / 'bundle', ('term-agent-01', 'ungranted-agent'), ('term-agent-01',))
    trust = bytes.fromhex((root / 'bundle/trust/manifest_public.hex').read_text().strip())
    esp_server, esp = mock_esp.make_server()
    runtime = FirstLightRuntime(release_dir=release, trusted_manifest_key=trust,
                               data_dir=root / 'usb-simulation',
                               esp_base_url=f'http://127.0.0.1:{esp_server.server_port}')
    pi = runtime_server(runtime, '127.0.0.1', 0)
    bridge = make_server(upstream=f'http://127.0.0.1:{pi.server_port}',
                         token=os.environ['ALICE_FEED_TOKEN'], source='local-runtime',
                         controller='mock', port=0)
    servers = [esp_server, pi, bridge]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()

    def submit(command, request_id=None):
        agent = 'ungranted-agent' if command == 'deny' else 'term-agent-01'
        seed = bytes.fromhex((root / f'bundle/client/{agent}-k1.seed').read_text().strip())
        envelope = build_envelope(seed, state='off' if command == 'off' else 'on',
                                  request_id=request_id or f'synthetic-{command}-{uuid.uuid4().hex[:8]}',
                                  agent_id=agent, key_id=f'{agent}-k1')
        code, result = runtime.handle_request(envelope)
        return {'request_id': envelope['request']['request_id'], 'http': code,
                'decision': result.get('decision'), 'execution': result.get('execution'),
                'observed_state': result.get('observed_state'), 'mock_commands': esp.commands}

    try:
        submit('on', 'synthetic-history-allow')
        submit('deny', 'synthetic-history-deny')
        print(json.dumps({'bridge': bridge.server_port, 'pi': pi.server_port,
                          'database': str(root / 'usb-simulation/ledger.sqlite'),
                          'source': 'SYNTHETIC / FIXTURE ASSESSMENT / MOCK ESP'}), flush=True)
        for line in sys.stdin:
            command = line.strip()
            if command == 'stop':
                break
            if command in ('on', 'off', 'deny'):
                print(json.dumps(submit(command)), flush=True)
    finally:
        for server in reversed(servers):
            server.shutdown()
            server.server_close()
        runtime.close()


if __name__ == '__main__':
    main()
