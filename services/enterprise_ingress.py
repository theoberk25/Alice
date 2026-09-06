"""Signed LAN demo ingress: verified Wazuh receipt before unchanged Pi forwarding.

See docs/integration/wazuh-audit-sync.md. This is not a permissions publisher.
"""
import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

from dcamr.audit.event_contract import canonical_bytes, parse_json
from dcamr.audit.signing import Ed25519Verifier, TrustError
from dcamr.main import _request_validator
from dcamr.packages.package_verifier import load_release
from cloud.wazuh_audit import WazuhAuditSink, DeliveryError, NoRedirect

INDEX = 'alice-enterprise-ingress-v1'
MAX_BYTES = 16 * 1024


class IngressError(ValueError):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


class ReceiptSink:
    def __init__(self, client):
        self.client = client

    def record(self, envelope):
        req = envelope['request']
        identity = sha256(req['request_id'].encode()).hexdigest()
        content = dict(schema_version='alice-enterprise-ingress-v1',
                       request_id=req['request_id'], agent_id=req['agent_id'],
                       request_sha256=sha256(canonical_bytes(req)).hexdigest(),
                       envelope=envelope)
        document = dict(content, received_at=datetime.now(timezone.utc).isoformat())
        status, _ = self.client._request('PUT', f'/{INDEX}/_create/{identity}', document)
        if status not in (201, 409):
            raise DeliveryError('ENTERPRISE_RECEIPT_WRITE_FAILED')
        code, stored = self.client._request('GET', f'/{INDEX}/_doc/{identity}')
        if code != 200 or stored.get('found') is not True or stored.get('_id') != identity:
            raise DeliveryError('ENTERPRISE_RECEIPT_READBACK_FAILED')
        original = stored.get('_source', {})
        if (set(original) != set(document) or not isinstance(original.get('received_at'), str)
                or canonical_bytes({k:v for k,v in original.items() if k!='received_at'}) != canonical_bytes(content)):
            raise IngressError(409, 'REQUEST_ID_CONFLICT')
        return dict(index=INDEX, document_id=identity, verified=True,
                    received_at=original['received_at'], replay=status==409)


class Gateway:
    def __init__(self, release, sink, forward, now=None, retain=None):
        self.release, self.sink, self.forward = release, sink, forward
        self.retain = retain
        self.validator = _request_validator()
        self.now = now or (lambda: datetime.now(timezone.utc))

    def submit(self, raw):
        try:
            envelope = parse_json(raw)
            if type(envelope) is not dict or set(envelope) != {'request','key_id','signature'}:
                raise ValueError()
            req = envelope['request']
            if type(envelope['key_id']) is not str or type(envelope['signature']) is not str:
                raise ValueError()
            key = self.release.terminal_keys.get(envelope['key_id'])
            if key is None:
                raise IngressError(401, 'UNKNOWN_KEY')
            Ed25519Verifier(key.public_key).verify(base64.b64decode(envelope['signature'],validate=True), canonical_bytes(req))
            if next(self.validator.iter_errors(req), None) is not None:
                raise IngressError(400, 'SCHEMA_VIOLATION')
            if req['agent_id'] != key.agent_id:
                raise IngressError(401, 'AGENT_KEY_BINDING_MISMATCH')
            issued = datetime.fromisoformat(req['issued_at'].replace('Z','+00:00'))
            age = (self.now()-issued).total_seconds()
            if not -5 <= age <= 300:
                raise IngressError(401, 'EXPIRED_OR_FUTURE_REQUEST')
        except IngressError:
            raise
        except (ValueError, TypeError, KeyError, TrustError):
            raise IngressError(401, 'INVALID_SIGNED_ENVELOPE') from None
        receipt = self.sink.record(envelope)  # Fail closed: never forward without readback.
        cache = None
        if self.retain is not None:
            cache = self.retain(envelope, receipt)
        try:
            status, result = self.forward(raw)  # Exact original envelope bytes.
        except (URLError, TimeoutError, OSError, ValueError):
            return 502, dict(request_id=req['request_id'], enterprise_receipt=receipt,
                             error='PI_OUTCOME_UNKNOWN_CHECK_HISTORY', retry='same envelope only; within freshness window')
        return status, dict(request_id=req['request_id'], enterprise_receipt=receipt,
                            pi_http_status=status, pi=result, pi_receipt_cache=cache)


