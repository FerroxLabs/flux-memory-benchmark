"""Regenerate every number in REPORT.md (and the Honcho block of COST.md) from results-public/. Deterministic.

Inputs (all committed): results-public/{lme,locomo}/<arm>.jsonl (stripped per-item results), results-public/ingest/<bench>/<arm>.jsonl,
results-public/ledger.jsonl, results-public/run-logs/ (qa-*.out summaries, progress.log). Dependencies: Python 3 stdlib and numpy (already in requirements.txt).
Statistics: Wilson 95% interval; exact two-sided McNemar on identical items; paired bootstrap 95% interval (10,000 resamples, numpy default_rng seed 20261003);
for LoCoMo also a conversation-clustered paired bootstrap (resample the 10 conversations with replacement, keep all their questions).
Holm correction is applied across the 7 comparisons made against each Flux arm within one item set.
usage: python3 analysis/report.py            rewrite the GEN blocks of REPORT.md and COST.md and write analysis/tables/report_tables.md
       python3 analysis/report.py --check    exit 1 if the committed REPORT.md / COST.md differ from what this script produces
"""
import argparse, collections, json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402  (wilson, mcnemar_exact, holm)

ROOT = analyze.ROOT
PUB = os.path.join(ROOT, 'results-public')
SEED, BOOT = 20261003, 10000
ARMS = ['full_context', 'flux_evidence', 'flux_public', 'honcho_retrieval', 'honcho_chat', 'letta', 'mem0', 'closed_book']
FLUX = ['flux_public', 'flux_evidence']
MONTH_TURNS, MONTH_RECALLS = 600, 100  # kit profile: 30 sessions x 20 turns, 100 recalls (README "Cost table and usage profile")
CATS = ['cat1-multi-hop', 'cat2-temporal', 'cat3-open-domain', 'cat4-single-hop', 'cat5-adversarial']


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def load():
    D = {}
    for bench in ('lme', 'locomo'):
        D[bench] = {a: {r['qid']: r for r in jl(os.path.join(PUB, bench, a + '.jsonl'))} for a in ARMS}
        ids = [set(v) for v in D[bench].values()]
        assert all(i == ids[0] for i in ids), f'{bench}: arms do not cover identical items'
    return D


def summ(bench, arm):
    p = os.path.join(PUB, 'run-logs', f'qa-{bench}-{arm}.out')
    last = [l for l in open(p) if l.startswith('{')][-1]
    return json.loads(last)


def pc(x, d=1):
    return f'{100 * x:.{d}f}'


def pm(x):
    return f'{100 * x:+.1f}'


