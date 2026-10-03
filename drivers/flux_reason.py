"""EXPLORATORY ARM, added after the main run (see PREREG-ADDENDUM-flux_reason.md). Not part of the preregistered comparison.

flux_reason = a reasoning pass over the memory Flux's flux_evidence arm already retrieved, then the unchanged reader and judges.
  Pass 1 (this file): ONE deepseek-flash call per question. Input: the stored flux_evidence context for that question (no re-ingest, no
         re-retrieve) and the raw question; prompt = prompts/flux_reason_prompt.txt. Output: a short memory note.
  Pass 2: runner/qa.py, unchanged, given ONLY the note as a single 'fact' item (exactly how honcho_chat hands Honcho's answer to the reader).
Pass 1 settings mirror what the kit records for Honcho's dialectic calls (infra/dsproxy.py): deepseek-flash direct, thinking disabled,
reasoning_effort not sent. Honcho's own temperature and max_tokens are not recorded by the kit: here temperature 0, max_tokens 1500.

usage (needs DEEPSEEK_API_KEY and JUDGE_API_KEY in the environment; run from the kit root):
  python3 drivers/flux_reason.py --bench lme    --src results/flux_evidence/retrieved.jsonl         --out results/flux_reason         [--smoke 5]
  python3 drivers/flux_reason.py --bench locomo --src results/locomo/flux_evidence/retrieved.jsonl --out results/locomo/flux_reason [--smoke 10]
Resumable. Hard rules in code: spend cap for this arm (--cap-usd, default 10, summed over both benchmarks from the ledger), at most 2 requests in flight and 3 starts per
second in each stage, stop if more than 2% of pass-1 calls fail, stop between qa batches if the arm's spend plus a batch reserve would pass the cap.
"""
import argparse, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ('drivers', 'prompts', 'runner'):
    sys.path.insert(0, os.path.join(ROOT, p))
os.environ.setdefault('READER_INFLIGHT', '2'); os.environ.setdefault('JUDGE_INFLIGHT', '1'); os.environ.setdefault('READ_WORKERS', '2')
import llm  # noqa: E402
import ledger  # noqa: E402
import locomo_prompts as LP  # noqa: E402

ARM = 'flux_reason'
PROMPT_PATH = os.path.join(ROOT, 'prompts', 'flux_reason_prompt.txt')
MAX_TOKENS, PASS1_RPS, BATCH = 1500, 3.0, 200
ERROR_STOP = 0.02


def memory_block(bench, row):
    """The stored flux_evidence context as text for pass 1. LongMemEval: sessions with facts and turns (same layout as runner/qa.render, without the
    reader template). LoCoMo: prompts/locomo_prompts.render."""
    if bench == 'locomo':
        return LP.render(row['context'])
    by, facts = {}, {}
    for t in row['context']:
        if t['role'] == 'fact':
            facts.setdefault(t['session_date'], []).append(t['content']); by.setdefault(t['session_date'], [])
        else:
            by.setdefault(t['session_date'], []).append({'role': t['role'], 'content': t['content']})
    parts = []
    for i, (date, turns) in enumerate(sorted(by.items())):
        s = f'\n### Session {i + 1}:\nSession Date: {date}\n'
        if facts.get(date):
            s += 'Session Facts:\n' + ''.join(f'- {x}\n' for x in facts[date])
        if turns:
            s += f'Session Content:\n{json.dumps(turns)}\n'
        parts.append(s)
    return ''.join(parts)


def pass1_prompt(bench, row, template):
    today = f"Current date: {row['question_date']}\n" if bench == 'lme' and row.get('question_date') else ''
    return template.format(today_line=today, question=row['question'], memory=memory_block(bench, row))


def pass1_call(prompt):
    """-> {content, cost, usage}. deepseek-flash direct, thinking disabled, temperature 0."""
    base = os.environ.get('READER_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    model = os.environ.get('READER_MODEL', 'deepseek-flash')
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0, 'max_tokens': MAX_TOKENS, 'thinking': {'type': 'disabled'}}
    t0 = time.time()
    with llm.READER.sem:
        d = llm._post(llm.READER, base + '/chat/completions', llm._key('DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY_FILE'), body, 600)
    u = d.get('usage') or {}
    cost = llm.ds_price(u, t0)
    llm.READER.add_cost(cost)
    if 'deepseek' not in str(d.get('model', '')).lower():
        raise llm.OffModel(str(d.get('model')))
    return {'content': d['choices'][0]['message'].get('content') or '', 'cost': cost, 'usage': u}


