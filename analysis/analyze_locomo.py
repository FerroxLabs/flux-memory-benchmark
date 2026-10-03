"""LoCoMo tables, rebuilt from the raw per-question outputs. Standard library only; reuses the statistics in analyze.py.

Layout: <results>/<arm>/qa/answers.jsonl etc., exactly as for LongMemEval, with results/locomo as <results> (spend is read from <results>/../ledger.jsonl if
<results>/ledger.jsonl is absent). Question ids and categories: sample/locomo_qids.tsv (ids only, no dataset text).

Tables (README "LoCoMo"):
  1. Overall, categories 1 to 4 (judge-graded): accuracy with Wilson 95% interval, paired exact McNemar against flux_public (Holm), paired-bootstrap interval.
  2. Per category: correct/total, accuracy, Wilson 95% interval, for categories 1 to 4.
  3. Category 5 (adversarial) separately, official string rule, with the same paired statistics. Never mixed into table 1.
  4. Operations (ingest per conversation, latency, drops) and spend, once.
Questions in one conversation are not independent; the paired test treats them as independent, so intervals are, if anything, too narrow. The README says so.
usage: python3 analysis/analyze_locomo.py --results results/locomo [--ids sample/locomo_qids.tsv] [--out analysis/tables]"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

ROOT = analyze.ROOT
ADV = 'cat5-adversarial'


def read_ids(path):
    """-> [(qid, type)]"""
    with open(path) as f:
        return [tuple(l.rstrip('\n').split('\t')) for l in f if l.strip()]


def analyse(results, ids_path, baseline='flux_public', bootstrap_n=10000, ledger=None):
    if ledger is None:  # one ledger for both benchmarks, kept beside the LongMemEval results
        own = os.path.join(results, 'ledger.jsonl')
        ledger = own if os.path.exists(own) else os.path.join(results, '..', 'ledger.jsonl')
    ids = read_ids(ids_path)
    main = [q for q, t in ids if t != ADV]
    adv = [q for q, t in ids if t == ADV]
    res = analyze.analyse(results, ids_path, baseline, bootstrap_n, qids=main, bench='locomo', ledger=ledger)
    res_adv = analyze.analyse(results, ids_path, baseline, bootstrap_n, qids=adv, bench='locomo', ledger=ledger) if adv else None
    if res_adv:  # ops and spend are identical in both calls; keep them once, in the main result
        res_adv.pop('ops', None); res_adv.pop('spend', None)
        res_adv['flags'] = [f for f in res_adv['flags'] if 'INCOMPLETE' in f or 'prompt hash' in f or 'baseline' in f]
        res['flags'] += [f'{f} (category 5)' for f in res_adv['flags'] if f not in res['flags']]
    return {'main': res, 'adversarial': res_adv, 'n_main': len(main), 'n_adv': len(adv)}


def tables(r):
    res, adv = r['main'], r['adversarial']
    L = ['# LoCoMo (Snap Research, CC BY-NC 4.0; data not redistributed)\n',
         f'## 1. Overall, categories 1 to 4 (n={r["n_main"]}, LLM judge, Wilson 95%)\n',
         '| Arm | Correct | Accuracy | 95% CI |', '|---|---|---|---|']
    for name in analyze.ARMS:
        a = res['arms'].get(name)
        if not a:
            continue
        if not a['complete']:
            L.append(f'| {name} | INCOMPLETE ({a["answered"]}/{r["n_main"]}) | | |')
        else:
            L.append(f'| {name} | {a["correct"]}/{r["n_main"]} | {analyze.pct(a["accuracy"])} | {analyze.pct(a["wilson95"][0])} to {analyze.pct(a["wilson95"][1])} |')
    L.append(f'\n{_paired(res, "1. Paired against " + res["baseline"] + ", categories 1 to 4")}')
    L.append('## 2. Per category (categories 1 to 4)\n')
    cats = res['types']
    L.append('| Arm | ' + ' | '.join(cats) + ' |')
    L.append('|---|' + '---|' * len(cats))
    for name in analyze.ARMS:
        a = res['arms'].get(name)
        if not a or not a['complete']:
            continue
        cells = []
        for t in cats:
            k, n = a['by_type'][t]
            lo, hi = analyze.wilson(k, n)
            cells.append(f'{k}/{n} = {analyze.pct(k / n) if n else "-"} ({analyze.pct(lo)} to {analyze.pct(hi)})')
        L.append(f'| {name} | ' + ' | '.join(cells) + ' |')
    L.append('')
    if adv:
        L.append(f'## 3. Category 5, adversarial (n={r["n_adv"]}, official string rule: the reader must decline; reported separately)\n')
        L.append('| Arm | Declined correctly | Accuracy | 95% CI |')
        L.append('|---|---|---|---|')
        for name in analyze.ARMS:
            a = adv['arms'].get(name)
            if not a:
                continue
            if not a['complete']:
                L.append(f'| {name} | INCOMPLETE ({a["answered"]}/{r["n_adv"]}) | | |')
            else:
                L.append(f'| {name} | {a["correct"]}/{r["n_adv"]} | {analyze.pct(a["accuracy"])} | {analyze.pct(a["wilson95"][0])} to {analyze.pct(a["wilson95"][1])} |')
        L.append('\n' + _paired(adv, f'3. Category 5 paired against {adv["baseline"]}'))
    L.append('## 4. Operations and spend\n')
    L.append(_ops(res))
    if res['flags']:
        L.append('## Flags\n')
        L += [f'- {x}' for x in res['flags']]
    return '\n'.join(L) + '\n'


def _paired(res, title):
    L = [f'### {title} (exact McNemar, Holm across {len(res["comparisons"])}; bootstrap 95% CI, points)\n',
         '| Arm | Diff (pts) | 95% CI | Arm only right | Baseline only right | p | p (Holm) | Reading |', '|---|---|---|---|---|---|---|---|']
    for name in analyze.ARMS:
        c = res['comparisons'].get(name)
        if c:
            L.append(f'| {name} | {100 * c["diff"]:+.1f} | {100 * c["ci95"][0]:+.1f} to {100 * c["ci95"][1]:+.1f} | {c["arm_only"]} | {c["baseline_only"]} | {c["p"]} | {c["p_holm"]} | {c["verdict"]} |')
    return '\n'.join(L) + '\n'


def _ops(res):
    f = lambda v: '' if v is None else str(v)  # noqa: E731
    L = ['| Arm | Conversations ingested | Ingest s/conversation | Ingest LLM $/conversation | Items dropped | Retrieval ms p50 / p95 | Empty retrievals |', '|---|---|---|---|---|---|---|']
    for name in analyze.ARMS:
        o = res['ops'].get(name)
        if o:
            dr = '' if o['drop_rate'] is None else f'{o["items_dropped"]}/{o["items_total"]} ({analyze.pct(o["drop_rate"])}%)'
            L.append(f'| {name} | {o["haystacks"]} | {f(o["ingest_s_mean"])} | {f(o["ingest_usd_mean"])} | {dr} | {f(o["retrieval_ms_p50"])} / {f(o["retrieval_ms_p95"])} | {f(o["empty_retrieval_share"])} |')
    s = res['spend']
    return '\n'.join(L) + f'\n\nTotal spend ${s["total"]} of ${s["cap"]} cap (both benchmarks). By benchmark: {json.dumps(s.get("by_bench", {}))}. By arm: {json.dumps(s["by_arm"])}\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=os.path.join(ROOT, 'results', 'locomo')); ap.add_argument('--ids', default=os.path.join(ROOT, 'sample', 'locomo_qids.tsv'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'analysis', 'tables')); ap.add_argument('--baseline', default='flux_public')
    a = ap.parse_args()
    r = analyse(a.results, a.ids, a.baseline)
    os.makedirs(a.out, exist_ok=True)
    json.dump(r, open(os.path.join(a.out, 'locomo_tables.json'), 'w'), indent=1)
    md = tables(r)
    open(os.path.join(a.out, 'locomo_tables.md'), 'w').write(md)
    print(md)


if __name__ == '__main__':
    main()
