"""Rebuild every table from the raw per-question outputs. Standard library only.

Inputs (per arm directory under --results, arm = directory name):
  <arm>/qa/answers.jsonl   one row per question: qid, type, label (the final grade), error?   (runner/qa.py)
  <arm>/qa/summary.json    prompt_sha256, n, expected                                         (runner/qa.py)
  <arm>/units.jsonl        one row per haystack: ingest{seconds, llm_usd, items_total, items_dropped}, error?   (drivers)
  <arm>/retrieved_meta.jsonl  (or retrieved.jsonl) one row per question: n_context, search_ms        (drivers; runner/strip_retrieved.py)
  results/ledger.jsonl     spend, one line per stage                                            (runner/ledger.py)
honcho_chat has no ingest of its own: its ingest figures are read from honcho_retrieval.

Method (README "Statistics"): accuracy with Wilson 95% interval, overall and per question type; each arm against the Flux public arm
(flux_public) by a paired exact McNemar test on the same question ids, Holm-corrected across all arms compared, plus a paired-bootstrap 95% interval
for the accuracy difference (10,000 resamples over questions, seed 0). Errors and empty answers score wrong. An arm that did not answer every
sampled question is marked INCOMPLETE and is left out of every comparison (stop rule: partial arms are not reported as results).
usage: python3 analysis/analyze.py --results results --ids sample/lme_s_ids_n100.txt [--out analysis/tables] [--baseline flux_public]
"""
import argparse, hashlib, json, math, os, random, sys

ARMS = ['flux_public', 'flux_evidence', 'mem0', 'letta', 'honcho_retrieval', 'honcho_chat', 'closed_book', 'full_context']
INGEST_FROM = {'honcho_chat': 'honcho_retrieval'}
DROP_LIMIT = 0.02
HONCHO_LIMIT, HONCHO_AFTER = 0.15, 10
CAP = 55.0  # LongMemEval and LoCoMo together
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(max(0.0, (c - h) / d), 3), round(min(1.0, (c + h) / d), 3))


def mcnemar_exact(a, b, qids):
    """Two-sided exact McNemar on discordant pairs. Returns (a_only, b_only, p)."""
    x = sum(1 for q in qids if a[q] and not b[q])
    y = sum(1 for q in qids if b[q] and not a[q])
    n = x + y
    if n == 0:
        return x, y, 1.0
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(x, y) + 1)) / 2 ** n)
    return x, y, p


