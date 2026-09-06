import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import { Readable } from 'node:stream';
import { feedConfig, runtimeProxy, webConfig } from '../../../apps/desktop/runtime-proxy.mjs';

function request(handler, { method = 'GET', url, cookie = '', body = '' }) {
  const req = Readable.from(body ? [Buffer.from(body)] : []);
  req.method = method;
  req.url = url;
  req.headers = { host: '192.168.50.50:1420', cookie };
  req.socket = { remoteAddress: '192.168.50.51' };
  return new Promise((resolve) => {
    const headers = {};
    const res = {
      statusCode: 200,
      setHeader(name, value) { headers[name.toLowerCase()] = value; },
      end(value) { resolve({ status: this.statusCode, headers, body: JSON.parse(value) }); },
    };
    handler(req, res, () => resolve({ status: 404, headers, body: {} }));
  });
}

function webHandler() {
  let handler;
  runtimeProxy({
    VITE_ALICE_WEB_LOGIN: 'enabled',
    ALICE_WEB_USERNAME: 'technician',
    ALICE_WEB_PASSWORD: 'a-long-demo-password',
    ALICE_WEB_PUBLIC_HOST: '192.168.50.50:1420',
  }).configureServer({ middlewares: { use(value) { handler = value; } } });
  return handler;
}
test('bridge configuration refuses LAN, URL credentials, paths, weak tokens and non-HTTP URLs', () => {
  for (const url of [
    'http://192.168.1.2:8787',
    'https://127.0.0.1:8787',
    'http://user@127.0.0.1:8787',
    'http://127.0.0.1:8787/request',
  ])
    assert.throws(() => feedConfig(url, 'x'.repeat(32)));
  assert.throws(() => feedConfig('http://127.0.0.1:8787', ''));
  assert.equal(feedConfig('http://127.0.0.1:8787', 'x'.repeat(32)).url, 'http://127.0.0.1:8787');
});
test('LAN web credentials and the advertised host are explicit server-only configuration', () => {
  assert.deepEqual(
    webConfig({
      ALICE_WEB_USERNAME: 'technician',
      ALICE_WEB_PASSWORD: 'a-long-demo-password',
      ALICE_WEB_PUBLIC_HOST: '192.168.50.50:1420',
    }),
    {
      username: 'technician',
      password: 'a-long-demo-password',
      publicHost: '192.168.50.50:1420',
    },
  );
  assert.throws(() => webConfig({}));
  assert.throws(() =>
    webConfig({
      ALICE_WEB_USERNAME: 'technician',
      ALICE_WEB_PASSWORD: 'short',
      ALICE_WEB_PUBLIC_HOST: '192.168.50.50:1420',
    }),
  );
});

test('web session survives a session probe and logout invalidates it', async () => {
  const handler = webHandler();
  const initial = await request(handler, { url: '/api/alice/session' });
  assert.deepEqual(initial.body, { authenticated: false });
  const login = await request(handler, {
    method: 'POST',
    url: '/api/alice/login',
    body: JSON.stringify({ username: 'technician', password: 'a-long-demo-password' }),
  });
  assert.equal(login.status, 200);
  assert.deepEqual(login.body, { authenticated: true });
  const cookie = login.headers['set-cookie'].split(';', 1)[0];
  const active = await request(handler, { url: '/api/alice/session', cookie });
  assert.deepEqual(active.body, { authenticated: true });
  const logout = await request(handler, { method: 'POST', url: '/api/alice/logout', cookie });
  assert.deepEqual(logout.body, { authenticated: false });
  const ended = await request(handler, { url: '/api/alice/session', cookie });
  assert.deepEqual(ended.body, { authenticated: false });
});
