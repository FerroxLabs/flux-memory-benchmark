"""Letta arm: ARCHIVAL memory (the passages API), letta==0.16.8 server (pgvector), letta-client==1.11.0. One agent per haystack (hard isolation).

Adapted from the private h2h-oss letta_driver.py. Every turn is inserted as an archival passage (Letta chunks long text itself, embedding_chunk_size 300)
with tags [session_date, role]; the embedding is local bge-small through the OpenAI endpoint type. No LLM call is made at ingest or search: the agent's
llm_config points at a metering proxy started with a $0 cap, so any LLM call would fail loudly. Query: passages.search(top_k=20).
Config from the environment:
  LETTA_URLS      comma list of Letta server URLs (default http://127.0.0.1:8283)
  LETTA_LLM_URL   OpenAI-compatible URL of the $0-capped proxy (default http://127.0.0.1:18801/letta/v1)
  EMBED_URLS      local bge-small endpoints (default http://127.0.0.1:18811/v1)
Failed passage inserts are retried twice and then counted as dropped (never silent). Known: Letta rejects a turn above its 8,192-token embedding limit.
usage: letta_driver.py --units work/units_n100.jsonl --out results/letta [--procs 8] [--only ids]
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import K, load_units, row, run_units  # noqa: E402

SERVERS = os.environ.get('LETTA_URLS', 'http://127.0.0.1:8283').split(',')
LLM = {'model': 'deepseek-flash', 'model_endpoint_type': 'openai', 'model_endpoint': os.environ.get('LETTA_LLM_URL', 'http://127.0.0.1:18801/letta/v1'),
       'context_window': 64000}
EMBED = os.environ.get('EMBED_URLS', 'http://127.0.0.1:18811/v1').split(',')


def one(u):
    from letta_client import Letta
    c = Letta(base_url=SERVERS[hash(u['unit_id']) % len(SERVERS)], timeout=300)
    emb = {'embedding_endpoint_type': 'openai', 'embedding_endpoint': EMBED[hash(u['unit_id']) % len(EMBED)].rstrip('/'),
           'embedding_model': 'bge-small-en-v1.5', 'embedding_dim': 384, 'embedding_chunk_size': 300}
    a = c.agents.create(name=f"h2h-{u['unit_id']}", llm_config=LLM, embedding_config=emb,
                        memory_blocks=[{'label': 'persona', 'value': 'benchmark archival store'}])
    t0 = time.time(); ok = dropped = stored = 0; errors = []
    for s in u['sessions']:
        for t in s['turns']:
            if not t['content'].strip():
                continue
            for attempt in range(3):
                try:
                    p = c.agents.passages.create(agent_id=a.id, text=t['content'], tags=[s['date'], t['role']])
                    stored += len(p) if isinstance(p, list) else 1; ok += 1
                    break
                except Exception as e:  # noqa: BLE001
                    if attempt == 2:
                        dropped += 1; errors.append(f'{type(e).__name__}: {e}'[:160])
                    time.sleep(2 * (attempt + 1))
    ingest_s = time.time() - t0
    rows = []
    for q in u['questions']:
        t1 = time.time()
        sr = c.agents.passages.search(agent_id=a.id, query=q['question'], top_k=K)
        ms = (time.time() - t1) * 1e3
        res = getattr(sr, 'results', None) or []
        items = [{'content': x.content, 'session_date': (x.tags or [''])[0], 'role': (x.tags or ['', 'user'])[1] if len(x.tags or []) > 1 else 'user'}
                 for x in res if x.content]
        rows.append(row('letta', q, items, ms))
    return {'unit_id': u['unit_id'], 'rows': rows, 'ingest': {'items_total': ok + dropped, 'items_dropped': dropped, 'passages_stored': stored,
                                                              'seconds': round(ingest_s, 1), 'llm_usd': 0.0, 'errors': errors[:5], 'agent': a.id}}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--procs', type=int, default=8); ap.add_argument('--only', default='')
    a = ap.parse_args()
    run_units(one, load_units(a.units, a.only.split(',') if a.only else None), a.out, a.procs)
