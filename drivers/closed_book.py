"""Closed-book baseline: the reader sees no memory at all (the contamination floor). No ingest, no retrieval, no cost beyond the reader.
usage: closed_book.py --units work/units_n100.jsonl --out results/closed_book"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_units, row, run_units  # noqa: E402


def one(u):
    return {'unit_id': u['unit_id'], 'ingest': {'seconds': 0.0, 'llm_usd': 0.0},
            'rows': [row('closed_book', q, [], 0.0) for q in u['questions']]}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True); ap.add_argument('--only', default='')
    a = ap.parse_args()
    run_units(one, load_units(a.units, a.only.split(',') if a.only else None), a.out, 1)