def holm(pvals):
    """Holm step-down adjustment. pvals: {key: p}. Returns {key: adjusted p}."""
    m = len(pvals)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(sorted(pvals.items(), key=lambda kv: kv[1])):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def paired_bootstrap(diffs, n=10000, seed=0):
    r = random.Random(seed)
    k = len(diffs)
    means = sorted(sum(diffs[r.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)


def prompt_sha(bench='lme'):
    h = hashlib.sha256()
    for n in (('lme_prompts.py', 'judges.json') if bench == 'lme' else ('locomo_prompts.py', 'judges.json')):
        with open(os.path.join(ROOT, 'prompts', n), 'rb') as f:
            h.update(f.read())
    return h.hexdigest()


def pct(x):
    return f'{100 * x:.1f}'


def quantile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def load_arm(results, arm, qids):
    d = os.path.join(results, arm)
    ans = {}
    for r in read_jsonl(os.path.join(d, 'qa', 'answers.jsonl')):
        ans[r['qid']] = r  # last row wins; runner/qa.py rewrites a qid only to retry an error
    types = {q: ans[q].get('type') for q in ans}
    label = {q: 1 if (q in ans and ans[q].get('label') and not ans[q].get('error')) else 0 for q in qids}
    answered = sum(1 for q in qids if q in ans and not ans[q].get('error'))
    summ = {}
    sp = os.path.join(d, 'qa', 'summary.json')
    if os.path.exists(sp):
        with open(sp) as f:
            summ = json.load(f)
    return {'arm': arm, 'label': label, 'types': types, 'answered': answered, 'errors': sum(1 for q in qids if q in ans and ans[q].get('error')),
            'present': bool(ans), 'complete': answered == len(qids), 'summary': summ, 'answers': ans}


def ops(results, arm):
    src = INGEST_FROM.get(arm, arm)
    units = read_jsonl(os.path.join(results, src, 'units.jsonl'))
    ok = [u for u in units if u.get('ingest') and not u.get('error')]
    secs = [u['ingest'].get('seconds') for u in ok if u['ingest'].get('seconds') is not None]
    usd = [u['ingest'].get('llm_usd') for u in ok if u['ingest'].get('llm_usd') is not None]
    tot = sum(u['ingest'].get('items_total') or 0 for u in ok)
    drop = sum(u['ingest'].get('items_dropped') or 0 for u in ok)
    rows = read_jsonl(os.path.join(results, arm, 'retrieved_meta.jsonl')) or read_jsonl(os.path.join(results, arm, 'retrieved.jsonl'))
    ms = [r['search_ms'] for r in rows if r.get('search_ms') is not None]
    empty = sum(1 for r in rows if r.get('n_context', 0) == 0)
    return {'haystacks': len(ok), 'unit_errors': len(units) - len(ok), 'ingest_s_mean': round(sum(secs) / len(secs), 1) if secs else None,
            'ingest_usd_mean': round(sum(usd) / len(usd), 4) if usd else None, 'ingest_usd_total': round(sum(usd), 3) if usd else None,
            'items_total': tot, 'items_dropped': drop, 'drop_rate': round(drop / tot, 4) if tot else None,
            'retrieval_ms_p50': round(quantile(ms, 0.5), 1) if ms else None, 'retrieval_ms_p95': round(quantile(ms, 0.95), 1) if ms else None,
            'empty_retrieval_share': round(empty / len(rows), 3) if rows else None, 'usd_first10': usd[:HONCHO_AFTER]}


def analyse(results, ids_path, baseline='flux_public', bootstrap_n=10000, qids=None, bench='lme', ledger=None):
    """qids: analyse this subset of ids instead of reading ids_path (used for LoCoMo, which splits by category)."""
    if qids is None:
        with open(ids_path) as f:
            qids = f.read().split()
    arms = {a: load_arm(results, a, qids) for a in ARMS if os.path.isdir(os.path.join(results, a))}
    types = {}
    for a in arms.values():
        types.update({q: t for q, t in a['types'].items() if t})
    qset = set(qids)
    tlist = sorted({t for q, t in types.items() if q in qset})  # only the types of the ids analysed (LoCoMo splits category 5 off)
    out = {'n': len(qids), 'baseline': baseline, 'types': tlist, 'arms': {}, 'comparisons': {}, 'ops': {}, 'flags': []}
    psha = prompt_sha(bench)
    for name, a in arms.items():
        k = sum(a['label'].values())
        entry = {'complete': a['complete'], 'answered': a['answered'], 'errors': a['errors']}
        if a['complete']:
            entry.update(correct=k, accuracy=round(k / len(qids), 4), wilson95=wilson(k, len(qids)),
                         by_type={t: [sum(a['label'][q] for q in qids if types.get(q) == t), sum(1 for q in qids if types.get(q) == t)] for t in tlist})
        else:
            out['flags'].append(f'{name}: INCOMPLETE ({a["answered"]}/{len(qids)} answered); not reported as a result and left out of comparisons')
        sha = a['summary'].get('prompt_sha256')
        if a['present'] and sha != psha:
            out['flags'].append(f'{name}: prompt hash in qa/summary.json does not match prompts/ ({sha}); the run is not comparable')
        out['arms'][name] = entry
    if baseline in arms and arms[baseline]['complete']:
        base = arms[baseline]['label']
        raw = {}
        for name, a in arms.items():
            if name == baseline or not a['complete']:
                continue
            x, y, p = mcnemar_exact(a['label'], base, qids)
            diffs = [a['label'][q] - base[q] for q in qids]
            raw[name] = {'diff': round(sum(diffs) / len(diffs), 4), 'ci95': paired_bootstrap(diffs, bootstrap_n), 'arm_only': x, 'baseline_only': y, 'p': p}
        adj = holm({k: v['p'] for k, v in raw.items()})
        for name, v in raw.items():
            v['p_holm'] = round(adj[name], 5)
            v['p'] = round(v['p'], 5)
            v['verdict'] = 'tie' if adj[name] >= 0.05 else ('better than baseline' if v['diff'] > 0 else 'worse than baseline')
            out['comparisons'][name] = v
    elif baseline in arms:
        out['flags'].append(f'baseline {baseline} is incomplete; no comparisons made')
    for name in arms:
        out['ops'][name] = ops(results, name)
        o = out['ops'][name]
        if o['drop_rate'] is not None and o['drop_rate'] > DROP_LIMIT:
            out['flags'].append(f'{name}: {pct(o["drop_rate"])}% of ingest items dropped or failed (> {pct(DROP_LIMIT)}%): stop rule, fix the setup and restart this arm from a clean store')
        if name.startswith('honcho') and len(o['usd_first10']) >= HONCHO_AFTER and sum(o['usd_first10']) / HONCHO_AFTER > HONCHO_LIMIT:
            out['flags'].append(f'{name}: Honcho ingest averaged over ${HONCHO_LIMIT}/haystack across the first {HONCHO_AFTER}: stop rule, pause and find out why')
    spend, bench_spend = {}, {}
    for r in read_jsonl(ledger or os.path.join(results, 'ledger.jsonl')):
        spend[r['arm']] = spend.get(r['arm'], 0) + r['usd']
        bench_spend[r.get('bench', 'lme')] = bench_spend.get(r.get('bench', 'lme'), 0) + r['usd']
    out['spend'] = {'by_arm': {k: round(v, 4) for k, v in spend.items()}, 'by_bench': {k: round(v, 4) for k, v in bench_spend.items()},
                    'total': round(sum(spend.values()), 4), 'cap': CAP}
    if sum(spend.values()) > CAP:
        out['flags'].append(f'spend {sum(spend.values()):.2f} is over the ${CAP:g} cap')
    return out


def tables(res):
    L = []
    n = res['n']
    L.append(f'## Accuracy, n={n} (Wilson 95%)\n')
    L.append('| Arm | Correct | Accuracy | 95% CI | ' + ' | '.join(t.replace('single-session-', 'ss-') for t in res['types']) + ' |')
    L.append('|---|---|---|---|' + '---|' * len(res['types']))
    for name in ARMS:
        a = res['arms'].get(name)
        if not a:
            continue
        if not a['complete']:
            L.append(f'| {name} | INCOMPLETE ({a["answered"]}/{n}) | | | ' + ' | '.join('' for _ in res['types']) + ' |')
            continue
        bt = ' | '.join(f'{v[0]}/{v[1]}' for v in (a['by_type'][t] for t in res['types']))
        L.append(f'| {name} | {a["correct"]}/{n} | {pct(a["accuracy"])} | {pct(a["wilson95"][0])} to {pct(a["wilson95"][1])} | {bt} |')
    L.append(f'\n## Paired against {res["baseline"]} (exact McNemar, Holm across {len(res["comparisons"])} comparisons; bootstrap 95% CI of the accuracy difference, points)\n')
    L.append('| Arm | Diff (pts) | 95% CI | Arm only right | Baseline only right | p | p (Holm) | Reading |')
    L.append('|---|---|---|---|---|---|---|---|')
    for name in ARMS:
        c = res['comparisons'].get(name)
        if c:
            L.append(f'| {name} | {100 * c["diff"]:+.1f} | {100 * c["ci95"][0]:+.1f} to {100 * c["ci95"][1]:+.1f} | {c["arm_only"]} | {c["baseline_only"]} | {c["p"]} | {c["p_holm"]} | {c["verdict"]} |')
    L.append('\n## Operations per system\n')
    L.append('| Arm | Haystacks ingested | Ingest s/haystack | Ingest LLM $/haystack | Ingest LLM $ total | Items dropped | Retrieval ms p50 / p95 | Empty retrievals |')
    L.append('|---|---|---|---|---|---|---|---|')
    f = lambda v, fmt='{}': '' if v is None else fmt.format(v)  # noqa: E731
    for name in ARMS:
        o = res['ops'].get(name)
        if o:
            dr = '' if o['drop_rate'] is None else f'{o["items_dropped"]}/{o["items_total"]} ({pct(o["drop_rate"])}%)'
            L.append(f'| {name} | {o["haystacks"]} | {f(o["ingest_s_mean"])} | {f(o["ingest_usd_mean"])} | {f(o["ingest_usd_total"])} | {dr} | '
                     f'{f(o["retrieval_ms_p50"])} / {f(o["retrieval_ms_p95"])} | {f(o["empty_retrieval_share"])} |')
    L.append(f'\n## Spend\n\nTotal ${res["spend"]["total"]} of ${res["spend"]["cap"]} cap. By arm: {json.dumps(res["spend"]["by_arm"])}\n')
    if res['flags']:
        L.append('## Flags\n')
        L += [f'- {x}' for x in res['flags']]
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=os.path.join(ROOT, 'results')); ap.add_argument('--ids', default=os.path.join(ROOT, 'sample', 'lme_s_ids_n100.txt'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'analysis', 'tables')); ap.add_argument('--baseline', default='flux_public')
    a = ap.parse_args()
    res = analyse(a.results, a.ids, a.baseline)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, 'tables.json'), 'w'), indent=1)
    md = tables(res)
    open(os.path.join(a.out, 'tables.md'), 'w').write(md)
    print(md)


if __name__ == '__main__':
    main()
