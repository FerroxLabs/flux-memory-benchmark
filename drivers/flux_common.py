"""Flux Memory arms over the PRODUCT retrieval code of the build under test (integration/phaseb @ a3b8a520), per-haystack isolation.

Adapted from the private quality2/attrib3 q2_ctx.py (the harness behind the LME-S 500 numbers: public 0.832, evidence 0.910). Every turn is one source.
  public   (arm flux_public)   : LexicalIndex + DenseIndex(bge-small) + RRF, LocalReranker top-30, then the product's store._recall_result
                                 (top-20, 16 KiB canonical cap, +-1 session neighbours nested in leftover bytes). This is what /v1/memory/recall returns.
  evidence (arm flux_evidence) : the product's evidence.assemble over the reranked top-20 turns + +-1 neighbours + extracted facts (facts._FactEntry),
                                 32 KiB, with the product's aggregation/advice branches. Facts come from drivers/flux_extract_facts.py.
This runs the release build's modules in-process (no HTTP, no Postgres): it measures ranking and assembly, the same code the API serves.
Required env: FLUX_SRC = a checkout of the Flux repo at the commit under test (its root holds src/flux_memory). Optional: EMB_CACHE (default work/emb).
Entry points: drivers/flux_public.py, drivers/flux_evidence.py.
"""
import argparse, json, os, sys, time, uuid
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ['FLUX_SRC'])
import numpy as np  # noqa: E402
from common import load_units, run_units  # noqa: E402

EMB = RR = FACTS = ARMS = QIDS = None
ACCESS = {'permission': 'read', 'authority': 'owner', 'vault_epoch': 1, 'grant_epoch': 1}


def init(threads, facts_path, arm_kind, qids):
    global EMB, RR, FACTS, ARMS, QIDS
    import torch
    torch.set_num_threads(threads)
    from src.flux_memory.retrieval import LocalEmbedder, LocalReranker
    EMB = LocalEmbedder('BAAI/bge-small-en-v1.5', max_tokens=512, batch=32, threads=threads)
    ARMS = [{'name': 'flux_public', 'kind': 'public'} if arm_kind == 'public' else {'name': 'flux_evidence', 'kind': 'evidence', 'product': True}]
    if any(a['kind'] != 'router' for a in ARMS):
        RR = LocalReranker('cross-encoder/ms-marco-MiniLM-L-6-v2', threads=threads)
    FACTS = {}
    if facts_path:
        for line in open(facts_path):
            r = json.loads(line)
            FACTS[r['session_id']] = r['facts']
    QIDS = set(open(qids).read().split()) if qids else None


def when(date, ti):
    return datetime.strptime(date, '%Y/%m/%d (%a) %H:%M').replace(tzinfo=timezone.utc) + timedelta(seconds=ti)


def strip_date(text):
    return text.split('] ', 1)[1] if text.startswith('[') and '] ' in text else text


def fact_key(unit_id, session_id):
    return session_id  # facts are keyed by the haystack session id


def cached(path, texts, query=False):
    if os.path.exists(path):
        v = np.load(path)
        if len(v) == len(texts):
            return v
    v = EMB.embed(texts, query=query).astype(np.float32) if texts else np.zeros((0, EMB.dim), np.float32)
    np.save(path + '.tmp.npy', v); os.replace(path + '.tmp.npy', path)
    return v


