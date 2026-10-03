"""Spend ledger and stop rules. Append-only results/ledger.jsonl; one line per stage end.

  python3 runner/ledger.py add  --arm mem0 --stage ingest --usd 0.081 [--units 1]
  python3 runner/ledger.py status [--cap 75]            # totals by arm; exit 3 if over the cap
  python3 runner/ledger.py check --reserve 2.5 [--cap 75]   # exit 3 if committed + reserve would pass the cap
  python3 runner/ledger.py honcho-rule --dir results/honcho_retrieval   # exit 4 if mean ingest cost > $0.15/haystack after the first 10
  python3 runner/ledger.py honcho-rule --dir results/locomo/honcho_retrieval --locomo   # LoCoMo: after the first 3 conversations, ceiling scaled by turns
"""
import argparse, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.environ.get('LEDGER_PATH') or os.path.join(ROOT, 'results', 'ledger.jsonl')  # LEDGER_PATH: inside containers /repo is read-only
CAP = 75.0  # LongMemEval and LoCoMo together; raised from 55 to 75 by the owner on 2026-10-03, before the run started (was 40 for LongMemEval alone)
HONCHO_PER_HAYSTACK_LIMIT = 0.15
HONCHO_AFTER = 10
# LoCoMo has 10 conversations, so the rule is checked after the first 3, against the LME ceiling scaled by turns per haystack (588 vs 491 turns).
LOCOMO_AFTER, LOCOMO_LIMIT = 3, round(0.15 * 588.2 / 490.83, 3)


def read():
    return [json.loads(l) for l in open(LEDGER)] if os.path.exists(LEDGER) else []


def total(rows=None):
    return sum(r['usd'] for r in (rows if rows is not None else read()))


def add(arm, stage, usd, units=None, bench=None):
    """bench: 'lme' or 'locomo' (default: the BENCH environment variable, else 'lme'). The cap applies to both together."""
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'a') as f:
        f.write(json.dumps({'ts': time.time(), 'arm': arm, 'stage': stage, 'usd': round(float(usd), 6), 'units': units,
                            'bench': bench or os.environ.get('BENCH', 'lme')}) + '\n')


def over_cap(reserve=0.0, cap=CAP):
    return total() + reserve > cap


def honcho_rule(dirpath, after=HONCHO_AFTER, limit=HONCHO_PER_HAYSTACK_LIMIT):
    """Mean LLM ingest cost over the first `after` units; True means the stop rule fires."""
    p = os.path.join(dirpath, 'units.jsonl')
    costs = [json.loads(l).get('llm_usd') for l in open(p)] if os.path.exists(p) else []
    costs = [c for c in costs if c is not None][:after]
    return len(costs) >= after and sum(costs) / len(costs) > limit, costs


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['add', 'status', 'check', 'honcho-rule'])
    ap.add_argument('--arm'); ap.add_argument('--stage'); ap.add_argument('--usd', type=float); ap.add_argument('--units', type=int)
    ap.add_argument('--cap', type=float, default=CAP); ap.add_argument('--reserve', type=float, default=0.0); ap.add_argument('--dir'); ap.add_argument('--locomo', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'add':
        add(a.arm, a.stage, a.usd, a.units)
    elif a.cmd == 'status':
        by, bb = {}, {}
        for r in read():
            by[r['arm']] = by.get(r['arm'], 0) + r['usd']
            bb[r.get('bench', 'lme')] = bb.get(r.get('bench', 'lme'), 0) + r['usd']
        print(json.dumps({'by_arm': {k: round(v, 4) for k, v in by.items()}, 'by_bench': {k: round(v, 4) for k, v in bb.items()}, 'total': round(total(), 4), 'cap': a.cap}))
        sys.exit(3 if total() > a.cap else 0)
    elif a.cmd == 'check':
        bad = over_cap(a.reserve, a.cap)
        print(f'committed {total():.4f} + reserve {a.reserve} {"EXCEEDS" if bad else "within"} cap {a.cap}')
        sys.exit(3 if bad else 0)
    else:
        after, limit = (LOCOMO_AFTER, LOCOMO_LIMIT) if a.locomo else (HONCHO_AFTER, HONCHO_PER_HAYSTACK_LIMIT)
        fire, costs = honcho_rule(a.dir, after, limit)
        print('STOP: Honcho ingest passes $%.3f/haystack after %d' % (limit, after) if fire else f'ok ({len(costs)} haystacks seen)')
        sys.exit(4 if fire else 0)