def pi_forwarder(url):
    if not url.startswith('http://192.168.50.20:8080') or url.rstrip('/') != 'http://192.168.50.20:8080':
        raise ValueError('This demo ingress targets the fixed Pi LAN origin only')
    opener = build_opener(ProxyHandler({}), NoRedirect())
    def forward(raw):
        try:
            response = opener.open(Request(url.rstrip('/')+'/request',data=raw,
                headers={'Content-Type':'application/json'},method='POST'),timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            data=response.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES:raise ValueError('Oversized Pi response')
            return response.code, json.loads(data)
    return forward


def make_server(host, port, gateway):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup(); self.connection.settimeout(5)
        def log_message(self,*args): pass
        def reply(self,status,body):
            data=json.dumps(body).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path!='/health':return self.reply(404,{'error':'NOT_FOUND'})
            self.reply(200,dict(service='alice-enterprise-ingress',auth='Ed25519 signed request',
                                note='Listener ready; downstream health not asserted'))
        def do_POST(self):
            if self.path!='/request':return self.reply(404,{'error':'NOT_FOUND'})
            try:
                lengths=self.headers.get_all('Content-Length',[])
                if len(lengths)!=1 or self.headers.get('Transfer-Encoding'):raise IngressError(400,'INVALID_LENGTH')
                n=int(lengths[0])
                if not 0<n<=MAX_BYTES:raise IngressError(413,'INVALID_LENGTH')
                raw=self.rfile.read(n)
                if len(raw)!=n:raise IngressError(400,'TRUNCATED_BODY')
                status,body=gateway.submit(raw)
            except IngressError as e:status,body=e.status,{'error':e.code,'forwarded':False}
            except DeliveryError as e:status,body=503,{'error':e.code,'forwarded':False}
            except (ValueError,TimeoutError):status,body=400,{'error':'INVALID_BODY','forwarded':False}
            self.reply(status,body)
    return HTTPServer((host,port),Handler)


def retain_on_pi(envelope, receipt):
    import subprocess
    body={'envelope':envelope,'enterprise_receipt':{k:v for k,v in receipt.items() if k!='replay'}}
    raw=canonical_bytes(body)
    command=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
             'pi@192.168.50.20',
             'cd /home/pi/Alice && .venv/bin/python -m dcamr.enterprise_receipts '
             '--usb-root /mnt/alice-usb --release /mnt/alice-usb/release '
             '--trust-key /home/pi/first-light/jared-2/trust/manifest_public.hex']
    try:
        result=subprocess.run(command,input=raw,capture_output=True,timeout=15,check=True)
        saved=json.loads(result.stdout)
        if saved.get('stored') is not True or saved.get('sha256')!=sha256(raw).hexdigest():
            raise ValueError('Invalid cache acknowledgement')
        return saved
    except (subprocess.SubprocessError,OSError,ValueError):
        raise DeliveryError('PI_RECEIPT_CACHE_UNCONFIRMED_NOT_FORWARDED') from None


def local_indexer_client(config):
    # Docker publishes locally; preserve certificate hostname verification without
    # requiring a machine-wide /etc/hosts modification.
    import http.client
    import socket
    import ssl
    from urllib.request import HTTPSHandler
    client=WazuhAuditSink.from_config(config)
    if client.url != 'https://wazuh.indexer:9200':
        raise ValueError('Expected local Docker indexer TLS identity')
    class LocalConnection(http.client.HTTPSConnection):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self._create_connection=lambda address,timeout,source_address: socket.create_connection(
                ('127.0.0.1',address[1]),timeout,source_address)
    class LocalHandler(HTTPSHandler):
        def https_open(self,req):
            return self.do_open(LocalConnection,req,context=self._context)
    context=ssl.create_default_context(cafile=json.loads(config.read_text())['ca_file'])
    client.opener=build_opener(ProxyHandler({}),NoRedirect(),LocalHandler(context=context))
    return client


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--release',type=Path,required=True)
    p.add_argument('--trust-key',type=Path,required=True)
    p.add_argument('--wazuh-config',type=Path,required=True)
    p.add_argument('--host',default='192.168.50.50',choices=['192.168.50.50','127.0.0.1'])
    p.add_argument('--port',type=int,default=8790)
    a=p.parse_args()
    release=load_release(a.release,bytes.fromhex(a.trust_key.read_text().strip()))
    gateway=Gateway(release,ReceiptSink(local_indexer_client(a.wazuh_config)),
                    pi_forwarder('http://192.168.50.20:8080'), retain=retain_on_pi)
    server=make_server(a.host,a.port,gateway)
    print(f'Enterprise signed ingress http://{a.host}:{a.port}/request',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
