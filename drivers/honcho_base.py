"""Honcho v3.2.2 driver (REST, no SDK; our code only, none of Honcho's). Adapted from the private honcho_driver.py (2026-10-02).
Per unit: workspace (isolation) -> peers -> sessions/messages with created_at = session date -> wait for the deriver queue to drain
-> per question: retrieval arm (ctx) and/or dialectic arm (chat) -> rows in the common row format (arms honcho_retrieval / honcho_chat).
Entry points: drivers/honcho_retrieval.py (ctx) and drivers/honcho_chat.py (chat). Run retrieval first with --arms ctx,chat to share one ingest;
honcho_chat.py --reuse-workspaces then answers from the already-ingested workspaces without paying for a second ingest.
Config from the environment: HONCHO_API (default http://127.0.0.1:18900/v3), DSPROXY_STATS (default http://127.0.0.1:18901/stats).
Cost per haystack (llm_usd) is the metering-proxy cost delta across the ingest, exact only at --conc 1 (the default).
usage: honcho_*.py --units U.jsonl --out DIR [--arms ctx,chat] [--conc 1] [--only ids] [--ingest-only] [--reuse-workspaces]"""
DEFAULT_ARMS = 'ctx,chat'
import argparse, asyncio, json, os, re, sys, time
from datetime import datetime, timedelta, timezone
import httpx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cap, K, ledger_add  # noqa: E402,F401

API = os.environ.get('HONCHO_API', 'http://127.0.0.1:18900/v3')
PROXY_STATS = os.environ.get('DSPROXY_STATS', 'http://127.0.0.1:18901/stats')
PER_PEER = 9


def slug(s):
    return re.sub(r'[^A-Za-z0-9_-]', '_', s)[:100]


def parse_date(d):
    return datetime.strptime(d.split(' (')[0] + ' ' + d.split(') ')[1], '%Y/%m/%d %H:%M').replace(tzinfo=timezone.utc)


def fmt_date(dt):
    return dt.strftime('%Y/%m/%d (%a) %H:%M')


TS = re.compile(r'^\s*\[?(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::\d{2})?[^\]]*\]?\s*(.*)$')


def parse_repr(md):
    """Honcho's representation markdown -> [(session_date|'', text)] in the order Honcho returned them (explicit/deductive/etc)."""
    out = []
    for ln in md.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#') or ln.startswith('Premises') or ln.startswith('- ') or ln.startswith('**'):
            continue
        m = TS.match(ln)
        if m:
            out.append((fmt_date(datetime.strptime(m.group(1) + ' ' + m.group(2), '%Y-%m-%d %H:%M')), ln))
        else:
            out.append(('', ln))
    return out


async def req(c, method, path, **kw):
    for i in range(3):
        try:
            r = await c.request(method, API + path, timeout=kw.pop('timeout', 300), **kw)
            if r.status_code < 500:
                return r
        except httpx.HTTPError as e:  # noqa: BLE001
            r = None
        await asyncio.sleep(2 * (i + 1))
    raise RuntimeError(f'{method} {path} failed')


async def proxy_cost(c):
    try:
        return (await c.get(PROXY_STATS, timeout=10)).json()
    except Exception:  # noqa: BLE001
        return {}