def one(u):
    from types import SimpleNamespace
    from src.flux_memory import evidence as ev
    from src.flux_memory.facts import _FactEntry
    from src.flux_memory.lexical_cache import LexicalIndex
    from src.flux_memory.retrieval import (RECALL_NEIGHBOURS, DenseIndex, HybridConfig, fts_expression, hybrid_order,
                                           lexical_terms, rerank)
    from src.flux_memory.store import MemoryStore
    qs = [q for q in u['questions'] if QIDS is None or q['qid'] in QIDS]
    if not qs:
        return {'unit_id': u['unit_id'], 'ingest': {'skipped': True}, 'rows': []}
    store = MemoryStore(None, None, hybrid=SimpleNamespace(recall_label=lambda: 'hybrid'))
    recs, by_id, fitems = [], {}, []
    for si, s in enumerate(u['sessions']):
        for ti, t in enumerate(s['turns']):
            at = when(s['date'], ti)
            sid = f"{u['unit_id']}__s{si}__t{ti}"
            row = {'client_event_id': str(uuid.uuid5(uuid.NAMESPACE_URL, sid)), 'text': t['content'],
                   'metadata': {'conversation_id': s['session_id'], 'role': t['role'], 'created_at': at.isoformat()},
                   'principal_id': '0' * 32, 'authority': 'owner', 'source_id': sid, 'revision': 1,
                   'created_at': at.isoformat(), 'updated_at': at.isoformat(), '_date': s['date'], '_si': si, '_ti': ti}
            recs.append(row); by_id[sid] = row
        for k, f in enumerate(FACTS.get(fact_key(u['unit_id'], s['session_id']), ())):
            w = f['turn'] // 24  # facts.FactProcessor.max_turns: the extraction window chunk this fact came from
            chunk = range(24 * w, min(len(s['turns']), 24 * w + 24))
            fitems.append({'id': f"{u['unit_id']}__s{si}__f{k}", 'derivation_id': f"{u['unit_id']}__s{si}__w{w}",
                           # product lineage = every turn of the window (36-char ids like store._id(), for byte cost)
                           'lineage': [(str(uuid.uuid5(uuid.NAMESPACE_URL, f"{u['unit_id']}__s{si}__t{x}")), 1) for x in chunk],
                           'text': strip_date(f['text']), 'entity': f.get('entity', ''), 'kind': f.get('kind'),
                           'date': s['date'], 'scope': {}, 'window_id': s['session_id'],
                           'source_id': f"{u['unit_id']}__s{si}__t{f['turn']}", 'revision': 1,
                           'supports': [f"{u['unit_id']}__s{si}__t{x}" for x in f.get('turns', [f['turn']])]})
    cache = os.environ.get('EMB_CACHE', 'work/emb'); os.makedirs(cache, exist_ok=True)
    vecs = cached(os.path.join(cache, f"{u['unit_id']}.npy"), [r['text'] for r in recs])
    idx = LexicalIndex(1)
    idx.apply([{'source_id': r['source_id'], 'erased': False, 'expires_at': None, 'created_at': r['created_at'], 'text': r['text'],
                'metadata': r['metadata']} for r in recs], lambda c: c, 1 << 34)
    dense_idx = DenseIndex(vecs.shape[1])
    dense_idx.upsert([(r['source_id'], vecs[i]) for i, r in enumerate(recs)])
    fentry = None
    if fitems and any(a['kind'] == 'evidence' for a in ARMS):
        fv = cached(os.path.join(cache, f"{u['unit_id']}.facts-{len(fitems)}.npy"), [f['text'] for f in fitems])
        fentry = _FactEntry(epoch=1, dim=fv.shape[1])
        fentry.add(fitems, list(fv))
    qvecs = EMB.embed([q['question'] for q in qs], query=True).astype(np.float32)
    out = []
    for qi, q in enumerate(qs):
        t0 = time.time()
        terms = lexical_terms(q['question'])
        lex = idx.search(fts_expression(terms), HybridConfig().candidates, 0) if terms else []
        dense = dense_idx.search(qvecs[qi], HybridConfig().candidates)
        fused = hybrid_order(lex, dense)
        t_fused = time.time() - t0
        rr = None
        for arm in ARMS:
            t1 = time.time()
            if arm['kind'] in ('public', 'evidence') and rr is None:
                rr = rerank(q['question'], fused, lambda i: by_id[i]['text'], RR, HybridConfig(rerank_top=arm.get('rerank_top', 30)))
            order = {'fused': fused, 'dense': dense}[arm.get('order', 'fused')] if arm['kind'] == 'router' else rr
            if arm.get('roles') == 'user' and not arm.get('session_focus'):
                order = [i for i in order if by_id[i]['metadata']['role'] == 'user']
            ctx, ids, fsup, size, frank, advice, agg = [], [], [], 0, [], False, False
            if arm['kind'] in ('router', 'public'):
                k = arm.get('k', 20)
                ranked = [{k2: v for k2, v in by_id[i].items() if not k2.startswith('_')} for i in order[:k + 1]]
                top = {r['source_id'] for r in ranked[:k]}
                near = idx.neighbours([r['source_id'] for r in ranked[:k]], RECALL_NEIGHBOURS, 0) if arm.get('neighbours', True) else {}
                near = {h: [(off, by_id[s]) for off, s in ns if s not in top and (arm.get('nb_roles') != 'user' or by_id[s]['metadata']['role'] == 'user')]
                        for h, ns in near.items()}
                res = store._recall_result(ACCESS, terms, ranked, None, k, arm.get('max_bytes', 16384), near)
                for item in res['results']:
                    c = item.get('context', [])
                    for e in [e for e in c if e['offset'] < 0] + [dict(item, offset=0)] + [e for e in c if e['offset'] > 0]:
                        src = by_id[e['source_id']]
                        ctx.append({'session_date': src['_date'], 'role': src['metadata']['role'], 'content': src['text']})
                        ids.append(e['source_id'])
                size = len(json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
            else:
                def turn(i):
                    r = by_id[i]
                    return {'source_id': i, 'revision': 1, 'text': r['text'], 'metadata': {'role': r['metadata']['role']},
                            'window_id': r['metadata']['conversation_id'], 'position': r['_ti'], 'date': r['_date']}
                hits = [turn(i) for i in order[:arm.get('limit', 20)]]

                def near_of(sid, radius=arm.get('radius', 1)):
                    stem, ti = sid.rsplit('__t', 1)
                    return [turn(f'{stem}__t{int(ti) + d}') for d in range(-radius, radius + 1)
                            if d and f'{stem}__t{int(ti) + d}' in by_id]
                fh, frank = [], []
                fact_limit, kw = arm.get('fact_limit', ev.FACT_LIMIT), {k: arm[k] for k in ('fact_share',) if k in arm}
                product = arm.get('product')  # emulate evidence.recall's branches with the product's own detectors/constants
                agg = product and ev.is_aggregation(q['question'])
                advice = product and hasattr(ev, 'is_advice') and ev.is_advice(q['question'])
                if agg:
                    fact_limit, kw = max(fact_limit, ev.AGG_FACT_LIMIT), dict(kw, fact_share=ev.AGG_FACT_SHARE, dedupe=True)
                if fentry is not None and arm.get('facts', True) and not advice:
                    frank = fentry.search(q['question'], qvecs[qi], 60)
                    fh = frank[:fact_limit]
                if advice:  # evidence._advice_focus: user turns of the top ADVICE_CONVERSATIONS conversations in dense order
                    convs = []
                    for i in dense:
                        cv = by_id[i]['metadata']['conversation_id']
                        if cv not in convs:
                            convs.append(cv)
                        if len(convs) >= ev.ADVICE_CONVERSATIONS:
                            break
                    hits = []
                    for cv in convs:
                        anchor = next(i for i in dense if by_id[i]['metadata']['conversation_id'] == cv)
                        ti0, stem = by_id[anchor]['_ti'], anchor.rsplit('__t', 1)[0]
                        for x in range(max(0, ti0 - ev.ADVICE_RADIUS), ti0 + ev.ADVICE_RADIUS + 1):
                            sid = f'{stem}__t{x}'
                            if sid in by_id and by_id[sid]['metadata']['role'] == 'user':
                                hits.append(dict(turn(sid), window_id='advice:' + cv))
                    res = ev.assemble(hits, [], lambda sid: [], max_bytes=arm.get('max_bytes', ev.EVIDENCE_MAX_BYTES))
                else:
                    res = ev.assemble(hits, fh, near_of, max_bytes=arm.get('max_bytes', ev.EVIDENCE_MAX_BYTES), **kw)
                for f in res['facts']:
                    ctx.append({'session_date': f['date'], 'role': 'fact', 'content': f['text']})
                    fsup.extend(next((x['supports'] for x in fitems if x['id'] == f['id']), [f['source_id']]))
                for t in res['results']:
                    ctx.append({'session_date': t['date'], 'role': t['metadata']['role'], 'content': t['text']})
                    ids.append(t['source_id'])
                size = len(json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
            ms = (t_fused + time.time() - t1) * 1e3
            out.append({'arm': arm['name'], 'qid': q['qid'], 'type': q['type'], 'question': q['question'],
                        'question_date': q['question_date'], 'answer': q['answer'], 'abstention': q.get('abstention', False),
                        'n_context': len(ctx), 'bytes': size, 'search_ms': round(ms, 1), 'context': ctx,
                        'ctx_turn_ids': ids, 'fact_support_ids': sorted(set(fsup)), 'retrieved_ids': order[:20],
                        'fact_rank': [[f['id'], f['source_id']] for f in frank] if arm['kind'] == 'evidence' else [],
                        'branch': ('advice' if advice else 'agg' if agg else 'evidence') if arm['kind'] == 'evidence' else arm['kind']})
    idx.close()
    return {'unit_id': u['unit_id'], 'ingest': {'turns': len(recs), 'facts': len(fitems)}, 'rows': out}


def main(arm_kind):
    ap = argparse.ArgumentParser()
    ap.add_argument('--units', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--facts', default=''); ap.add_argument('--qids', default='')
    ap.add_argument('--procs', type=int, default=4); ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    if arm_kind == 'evidence' and not a.facts:
        sys.exit('flux_evidence needs --facts (run drivers/flux_extract_facts.py first)')
    units = load_units(a.units)
    if a.qids:
        keep = set(open(a.qids).read().split())
        units = [u for u in units if any(q['qid'] in keep for q in u['questions'])]
    run_units(one, units, a.out, a.procs, init, (a.threads, a.facts, arm_kind, a.qids))
