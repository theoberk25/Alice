// Workstation-only development boundary. Secrets are never VITE_* variables.
/* global fetch, AbortSignal */
import { Buffer } from 'node:buffer';
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { URL } from 'node:url';

const SESSION_COOKIE = 'alice_web_session';
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;

function constantEqual(left, right) {
  const a = createHash('sha256').update(left).digest();
  const b = createHash('sha256').update(right).digest();
  return timingSafeEqual(a, b);
}

export function webConfig(env) {
  const username = env.ALICE_WEB_USERNAME ?? '';
  const password = env.ALICE_WEB_PASSWORD ?? '';
  const publicHost = env.ALICE_WEB_PUBLIC_HOST ?? '';
  if (!/^[A-Za-z0-9._-]{3,64}$/.test(username))
    throw new Error('ALICE_WEB_USERNAME must be 3-64 safe characters');
  if (password.length < 12 || password.length > 256)
    throw new Error('ALICE_WEB_PASSWORD must be 12-256 characters');
  if (!/^[A-Za-z0-9.-]+:\d+$/.test(publicHost))
    throw new Error('ALICE_WEB_PUBLIC_HOST must be host:port');
  return { username, password, publicHost };
}
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
  const sessions = new Map();
  const attempts = new Map();
  return {
    name: 'alice-runtime-feed',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url?.startsWith('/api/alice/')) return next();
        res.setHeader('Cache-Control', 'no-store');
        res.setHeader('Content-Type', 'application/json');
        const reply = (code, message) => {
          res.statusCode = code;
          res.end(JSON.stringify(typeof message === 'string' ? { error: message } : message));
        };
        let web = null;
        if (env.VITE_ALICE_WEB_LOGIN === 'enabled') {
          try {
            web = webConfig(env);
          } catch {
            return reply(503, 'Web dashboard authentication is not configured');
          }
        }
        const host = req.headers.host ?? '';
        const port = web?.publicHost.split(':').at(-1);
        const allowedHost = web
          ? [web.publicHost, `127.0.0.1:${port}`, `localhost:${port}`].includes(host)
          : /^(127\.0\.0\.1|localhost):\d+$/.test(host);
        if (
          !allowedHost ||
          (req.headers.origin && req.headers.origin !== `http://${host}`) ||
          (req.headers['sec-fetch-site'] &&
            !['same-origin', 'none'].includes(req.headers['sec-fetch-site']))
        )
          return reply(403, 'Same-origin dashboard access required');
        const now = Date.now();
        for (const [id, expires] of sessions) if (expires <= now) sessions.delete(id);
        const cookies = Object.fromEntries(
          (req.headers.cookie ?? '').split(';').map((part) => part.trim().split('=', 2)),
        );
        const authenticated = !web || (sessions.get(cookies[SESSION_COOKIE]) ?? 0) > now;
        if (req.url === '/api/alice/session' && req.method === 'GET')
          return reply(200, { authenticated });
        if (web && req.url === '/api/alice/logout' && req.method === 'POST') {
          if (cookies[SESSION_COOKIE]) sessions.delete(cookies[SESSION_COOKIE]);
          res.setHeader('Set-Cookie', `${SESSION_COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0`);
          return reply(200, { authenticated: false });
        }
        if (web && req.url === '/api/alice/login' && req.method === 'POST') {
          const address = req.socket.remoteAddress ?? 'unknown';
          const recent = (attempts.get(address) ?? []).filter((time) => now - time < 60_000);
          if (recent.length >= 5) return reply(429, 'Too many login attempts; wait one minute');
          attempts.set(address, [...recent, now]);
          const chunks = [];
          let size = 0;
          for await (const chunk of req) {
            size += chunk.length;
            if (size > 1024) return reply(413, 'Login payload too large');
            chunks.push(chunk);
          }
          let body;
          try {
            body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          } catch {
            return reply(400, 'Invalid login payload');
          }
          if (
            !body ||
            Object.keys(body).sort().join(',') !== 'password,username' ||
            typeof body.username !== 'string' ||
            typeof body.password !== 'string' ||
            !constantEqual(body.username, web.username) ||
            !constantEqual(body.password, web.password)
          )
            return reply(401, 'Invalid username or password');
          attempts.delete(address);
          const id = randomBytes(32).toString('hex');
          sessions.set(id, now + SESSION_TTL_MS);
          res.setHeader(
            'Set-Cookie',
            `${SESSION_COOKIE}=${id}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${SESSION_TTL_MS / 1000}`,
          );
          return reply(200, { authenticated: true });
        }
        if (!authenticated) return reply(401, 'Dashboard login required');
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