async def ingest(c, u):
    ws = slug(u['unit_id'])
    t0 = time.time(); errors = []; nmsg = 0
    r = await req(c, 'POST', '/workspaces', json={'id': ws}); assert r.status_code in (200, 201), r.text
    speakers = []
    for s in u['sessions']:
        for t in s['turns']:
            if t['role'] not in speakers:
                speakers.append(t['role'])
    pid = {sp: slug(sp) for sp in speakers}
    for sp in speakers:
        r = await req(c, 'POST', f'/workspaces/{ws}/peers', json={'id': pid[sp]}); assert r.status_code in (200, 201), r.text
    for s in sorted(u['sessions'], key=lambda s: parse_date(s['date'])):
        sid = slug(s['session_id']); base = parse_date(s['date'])
        r = await req(c, 'POST', f'/workspaces/{ws}/sessions', json={'id': sid, 'peers': {pid[p]: {} for p in {t['role'] for t in s['turns']}}})
        assert r.status_code in (200, 201), r.text
        msgs = [{'peer_id': pid[t['role']], 'content': t['content'], 'created_at': (base + timedelta(milliseconds=i)).isoformat()}
                for i, t in enumerate(x for x in s['turns'] if x['content'].strip())]
        for i in range(0, len(msgs), 100):
            r = await req(c, 'POST', f'/workspaces/{ws}/sessions/{sid}/messages', json={'messages': msgs[i:i + 100]})
            if r.status_code not in (200, 201):
                errors.append(f'{sid}: {r.status_code} {r.text[:120]}')
            else:
                nmsg += len(msgs[i:i + 100])
    t_posted = time.time() - t0
    quiet = 0; deadline = time.time() + 45 * 60; st = {}
    while time.time() < deadline:
        r = await req(c, 'GET', f'/workspaces/{ws}/queue/status'); st = r.json()
        if st.get('pending_work_units', 1) == 0 and st.get('in_progress_work_units', 1) == 0:
            quiet += 1
            if quiet >= 3:
                break
        else:
            quiet = 0
        await asyncio.sleep(3)
    else:
        errors.append('queue drain timeout 45 min')
    wall = time.time() - t0
    r = await req(c, 'POST', f'/workspaces/{ws}/conclusions/list', json={'filters': {}}, params={'size': 1})
    nconc = (r.json() or {}).get('total') if r.status_code == 200 else None
    return ws, pid, {'unit_id': u['unit_id'], 'sessions': len(u['sessions']), 'messages_posted': nmsg, 'post_s': round(t_posted, 1),
                     'wall_s': round(wall, 1), 'conclusions': nconc, 'queue': {k: st.get(k) for k in ('total_work_units', 'completed_work_units', 'pending_work_units', 'in_progress_work_units')},
                     'errors': errors[:6]}


async def retrieve(c, ws, pid, q, arms):
    out = {}
    if 'ctx' in arms:
        t1 = time.time(); items = []; cards = []; raws = []
        per = []
        for sp, p in pid.items():
            r = await req(c, 'GET', f'/workspaces/{ws}/peers/{p}/context',
                          params={'target': p, 'search_query': q['question'], 'search_top_k': PER_PEER, 'max_conclusions': PER_PEER,
                                  'include_most_frequent': 'false'})
            if r.status_code != 200:
                raws.append(f'{r.status_code}'); continue
            j = r.json(); raws.append(len(j.get('representation') or ''))
            per.append([{'content': t, 'role': 'fact', 'session_date': d} for d, t in parse_repr(j.get('representation') or '')][:PER_PEER])
            if j.get('peer_card'):
                cards.append({'content': f'Peer card ({sp}): ' + '; '.join(j['peer_card']), 'role': 'fact', 'session_date': ''})
        for i in range(PER_PEER):  # interleave peers
            for lst in per:
                if i < len(lst):
                    items.append(lst[i])
        out['ctx'] = (items + cards, (time.time() - t1) * 1e3, {'repr_chars': raws})
    if 'chat' in arms:
        t1 = time.time()
        r = await req(c, 'POST', f'/workspaces/{ws}/chat', json={'query': q['question'], 'reasoning_level': 'low'}, timeout=600)
        txt = (r.json().get('content') or '') if r.status_code == 200 else ''
        out['chat'] = ([{'content': txt, 'role': 'fact', 'session_date': ''}] if txt.strip() else [], (time.time() - t1) * 1e3,
                       {'status': r.status_code})
    return out


