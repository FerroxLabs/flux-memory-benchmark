"""EXPLORATORY, POST HOC, IN-SAMPLE ARM added after the main run (see PREREG-ADDENDUM-flux_temporal.md). Not part of the preregistered comparison.

flux_temporal = a router decides per question whether it is temporal; TEMPORAL questions take the stored flux_reason result, all others take the stored
flux_evidence result. No new reader or judge call is made; the only paid calls are the router calls of this file.

  route:   one deepseek-flash call per question (thinking disabled, temperature 0, max_tokens 8, prompts/flux_temporal_router_prompt.txt). The prompt
           contains ONLY the question text. Question texts are read from --src (a stored retrieved.jsonl) and are never written to any output file.
  compose: build results/.../flux_temporal/qa/answers.jsonl from router.jsonl plus the stored per-item graded outputs of flux_reason and flux_evidence.

usage (run from the kit root; route needs DEEPSEEK_API_KEY in the environment):
  python3 drivers/flux_temporal.py route   --bench lme    --src results/flux_reason/retrieved.jsonl         --out results/flux_temporal         [--smoke 5]
  python3 drivers/flux_temporal.py route   --bench locomo --src results/locomo/flux_reason/retrieved.jsonl --out results/locomo/flux_temporal [--smoke 10]
  python3 drivers/flux_temporal.py compose --bench lme    --results results
  python3 drivers/flux_temporal.py compose --bench locomo --results results/locomo
Hard rules in code: spend cap for this arm (--cap-usd, default 3, summed over the ledger), at most 2 requests in flight and 3 starts per second,
stop if more than 2% of router calls error (checked from 50 calls on). Resumable; smoke items are kept for the full run.
"""
import argparse, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ('drivers', 'runner'):
    sys.path.insert(0, os.path.join(ROOT, p))
os.environ.setdefault('READER_INFLIGHT', '2')
ARM = 'flux_temporal'
PROMPT_PATH = os.path.join(ROOT, 'prompts', 'flux_temporal_router_prompt.txt')
MAX_TOKENS, RPS, ERROR_STOP = 8, 3.0, 0.02


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def parse(text):
    """-> 'TEMPORAL' | 'OTHER' | 'UNPARSEABLE' (the last counts as OTHER)."""
    t = re.sub(r'[^A-Za-z]', '', text or '').upper()
    return t if t in ('TEMPORAL', 'OTHER') else 'UNPARSEABLE'


def router_call(question, template):
    import llm
    base = os.environ.get('READER_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    body = {'model': os.environ.get('READER_MODEL', 'deepseek-flash'), 'messages': [{'role': 'user', 'content': template.format(question=question)}],
            'temperature': 0, 'max_tokens': MAX_TOKENS, 'thinking': {'type': 'disabled'}}
    t0 = time.time()
    with llm.READER.sem:
        d = llm._post(llm.READER, base + '/chat/completions', llm._key('DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY_FILE'), body, 120)
    u = d.get('usage') or {}
    cost = llm.ds_price(u, t0)
    llm.READER.add_cost(cost)
    if 'deepseek' not in str(d.get('model', '')).lower():
        raise llm.OffModel(str(d.get('model')))
    return d['choices'][0]['message'].get('content') or '', cost