def arm_spend():
    return sum(r['usd'] for r in ledger.read() if r.get('arm') == ARM)


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def pick(rows, smoke):
    if not smoke:
        return rows
    step = max(1, len(rows) // smoke)
    return rows[::step][:smoke]


def stage_pass1(a):
    template = open(PROMPT_PATH).read()
    src = [r for r in jl(a.src) if r['arm'] == 'flux_evidence']
    seen = set(); src = [r for r in src if not (r['qid'] in seen or seen.add(r['qid']))]
    os.makedirs(a.out, exist_ok=True)
    outp = os.path.join(a.out, 'retrieved.jsonl')
    done = {r['qid'] for r in jl(outp)}
    todo = [r for r in pick(src, a.smoke) if r['qid'] not in done]
    print(f'pass1 {a.bench}: {len(done)} done, {len(todo)} to run (of {len(src)})', flush=True)
    llm.READER.rps = PASS1_RPS
    lock = threading.Lock(); st = {'calls': 0, 'err': 0, 'spent': 0.0, 'stop': None}
    base_spend = arm_spend()
    out = open(outp, 'a')

    def one(row):
        if st['stop']:
            return
        if base_spend + st['spent'] + 0.03 > a.cap_usd:  # hard stop: one call costs about 1 cent
            st['stop'] = f'cap: arm spend {base_spend + st["spent"]:.4f} + 0.03 > {a.cap_usd}'; return
        rec = {'arm': ARM, 'qid': row['qid'], 'type': row['type'], 'question': row['question'], 'question_date': row['question_date'], 'answer': row['answer'],
               'abstention': row.get('abstention', False), 'n_src_context': len(row['context']), 'reasoned_from': 'flux_evidence'}
        try:
            r = pass1_call(pass1_prompt(a.bench, row, template))
            note = r['content'].strip()
            rec.update(pass1_cost=r['cost'], pass1_tokens=(r['usage'] or {}).get('completion_tokens'), pass1_empty=not note,
                       n_retrieved=1 if note else 0, n_context=1 if note else 0, search_ms=0,
                       context=[{'session_date': '', 'role': 'fact', 'content': note}] if note else [])
        except Exception as e:  # noqa: BLE001
            rec.update(pass1_error=f'{type(e).__name__}:{e}'[:160], pass1_cost=0.0, n_retrieved=0, n_context=0, search_ms=0, context=[])
        with lock:
            st['calls'] += 1; st['err'] += 'pass1_error' in rec; st['spent'] += rec['pass1_cost']
            out.write(json.dumps(rec) + '\n'); out.flush()
            if st['calls'] >= 50 and st['err'] / st['calls'] > ERROR_STOP:
                st['stop'] = f'errors {st["err"]}/{st["calls"]} > {ERROR_STOP:.0%}'

    try:
        with ThreadPoolExecutor(2) as ex:
            list(ex.map(one, todo))
    finally:
        out.close()
        if st['spent']:
            ledger.add(ARM, 'pass1', st['spent'], st['calls'], bench=a.bench)
    print(f'pass1 {a.bench}: calls={st["calls"]} errors={st["err"]} spent=${st["spent"]:.4f} stop={st["stop"]}', flush=True)
    if st['stop']:
        sys.exit(f'STOPPED: {st["stop"]}')


def qa_worker(argv):
    """Run runner/qa.py unchanged, with the gates paced so reader plus judge starts stay at or below 3 per second in total."""
    llm.READER.rps = 1.5; llm.JUDGE.rps = 1.5
    sys.argv = ['qa.py'] + argv
    import qa
    qa.main()


def stage_qa(a):
    outp = os.path.join(a.out, 'retrieved.jsonl')
    ans = os.path.join(a.out, 'qa', 'answers.jsonl')
    allrows = {r['qid']: r for r in jl(outp)}
    rows = [r for r in allrows.values() if 'pass1_error' not in r]
    if a.smoke:
        rows = rows[:a.smoke]
    n_all = len(rows)
    for k in range(0, n_all, BATCH):
        sub = rows[:k + BATCH]
        spent = arm_spend()
        reserve = 0.6
        if spent + reserve > a.cap_usd:
            sys.exit(f'STOPPED: arm spend {spent:.4f} + batch reserve {reserve} would pass {a.cap_usd}')
        inp = os.path.join(a.out, 'qa_input.jsonl')
        open(inp, 'w').write(''.join(json.dumps(r) + '\n' for r in sub))
        have = {json.loads(l)['qid'] for l in open(ans)} if os.path.exists(ans) else set()
        if all(r['qid'] in have for r in sub):
            continue
        env = dict(os.environ, BENCH=a.bench)
        cmd = [sys.executable, os.path.abspath(__file__), '--qa-worker', '--bench', a.bench, '--inputs', inp, '--arm', ARM, '--out', os.path.join(a.out, 'qa'), '--reserve', '3']
        print(f'qa {a.bench}: batch up to {len(sub)}/{n_all}, arm spend so far ${spent:.4f}', flush=True)
        rc = subprocess.call(cmd, env=env)
        recs = jl(ans)
        err = sum(1 for r in recs if 'error' in r)
        if rc != 0:
            sys.exit(f'STOPPED: qa exit {rc}')
        if len(recs) >= 50 and err / len(recs) > ERROR_STOP:
            sys.exit(f'STOPPED: qa errors {err}/{len(recs)} > {ERROR_STOP:.0%}')


def stage_finish(a):
    """Add pass-1 failures as wrong answers (never silently dropped), write the summary the analysis reads."""
    allrows = jl(os.path.join(a.out, 'retrieved.jsonl'))
    ans = os.path.join(a.out, 'qa', 'answers.jsonl')
    recs = [r for r in jl(ans) if r.get('error', '').split(':')[0] != 'pass1']
    have = {r['qid'] for r in recs}
    for r in allrows:
        if 'pass1_error' in r and r['qid'] not in have:
            recs.append({'qid': r['qid'], 'arm': ARM, 'type': r['type'], 'abstention': bool(r.get('abstention')), 'error': 'pass1:' + r['pass1_error'], 'label': False})
    with open(ans, 'w') as f:
        for r in recs:
            f.write(json.dumps(r) + '\n')
    import qa
    p1 = sum(r.get('pass1_cost', 0) for r in allrows)
    summ = {'arm': ARM, 'n': len(recs), 'expected': len(allrows), 'accuracy': round(sum(1 for r in recs if r.get('label')) / max(1, len(recs)), 4),
            'errors': sum(1 for r in recs if 'error' in r), 'reader_usd': round(sum(r.get('reader_cost', 0) or 0 for r in recs), 4),
            'judge_usd': round(sum(r.get('judge_cost', 0) or 0 for r in recs), 4), 'pass1_usd': round(p1, 4),
            'pass1_errors': sum(1 for r in allrows if 'pass1_error' in r), 'pass1_empty_notes': sum(1 for r in allrows if r.get('pass1_empty')),
            'offmodel': [], 'prompt_sha256': qa.prompt_sha(a.bench), 'bench': a.bench,
            'judge_models': sorted({r.get('judge_model') for r in recs if r.get('judge_model')})}
    json.dump(summ, open(os.path.join(a.out, 'qa', 'summary.json'), 'w'), indent=1)
    print(json.dumps(summ), flush=True)


def main():
    if '--qa-worker' in sys.argv:
        argv = [x for x in sys.argv[1:] if x != '--qa-worker']
        return qa_worker(argv)
    ap = argparse.ArgumentParser()
    ap.add_argument('--bench', choices=['lme', 'locomo'], required=True); ap.add_argument('--src', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--smoke', type=int, default=0, help='run only N evenly spaced questions (smoke); smoke items are kept for the full run')
    ap.add_argument('--cap-usd', type=float, default=10.0)
    a = ap.parse_args()
    os.environ['BENCH'] = a.bench
    stage_pass1(a)
    stage_qa(a)
    stage_finish(a)


if __name__ == '__main__':
    main()