def mkrow(arm, q, items, ms, extra):
    ctx = cap(items)
    return {'arm': arm, 'qid': q['qid'], 'type': q['type'], 'question': q['question'], 'question_date': q['question_date'], 'answer': q['answer'],
            'abstention': q.get('abstention', False), 'n_retrieved': len(items), 'n_context': len(ctx), 'search_ms': round(ms, 1),
            'context': [{'session_date': it.get('session_date') or '', 'role': it.get('role', 'user'), 'content': it['content']} for it in ctx], **extra}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True); ap.add_argument('--arms', default=DEFAULT_ARMS)
    ap.add_argument('--conc', type=int, default=1); ap.add_argument('--only', default=''); ap.add_argument('--ingest-only', action='store_true'); ap.add_argument('--reuse-workspaces', action='store_true')
    a = ap.parse_args(); arms = a.arms.split(',')
    units = [json.loads(l) for l in open(a.units)]
    if a.only:
        units = [u for u in units if u['unit_id'] in set(a.only.split(','))]
    os.makedirs(a.out, exist_ok=True)
    done = set()
    sp = os.path.join(a.out, 'units.jsonl')
    if os.path.exists(sp):
        done = {json.loads(l)['unit_id'] for l in open(sp)}
    units = [u for u in units if u['unit_id'] not in done]
    sem = asyncio.Semaphore(a.conc); lock = asyncio.Lock()
    limits = httpx.Limits(max_connections=64)
    async with httpx.AsyncClient(limits=limits) as c:
        async def one(u):
            async with sem:
                try:
                    if a.reuse_workspaces:  # chat is workspace-level, so the deterministic workspace id is enough
                        ws, pid, st = slug(u['unit_id']), {}, {'unit_id': u['unit_id'], 'reused_workspace': True, 'errors': []}
                        assert 'ctx' not in arms, 'retrieval needs the peer map; ingest in the same run'
                    else:
                        c0 = await proxy_cost(c)
                        ws, pid, st = await ingest(c, u)
                        c1 = await proxy_cost(c)
                        st['llm_usd'] = round(c1.get('cost', 0) - c0.get('cost', 0), 5)  # exact only when conc=1
                        st['llm_calls'] = c1.get('calls', 0) - c0.get('calls', 0)
                        st['seconds'] = st['wall_s']
                        st['items_total'] = st['messages_posted'] + len(st['errors']); st['items_dropped'] = len(st['errors'])
                    if st.get('llm_usd'):
                        ledger_add(os.path.basename(os.path.normpath(a.out)), 'ingest', st['llm_usd'])
                    q0 = (await proxy_cost(c)).get('cost', 0)
                    rows = {x: [] for x in arms}
                    if not a.ingest_only:
                        for q in u['questions']:
                            res = await retrieve(c, ws, pid, q, arms)
                            for arm, (items, ms, extra) in res.items():
                                rows[arm].append(mkrow({'ctx': 'honcho_retrieval', 'chat': 'honcho_chat'}[arm], q, items, ms, extra))
                    q_usd = (await proxy_cost(c)).get('cost', 0) - q0  # retrieval and dialectic calls (exact only at --conc 1)
                    if q_usd > 0:
                        ledger_add(os.path.basename(os.path.normpath(a.out)), 'query', q_usd)
                    async with lock:
                        for arm, rs in rows.items():
                            with open(os.path.join(a.out, 'retrieved.jsonl'), 'a') as f:
                                for r in rs:
                                    f.write(json.dumps(r) + '\n')
                        open(sp, 'a').write(json.dumps({**st, 'ingest': st, 'error': None}) + '\n')  # flat fields for runner/ledger.py, nested 'ingest' for analysis/analyze.py
                    print('done', u['unit_id'], st.get('wall_s'), st.get('conclusions'), st['errors'][:1], flush=True)
                except Exception as e:  # noqa: BLE001
                    print('FAILED', u['unit_id'], repr(e)[:300], flush=True)
        await asyncio.gather(*(one(u) for u in units))


def run(default_arms):
    global DEFAULT_ARMS
    DEFAULT_ARMS = default_arms
    asyncio.run(main())
