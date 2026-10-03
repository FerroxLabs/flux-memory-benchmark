"""Metering reverse proxy: Honcho -> DeepSeek direct (api.deepseek.com) only. 127.0.0.1 only.
Path /<tag>/v1/chat/completions (tag = Honcho module, for the spend ledger). <=8 in flight, <=2 retries on 429/5xx,
thinking disabled (injected), non-stream. Cost = DeepSeek list price by call time (peak Mon-Fri 01-04 & 06-10 UTC x1 else x0.5:
$0.006 hit / $0.30 miss / $1.20 out per 1M). A reply whose model is not deepseek-* is a refused call. Key read from a file, never logged.
Adapted from the private honcho-20261002 infra: key from $DEEPSEEK_API_KEY (or the file named by $DEEPSEEK_API_KEY_FILE) instead of a key-file
argument, and per-tag cost totals so concurrent mem0 units still get an exact per-unit cost: GET /stats?tag=<tag> (no tag = grand total).
usage: dsproxy.py <port> <logfile> [max_usd]   (max_usd: hard stop, refuses further calls once the logged cost passes it; 0 = refuse every call)"""
import asyncio, json, os, sys, time
from datetime import datetime, timezone
import aiohttp
from aiohttp import web

PORT, LOG = int(sys.argv[1]), sys.argv[2]
MAX_USD = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9
KEY = (os.environ.get('DEEPSEEK_API_KEY') or open(os.path.expanduser(os.environ['DEEPSEEK_API_KEY_FILE'])).read()).strip()
SEM = asyncio.Semaphore(8)
TOTAL = [0.0, 0]
BY_TAG = {}


def price(u, t):
    d = datetime.fromtimestamp(t, timezone.utc)
    k = 1.0 if d.weekday() < 5 and (1 <= d.hour < 4 or 6 <= d.hour < 10) else 0.5
    hit = u.get('prompt_cache_hit_tokens', 0) or 0
    miss = u.get('prompt_cache_miss_tokens', (u.get('prompt_tokens', 0) or 0) - hit) or 0
    return k * (hit * 0.006 + miss * 0.30 + (u.get('completion_tokens', 0) or 0) * 1.20) / 1e6


async def handle(req):
    tag = req.match_info['tag']
    if TOTAL[0] >= MAX_USD:  # note: with max_usd=0 the first call is refused too
        return web.json_response({'error': 'proxy spend cap reached'}, status=402)
    body = await req.json()
    if body.get('stream'):
        return web.json_response({'error': 'stream unsupported by metering proxy'}, status=400)
    body['model'] = 'deepseek-flash'
    body['thinking'] = {'type': 'disabled'}
    body.pop('reasoning_effort', None)
    if 'max_completion_tokens' in body:
        body['max_tokens'] = body.pop('max_completion_tokens')
    async with SEM:
        for i in range(3):
            t0 = time.time()
            try:
                async with req.app['s'].post('https://api.deepseek.com/chat/completions', json=body,
                                              headers={'Authorization': 'Bearer ' + KEY}) as r:
                    status, data = r.status, await r.read()
            except Exception as e:  # noqa: BLE001
                status, data = 599, str(e).encode()
            if status == 200 or (status not in (429, 599) and status < 500) or i == 2:
                break
            await asyncio.sleep(2 * 2 ** i)
    rec = {'ts': time.time(), 'tag': tag, 'status': status, 'dt': round(time.time() - t0, 2)}
    if status == 200:
        d = json.loads(data); u = d.get('usage') or {}
        if 'deepseek' not in str(d.get('model', '')).lower():
            rec['offmodel'] = d.get('model'); status = 502
        c = price(u, t0); TOTAL[0] += c; TOTAL[1] += 1
        t = BY_TAG.setdefault(tag, [0.0, 0]); t[0] += c; t[1] += 1
        rec.update(cost=round(c, 7), pt=u.get('prompt_tokens'), ct=u.get('completion_tokens'), hit=u.get('prompt_cache_hit_tokens'))
    open(LOG, 'a').write(json.dumps(rec) + '\n')
    return web.Response(status=status, body=data, content_type='application/json')


async def stats(req):
    tag = req.query.get('tag')
    c, n = BY_TAG.get(tag, [0.0, 0]) if tag else TOTAL
    return web.json_response({'cost': round(c, 6), 'calls': n})


async def init(app):
    app['s'] = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600))


app = web.Application(client_max_size=64 * 1024 * 1024)
app.on_startup.append(init)
app.add_routes([web.post('/{tag}/v1/chat/completions', handle), web.get('/stats', stats)])
web.run_app(app, host='127.0.0.1', port=PORT, print=None)
