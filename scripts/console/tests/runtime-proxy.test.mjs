import { test } from 'node:test';
import assert from 'node:assert/strict';
import { feedConfig } from '../../../apps/desktop/runtime-proxy.mjs';
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
