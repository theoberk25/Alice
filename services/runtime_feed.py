"""Authenticated, read-only workstation bridge to the existing Pi /events feed.

Run with python -m services.runtime_feed. Deployment and boundaries: AGENTS.md
and docs/integration/live-dashboard.md. This service owns no database and never
accepts commands. Remote access is through a separately authenticated SSH tunnel.
"""
import argparse
import copy
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from urllib.parse import urlsplit, parse_qs
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler

from dcamr.audit.event_contract import validate_event

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_SAFE_INTEGER = 2**53 - 1


class CursorLost(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def loopback_url(value):
    u = urlsplit(value)
    if (u.scheme != 'http' or u.hostname not in ('127.0.0.1', '::1')
            or u.username or u.password or u.query or u.fragment or u.path not in ('', '/')):
        raise ValueError('Feed upstream must be an HTTP loopback base URL; use SSH forwarding for Pi access')
    if not u.port:
        raise ValueError('Explicit loopback port required')
    return value.rstrip('/')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def validate_page(payload, after):
    if type(payload) is not dict or set(payload) != {'events'} or type(payload['events']) is not list:
        raise ValueError('Invalid runtime feed envelope')
    events = payload['events']
    if after and not events:
        raise CursorLost('Acknowledged ledger head is no longer available')
    previous = None
    ids = set()
    for event in events:
        validate_event(event)  # agreed schema, semantic bindings and canonical hash
        if event['sequence'] > MAX_SAFE_INTEGER:
            raise ValueError('Sequence exceeds console integer range')
        if event['event_id'] in ids:
            raise ValueError('Duplicate event identity in runtime page')
        ids.add(event['event_id'])
        if previous is None:
            if event['sequence'] != max(1, after):
                raise CursorLost('Missing ledger cursor anchor')
        elif (event['sequence'] != previous['sequence'] + 1
              or event['previous_hash'] != previous['event_hash']
              or event['ledger_id'] != previous['ledger_id']
              or event['node_id'] != previous['node_id']):
            raise ValueError('Broken runtime event continuity')
        previous = event
    # Preserve 64-bit monotonic nanoseconds exactly across JavaScript JSON parsing.
    wire = copy.deepcopy(events)
    for event in wire:
        event['time']['monotonic_ns'] = str(event['time']['monotonic_ns'])
    return wire


def make_server(*, upstream, token, source, controller, port=8787):
    upstream = loopback_url(upstream)
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('ALICE_FEED_TOKEN must contain at least 32 non-whitespace ASCII characters')
    if source not in ('local-runtime', 'ssh-tunnel') or controller not in ('mock', 'physical-serial', 'unavailable'):
        raise ValueError('Explicit supported source/controller labels required')
    opener = build_opener(ProxyHandler({}), NoRedirect())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload):
            body = json.dumps(payload, separators=(',', ':')).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), f'Bearer {token}'):
                return self.reply(401, {'error': 'Feed authentication required'})
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if parsed.path != '/events':
                return self.reply(404, {'error': 'Read-only events endpoint only'})
            try:
                if set(query) != {'after'} or len(query['after']) != 1 or not query['after'][0].isascii() or not query['after'][0].isdigit():
                    raise ValueError
                after = int(query['after'][0])
                if not 0 <= after <= MAX_SAFE_INTEGER:
                    raise ValueError
            except ValueError:
                return self.reply(400, {'error': 'Invalid after cursor'})
            try:
                with opener.open(f'{upstream}/events?after={max(0, after - 1)}', timeout=5) as response:
                    data = response.read(MAX_RESPONSE_BYTES + 1)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise ValueError('Feed response exceeds supported size')
                payload = json.loads(data, object_pairs_hook=unique_object)
                events = validate_page(payload, after)
            except CursorLost:
                return self.reply(409, {'error': 'Ledger cursor lost; retained history requires revalidation'})
            except (ValueError, OSError):
                return self.reply(502, {'error': 'Runtime unavailable or invalid feed; no records substituted'})
            self.reply(200, {'schema_version': 'alice-runtime-feed-v1',
                             'source': {'connection': source, 'controller': controller},
                             'events': events})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--source', required=True, choices=('local-runtime', 'ssh-tunnel'))
    parser.add_argument('--controller', default='unavailable', choices=('mock', 'physical-serial', 'unavailable'),
                        help='Operator-declared mock or unknown hardware provenance; never a hardware verification claim')
    parser.add_argument('--port', type=int, default=8787)
    args = parser.parse_args()
    server = make_server(upstream=args.upstream, token=os.environ.get('ALICE_FEED_TOKEN', ''),
                         source=args.source, controller=args.controller, port=args.port)
    print(f'Read-only feed bridge listening on {server.server_address}; {args.source}, controller={args.controller}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