def boot_iid(d):
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(d), size=(BOOT, len(d)))
    m = d[idx].mean(axis=1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def boot_cluster(d, conv):
    rng = np.random.default_rng(SEED)
    names = sorted(set(conv))
    S = np.array([d[[c == n for c in conv]].sum() for n in names], dtype=float)
    N = np.array([sum(1 for c in conv if c == n) for n in names], dtype=float)
    idx = rng.integers(0, len(names), size=(BOOT, len(names)))
    m = S[idx].sum(axis=1) / N[idx].sum(axis=1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def item_sets(D):
    """name -> (bench, [qids])"""
    lme = sorted(D['lme']['flux_public'])
    lo = sorted(D['locomo']['flux_public'])
    typ = {q: D['locomo']['flux_public'][q]['type'] for q in lo}
    return {'LongMemEval-S (n=100)': ('lme', lme),
            'LoCoMo categories 1-4 (n=%d, preregistered headline)' % sum(1 for q in lo if not typ[q].startswith('cat5')): ('locomo', [q for q in lo if not typ[q].startswith('cat5')]),
            'LoCoMo all five categories (n=%d, the figure in the qa summaries)' % len(lo): ('locomo', lo),
            'LoCoMo category 5 adversarial (n=%d)' % sum(1 for q in lo if typ[q].startswith('cat5')): ('locomo', [q for q in lo if typ[q].startswith('cat5')])}


def acc_table(D, name, bench, qids):
    L = [f'| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty | Qa-summary accuracy % | Match |', '|---|---|---|---|---|---|---|---|']
    for a in ARMS:
        rows = [D[bench][a][q] for q in qids]
        k = sum(r['correct'] for r in rows)
        lo, hi = analyze.wilson(k, len(rows))
        err = sum(1 for r in rows if r['verdict'] == 'error')
        emp = sum(1 for r in rows if r['verdict'] == 'empty')
        s = summ(bench, a)['accuracy']
        full = len(qids) == len(D[bench][a])
        sc = f'{100 * s:.2f}' if full else 'n/a (subset)'
        ok = ('yes' if abs(s - k / len(rows)) < 5e-5 else 'NO') if full else '-'
        L.append(f'| {a} | {k}/{len(rows)} | {pc(k / len(rows))} | {pc(lo)} to {pc(hi)} | {err} | {emp} | {sc} | {ok} |')
    return '\n'.join(L)


def paired_table(D, name, bench, qids):
    conv = [q.split('__')[0] for q in qids] if bench == 'locomo' else None
    L = [f'**{name}.** Difference = Flux arm minus the other arm, percentage points (positive favours Flux). Bootstrap: 10,000 resamples, seed {SEED}.', '']
    hdr = '| Flux arm | Other arm | Diff pts | Item bootstrap 95% | ' + ('Conversation-clustered 95% | ' if conv else '') + 'Flux only right | Other only right | McNemar p | Holm p |'
    L += [hdr, '|' + '---|' * (hdr.count('|') - 1)]
    for fa in FLUX:
        res = []
        for oa in ARMS:
            if oa == fa:
                continue
            f = {q: D[bench][fa][q]['correct'] for q in qids}
            o = {q: D[bench][oa][q]['correct'] for q in qids}
            x, y, p = analyze.mcnemar_exact(f, o, qids)
            d = np.array([f[q] - o[q] for q in qids], dtype=float)
            res.append((oa, d.mean(), boot_iid(d), boot_cluster(d, conv) if conv else None, x, y, p))
        adj = analyze.holm({r[0]: r[6] for r in res})
        for oa, m, bi, bc, x, y, p in res:
            row = f'| {fa} | {oa} | {pm(m)} | {pm(bi[0])} to {pm(bi[1])} | ' + (f'{pm(bc[0])} to {pm(bc[1])} | ' if conv else '') + f'{x} | {y} | {p:.4g} | {adj[oa]:.4g} |'
            L.append(row)
    return '\n'.join(L)


def cat_tables(D):
    out = []
    lo = D['locomo']
    q0 = sorted(lo['flux_public'])
    cnt = collections.Counter(lo['flux_public'][q]['type'] for q in q0)
    out.append('**LoCoMo, per category** (correct/n, accuracy %; Wilson 95% in brackets)\n')
    out.append('| Arm | ' + ' | '.join(f'{c} (n={cnt[c]})' for c in CATS) + ' |')
    out.append('|---|' + '---|' * len(CATS))
    for a in ARMS:
        cells = []
        for c in CATS:
            k = sum(lo[a][q]['correct'] for q in q0 if lo[a][q]['type'] == c)
            w = analyze.wilson(k, cnt[c])
            cells.append(f'{k}/{cnt[c]} {pc(k / cnt[c])} [{pc(w[0], 0)}-{pc(w[1], 0)}]')
        out.append(f'| {a} | ' + ' | '.join(cells) + ' |')
    lm = D['lme']
    q1 = sorted(lm['flux_public'])
    types = sorted({lm['flux_public'][q]['type'] for q in q1})
    cnt = collections.Counter(lm['flux_public'][q]['type'] for q in q1)
    out.append('\n**LongMemEval-S, per question type** (correct/n, accuracy %; types have 6 to 27 questions, so intervals are wide and are omitted)\n')
    out.append('| Arm | ' + ' | '.join(f'{t} (n={cnt[t]})' for t in types) + ' |')
    out.append('|---|' + '---|' * len(types))
    for a in ARMS:
        cells = []
        for t in types:
            k = sum(lm[a][q]['correct'] for q in q1 if lm[a][q]['type'] == t)
            cells.append(f'{k}/{cnt[t]} {pc(k / cnt[t], 0)}')
        out.append(f'| {a} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)


def ledger():
    rows = jl(os.path.join(PUB, 'ledger.jsonl'))
    d = collections.defaultdict(float)
    for r in rows:
        d[(r['bench'], r['arm'], r['stage'])] += r['usd']
    return d, sum(r['usd'] for r in rows)


def cost_table(D):
    led, total = ledger()
    L = []
    for bench, title in (('lme', 'LongMemEval-S'), ('locomo', 'LoCoMo')):
        L.append(f'**{title}** (USD; reader and judge from the qa summaries; ingestion, extraction and query from `results-public/ledger.jsonl`)\n')
        L.append('| Arm | Reader | Judge | Ingest / extraction | Memory-system LLM at query | Ledger total for the arm |')
        L.append('|---|---|---|---|---|---|')
        for a in ARMS:
            s = summ(bench, a)
            ing = led.get((bench, a, 'ingest'), 0) + led.get((bench, a, 'extract'), 0)
            q = led.get((bench, a, 'query'), 0)
            tot = sum(v for (b, ar, st), v in led.items() if b == bench and ar == a)
            note_i = ' (shared ingest with honcho_retrieval; see below)' if a == 'honcho_chat' else ''
            qs = f'{q:.4f} (retrieval and dialectic combined)' if a == 'honcho_retrieval' else (f'{q:.4f}' if q else '0')
            L.append(f'| {a} | {s["reader_usd"]:.4f} | {s["judge_usd"]:.4f} | {ing:.4f}{note_i} | {qs} | {tot:.4f} |')
        L.append('')
    L.append(f'Total spend in the ledger: **${total:.4f}** (progress.log final line: ' + final_spend() + ').')
    L.append('Honcho: ingestion for both Honcho arms was done once and is booked under `honcho_retrieval`; the query-time LLM spend (the dialectic calls) is booked under `honcho_retrieval` too, because both arms ran in the same process (`--arms ctx,chat`). Honcho retrieval (`peer.context` with a search query) makes no chat-model call as far as the driver shows, so this query spend is attributed below to the dialectic (chat) arm; that attribution is an inference from the driver code, not a separate measurement. The Honcho proxy log that would separate the two was not copied.')
    return '\n'.join(L)


def final_spend():
    for l in open(os.path.join(PUB, 'run-logs', 'progress.log')):
        m = re.search(r'final spend_total=([\d.]+)', l)
        if m:
            return f'{m.group(1)}'
    return 'not found'


def ingest_table():
    L = ['| Bench | Arm | Units | Items posted | Items dropped | Mean ingest s per unit | Mean ingest LLM USD per unit |', '|---|---|---|---|---|---|---|']
    for bench in ('lme', 'locomo'):
        for a in ('flux_public', 'flux_evidence', 'mem0', 'letta', 'honcho_retrieval'):
            u = jl(os.path.join(PUB, 'ingest', bench, a + '.jsonl'))
            if not u:
                continue
            tot = sum(r.get('items_total', r.get('turns', 0)) for r in u)
            dr = sum(r.get('items_dropped', 0) for r in u)
            sec = np.mean([r.get('seconds', 0) for r in u])
            usd = np.mean([r.get('llm_usd', 0) for r in u])
            L.append(f'| {bench} | {a} | {len(u)} | {tot} | {dr} | {sec:.1f} | {usd:.4f} |')
    L.append('\nFlux evidence ingest figures reuse cached embeddings from flux_public (seconds are not comparable); its extraction cost is in the cost table. Items are turns for Flux and Honcho, sessions for mem0, passages for Letta.')
    return '\n'.join(L)


def honcho_month(D):
    """Measured LLM cost of running Honcho as configured here, per active user-month, kit profile: 600 turns ingested + 100 recalls."""
    led, _ = ledger()
    L = []
    rows = {}
    for bench, title in (('lme', 'LongMemEval-S'), ('locomo', 'LoCoMo')):
        u = jl(os.path.join(PUB, 'ingest', bench, 'honcho_retrieval.jsonl'))
        turns = sum(r['messages_posted'] for r in u)
        ing = led[(bench, 'honcho_retrieval', 'ingest')]
        nq = len(D[bench]['honcho_chat'])
        q = led[(bench, 'honcho_retrieval', 'query')]
        per_turn = ing / turns
        per_q = q / nq
        rows[bench] = (title, ing, turns, per_turn, q, nq, per_q)
    L.append('| Corpus | Ledger ingest USD | Turns posted | USD per turn | Ledger query USD | Questions | USD per query | Retrieval arm: 600 x USD/turn | Chat arm: 600 x USD/turn + 100 x USD/query |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for bench, (title, ing, turns, per_turn, q, nq, per_q) in rows.items():
        r = MONTH_TURNS * per_turn
        c = r + MONTH_RECALLS * per_q
        L.append(f'| {title} | {ing:.4f} | {turns} | {per_turn:.7f} | {q:.4f} | {nq} | {per_q:.6f} | ${r:.4f} | ${c:.4f} |')
    return '\n'.join(L)


def key_findings(D):
    lo = D['locomo']
    q = sorted(lo['flux_public'])
    q14 = [x for x in q if not lo['flux_public'][x]['type'].startswith('cat5')]
    A = lambda a, qs: sum(lo[a][x]['correct'] for x in qs) / len(qs)  # noqa: E731
    L = []
    L.append(f'On LoCoMo (all five categories, the figure in the qa summaries), the Honcho chat arm scored **{pc(A("honcho_chat", q))}%**. That is above every Flux arm (flux_public {pc(A("flux_public", q))}%, flux_evidence {pc(A("flux_evidence", q))}%) and above full context ({pc(A("full_context", q))}%). '
             f'On categories 1 to 4 only (the preregistered headline, n={len(q14)}) the figures are: honcho_chat {pc(A("honcho_chat", q14))}%, full_context {pc(A("full_context", q14))}%, flux_public {pc(A("flux_public", q14))}%, flux_evidence {pc(A("flux_evidence", q14))}%, honcho_retrieval {pc(A("honcho_retrieval", q14))}%, mem0 {pc(A("mem0", q14))}%, letta {pc(A("letta", q14))}%, closed_book {pc(A("closed_book", q14))}%.')
    lm = D['lme']
    ql = sorted(lm['flux_public'])
    B = lambda a: sum(lm[a][x]['correct'] for x in ql) / len(ql)  # noqa: E731
    L.append(f'On LongMemEval-S (n={len(ql)}): full_context {pc(B("full_context"), 0)}%, flux_evidence {pc(B("flux_evidence"), 0)}%, flux_public {pc(B("flux_public"), 0)}%, honcho_retrieval {pc(B("honcho_retrieval"), 0)}%, honcho_chat {pc(B("honcho_chat"), 0)}%, letta {pc(B("letta"), 0)}%, mem0 {pc(B("mem0"), 0)}%, closed_book {pc(B("closed_book"), 0)}%.')
    return '\n\n'.join(L)


def blocks(D):
    S = item_sets(D)
    acc = []
    for name, (bench, qids) in S.items():
        acc.append(f'**{name}**\n\n' + acc_table(D, name, bench, qids) + '\n')
    pair = '\n\n'.join(paired_table(D, n, b, q) for n, (b, q) in S.items())
    out = {'key_findings': key_findings(D), 'accuracy': '\n'.join(acc), 'paired': pair, 'categories': cat_tables(D), 'cost': cost_table(D),
           'ingest': ingest_table(), 'honcho_month': honcho_month(D)}
    R = load_reason(D)
    if R:
        out['reason'] = reason_block(D, R)
        T = load_temporal(D)
        if T:
            out['temporal'] = temporal_block(D, R, T)
    return out


# ---------- exploratory arm added after the main run (PREREG-ADDENDUM-flux_reason.md); nothing above this line reads it ----------
REASON = 'flux_reason'
REF = ['flux_evidence', 'flux_public', 'honcho_chat']
REASON_THRESHOLD = 1214  # preregistered: within 5.0 points of honcho_chat on LoCoMo categories 1-4 = at least 1,214 of 1,540 correct


def load_reason(D):
    """-> {bench: {qid: stripped row}} or None when the arm has not been added (the main report is unchanged)."""
    R = {b: {r['qid']: r for r in jl(os.path.join(PUB, b, REASON + '.jsonl'))} for b in ('lme', 'locomo')}
    if not all(R.values()):
        return None
    for b in R:
        assert set(R[b]) == set(D[b]['flux_public']), f'{b}: {REASON} does not cover identical items'
    return R


def reason_summ(bench):
    p = os.path.join(PUB, 'run-logs', f'qa-{bench}-{REASON}.out')
    return json.loads([l for l in open(p) if l.startswith('{')][-1])


def reason_block(D, R):
    S = item_sets(D)
    sets = [(n, b, q) for n, (b, q) in S.items() if not n.startswith('LoCoMo all five')]
    L = []
    L.append('**Accuracy** (reference arms are the main run\'s numbers, repeated here for comparison only)\n')
    for name, bench, qids in sets:
        L.append(f'**{name}**\n')
        L.append('| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |')
        L.append('|---|---|---|---|---|---|')
        for a in [REASON] + REF:
            src = R[bench] if a == REASON else D[bench][a]
            rows = [src[q] for q in qids]
            k = sum(r['correct'] for r in rows)
            lo, hi = analyze.wilson(k, len(rows))
            L.append(f"| {a} | {k}/{len(rows)} | {pc(k / len(rows))} | {pc(lo)} to {pc(hi)} | {sum(1 for r in rows if r['verdict'] == 'error')} | {sum(1 for r in rows if r['verdict'] == 'empty')} |")
        L.append('')
    # paired
    L.append(f'**Paired differences.** Difference = {REASON} minus the other arm, percentage points (positive favours {REASON}), on identical items. Bootstrap: 10,000 resamples, seed {SEED}. Holm is applied across these 3 comparisons within each item set; these tests stand on their own and are not part of the main report\'s Holm family.\n')
    for name, bench, qids in sets:
        conv = [q.split('__')[0] for q in qids] if bench == 'locomo' else None
        L.append(f'**{name}**\n')
        hdr = f'| Other arm | Diff pts | Item bootstrap 95% | ' + ('Conversation-clustered 95% | ' if conv else '') + f'{REASON} only right | Other only right | McNemar p | Holm p |'
        L += [hdr, '|' + '---|' * (hdr.count('|') - 1)]
        res = []
        for oa in REF:
            f = {q: R[bench][q]['correct'] for q in qids}
            o = {q: D[bench][oa][q]['correct'] for q in qids}
            x, y, p = analyze.mcnemar_exact(f, o, qids)
            d = np.array([f[q] - o[q] for q in qids], dtype=float)
            res.append((oa, d.mean(), boot_iid(d), boot_cluster(d, conv) if conv else None, x, y, p))
        adj = analyze.holm({r[0]: r[6] for r in res})
        for oa, m, bi, bc, x, y, p in res:
            L.append(f'| {oa} | {pm(m)} | {pm(bi[0])} to {pm(bi[1])} | ' + (f'{pm(bc[0])} to {pm(bc[1])} | ' if conv else '') + f'{x} | {y} | {p:.4g} | {adj[oa]:.4g} |')
        L.append('')
    # categories and types
    lo = D['locomo']; q0 = sorted(lo['flux_public']); cnt = collections.Counter(lo['flux_public'][q]['type'] for q in q0)
    L.append('**LoCoMo, per category** (correct/n, accuracy %)\n')
    L.append('| Arm | ' + ' | '.join(f'{c} (n={cnt[c]})' for c in CATS) + ' |'); L.append('|---|' + '---|' * len(CATS))
    for a in [REASON] + REF:
        src = R['locomo'] if a == REASON else lo[a]
        L.append(f'| {a} | ' + ' | '.join(f"{sum(src[q]['correct'] for q in q0 if src[q]['type'] == c)}/{cnt[c]} {pc(sum(src[q]['correct'] for q in q0 if src[q]['type'] == c) / cnt[c])}" for c in CATS) + ' |')
    lm = D['lme']; q1 = sorted(lm['flux_public']); types = sorted({lm['flux_public'][q]['type'] for q in q1}); cnt = collections.Counter(lm['flux_public'][q]['type'] for q in q1)
    L.append('\n**LongMemEval-S, per question type** (correct/n, accuracy %; cells of 6 to 27 questions, not tested)\n')
    L.append('| Arm | ' + ' | '.join(f'{t} (n={cnt[t]})' for t in types) + ' |'); L.append('|---|' + '---|' * len(types))
    for a in [REASON] + REF:
        src = R['lme'] if a == REASON else lm[a]
        L.append(f'| {a} | ' + ' | '.join(f"{sum(src[q]['correct'] for q in q1 if src[q]['type'] == t)}/{cnt[t]} {pc(sum(src[q]['correct'] for q in q1 if src[q]['type'] == t) / cnt[t], 0)}" for t in types) + ' |')
    # verdict
    q14 = S[[n for n in S if n.startswith('LoCoMo categories 1-4')][0]][1]
    k = sum(R['locomo'][q]['correct'] for q in q14)
    kh = sum(D['locomo']['honcho_chat'][q]['correct'] for q in q14)
    ke = sum(D['locomo']['flux_evidence'][q]['correct'] for q in q14)
    closed = (kh - ke) and (k - ke) / (kh - ke)
    L.append(f'\n**Verdict against the preregistered threshold** (within 5.0 points of honcho_chat on LoCoMo categories 1 to 4, that is at least {REASON_THRESHOLD} of {len(q14)} correct): {REASON} scored {k}/{len(q14)} ({pc(k / len(q14))}%), honcho_chat {kh}/{len(q14)} ({pc(kh / len(q14))}%), flux_evidence {ke}/{len(q14)} ({pc(ke / len(q14))}%). '
             f'Gap to honcho_chat: {pm((k - kh) / len(q14))} points; share of the honcho_chat minus flux_evidence gap closed: {pc(closed, 0)}%. Verdict: **{"closes most of the gap" if k >= REASON_THRESHOLD else "does not close most of the gap"}**.')
    # cost and errors
    L.append('\n**Cost and failures** (USD; pass 1 = the reasoning call, pass 2 = reader plus judge, both from the arm\'s own summaries)\n')
    L.append('| Bench | Pass 1 | Pass 2 reader | Pass 2 judge | Arm total | Pass-1 failures | Empty notes | Rows scored as error | Empty reader answers |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    tot = 0.0
    for bench, title in (('lme', 'LongMemEval-S'), ('locomo', 'LoCoMo')):
        s = reason_summ(bench); t = s['pass1_usd'] + s['reader_usd'] + s['judge_usd']; tot += t
        emp = sum(1 for r in R[bench].values() if r['verdict'] == 'empty')
        L.append(f"| {title} | {s['pass1_usd']:.4f} | {s['reader_usd']:.4f} | {s['judge_usd']:.4f} | {t:.4f} | {s['pass1_errors']} | {s['pass1_empty_notes']} | {s['errors']} | {emp} |")
    led = jl(os.path.join(PUB, 'ledger-flux_reason.jsonl'))
    L.append(f"\nArm total {tot:.4f} USD from the summaries; ledger lines for the arm (`results-public/ledger-flux_reason.jsonl`) sum to {sum(r['usd'] for r in led):.4f} USD against the arm's cap of 10 USD. "
             f"The qa summaries record prompt_sha256 `{reason_summ('lme')['prompt_sha256'][:16]}...` (LongMemEval) and `{reason_summ('locomo')['prompt_sha256'][:16]}...` (LoCoMo), equal to the honcho_chat arm's: "
             f"{'yes' if reason_summ('lme')['prompt_sha256'] == summ('lme', 'honcho_chat')['prompt_sha256'] and reason_summ('locomo')['prompt_sha256'] == summ('locomo', 'honcho_chat')['prompt_sha256'] else 'NO'}.")
    return '\n'.join(L)


# ---------- exploratory arm flux_temporal (PREREG-ADDENDUM-flux_temporal.md); exploratory, post hoc, in-sample ----------
TEMP = 'flux_temporal'
BAR_I, BAR_II, BAR_III = 4.0, -2.0, -2.0  # points; preregistered


def load_temporal(D):
    T = {b: {r['qid']: r for r in jl(os.path.join(PUB, b, TEMP + '.jsonl'))} for b in ('lme', 'locomo')}
    if not all(T.values()):
        return None
    for b in T:
        assert set(T[b]) == set(D[b]['flux_public']), f'{b}: {TEMP} does not cover identical items'
    return T


def temporal_block(D, R, T):
    S = item_sets(D)
    sets = [(n, b, q) for n, (b, q) in S.items() if not n.startswith('LoCoMo all five')]
    REFT = ['flux_evidence', 'flux_public', 'flux_reason', 'honcho_chat']

    def arm(a, bench):
        return T[bench] if a == TEMP else (R[bench] if a == 'flux_reason' else D[bench][a])
    L = ['**Accuracy** (reference arms are earlier numbers, repeated here for comparison only; this arm is in-sample, see the caution above)\n']
    for name, bench, qids in sets:
        L += [f'**{name}**\n', '| Arm | Correct / n | Accuracy % | Wilson 95% | Errors | Empty |', '|---|---|---|---|---|---|']
        for a in [TEMP] + REFT:
            rows = [arm(a, bench)[q] for q in qids]
            k = sum(r['correct'] for r in rows)
            lo, hi = analyze.wilson(k, len(rows))
            L.append(f"| {a} | {k}/{len(rows)} | {pc(k / len(rows))} | {pc(lo)} to {pc(hi)} | {sum(1 for r in rows if r['verdict'] == 'error')} | {sum(1 for r in rows if r['verdict'] == 'empty')} |")
        L.append('')
    L.append(f'**Paired differences.** Difference = {TEMP} minus the other arm, percentage points (positive favours {TEMP}), on identical items. Bootstrap: 10,000 resamples, seed {SEED}. Holm is applied across these 4 comparisons within each item set; these tests stand on their own and are not part of the main report\'s Holm family. {TEMP} is a composition of stored {REASON} and flux_evidence results, so it overlaps both by construction.\n')
    stat = {}
    for name, bench, qids in sets:
        conv = [q.split('__')[0] for q in qids] if bench == 'locomo' else None
        L.append(f'**{name}**\n')
        hdr = '| Other arm | Diff pts | Item bootstrap 95% | ' + ('Conversation-clustered 95% | ' if conv else '') + f'{TEMP} only right | Other only right | McNemar p | Holm p |'
        L += [hdr, '|' + '---|' * (hdr.count('|') - 1)]
        res = []
        for oa in REFT:
            f = {q: T[bench][q]['correct'] for q in qids}
            o = {q: arm(oa, bench)[q]['correct'] for q in qids}
            x, y, p = analyze.mcnemar_exact(f, o, qids)
            d = np.array([f[q] - o[q] for q in qids], dtype=float)
            res.append((oa, d.mean(), boot_iid(d), boot_cluster(d, conv) if conv else None, x, y, p))
        adj = analyze.holm({r[0]: r[6] for r in res})
        for oa, m, bi, bc, x, y, p in res:
            stat[(name, oa)] = (m, bi, bc)
            L.append(f'| {oa} | {pm(m)} | {pm(bi[0])} to {pm(bi[1])} | ' + (f'{pm(bc[0])} to {pm(bc[1])} | ' if conv else '') + f'{x} | {y} | {p:.4g} | {adj[oa]:.4g} |')
        L.append('')
    lo = D['locomo']; q0 = sorted(lo['flux_public']); cnt = collections.Counter(lo['flux_public'][q]['type'] for q in q0)
    L.append('**LoCoMo, per category** (correct/n, accuracy %)\n')
    L += ['| Arm | ' + ' | '.join(f'{c} (n={cnt[c]})' for c in CATS) + ' |', '|---|' + '---|' * len(CATS)]
    catacc = {}
    for a in [TEMP] + REFT:
        src = arm(a, 'locomo'); cells = []
        for c in CATS:
            k = sum(src[q]['correct'] for q in q0 if src[q]['type'] == c); catacc[(a, c)] = k / cnt[c]
            cells.append(f'{k}/{cnt[c]} {pc(k / cnt[c])}')
        L.append(f'| {a} | ' + ' | '.join(cells) + ' |')
    lm = D['lme']; q1 = sorted(lm['flux_public']); types = sorted({lm['flux_public'][q]['type'] for q in q1}); tc = collections.Counter(lm['flux_public'][q]['type'] for q in q1)
    L.append('\n**LongMemEval-S, per question type** (correct/n, accuracy %; cells of 6 to 27 questions, not tested)\n')
    L += ['| Arm | ' + ' | '.join(f'{t} (n={tc[t]})' for t in types) + ' |', '|---|' + '---|' * len(types)]
    for a in [TEMP] + REFT:
        src = arm(a, 'lme')
        L.append(f'| {a} | ' + ' | '.join(f"{sum(src[q]['correct'] for q in q1 if src[q]['type'] == t)}/{tc[t]} {pc(sum(src[q]['correct'] for q in q1 if src[q]['type'] == t) / tc[t], 0)}" for t in types) + ' |')
    # router readouts
    L.append('\n**Router readouts** (reported only, no bar; the category and type labels were never shown to the router and are used here after the run)\n')
    L += ['| Item set | Routed TEMPORAL | Share | Truth label | True positives | Precision % | Recall % | Unparseable | Failed calls |', '|---|---|---|---|---|---|---|---|---|']
    for name, bench, qids, truth, tname in [('LongMemEval-S (n=100)', 'lme', q1, lambda q: lm['flux_public'][q]['type'] == 'temporal-reasoning', 'type temporal-reasoning'),
                                            ('LoCoMo categories 1-4', 'locomo', S[[n for n in S if n.startswith('LoCoMo categories 1-4')][0]][1], lambda q: lo['flux_public'][q]['type'] == 'cat2-temporal', 'category 2'),
                                            ('LoCoMo all five categories', 'locomo', q0, lambda q: lo['flux_public'][q]['type'] == 'cat2-temporal', 'category 2')]:
        pos = [q for q in qids if T[bench][q]['routed'] == 'TEMPORAL']; tp = [q for q in pos if truth(q)]; nt = sum(1 for q in qids if truth(q))
        un = sum(1 for q in qids if T[bench][q]['routed'] == 'UNPARSEABLE'); er = sum(1 for q in qids if T[bench][q]['routed'] == 'ERROR')
        L.append(f'| {name} | {len(pos)}/{len(qids)} | {pc(len(pos) / len(qids))}% | {tname} (n={nt}) | {len(tp)} | {pc(len(tp) / len(pos)) if pos else "n/a"} | {pc(len(tp) / nt)} | {un} | {er} |')
    # verdict
    n14 = [n for n in S if n.startswith('LoCoMo categories 1-4')][0]; nl = [n for n in S if n.startswith('LongMemEval')][0]
    m1, _, c1 = stat[(n14, 'flux_evidence')]; m2 = stat[(nl, 'flux_evidence')][0]
    d3 = {c: 100 * (catacc[(TEMP, c)] - catacc[('flux_evidence', c)]) for c in ('cat1-multi-hop', 'cat3-open-domain', 'cat4-single-hop')}
    b1 = 100 * m1 >= BAR_I - 1e-9 and c1[0] > 0; b2 = 100 * m2 >= BAR_II - 1e-9; b3 = all(v >= BAR_III - 1e-9 for v in d3.values())
    mh = stat[(n14, 'honcho_chat')][0]
    L.append('\n**Verdict against the preregistered bars** (all against flux_evidence; exploratory, in-sample: a PASS only justifies an out-of-sample confirmation)\n')
    L += ['| Bar | Requirement | Observed | Result |', '|---|---|---|---|',
          f'| (i) LoCoMo categories 1-4 | diff at least +{BAR_I:.1f} pts and the conversation-clustered 95% interval excludes zero | {pm(m1)} pts, clustered {pm(c1[0])} to {pm(c1[1])} | **{"PASS" if b1 else "FAIL"}** |',
          f'| (ii) LongMemEval-S | diff at least {BAR_II:.1f} pts | {pm(m2)} pts | **{"PASS" if b2 else "FAIL"}** |',
          f'| (iii) LoCoMo categories 1, 3, 4 | none falls by more than 2.0 pts | cat1 {d3["cat1-multi-hop"]:+.1f}, cat3 {d3["cat3-open-domain"]:+.1f}, cat4 {d3["cat4-single-hop"]:+.1f} pts | **{"PASS" if b3 else "FAIL"}** |',
          f'| Overall | all three | | **{"PASS" if (b1 and b2 and b3) else "FAIL"}** |']
    L.append(f'\nGap to honcho_chat on LoCoMo categories 1-4: {pm(mh)} points ({TEMP} minus honcho_chat; conversation-clustered {pm(stat[(n14, "honcho_chat")][2][0])} to {pm(stat[(n14, "honcho_chat")][2][1])}).')
    # cost
    L.append('\n**Cost** (USD; router calls are the only new spend; the chosen path\'s reader, judge and, for the flux_reason path, pass-1 costs are the stored ones; shared ingest, extraction and retrieval are not counted)\n')
    L += ['| Bench | Router | Chosen paths (stored calls) | Arm total | Router failures | Items on the flux_reason path |', '|---|---|---|---|---|---|']
    led = jl(os.path.join(PUB, 'ledger-flux_temporal.jsonl'))
    for bench, title in (('lme', 'LongMemEval-S'), ('locomo', 'LoCoMo')):
        rc = sum(r['router_cost'] for r in T[bench].values()); pcost = sum(r['path_cost'] for r in T[bench].values())
        L.append(f"| {title} | {rc:.4f} | {pcost:.4f} | {rc + pcost:.4f} | {sum(1 for r in T[bench].values() if r['routed'] == 'ERROR')} | {sum(1 for r in T[bench].values() if r['path'] == 'flux_reason')} |")
    L.append(f"\nLedger lines for the arm (`results-public/ledger-flux_temporal.jsonl`) sum to {sum(r['usd'] for r in led):.4f} USD against the arm's cap of 3 USD.")
    return '\n'.join(L)


def splice(path, blks, only=None):
    t = open(path).read()
    for k, v in blks.items():
        if only and k not in only:
            continue
        pat = re.compile(rf'(<!-- GEN:{k} -->\n)(.*?)(\n<!-- /GEN:{k} -->)', re.S)
        if pat.search(t):
            t = pat.sub(lambda m: m.group(1) + v + m.group(3), t)
    return t


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    D = load()
    blks = blocks(D)
    os.makedirs(os.path.join(HERE, 'tables'), exist_ok=True)
    open(os.path.join(HERE, 'tables', 'report_tables.md'), 'w').write('\n\n'.join(f'<!-- {k} -->\n{v}' for k, v in blks.items()) + '\n')
    outs = {os.path.join(ROOT, 'REPORT.md'): None, os.path.join(ROOT, 'COST.md'): ['honcho_month']}
    bad = []
    for p, only in outs.items():
        new = splice(p, blks, only)
        if a.check:
            if new != open(p).read():
                bad.append(p)
        else:
            open(p, 'w').write(new)
    if bad:
        print('out of date:', bad); sys.exit(1)
    print('ok')


if __name__ == '__main__':
    main()
