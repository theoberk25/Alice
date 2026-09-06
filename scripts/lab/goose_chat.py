#!/usr/bin/env python3
"""Very basic chat window for the local Goose agent (docs/agent-build/02-local-harness.md).

Serves a one-page chat at http://127.0.0.1:8791 and relays each message to the
local Goose agent via `goose run` (one persistent session for continuity). Goose
talks to the Light-Control MCP on :8790, so you can say things like
"turn machine-03 on" and watch the tool calls come back.

Run from the repo root:  python scripts/lab/goose_chat.py
Requires: goose installed + configured (~/.config/goose/config.yaml), and the
Light MCP server running (python -m services.light_mcp.server).
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOST, PORT = "127.0.0.1", 8791
SESSION = f"lightchat-{int(time.time())}"
GOOSE_TIMEOUT = 240  # cold model load on the first message can be slow

_lock = threading.Lock()   # goose runs one message at a time
_started = False           # first message creates the session; later ones --resume
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
_BANNER = ("__( O)>", "\\____)", "L L", "goose is ready", "starting session",
           "logging to", "working directory")


def _clean(out: str) -> str:
    out = _ANSI.sub("", out)
    lines = []
    for ln in out.splitlines():
        s = ln.strip()
        if not s:
            lines.append("")
            continue
        if s == "[exited with code 0]" or any(b in ln for b in _BANNER):
            continue
        lines.append(ln.rstrip())
    text = "\n".join(lines).strip("\n")
    # collapse 3+ blank lines
    return re.sub(r"\n{3,}", "\n\n", text) or "(no output)"


def ask_goose(message: str) -> str:
    global _started
    with _lock:
        cmd = ["goose", "run", "-n", SESSION]
        if _started:
            cmd.append("--resume")
        cmd += ["-t", message]
        try:
            proc = subprocess.run(
                cmd, cwd=str(REPO), capture_output=True, text=True, timeout=GOOSE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"(goose timed out after {GOOSE_TIMEOUT}s — the local model may still be loading; try again)"
        except FileNotFoundError:
            return "(goose is not on PATH — install it and configure ~/.config/goose/config.yaml)"
        _started = True
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr.strip() else "")
        return _clean(out)


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Goose · local agent</title><style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:#0b0f14;color:#d7e0ea}
header{padding:10px 14px;border-bottom:1px solid #1e2a36;color:#7fe0c8;font-weight:600}
header small{color:#5b6b7a;font-weight:400}
#log{padding:14px;max-width:860px;margin:0 auto}
.msg{margin:0 0 12px;white-space:pre-wrap;word-break:break-word}
.you{color:#9ad}
.you b,.bot b{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#5b6b7a;margin-bottom:2px}
.bot{background:#111823;border:1px solid #1e2a36;border-radius:8px;padding:10px 12px}
.pending{color:#7a8697;font-style:italic}
form{position:sticky;bottom:0;display:flex;gap:8px;padding:12px 14px;max-width:860px;margin:0 auto;background:#0b0f14;border-top:1px solid #1e2a36}
input{flex:1;padding:10px 12px;border:1px solid #24323f;border-radius:8px;background:#0f1620;color:#e6eef7;font:inherit}
button{padding:10px 16px;border:0;border-radius:8px;background:#1f7a63;color:#eafff8;font:inherit;font-weight:600;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
</style></head><body>
<header>Goose — local agent <small>&nbsp; qwen2.5-tools · Ollama :11434 · light_control MCP :8790</small></header>
<div id=log></div>
<form id=f><input id=m autocomplete=off placeholder="e.g. list machines, then turn machine-03 on" autofocus>
<button id=b>Send</button></form>
<script>
const log=document.getElementById('log'),f=document.getElementById('f'),m=document.getElementById('m'),b=document.getElementById('b');
function add(cls,who,txt){const d=document.createElement('div');d.className='msg '+cls;d.innerHTML='<b></b>';d.querySelector('b').textContent=who;d.appendChild(document.createTextNode(txt));log.appendChild(d);window.scrollTo(0,document.body.scrollHeight);return d;}
f.onsubmit=async e=>{e.preventDefault();const msg=m.value.trim();if(!msg)return;m.value='';b.disabled=true;m.disabled=true;add('you','you',msg);const p=add('bot pending','goose','thinking…');
try{const r=await fetch('/send',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:msg})});const j=await r.json();p.className='msg bot';p.querySelector('b').textContent='goose';p.lastChild.textContent=j.reply;}catch(err){p.className='msg bot';p.lastChild.textContent='(error: '+err+')';}
b.disabled=false;m.disabled=false;m.focus();};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/send":
            self._send(404, "not found", "text/plain")
            return
        n = int(self.headers.get("content-length", 0))
        try:
            msg = json.loads(self.rfile.read(n) or b"{}").get("message", "")
        except json.JSONDecodeError:
            msg = ""
        reply = ask_goose(msg) if msg.strip() else "(empty message)"
        self._send(200, json.dumps({"reply": reply}), "application/json")


if __name__ == "__main__":
    print(f"goose chat on http://{HOST}:{PORT}  (session {SESSION}, repo {REPO})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
