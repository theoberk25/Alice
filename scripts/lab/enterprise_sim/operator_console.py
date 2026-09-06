"""Local authenticated-agent demo workbench; no enterprise permission publisher."""
import argparse
import html
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from lab.first_light.terminal_client import build_envelope, send
from .console import server as enterprise

PAGE = '''<!doctype html><meta charset="utf-8"><title>Sentinel operator</title>
<style>body{background:#101820;color:#e7eef6;font:17px system-ui;max-width:1000px;margin:45px auto;padding:20px}button,a{padding:12px;margin:8px;color:#071b25;background:#66d9bc;border:0;border-radius:6px;font:inherit}pre{white-space:pre-wrap;background:#1d2a37;padding:18px;border-radius:8px}small{color:#afbfce}</style>
<h1>Sentinel · SSgt A. Okafor</h1><p>Electrician · elec-agent-01 · Eight mapped lights</p>
<p>Signed action → enterprise receipt → Pi permissions check → USB audit → Wazuh upload</p>
<p><strong>Controller: CONTROLLER_LABEL.</strong> ON enables slow blinking (1 second lit / 1 second dark). Feedback reports blink enabled, not instantaneous brightness.</p>
<button onclick="allOff()">All lights off</button><pre id="bulk" hidden></pre>
<div id="lights"></div>
<a href="http://127.0.0.1:8787/" target="_blank">Enterprise overview</a>
<p id="message">Ready. Actions use your provisioned agent key on this Mac.</p>
<h2>Pi decision and USB-backed history</h2><pre id="pi">No request submitted in this page.</pre>
<h2>Actual Wazuh records for this request</h2><pre id="siem">Waiting for a request.</pre>
<small>Wazuh access uses the ssgt.a.okafor account. Login does not grant agent authority.
The Pi's signed release grants the action. Enterprise → Pi permission-cache refresh is not implemented by this page.</small>
<script>
let id=null; const token='TOKEN';
const labels=['Yellow 1 · D0','Blue 1 · D3','Red 1 · D5','White 1 · D6','Yellow 2 · D10','Blue 2 · D9','Red 2 · D8','White 2 · D7'];
labels.forEach((label,i)=>{const row=document.createElement('p');row.textContent=label+' ';['on','off'].forEach(state=>{const b=document.createElement('button');b.textContent=state.toUpperCase();b.onclick=()=>act(state,'ESP-LIGHT-'+String(i+1).padStart(2,'0'));row.appendChild(b)});document.getElementById('lights').appendChild(row)});
async function act(state,target){document.querySelectorAll('button').forEach(b=>b.disabled=true);
try{const r=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json','X-Operator-Token':token},body:JSON.stringify({state,target})});const d=await r.json();if(!r.ok)throw Error(d.error||'Action failed');id=d.request_id;document.getElementById('pi').textContent=JSON.stringify(d,null,2);document.getElementById('message').textContent='Request '+id;await poll();}catch(e){document.getElementById('message').textContent=e.message;}finally{document.querySelectorAll('button').forEach(b=>b.disabled=false);}}
async function allOff(){
 document.querySelectorAll('button').forEach(b=>b.disabled=true);
 id=null;const results=[];const box=document.getElementById('bulk');box.hidden=false;
 try{for(let i=0;i<8;i++){
  const target='ESP-LIGHT-'+String(i+1).padStart(2,'0');
  try{const r=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json','X-Operator-Token':token},body:JSON.stringify({state:'off',target})});
   const d=await r.json();const ok=r.ok&&d.http_status===200&&d.response?.execution==='COMPLETED'&&d.response?.observed_state==='off';
   results.push({light:labels[i],target,status:ok?'OFF confirmed':'Not confirmed',request_id:d.request_id,result:d});
  }catch(e){results.push({light:labels[i],target,status:'Not confirmed',error:e.message});}
  box.textContent=JSON.stringify(results,null,2);
 }
 document.getElementById('message').textContent=results.every(r=>r.status==='OFF confirmed')?'All eight lights confirmed OFF':'Some lights could not be confirmed OFF—see results';
 }finally{document.querySelectorAll('button').forEach(b=>b.disabled=false);}
}
async function poll(){if(!id)return;try{const r=await fetch('/status?id='+encodeURIComponent(id));const d=await r.json();document.getElementById('pi').textContent=JSON.stringify(d.pi,null,2);document.getElementById('siem').textContent=JSON.stringify(d.wazuh,null,2);}catch(e){document.getElementById('siem').textContent='Unavailable: '+e.message;}}
setInterval(poll,2500);
</script>'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--key-file',type=Path,required=True)
    p.add_argument('--credentials',type=Path,required=True)
    p.add_argument('--pi-url',default='http://192.168.50.20:8080')
    p.add_argument('--port',type=int,default=8789)
    p.add_argument('--enterprise-url',default='http://192.168.50.50:8790',
                   help='Signed ingress; verified Wazuh receipt before Pi forwarding')
    p.add_argument('--controller-label',default='Unverified controller')
    a=p.parse_args()
    for f in (a.key_file,a.credentials):
        if f.is_symlink() or f.stat().st_mode & 0o077: p.error('Private files must be mode 0600')
    seed=bytes.fromhex(a.key_file.read_text().strip()); c=json.loads(a.credentials.read_text())
    if c['username']!='ssgt.a.okafor':p.error('Expected selected Sentinel operator')
    enterprise.INDEXER_USER=c['username'];enterprise.INDEXER_PW=c['password']
    token=secrets.token_urlsafe(32); known={}; lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,body,html=False):
            data=body.encode() if html else json.dumps(body).encode()
            self.send_response(status);self.send_header('Content-Type','text/html' if html else 'application/json')
            self.send_header('Cache-Control','no-store');self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            if self.path!='/action':return self.reply(404,{'error':'Not found'})
            if self.headers.get('X-Operator-Token')!=token:return self.reply(403,{'error':'Forbidden'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=128:raise ValueError
                body=json.loads(self.rfile.read(length))
                if set(body)!={'state','target'} or body['state'] not in ('on','off') or body.get('target') not in [f'ESP-LIGHT-{i:02d}' for i in range(1,9)]:raise ValueError
            except (ValueError,TypeError):return self.reply(400,{'error':'Expected on/off state'})
            with lock:
                e=build_envelope(seed,state=body['state'],target=body['target'],agent_id='elec-agent-01',key_id='elec-agent-01-k1')
                rid=e['request']['request_id']
                receipt = None
                try:
                    code, ingress = send(a.enterprise_url,e)
                    receipt = ingress.get('enterprise_receipt')
                    result = ingress.get('pi', ingress)
                except Exception:
                    code,result=503,{'error':'Enterprise response unavailable; check history before retrying'}
                known[rid]={'request_id':rid,'http_status':code,'response':result,
                            'enterprise_receipt':receipt}
                if len(known)>100:known.pop(next(iter(known)))
            self.reply(200,known[rid])
        def do_GET(self):
            if self.path=='/':return self.reply(200,PAGE.replace('TOKEN',token).replace('CONTROLLER_LABEL',html.escape(a.controller_label)),True)
            from urllib.parse import urlsplit,parse_qs
            rid=parse_qs(urlsplit(self.path).query).get('id',[''])[0]
            with lock: result=known.get(rid)
            if not result:return self.reply(404,{'error':'Unknown request in this session'})
            pi=dict(result)
            try:
                with urlopen(a.pi_url+'/events?after=0',timeout=3) as r: events=json.load(r)['events']
                pi['events']=[e for e in events if e['correlation']['request_id']==rid]
                pi['source']='LIVE_PI_USB_LEDGER'
            except Exception:pi['history_status']='UNAVAILABLE'
            try:
                hits=enterprise._indexer_request('/alice-ledger-v1/_search',{'size':20,'query':{'term':{'request_id':rid}},'sort':[{'sequence':'asc'}]})
                wazuh={'source':'LIVE_WAZUH_INDEXER','records':[x['_source'] for x in hits['hits']['hits']]}
            except Exception:wazuh={'source':'UNAVAILABLE','records':[]}
            self.reply(200,{'pi':pi,'wazuh':wazuh})
    srv=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    print(f'Operator console: http://127.0.0.1:{a.port}/',flush=True)
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()

if __name__=='__main__':main()
