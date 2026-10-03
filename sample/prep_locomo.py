"""Build per-conversation haystack units for LoCoMo, in the same unit format the LongMemEval drivers read (so every driver runs unchanged):
unit = {unit_id, sessions:[{session_id, date, turns:[{role, content}]}], questions:[{qid, type, question, question_date, answer, abstention}]}
One unit per conversation (10), all questions, all five categories. Categories: 1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop, 5 adversarial.
Dates are normalised to the LongMemEval format ('2023/05/08 (Mon) 13:56') so every arm sorts them alike. A turn is 'Speaker: text' (+ ' [shares a photo: caption]'),
role = speaker name (also in 'speaker', which Flux's multi-party fact extraction reads; the other drivers ignore it). question_date is the last session's date. For category 5 the 'answer' field holds the adversarial answer (the wrong option); the official handling
(prompts/locomo_prompts.py) scores whether the reader declines instead. Ingestion code adapted from the private h2h-oss prep_units.py (2026-09-30).
The units file holds dataset text (CC BY-NC 4.0): it is git-ignored. --write-ids writes only ids and categories (sample/locomo_qids.tsv), which is committed.
usage: python3 sample/prep_locomo.py [--data data/locomo10.json] --out work/locomo_units.jsonl [--write-ids sample/locomo_qids.tsv]"""
import argparse, json, os, sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'prompts'))
from locomo_prompts import CAT_NAMES  # noqa: E402


def locomo_date(s):
    d = datetime.strptime(s.strip(), '%I:%M %p on %d %B, %Y')
    return d.strftime('%Y/%m/%d (%a) %H:%M'), d


def build_units(data):
    units = []
    for s in data:
        conv = s['conversation']
        keys = sorted((k for k in conv if k.startswith('session_') and not k.endswith('date_time')), key=lambda k: int(k.split('_')[1]))
        sessions, last = [], None
        for k in keys:
            if not conv[k]:
                continue
            date, dt = locomo_date(conv[k + '_date_time'])
            last = max(last, dt) if last else dt
            turns = []
            for t in conv[k]:
                c = f"{t['speaker']}: {t.get('text', '')}"
                if t.get('blip_caption'):
                    c += f" [shares a photo: {t['blip_caption']}]"
                turns.append({'role': t['speaker'], 'speaker': t['speaker'], 'content': c})
            sessions.append({'session_id': f"{s['sample_id']}__{k}", 'date': date, 'turns': turns})
        qdate = last.strftime('%Y/%m/%d (%a) %H:%M')
        qs = []
        for qi, q in enumerate(s['qa']):
            cat = q['category']
            ans = q.get('adversarial_answer', q.get('answer')) if cat == 5 else q['answer']
            qs.append({'qid': f"{s['sample_id']}__q{qi}", 'type': CAT_NAMES[cat], 'question': q['question'], 'question_date': qdate,
                       'answer': str(ans), 'abstention': False})
        units.append({'unit_id': s['sample_id'], 'sessions': sessions, 'questions': qs})
    return units


def qid_table(units):
    return [(q['qid'], q['type']) for u in units for q in u['questions']]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=os.path.join(ROOT, 'data', 'locomo10.json')); ap.add_argument('--out', required=True)
    ap.add_argument('--write-ids', default='')
    a = ap.parse_args()
    units = build_units(json.load(open(a.data)))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w') as f:
        for u in units:
            f.write(json.dumps(u) + '\n')
    if a.write_ids:
        with open(a.write_ids, 'w') as f:
            f.write(''.join(f'{q}\t{t}\n' for q, t in qid_table(units)))
    from collections import Counter
    c = Counter(t for _, t in qid_table(units))
    print(len(units), 'units', sum(len(u['questions']) for u in units), 'questions', dict(sorted(c.items())),
          sum(len(u['sessions']) for u in units), 'sessions', sum(len(s['turns']) for u in units for s in u['sessions']), 'turns')
