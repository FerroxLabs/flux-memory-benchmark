"""Full-context ceiling: the whole haystack (every session, every turn, in date order) is the reader's context, uncapped.
Only meaningful where the haystack fits the reader's context window (LongMemEval-S is roughly 120k tokens per question).
usage: full_context.py --units work/units_n100.jsonl --out results/full_context"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_units, row, run_units  # noqa: E402


def one(u):
    items = [{'content': t['content'], 'role': t['role'], 'session_date': s['date']} for s in u['sessions'] for t in s['turns'] if t['content'].strip()]
    return {'unit_id': u['unit_id'], 'ingest': {'seconds': 0.0, 'llm_usd': 0.0, 'turns': len(items)},
            'rows': [row('full_context', q, items, 0.0, capped=False) for q in u['questions']]}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True); ap.add_argument('--only', default='')
    a = ap.parse_args()
    run_units(one, load_units(a.units, a.only.split(',') if a.only else None), a.out, 1)
