// Friday Deploy leaderboard API (Cloudflare Worker + D1).
// Every request must carry Telegram WebApp initData, which is verified with the bot token
// (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).

const MAX_AGE_SEC = 24 * 60 * 60;   // reject initData older than a day
const MAX_SCORE = 200000;           // sanity cap
// One leaderboard table and one scoring-rate cap per game. Table names come only from this map, never from the request.
const GAMES = { deploy: { table: 'scores', rate: 400 }, bots: { table: 'scores_bots', rate: 1500 } };
const TOP_N = 20;

const enc = new TextEncoder();

async function hmac(key, data) {
  const k = await crypto.subtle.importKey('raw', typeof key === 'string' ? enc.encode(key) : key,
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', k, enc.encode(data)));
}
const hex = buf => [...buf].map(b => b.toString(16).padStart(2, '0')).join('');

async function verifyInitData(initData, botToken) {
  if (!initData || !botToken) return null;
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  if (!hash) return null;
  params.delete('hash');
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${k}=${v}`).join('\n');
  const secret = await hmac('WebAppData', botToken);
  const calc = hex(await hmac(secret, dataCheckString));
  if (calc.length !== hash.length) return null;
  let diff = 0;
  for (let i = 0; i < calc.length; i++) diff |= calc.charCodeAt(i) ^ hash.charCodeAt(i);
  if (diff !== 0) return null;
  const authDate = Number(params.get('auth_date'));
  if (!authDate || Date.now() / 1000 - authDate > MAX_AGE_SEC) return null;
  try { return JSON.parse(params.get('user') || 'null'); } catch { return null; }
}

function cors(env) {
  return {
    'Access-Control-Allow-Origin': env.ALLOWED_ORIGIN || '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Init-Data',
    'Access-Control-Max-Age': '86400',
  };
}
const json = (env, body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...cors(env) } });

async function board(env, userId, table) {
  const { results } = await env.DB.prepare(
    `SELECT user_id, name, username, best FROM ${table} ORDER BY best DESC, updated_at ASC LIMIT ?`
  ).bind(TOP_N).all();
  let me = null;
  if (userId) {
    me = await env.DB.prepare(
      `SELECT s.best, (SELECT COUNT(*) FROM ${table} o WHERE o.best > s.best) + 1 AS rank
       FROM ${table} s WHERE s.user_id = ?`
    ).bind(userId).first();
  }
  return {
    top: results.map((r, i) => ({ rank: i + 1, name: r.name, username: r.username, best: r.best, me: r.user_id === userId })),
    me,
  };
}

export default {
  async fetch(req, env) {
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(env) });
    const url = new URL(req.url);

    const initData = req.headers.get('X-Init-Data');
    const user = await verifyInitData(initData, env.BOT_TOKEN);
    if (!user || !user.id) return json(env, { error: 'unauthorized' }, 401);

    if (req.method === 'GET' && url.pathname === '/top') {
      const game = GAMES[url.searchParams.get('game') || 'deploy'];
      if (!game) return json(env, { error: 'unknown game' }, 400);
      return json(env, await board(env, user.id, game.table));
    }

    if (req.method === 'POST' && url.pathname === '/score') {
      let body;
      try { body = await req.json(); } catch { return json(env, { error: 'bad json' }, 400); }
      const game = GAMES[body.game || 'deploy'];
      if (!game) return json(env, { error: 'unknown game' }, 400);
      const score = Math.floor(Number(body.score));
      const duration = Number(body.duration);
      if (!Number.isFinite(score) || score < 0 || score > MAX_SCORE) return json(env, { error: 'bad score' }, 400);
      if (!Number.isFinite(duration) || duration <= 0 || score > duration * game.rate + 50)
        return json(env, { error: 'implausible score' }, 400);

      const name = [user.first_name, user.last_name].filter(Boolean).join(' ').slice(0, 64) || 'Anonymous';
      await env.DB.prepare(
        `INSERT INTO ${game.table} (user_id, name, username, best, games, updated_at) VALUES (?1, ?2, ?3, ?4, 1, ?5)
         ON CONFLICT(user_id) DO UPDATE SET
           name = excluded.name, username = excluded.username, games = games + 1,
           updated_at = CASE WHEN excluded.best > best THEN excluded.updated_at ELSE updated_at END,
           best = MAX(best, excluded.best)`
      ).bind(user.id, name, user.username || null, score, Date.now()).run();
      return json(env, await board(env, user.id, game.table));
    }

    return json(env, { error: 'not found' }, 404);
  },
};
