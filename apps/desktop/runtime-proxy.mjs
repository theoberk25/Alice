// Workstation-only development boundary. Secrets are never VITE_* variables.
/* global fetch, AbortSignal */
import { Buffer } from 'node:buffer';
import { URL } from 'node:url';
export function feedConfig(url, token) {
  const parsed = new URL(url);
  if (
    parsed.protocol !== 'http:' ||
    !['127.0.0.1', '[::1]'].includes(parsed.hostname) ||
    !parsed.port ||
    parsed.pathname !== '/' ||
    parsed.search ||
    parsed.hash ||
    parsed.username ||
    parsed.password
  )
    throw new Error('ALICE_FEED_URL must be an explicit loopback HTTP base URL');
  if (!token || token.length < 32 || !/^[\x21-\x7e]+$/.test(token))
    throw new Error('Configure ALICE_FEED_TOKEN outside the renderer');
  return { url: parsed.origin, token };
}
export function runtimeProxy(env) {
  return {
    name: 'alice-runtime-feed',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url?.startsWith('/api/alice/')) return next();
        res.setHeader('Cache-Control', 'no-store');
        res.setHeader('Content-Type', 'application/json');
        const reply = (code, message) => {
          res.statusCode = code;
          res.end(JSON.stringify({ error: message }));
        };
        const host = req.headers.host ?? '';
        if (
          !/^(127\.0\.0\.1|localhost):\d+$/.test(host) ||
          (req.headers.origin && req.headers.origin !== `http://${host}`) ||
          (req.headers['sec-fetch-site'] &&
            !['same-origin', 'none'].includes(req.headers['sec-fetch-site']))
        )
          return reply(403, 'Same-origin workstation access required');
        if (req.method !== 'GET' || !/^\/api\/alice\/events\?after=\d+$/.test(req.url))
          return reply(400, 'Read-only events cursor required');
        let config;
        try {
          config = feedConfig(env.ALICE_FEED_URL, env.ALICE_FEED_TOKEN);
        } catch {
          return reply(503, 'Runtime bridge not configured; no simulation fallback');
        }
        try {
          const response = await fetch(`${config.url}${req.url.replace('/api/alice', '')}`, {
            headers: { Authorization: `Bearer ${config.token}` },
            redirect: 'error',
            signal: AbortSignal.timeout(6500),
          });
          const chunks = [];
          let size = 0;
          for await (const chunk of response.body) {
            size += chunk.length;
            if (size > 16 * 1024 * 1024) throw new Error('Feed too large');
            chunks.push(Buffer.from(chunk));
          }
          res.statusCode = response.status;
          res.end(Buffer.concat(chunks));
        } catch {
          reply(502, 'Runtime bridge unavailable; history retained');
        }
      });
    },
  };
}
