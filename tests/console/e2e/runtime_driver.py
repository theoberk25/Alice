"""Process fixture: real runtime and bridge, fixture assessment, mock ESP only."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

from dcamr.main import FirstLightRuntime, make_server as runtime_server
from lab.first_light import build_release, mock_esp
from lab.first_light.terminal_client import build_envelope
from services.runtime_feed import make_server

with tempfile.TemporaryDirectory(prefix='alice-live-browser-') as raw:
    root = Path(raw)
    release = build_release.build(root / 'bundle')
    trust = bytes.fromhex((root / 'bundle/trust/manifest_public.hex').read_text().strip())
    seed = bytes.fromhex((root / 'bundle/client/term-agent-01-k1.seed').read_text().strip())
    esp_server, esp = mock_esp.make_server()
    runtime = FirstLightRuntime(release_dir=release, trusted_manifest_key=trust,
                               data_dir=root / 'usb-test-data',
                               esp_base_url=f'http://127.0.0.1:{esp_server.server_port}')
    pi = runtime_server(runtime, '127.0.0.1', 0)
    bridge = make_server(upstream=f'http://127.0.0.1:{pi.server_port}',
                         token=os.environ['ALICE_FEED_TOKEN'], source='local-runtime',
                         controller='mock', port=0)
    for server in [esp_server, pi, bridge]:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    # Existing history before dashboard connection.
    runtime.handle_request(build_envelope(seed, state='on', request_id='history-request'))
    print(json.dumps({'pi': pi.server_port, 'bridge': bridge.server_port,
                      'envelope': build_envelope(seed, state='off', request_id='new-live-request')}), flush=True)
    try:
        for line in sys.stdin:
            command = line.strip()
            if command == 'stop':
                break
            if command == 'disconnect':
                bridge.shutdown()
                bridge.server_close()
                print('disconnected', flush=True)
            if command == 'reconnect':
                bridge = make_server(upstream=f'http://127.0.0.1:{pi.server_port}',
                                     token=os.environ['ALICE_FEED_TOKEN'], source='local-runtime',
                                     controller='mock', port=bridge.server_port)
                threading.Thread(target=bridge.serve_forever, daemon=True).start()
                print('reconnected', flush=True)
    finally:
        for server in [bridge, pi, esp_server]:
            server.shutdown()
            server.server_close()
        runtime.close()
