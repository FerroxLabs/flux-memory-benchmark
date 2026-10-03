"""Run Flux's own LLM fact extractor (src/flux_memory/llm_extraction.py of the build under test, PROMPT_VERSION 4) over every distinct haystack session
of the drawn units. Used only by the flux_evidence arm. DeepSeek direct, thinking disabled, JSON mode, max_tokens 2000 (= facts.FluxRouterCompleter).
Adapted from the private attrib3 extract_ds.py. Output = one line per session: session_id, date, facts[{text, entity, kind, turn, quote, subject}].
Resumable (--skip-done). The cost is appended to results/ledger.jsonl (arm flux_evidence, stage extract). Measured privately at about $0.00043 per session.
Required env: FLUX_SRC (Flux checkout at the commit under test), DEEPSEEK_API_KEY. Optional: EX_WORKERS (default 8), READER_INFLIGHT.

usage: flux_extract_facts.py --units work/units_n100.jsonl --out work/facts_n100.jsonl [--skip-done]
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.environ['FLUX_SRC'])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'runner'))
import llm  # noqa: E402
import ledger  # noqa: E402
from src.flux_memory.config import MemoryError  # noqa: E402
from src.flux_memory.llm_extraction import PROMPT_VERSION, build_prompt, fact_text, parse_facts  # noqa: E402

EXTRA = ('applies_to', 'replaces', 'about')  # v3 preference fields, when present


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--reserve', type=float, default=0.0)
    ap.add_argument('--skip-done', action='store_true')
    a = ap.parse_args()
    sessions, seen = [], set()
    for l in open(a.units):  # distinct haystack sessions across all units (shared sessions are extracted once)
        for s_ in json.loads(l)['sessions']:
            if s_['session_id'] not in seen:
                seen.add(s_['session_id']); sessions.append({'session_id': s_['session_id'], 'date': s_['date'], 'turns': s_['turns']})
    if a.skip_done and os.path.exists(a.out):
        done = {json.loads(l)['session_id'] for l in open(a.out)}
        sessions = [s for s in sessions if s['session_id'] not in done]
    if not sessions:
        print('nothing to do'); return
    turns_of = {s['session_id']: [{'role': t['role'], 'text': t.get('content', t.get('text')), **({'speaker': t['speaker']} if t.get('speaker') else {})}
                                  for t in s['turns']] for s in sessions}

    def participants(sid):  # multi-party transcripts carry a speaker on every turn; LongMemEval turns do not, so this is None
        return list(dict.fromkeys(t['speaker'] for t in turns_of[sid] if t.get('speaker'))) or None
    if ledger.over_cap(a.reserve):
        sys.exit('spend cap: committed + reserve would pass the cap')
    stats = {'ok': 0, 'invalid': 0, 'error': 0, 'facts': 0, 'dropped': 0}

    def one(s):
        turns = turns_of[s['session_id']]
        try:
            r = llm.deepseek(build_prompt(s['date'], turns, participants(s['session_id'])), 2000, thinking=False, json_mode=True, timeout=180)
        except llm.Breaker:
            raise
        except Exception as e:  # noqa: BLE001
            return {'session_id': s['session_id'], 'error': str(e)[:120]}
        try:
            claims, dropped = parse_facts(r['content'], turns, s['date'], participants(s['session_id']))
        except MemoryError as e:
            return {'session_id': s['session_id'], 'invalid': e.code}
        raw = {}
        try:  # keep v3 extra fields (parse_facts may or may not carry them)
            import re
            items = json.loads(re.search(r'\{.*\}', r['content'], re.S).group(0))['facts']
            raw = {it.get('fact', '').strip()[:400]: it for it in items if isinstance(it, dict)}
        except Exception:  # noqa: BLE001
            pass
        facts = []
        for c in claims:
            f = {'text': fact_text(c), 'entity': c['entity'], 'kind': c['predicate'], 'turn': int(c['support'][0]['source_id']),
                 'quote': c['support'][0]['quote'][:200], 'subject': c.get('subject', 'user')}
            for k in EXTRA:
                v = c.get(k, (raw.get(c['value']) or {}).get(k))
                if isinstance(v, str) and v.strip():
                    f[k] = v.strip()[:120]
            facts.append(f)
        return {'session_id': s['session_id'], 'date': s['date'], 'dropped': dropped, 'prompt_version': PROMPT_VERSION,
                'facts': facts, 'prompt_tokens': (r.get('usage') or {}).get('prompt_tokens'),
                'completion_tokens': (r.get('usage') or {}).get('completion_tokens'),
                'about_missing': sum(1 for it in raw.values() if not isinstance(it.get('about'), str))}

    # parse_facts names support by turn index when turns carry no source_id
    for s in sessions:
        for i, t in enumerate(turns_of[s['session_id']]):
            t['source_id'] = str(i)
    try:
        with ThreadPoolExecutor(int(os.environ.get('EX_WORKERS', '8'))) as ex, open(a.out, 'a') as f:
            futs = [ex.submit(one, s) for s in sessions]
            for n, fu in enumerate(as_completed(futs), 1):
                rec = fu.result()
                if 'facts' in rec:
                    stats['ok'] += 1; stats['facts'] += len(rec['facts']); stats['dropped'] += rec['dropped']
                    f.write(json.dumps(rec) + '\n'); f.flush()
                else:
                    stats['invalid' if 'invalid' in rec else 'error'] += 1
                if n % 200 == 0:
                    print(f'{n}/{len(sessions)} {stats} ${llm.READER.cost:.3f}', flush=True)
    finally:
        ledger.add('flux_evidence', 'extract', llm.READER.cost, len(sessions))
    print(json.dumps({'cost_usd': round(llm.READER.cost, 6), **stats, 'offmodel': llm.READER.offmodel}))


if __name__ == '__main__':
    main()
