"""Cost table per system and benchmark, rebuilt from the raw outputs. Standard library only.

Columns (measured unless stated): ingest $ per haystack (LongMemEval) or per conversation (LoCoMo), memory-system LLM $ per query (the 'query' stage of the
ledger: Honcho's retrieval and dialectic calls; 0 for systems with no LLM at query time), reader+judge $ per query (the same reader and judge for every arm,
so it differs only through context size; it is the answering model's cost, not the memory system's), retrieval latency p50 and p95, failure rates
(units that failed, ingest items dropped, questions that errored or came back empty) and the DERIVED 'memory cost per active user per month':

  PROFILE: 30 sessions a month x 20 turns each = 600 turns ingested, and 100 recalls.
  monthly = 600 x (ingest $ per haystack / mean turns per haystack) + 100 x (memory-system LLM $ per query).

It counts the memory system's own LLM spend only: not the reader, not the judge, not servers, storage or embeddings we ran ourselves. Ingest $ per turn is the
measured per-haystack cost divided by the haystack's turns (read from the units file, which holds dataset text and is git-ignored; or pass --turns-lme / --turns-locomo).
The vendor list-price column is read from analysis/prices.json (hand-edited, url and date per entry; null prints TODO).
usage: python3 analysis/cost_table.py [--lme results] [--locomo results/locomo] [--prices analysis/prices.json] [--out analysis/tables]"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

ROOT = analyze.ROOT
SESSIONS_PER_MONTH, TURNS_PER_SESSION, RECALLS_PER_MONTH = 30, 20, 100
TURNS_PER_MONTH = SESSIONS_PER_MONTH * TURNS_PER_SESSION


def mean_turns(units_path):
    """Mean turns per unit from a units file (dataset text stays local); None if the file is absent."""
    if not units_path or not os.path.exists(units_path):
        return None
    us = analyze.read_jsonl(units_path)
    return sum(len(s['turns']) for u in us for s in u['sessions']) / len(us) if us else None


def monthly(ingest_usd, turns_per_haystack, query_usd):
    """Memory-system LLM $ per active user per month under the stated profile, or None when an input is missing."""
    if ingest_usd is None or not turns_per_haystack:
        return None
    return TURNS_PER_MONTH * ingest_usd / turns_per_haystack + RECALLS_PER_MONTH * (query_usd or 0.0)


def arm_row(results, arm, turns, ledger_rows, bench):
    o = analyze.ops(results, arm)
    ans = analyze.read_jsonl(os.path.join(results, arm, 'qa', 'answers.jsonl'))
    n = len(ans)
    qa_usd = sum((r.get('reader_cost') or 0) + (r.get('judge_cost') or 0) for r in ans)
    failed = sum(1 for r in ans if 'error' in r or r.get('reader_empty'))
    q_usd = sum(r['usd'] for r in ledger_rows if r['arm'] == arm and r['stage'] == 'query' and r.get('bench', 'lme') == bench)
    units = o['haystacks'] + o['unit_errors']
    return {'arm': arm, 'haystacks': o['haystacks'], 'ingest_usd': o['ingest_usd_mean'], 'ingest_s': o['ingest_s_mean'],
            'query_usd': (q_usd / n) if n and q_usd else (0.0 if n else None), 'qa_usd': (qa_usd / n) if n else None,
            'p50': o['retrieval_ms_p50'], 'p95': o['retrieval_ms_p95'],
            'unit_fail': (o['unit_errors'] / units) if units else None, 'drop_rate': o['drop_rate'], 'q_fail': (failed / n) if n else None,
            'monthly': monthly(o['ingest_usd_mean'], turns, (q_usd / n) if n and q_usd else 0.0), 'questions': n}


def build(results, bench, turns, ledger_path):
    ledger_rows = analyze.read_jsonl(ledger_path)
    return [arm_row(results, a, turns, ledger_rows, bench) for a in analyze.ARMS if os.path.isdir(os.path.join(results, a))]


def price_cell(prices, arm):
    p = (prices.get('systems') or {}).get(arm) or {}
    v = p.get('list_price_usd_per_month')
    if v is None:
        return 'TODO'
    return f'${v:g}/month' + (f' per {p["unit"]}' if p.get('unit') and p['unit'] != 'n/a' else '') + (f' ({p.get("url") or "no url"}, {p.get("date") or "no date"})' if v else '')


def render(rows, prices, bench_title, unit_word, turns):
    f = lambda v, fmt='{}': '-' if v is None else fmt.format(v)  # noqa: E731
    pc = lambda v: '-' if v is None else f'{100 * v:.1f}%'  # noqa: E731
    L = [f'## {bench_title}\n',
         f'Mean turns per {unit_word}: {f(turns, "{:.0f}")}. Profile: {SESSIONS_PER_MONTH} sessions x {TURNS_PER_SESSION} turns = {TURNS_PER_MONTH} turns ingested and {RECALLS_PER_MONTH} recalls per active user per month.\n',
         f'| Arm | Ingest $/{unit_word} | Memory LLM $/query | Reader+judge $/query | Retrieval ms p50 / p95 | Failed units | Items dropped | Failed questions | Memory cost per active user per month | Vendor list price |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f'| {r["arm"]} | {f(r["ingest_usd"], "{:.4f}")} | {f(r["query_usd"], "{:.5f}")} | {f(r["qa_usd"], "{:.5f}")} | {f(r["p50"])} / {f(r["p95"])} | '
                 f'{pc(r["unit_fail"])} | {pc(r["drop_rate"])} | {pc(r["q_fail"])} | {f(r["monthly"], "${:.2f}")} | {price_cell(prices, r["arm"])} |')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lme', default=os.path.join(ROOT, 'results')); ap.add_argument('--locomo', default=os.path.join(ROOT, 'results', 'locomo'))
    ap.add_argument('--ledger', default=os.path.join(ROOT, 'results', 'ledger.jsonl'))
    ap.add_argument('--prices', default=os.path.join(HERE, 'prices.json')); ap.add_argument('--out', default=os.path.join(HERE, 'tables'))
    ap.add_argument('--lme-units', default=os.path.join(ROOT, 'work', 'units_n100.jsonl')); ap.add_argument('--locomo-units', default=os.path.join(ROOT, 'work', 'locomo_units.jsonl'))
    ap.add_argument('--turns-lme', type=float); ap.add_argument('--turns-locomo', type=float)
    a = ap.parse_args()
    prices = json.load(open(a.prices))
    t_lme = a.turns_lme or mean_turns(a.lme_units); t_lo = a.turns_locomo or mean_turns(a.locomo_units)
    md = ['# Cost table\n', 'Measured per-system costs and a derived monthly figure under one stated profile (see analysis/cost_table.py). LLM spend of the memory system only; not reader, judge or our own servers.\n']
    if os.path.isdir(a.lme):
        md.append(render(build(a.lme, 'lme', t_lme, a.ledger), prices, 'LongMemEval-S (n=100)', 'haystack', t_lme))
    if os.path.isdir(a.locomo):
        md.append(render(build(a.locomo, 'locomo', t_lo, a.ledger), prices, 'LoCoMo (10 conversations)', 'conversation', t_lo))
    os.makedirs(a.out, exist_ok=True)
    out = '\n'.join(md)
    open(os.path.join(a.out, 'cost_table.md'), 'w').write(out)
    print(out)


if __name__ == '__main__':
    main()
