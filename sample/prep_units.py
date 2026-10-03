"""Build the per-question haystack units for the drawn ids, from your local copy of LongMemEval-S.
The output (units_n100.jsonl) contains dataset text, so it is git-ignored and never published.

unit = {unit_id, sessions:[{session_id, date, turns:[{role, content}]}], questions:[{qid, type, question, question_date, answer, abstention}]}
Adapted from the private h2h-oss prep_units.py (LongMemEval branch only).

usage: LME_S_PATH=... python3 sample/prep_units.py --out work/units_n100.jsonl
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def lme(path, qids):
    keep = set(qids)
    out = []
    for q in json.load(open(path)):
        if q['question_id'] not in keep:
            continue
        sessions = [{'session_id': sid, 'date': date,
                     'turns': [{'role': t.get('role', 'user'), 'content': t.get('content') or ''} for t in sess]}
                    for sid, date, sess in zip(q['haystack_session_ids'], q['haystack_dates'], q['haystack_sessions'])]
        out.append({'unit_id': q['question_id'], 'sessions': sessions,
                    'questions': [{'qid': q['question_id'], 'type': q['question_type'], 'question': q['question'],
                                   'question_date': q['question_date'], 'answer': q['answer'],
                                   'abstention': q['question_id'].endswith('_abs')}]})
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--ids', default=os.path.join(HERE, 'lme_s_ids_n100.txt'))
    a = ap.parse_args()
    path = os.environ.get('LME_S_PATH') or sys.exit('set LME_S_PATH')
    ids = open(a.ids).read().split()
    units = lme(path, ids)
    assert len(units) == len(ids), (len(units), len(ids))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w') as f:
        for u in units:
            f.write(json.dumps(u) + '\n')
    print(len(units), 'units', sum(len(u['sessions']) for u in units), 'sessions', sum(len(s['turns']) for u in units for s in u['sessions']), 'turns')
