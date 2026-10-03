"""mem0 OSS arm (mem0ai==2.2.1, additive extraction), one isolated store per haystack.

Adapted from the private h2h-oss mem0_driver.py. Documented default path: one Memory per unit (local on-disk Qdrant + history DB in a private dir);
ingest = one add() per session with role-tagged messages and metadata.session_date; query = search(question, filters={'user_id': unit}, top_k=20).
(The OSS SDK rejects a timestamp= argument, so the session date rides in metadata.)
Config from the environment:
  MEM0_LLM_BASE_URL    mem0's internal LLM, an OpenAI-compatible URL. Default http://127.0.0.1:18800 -> per-unit metering proxy path (infra/dsproxy.py) to DeepSeek direct.
  MEM0_LLM_MODEL       default deepseek-flash
  EMBED_URLS           comma list of local bge-small OpenAI-compatible endpoints (infra/embed_server.py), default http://127.0.0.1:18811/v1
  DSPROXY_STATS        default http://127.0.0.1:18800/stats   (per-unit cost = /stats?tag=mem0__<unit>)
  MEM0_TMP             scratch dir for stores (default /tmp/mem0-h2h)
A failed add() is retried once and then counted as dropped (never silent).
usage: mem0_driver.py --units work/units_n100.jsonl --out results/mem0 [--procs 8] [--only ids]
"""
import argparse, json, os, shutil, sys, tempfile, time, urllib.request
os.environ['MEM0_TELEMETRY'] = 'False'  # telemetry opens a shared ~/.mem0 dir (lock clash across units)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import K, load_units, row, run_units  # noqa: E402

PROXY = os.environ.get('MEM0_LLM_BASE_URL', 'http://127.0.0.1:18800').rstrip('/')
STATS = os.environ.get('DSPROXY_STATS', 'http://127.0.0.1:18800/stats')
EMBED = os.environ.get('EMBED_URLS', 'http://127.0.0.1:18811/v1').split(',')
TMP = os.environ.get('MEM0_TMP', '/tmp/mem0-h2h')


def tag_cost(tag):
    try:
        return json.load(urllib.request.urlopen(f'{STATS}?tag={tag}', timeout=10))['cost']
    except Exception:  # noqa: BLE001
        return None


def one(u):
    import logging
    logging.disable(logging.WARNING)
    from mem0 import Memory
    os.makedirs(TMP, exist_ok=True)
    d = tempfile.mkdtemp(prefix=f"mem0-{u['unit_id'][:12]}-", dir=TMP)
    os.environ['MEM0_DIR'] = d
    tag = 'mem0__' + u['unit_id']
    cfg = {'vector_store': {'provider': 'qdrant', 'config': {'path': os.path.join(d, 'qdrant'), 'on_disk': True,
                                                              'collection_name': 'h2h', 'embedding_model_dims': 384}},
           'llm': {'provider': 'openai', 'config': {'model': os.environ.get('MEM0_LLM_MODEL', 'deepseek-flash'), 'api_key': 'proxy',
                                                     'openai_base_url': f'{PROXY}/{tag}/v1', 'temperature': 0, 'max_tokens': 8000}},
           'embedder': {'provider': 'openai', 'config': {'model': 'bge-small-en-v1.5', 'api_key': 'local', 'embedding_dims': 384,
                                                          'openai_base_url': EMBED[hash(u['unit_id']) % len(EMBED)]}},
           'history_db_path': os.path.join(d, 'history.db')}
    try:
        mem = Memory.from_config(cfg)
        c0 = tag_cost(tag) or 0.0
        t0 = time.time(); ok = dropped = added = 0; errors = []
        for s in u['sessions']:
            msgs = [{'role': t['role'] if t['role'] in ('user', 'assistant') else 'user', 'content': t['content']}
                    for t in s['turns'] if t['content'].strip()]
            if not msgs:
                continue
            for attempt in range(2):
                try:
                    r = mem.add(msgs, user_id=u['unit_id'], metadata={'session_date': s['date']})
                    added += len(r.get('results', []) if isinstance(r, dict) else r); ok += 1
                    break
                except Exception as e:  # noqa: BLE001
                    if attempt == 1:
                        dropped += 1; errors.append(f'{type(e).__name__}: {e}'[:160])
                    time.sleep(3 * (attempt + 1))
        ingest_s = time.time() - t0
        c1 = tag_cost(tag)
        stored = len((mem.get_all(filters={'user_id': u['unit_id']}, top_k=100000) or {}).get('results', []))
        rows = []
        for q in u['questions']:
            t1 = time.time()
            res = mem.search(q['question'], filters={'user_id': u['unit_id']}, top_k=K)
            ms = (time.time() - t1) * 1e3
            items = [{'content': x.get('memory', ''), 'role': 'fact',
                      'session_date': (x.get('metadata') or {}).get('session_date') or x.get('session_date') or ''}
                     for x in (res.get('results', []) if isinstance(res, dict) else res) if x.get('memory')]
            rows.append(row('mem0', q, items, ms))
        return {'unit_id': u['unit_id'], 'rows': rows,
                'ingest': {'sessions': len(u['sessions']), 'sessions_ok': ok, 'items_dropped': dropped, 'items_total': ok + dropped,
                           'memories_added': added, 'memories_stored': stored, 'seconds': round(ingest_s, 1),
                           'llm_usd': round(c1 - c0, 6) if c1 is not None else None, 'errors': errors[:5]}}
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--procs', type=int, default=8); ap.add_argument('--only', default='')
    a = ap.parse_args()
    run_units(one, load_units(a.units, a.only.split(',') if a.only else None), a.out, a.procs)
