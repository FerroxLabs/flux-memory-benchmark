"""Reader + grader over a driver's retrieved.jsonl. One run per arm, resumable (finished rows are kept, only errors are retried).

usage: python3 runner/qa.py --inputs results/<arm>/retrieved.jsonl --arm <arm-name-in-rows> --out results/<arm>/qa [--reserve USD] [--bench lme|locomo]
--bench locomo: reader and scoring from prompts/locomo_prompts.py (official LoCoMo reader prompts; categories 1 to 4 graded by the published mem0/Zep
judge prompt on the same judge model; category 5 scored by the official string rule, no judge call). Spend is booked under bench 'locomo'.
Writes <out>/answers.jsonl (one row per question: hypothesis, label, costs, judge model) and <out>/summary.json.
label = the grade used in the analysis: the official LongMemEval judge prompt on JUDGE_MODEL for every type except
single-session-preference, which is graded by PREF_JUDGE_MODEL (decision 14). Errors and empty answers score wrong.
Adapted from the private qa_lme.py (render() is unchanged); the spend ledger is runner/ledger.py.
"""
import argparse, hashlib, json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'drivers')); sys.path.insert(0, os.path.join(ROOT, 'prompts')); sys.path.insert(0, os.path.join(ROOT, 'runner'))
import llm  # noqa: E402
import ledger  # noqa: E402
from lme_prompts import READER_COT, READER_FACTS_COT, anscheck_prompt  # noqa: E402
import locomo_prompts as LP  # noqa: E402


def prompt_sha(bench='lme'):
    h = hashlib.sha256()
    for n in (('lme_prompts.py', 'judges.json') if bench == 'lme' else ('locomo_prompts.py', 'judges.json')):
        with open(os.path.join(ROOT, 'prompts', n), 'rb') as f:
            h.update(f.read())
    return h.hexdigest()


def render(row):
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
    tpl = READER_FACTS_COT if facts else READER_COT
    return tpl.format(''.join(parts), row['question_date'], row['question'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', required=True); ap.add_argument('--arm', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--reserve', type=float, default=0.0, help='refuse to start if committed spend + reserve passes the $75 cap')
    ap.add_argument('--bench', choices=['lme', 'locomo'], default='lme')
    a = ap.parse_args()
    if ledger.over_cap(a.reserve):
        sys.exit(f'spend cap: committed {ledger.total():.2f} + reserve {a.reserve} > {ledger.CAP}')
    rows = [json.loads(l) for l in open(a.inputs)]
    rows = [r for r in rows if r['arm'] == a.arm]
    seen = set(); rows = [r for r in rows if not (r['qid'] in seen or seen.add(r['qid']))]
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'answers.jsonl')
    kept = {}
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l)
            if 'label' in r and 'error' not in r:
                kept[r['qid']] = r
    todo = [r for r in rows if r['qid'] not in kept]
    with open(path, 'w') as f:
        for r in kept.values():
            f.write(json.dumps(r) + '\n')
    lock = threading.Lock(); out = open(path, 'a')

    def write(rec):
        with lock:
            out.write(json.dumps(rec) + '\n'); out.flush()

    def one(row):
        rec = {'qid': row['qid'], 'arm': a.arm, 'type': row.get('type'), 'abstention': bool(row.get('abstention'))}
        try:
            prompt = render(row) if a.bench == 'lme' else LP.reader_prompt(row)
            r = llm.reader(prompt, 6000)
            if not r['content'].strip():
                r2 = llm.reader(prompt, 12000); r2['cost'] += r['cost']; r = r2
            rec.update(hypothesis=r['content'], reader_cost=r['cost'], reader_tokens=(r['usage'] or {}).get('completion_tokens'))
            if not r['content'].strip():
                rec.update(reader_empty=True, label=False); write(rec); return
            if a.bench == 'locomo':
                if row['type'] == LP.ADVERSARIAL:  # official string rule, no judge
                    rec.update(label=LP.score_cat5(r['content'], row['qid'], row['answer']), judge_kind='official-cat5')
                else:
                    v = llm.judge(LP.judge_prompt(row['question'], row['answer'], r['content']))
                    rec.update(judge=v['content'].strip()[:40], label=LP.parse_label(v['content']), judge_cost=v['cost'], judge_model=v['model'],
                               judge_kind='locomo-mem0', judge_tokens=v['usage'])
                write(rec); return
            pref = row['type'] == 'single-session-preference'
            v = llm.judge(anscheck_prompt(row['type'], row['question'], row['answer'], r['content'], bool(row.get('abstention'))), preference=pref)
            rec.update(judge=v['content'].strip()[:40], label='yes' in v['content'].lower(), judge_cost=v['cost'], judge_model=v['model'],
                       judge_kind='preference' if pref else 'standard', judge_tokens=v['usage'])
        except llm.Breaker:
            raise
        except Exception as e:  # noqa: BLE001
            rec.update(error=f'{type(e).__name__}:{e}'[:160], label=False)
        write(rec)

    try:
        with ThreadPoolExecutor(int(os.environ.get('READ_WORKERS', '8'))) as ex:
            list(ex.map(one, todo))
    finally:
        out.close()
        spent = llm.READER.cost + llm.JUDGE.cost
        ledger.add(a.arm, 'qa', spent, len(todo), bench=a.bench)
    res = [json.loads(l) for l in open(path)]
    summ = {'arm': a.arm, 'n': len(res), 'expected': len(rows), 'accuracy': round(sum(1 for r in res if r.get('label')) / max(1, len(res)), 4),
            'errors': sum(1 for r in res if 'error' in r), 'reader_usd': round(llm.READER.cost, 4), 'judge_usd': round(llm.JUDGE.cost, 4),
            'offmodel': llm.READER.offmodel, 'prompt_sha256': prompt_sha(a.bench), 'bench': a.bench,
            'judge_models': sorted({r.get('judge_model') for r in res if r.get('judge_model')})}
    json.dump(summ, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
