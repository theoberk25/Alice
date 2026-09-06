"""Authenticated loopback demo API; native signed review is reused unchanged."""
import argparse
import hmac
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from urllib.parse import urlsplit, parse_qs

from dcamr.audit.event_contract import parse_json, _unique_object, _reject_number
from .environment import DemoError, Environment, GatewayUnavailable


def make_server(environment, operator_token, agent_token=None, agent_id='demo-agent', port=0,
                *, agents=None, runtime=None, renderer=None):
    agents = dict(agents or ({agent_id: agent_token} if agent_token else {}))
    tokens = [operator_token, *agents.values()]
    if (not agents or any(type(t) is not str or not t or not t.isascii() for t in tokens)
            or len(set(tokens)) != len(tokens)):
        raise ValueError('Distinct nonempty ASCII operator and agent tokens are required')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *args):
            pass

        def reply(self, code, value):
            payload = json.dumps(value, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(payload)

        def identity(self):
            token = self.headers.get('Authorization', '').encode('utf-8')
            if hmac.compare_digest(token, ('Bearer ' + operator_token).encode()):
                return 'operator', None
            for agent, secret in agents.items():
                if hmac.compare_digest(token, ('Bearer ' + secret).encode()):
                    return 'agent', agent
            return None, None

        def do_GET(self):
            role, _ = self.identity()
            if not role:
                return self.reply(401, {'error': 'Authentication required'})
            path = self.path.removeprefix('/demo')
            if path.startswith('/review/') and role == 'operator' and runtime:
                return self.reply(*runtime.review(request_id=path[len('/review/'):]))
            if urlsplit(path).path == '/events' and role == 'operator' and runtime:
                try:
                    query = parse_qs(urlsplit(path).query, keep_blank_values=True)
                    if set(query) - {'after'} or len(query.get('after', ['0'])) != 1:
                        raise ValueError
                    after = int(query.get('after', ['0'])[0])
                    if not 0 <= after <= 2**53 - 1:
                        raise ValueError
                    with runtime._lock:
                        runtime._owner.check()
                        if runtime.storage:
                            runtime.storage.check()
                        events = runtime.ledger.read(after=after, limit=64)
                    return self.reply(200, {'events': events})
                except ValueError:
                    return self.reply(400, {'error': 'Invalid event cursor'})
                except (OSError, RuntimeError):
                    return self.reply(503, {'error': 'Audit unavailable'})
            if self.path != '/demo/state':
                return self.reply(404, {'error': 'Unknown endpoint'})
            state = environment.snapshot()
            state['display'] = renderer.status.copy() if renderer else {'state': 'DISABLED'}
            self.reply(200, state)

        def do_POST(self):
            role, agent = self.identity()
            required = 'agent' if self.path == '/demo/fan-requests' else 'operator'
            if role != required:
                return self.reply(403, {'error': 'Role not permitted'})
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise DemoError('Transfer-Encoding is unsupported')
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1:
                    raise DemoError('One Content-Length required')
                length = int(lengths[0])
                if not 0 < length <= 16384:
                    raise DemoError('Body must be 1..16384 bytes')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise DemoError('Incomplete request body')
                body = (parse_json(raw) if self.path in ('/demo/review', '/review') else
                        json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object, parse_constant=_reject_number))
                if self.path == '/demo/configure':
                    value = environment.configure(body)
                elif self.path in ('/demo/start', '/demo/pause', '/demo/resume', '/demo/stop'):
                    if body != {}:
                        raise DemoError('Lifecycle body must be {}')
                    value = environment.control(self.path.rsplit('/', 1)[1])
                elif self.path == '/demo/fan-requests':
                    value = environment.request_fan(body, agent)
                elif self.path in ('/demo/review', '/review') and runtime:
                    # Operator token only permits transport; it cannot approve.
                    code, value = runtime.review(envelope=body)
                    environment.reconcile()
                    return self.reply(code, value)
                else:
                    return self.reply(404, {'error': 'Unknown endpoint'})
                self.reply(200, value)
            except (DemoError, ValueError, TypeError, UnicodeError, RecursionError):
                self.reply(400, {'error': 'Invalid request or lifecycle transition'})
            except GatewayUnavailable:
                self.reply(503, {'error': 'ALICE outcome unavailable; reconcile before retrying'})
            except (OSError, RuntimeError):
                self.reply(503, {'error': 'Service unavailable; outcome requires reconciliation'})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    from .runtime import ThermalRuntime, load_agent_keys
    from dcamr.display.renderer import PatternRenderer
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8795)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--trust-key', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--agent-keys', type=Path, required=True)
    parser.add_argument('--console-trust-file', type=Path)
    parser.add_argument('--esp-serial')
    parser.add_argument('--capacity-wh', type=float, default=100)
    parser.add_argument('--energy-time-scale', type=float, default=1)
    args = parser.parse_args()
    env = Environment(capacity_wh=args.capacity_wh, energy_time_scale=args.energy_time_scale)
    runtime = ThermalRuntime(environment=env, agent_keys=load_agent_keys(args.agent_keys),
        release_dir=args.release, trusted_manifest_key=bytes.fromhex(args.trust_key.read_text().strip()),
        data_dir=args.data_dir, esp_serial=args.esp_serial, serial_timeout=.25,
        console_trust_file=args.console_trust_file)
    stopped = threading.Event()
    workers = []
    server = None
    try:
        agents = json.loads(os.environ['THERMAL_AGENT_TOKENS'])
        if set(agents) != set(runtime.agent_keys):
            raise ValueError('Agent tokens must exactly match configured signing identities')
        renderer = PatternRenderer(runtime.controller) if runtime.controller else None
        server = make_server(env, os.environ.get('THERMAL_OPERATOR_TOKEN'), agents=agents,
                             port=args.port, runtime=runtime, renderer=renderer)
        def tick():
            while not stopped.wait(.1):
                env.snapshot()
                env.reconcile()
        def display():
            while not stopped.wait(.1):
                state = env.snapshot()
                renderer.update(state, received_at=time.monotonic())
        for target in ([tick, display] if renderer else [tick]):
            worker = threading.Thread(target=target, daemon=True)
            worker.start()
            workers.append(worker)
        print(f'Simulated environment listening on {server.server_address}', flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        if server:
            server.server_close()
        for worker in workers:
            worker.join()
        # Firmware's 2-second watchdog marks indicators unavailable on disconnect.
        runtime.close()


if __name__ == '__main__':
    main()
