"""Spend ledger and stop rules. Append-only results/ledger.jsonl; one line per stage end.

  python3 runner/ledger.py add  --arm mem0 --stage ingest --usd 0.081 [--units 1]
  python3 runner/ledger.py status [--cap 40]            # totals by arm; exit 3 if over the cap
  python3 runner/ledger.py check --reserve 2.5 [--cap 40]   # exit 3 if committed + reserve would pass the cap
  python3 runner/ledger.py honcho-rule --dir results/honcho_retrieval   # exit 4 if mean ingest cost > $0.15/haystack after the first 10
"""
import argparse, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'results', 'ledger.jsonl')
CAP = 40.0
HONCHO_PER_HAYSTACK_LIMIT = 0.15
HONCHO_AFTER = 10


def read():
    return [json.loads(l) for l in open(LEDGER)] if os.path.exists(LEDGER) else []


def total(rows=None):
    return sum(r['usd'] for r in (rows if rows is not None else read()))


def add(arm, stage, usd, units=None):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'a') as f:
        f.write(json.dumps({'ts': time.time(), 'arm': arm, 'stage': stage, 'usd': round(float(usd), 6), 'units': units}) + '\n')


def over_cap(reserve=0.0, cap=CAP):
    return total() + reserve > cap


def honcho_rule(dirpath):
    """Mean LLM ingest cost over the first HONCHO_AFTER units; True means the stop rule fires."""
    p = os.path.join(dirpath, 'units.jsonl')
    costs = [json.loads(l).get('llm_usd') for l in open(p)] if os.path.exists(p) else []
    costs = [c for c in costs if c is not None][:HONCHO_AFTER]
    return len(costs) >= HONCHO_AFTER and sum(costs) / len(costs) > HONCHO_PER_HAYSTACK_LIMIT, costs


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['add', 'status', 'check', 'honcho-rule'])
    ap.add_argument('--arm'); ap.add_argument('--stage'); ap.add_argument('--usd', type=float); ap.add_argument('--units', type=int)
    ap.add_argument('--cap', type=float, default=CAP); ap.add_argument('--reserve', type=float, default=0.0); ap.add_argument('--dir')
    a = ap.parse_args()
    if a.cmd == 'add':
        add(a.arm, a.stage, a.usd, a.units)
    elif a.cmd == 'status':
        by = {}
        for r in read():
            by[r['arm']] = by.get(r['arm'], 0) + r['usd']
        print(json.dumps({'by_arm': {k: round(v, 4) for k, v in by.items()}, 'total': round(total(), 4), 'cap': a.cap}))
        sys.exit(3 if total() > a.cap else 0)
    elif a.cmd == 'check':
        bad = over_cap(a.reserve, a.cap)
        print(f'committed {total():.4f} + reserve {a.reserve} {"EXCEEDS" if bad else "within"} cap {a.cap}')
        sys.exit(3 if bad else 0)
    else:
        fire, costs = honcho_rule(a.dir)
        print('STOP: Honcho ingest passes $%.2f/haystack after %d' % (HONCHO_PER_HAYSTACK_LIMIT, HONCHO_AFTER) if fire else f'ok ({len(costs)} haystacks seen)')
        sys.exit(4 if fire else 0)