def route(a):
    import llm, ledger
    template = open(PROMPT_PATH).read()
    src = jl(a.src)
    seen = set(); src = [r for r in src if not (r['qid'] in seen or seen.add(r['qid']))]
    if a.smoke:
        step = max(1, len(src) // a.smoke); src = src[::step][:a.smoke]
    os.makedirs(a.out, exist_ok=True)
    outp = os.path.join(a.out, 'router.jsonl')
    done = {r['qid'] for r in jl(outp)}
    todo = [r for r in src if r['qid'] not in done]
    print(f'route {a.bench}: {len(done)} done, {len(todo)} to run', flush=True)
    llm.READER.rps = RPS
    lock = threading.Lock(); st = {'calls': 0, 'err': 0, 'spent': 0.0, 'stop': None}
    base_spend = sum(r['usd'] for r in ledger.read() if r.get('arm') == ARM)
    out = open(outp, 'a')

    def one(row):
        if st['stop']:
            return
        if base_spend + st['spent'] + 0.01 > a.cap_usd:
            st['stop'] = f'cap: arm spend {base_spend + st["spent"]:.4f} + 0.01 > {a.cap_usd}'; return
        rec = {'arm': ARM, 'qid': row['qid'], 'type': row['type']}
        try:
            text, cost = router_call(row['question'], template)
            rec.update(label=parse(text), cost=cost)
        except Exception as e:  # noqa: BLE001
            rec.update(label='ERROR', error=type(e).__name__ + ':' + str(e)[:60], cost=0.0)
        with lock:
            st['calls'] += 1; st['err'] += rec['label'] == 'ERROR'; st['spent'] += rec['cost']
            out.write(json.dumps(rec) + '\n'); out.flush()
            if st['calls'] >= 50 and st['err'] / st['calls'] > ERROR_STOP:
                st['stop'] = f'errors {st["err"]}/{st["calls"]} > {ERROR_STOP:.0%}'

    try:
        with ThreadPoolExecutor(2) as ex:
            list(ex.map(one, todo))
    finally:
        out.close()
        if st['spent']:
            ledger.add(ARM, 'router', st['spent'], st['calls'], bench=a.bench)
    print(f'route {a.bench}: calls={st["calls"]} errors={st["err"]} spent=${st["spent"]:.4f} stop={st["stop"]}', flush=True)
    if st['stop']:
        sys.exit(f'STOPPED: {st["stop"]}')


def compose(a):
    """Rows keep every field of the chosen stored row (local, git-ignored); routed / path / router_cost / path_cost are added. Costs: router call plus the
    chosen path's reader and judge calls (plus the pass-1 call when the path is flux_reason); the shared ingest, extraction and retrieval are not counted."""
    R = os.path.join(ROOT, a.results)
    rt = {r['qid']: r for r in jl(os.path.join(R, 'flux_temporal', 'router.jsonl'))}
    ev = {r['qid']: r for r in jl(os.path.join(R, 'flux_evidence', 'qa', 'answers.jsonl'))}
    rs = {r['qid']: r for r in jl(os.path.join(R, 'flux_reason', 'qa', 'answers.jsonl'))}
    p1 = {r['qid']: r.get('pass1_cost') or 0.0 for r in jl(os.path.join(R, 'flux_reason', 'retrieved.jsonl'))}
    assert set(rt) == set(ev) == set(rs), (len(rt), len(ev), len(rs))
    outd = os.path.join(R, 'flux_temporal', 'qa'); os.makedirs(outd, exist_ok=True)
    with open(os.path.join(outd, 'answers.jsonl'), 'w') as f:
        for q in sorted(rt):
            temporal = rt[q]['label'] == 'TEMPORAL'
            row = dict(rs[q] if temporal else ev[q])
            path_cost = (row.get('reader_cost') or 0) + (row.get('judge_cost') or 0) + (p1.get(q, 0.0) if temporal else 0.0)
            row.update(arm=ARM, routed=rt[q]['label'], path='flux_reason' if temporal else 'flux_evidence', router_cost=rt[q]['cost'], path_cost=path_cost)
            f.write(json.dumps(row) + '\n')
    print(f'compose {a.bench}: {len(rt)} items, routed TEMPORAL {sum(1 for r in rt.values() if r["label"] == "TEMPORAL")}', flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['route', 'compose'])
    ap.add_argument('--bench', choices=['lme', 'locomo'], required=True)
    ap.add_argument('--src'); ap.add_argument('--out'); ap.add_argument('--results')
    ap.add_argument('--smoke', type=int, default=0); ap.add_argument('--cap-usd', type=float, default=3.0)
    a = ap.parse_args()
    os.environ['BENCH'] = a.bench
    route(a) if a.cmd == 'route' else compose(a)


if __name__ == '__main__':
    main()
