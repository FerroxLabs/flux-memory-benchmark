"""Build results-public/ from the full per-item outputs in results/ (which are git-ignored because they quote dataset text).

Per-item files keep only: qid, arm, type (question type / LoCoMo category), correct (0/1), verdict, judge_kind, error (class name only), reader_empty,
reader_cost, judge_cost. Question text, gold answers, retrieved context, model answers and the judge's free text are dropped (they quote the dataset).
Ingest files keep only numeric fields per haystack or conversation.
Standard library only. usage: python3 analysis/make_public.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARMS = ['flux_public', 'flux_evidence', 'mem0', 'letta', 'honcho_retrieval', 'honcho_chat', 'closed_book', 'full_context']
BENCH_DIR = {'lme': 'results', 'locomo': 'results/locomo'}


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def strip_item(r):
    err = r.get('error')
    return {'qid': r['qid'], 'arm': r['arm'], 'type': r.get('type'), 'correct': 1 if (r.get('label') and not err) else 0,
            'verdict': 'error' if err else ('empty' if r.get('reader_empty') else ('correct' if r.get('label') else 'incorrect')),
            'judge_kind': r.get('judge_kind'), 'error': err.split(':')[0] if err else None, 'reader_empty': bool(r.get('reader_empty')),
            'reader_cost': r.get('reader_cost'), 'judge_cost': r.get('judge_cost')}


def flat_numeric(d):
    return {k: v for k, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def main():
    for bench, rel in BENCH_DIR.items():
        for arm in ARMS:
            d = os.path.join(ROOT, rel, arm)
            items = jl(os.path.join(d, 'qa', 'answers.jsonl'))
            if items:
                os.makedirs(os.path.join(ROOT, 'results-public', bench), exist_ok=True)
                with open(os.path.join(ROOT, 'results-public', bench, arm + '.jsonl'), 'w') as f:
                    for r in sorted(items, key=lambda r: r['qid']):
                        f.write(json.dumps(strip_item(r), sort_keys=True) + '\n')
            units = jl(os.path.join(d, 'units.jsonl'))
            if units:
                os.makedirs(os.path.join(ROOT, 'results-public', 'ingest', bench), exist_ok=True)
                with open(os.path.join(ROOT, 'results-public', 'ingest', bench, arm + '.jsonl'), 'w') as f:
                    for u in sorted(units, key=lambda u: u['unit_id']):
                        row = flat_numeric(u.get('ingest') or {})
                        row.update(unit_id=u['unit_id'], unit_error=bool(u.get('error')))
                        f.write(json.dumps(row, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
