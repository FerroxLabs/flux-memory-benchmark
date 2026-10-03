"""Shared helpers for every driver: units I/O, the 16 KiB context budget, the output row, a unit-parallel runner.
Adapted from the private h2h-oss harness (2026-09-30), unchanged in behaviour except row(capped=False) for the full-context ceiling."""
import json, os, sys, time, traceback
from multiprocessing import get_context

K = 20                      # retrieval k, every arm
ENVELOPE, PER_ITEM, MAX_BYTES = 200, 260, 16384   # tier2 offline_eval.cap (16 KiB service response)


def cap(items, limit=K, max_bytes=MAX_BYTES):
    """items: [{'content': str, ...}] best-first -> prefix that fits the 16 KiB budget (tier2 semantics)."""
    used, out = ENVELOPE, []
    for it in items[:limit]:
        used += PER_ITEM + len(json.dumps(it['content'], ensure_ascii=False).encode())
        if used > max_bytes:
            break
        out.append(it)
    return out


def load_units(path, only=None):
    units = [json.loads(l) for l in open(path)]
    if only:
        keep = set(only)
        units = [u for u in units if u['unit_id'] in keep]
    return units


def ledger_add(arm, stage, usd, units=1):
    """Put a stage's spend on the shared ledger (runner/ledger.py), so the $55 cap sees ingest and query spend as well as reader and judge spend."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'runner'))
    import ledger
    ledger.add(arm, stage, usd, units)  # bench comes from the BENCH environment variable ('lme' default, 'locomo')


def row(arm, q, items, search_ms, extra=None, capped=True):
    ctx = cap(items) if capped else items
    return {'arm': arm, 'qid': q['qid'], 'type': q['type'], 'question': q['question'], 'question_date': q['question_date'],
            'answer': q['answer'], 'abstention': q.get('abstention', False), 'n_retrieved': len(items), 'n_context': len(ctx),
            'search_ms': round(search_ms, 1),
            'context': [{'session_date': it.get('session_date') or '', 'role': it.get('role', 'user'), 'content': it['content']} for it in ctx],
            **(extra or {})}


def run_units(fn, units, out_dir, procs, init=None, initargs=()):
    """fn(unit) -> {'unit_id', 'ingest': {...}, 'rows': [...]}. Resumable: skips units already in out_dir/units.jsonl."""
    os.makedirs(out_dir, exist_ok=True)
    done_path = os.path.join(out_dir, 'units.jsonl')
    done = set()
    if os.path.exists(done_path):
        done = {json.loads(l)['unit_id'] for l in open(done_path)}
    todo = [u for u in units if u['unit_id'] not in done]
    print(f'{len(done)} done, {len(todo)} to run', file=sys.stderr, flush=True)
    t0 = time.time()
    with get_context('spawn').Pool(procs, init, initargs, maxtasksperchild=1) as pool:
        for n, res in enumerate(pool.imap_unordered(_safe, [(fn, u) for u in todo]), 1):
            with open(done_path, 'a') as f:
                f.write(json.dumps({'unit_id': res['unit_id'], 'ingest': res.get('ingest'), 'error': res.get('error')}) + '\n')
            if (res.get('ingest') or {}).get('llm_usd'):
                ledger_add(os.path.basename(os.path.normpath(out_dir)), 'ingest', res['ingest']['llm_usd'])
            if res.get('rows'):
                with open(os.path.join(out_dir, 'retrieved.jsonl'), 'a') as f:
                    for r in res['rows']:
                        f.write(json.dumps(r) + '\n')
            print(f"{n}/{len(todo)} {res['unit_id']} {time.time() - t0:.0f}s err={bool(res.get('error'))} {json.dumps(res.get('ingest'))[:200]}",
                  file=sys.stderr, flush=True)


def _safe(args):
    fn, u = args
    try:
        return fn(u)
    except Exception as e:  # noqa: BLE001
        return {'unit_id': u['unit_id'], 'error': f'{type(e).__name__}: {e}'[:500], 'trace': traceback.format_exc()[-1500:]}
