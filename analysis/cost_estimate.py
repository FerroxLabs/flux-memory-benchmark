"""Budget estimate for both benchmarks (LongMemEval-S n=100 and LoCoMo, 10 conversations, 1,986 questions) against the cap (now $75; the estimate was written against $55). Prints the markdown used in COST.md.
Every input is MEASURED in the private runs (2026-09-30 to 2026-10-03; source in the row) or flagged ESTIMATED. No accuracy figure is used here.
Flux build priced here: integration/phaseb @ c63e8d14 (same code as a3b8a520 plus a manifests-only commit).
usage: python3 analysis/cost_estimate.py"""
N = 100
CAP = 55.0                     # LongMemEval and LoCoMo together (decision 9)
SESSIONS_UPPER = 4753          # session slots across the 100 drawn LME haystacks (counted from the drawn units); distinct sessions are fewer, so an upper bound
READER, JUDGE, ASTRA = 0.001326, 0.000271, 0.00786   # $/question MEASURED: attrib3 LME-500 evidence arm, reader mean, gpt-5-mini judge mean, Astra preference grade mean
PREF_Q = 6                     # preference questions in the sample
FULLCTX_TOKENS = 122_000       # ESTIMATED: chars/4 over the 100 drawn haystacks (48.8M chars)

# LoCoMo (counted from the pinned locomo10.json, sha256 79fa87e9...): 10 conversations, 272 sessions, 5,882 turns, 726,756 characters of turns
LC_CONVS, LC_SESSIONS, LC_TURNS = 10, 272, 5882
LC_Q_JUDGED, LC_Q_ADV = 1540, 446                    # categories 1 to 4 (LLM judge) and category 5 (official string rule, no judge call)
LC_Q = LC_Q_JUDGED + LC_Q_ADV
LC_READER = 0.000488           # MEASURED: attrib3 private LoCoMo QA run, reader $0.3795 / 777 questions (short answers, 16 KiB context)
LC_FULLCTX_TOKENS = 18_200     # ESTIMATED: chars/4 of one conversation (72.7k chars on average)
LME_TURNS = 490.83             # mean turns per drawn LME haystack, to scale per-haystack ingest cost to a conversation (588.2 turns)
TURN_RATIO = (LC_TURNS / LC_CONVS) / LME_TURNS        # 1.20: a conversation has more turns but far fewer characters than a haystack
CHAR_RATIO = 72_676 / 488_329                          # 0.149

lme = [
    ('mem0 ingest', 'measured', N * 0.081, N * 0.081, 'h2h-oss 2026-09-30: $0.081/haystack, 778 s'),
    ('Honcho ingest', 'measured', N * 0.093, N * 0.15, 'honcho 2026-10-02 clean run: $0.093/haystack ($2.79 for 30). High = the stop-rule ceiling ($0.15 averaged over the first 10); the cancelled extension ran near $0.29'),
    ('Honcho dialectic (chat arm)', 'measured, scaled', N * 0.001, N * 0.005, '$0.00098/question measured on a smaller corpus; high allows 5x for LongMemEval-size workspaces'),
    ('Flux evidence: fact extraction', 'measured', SESSIONS_UPPER * 0.000431 * 0.8, SESSIONS_UPPER * 0.000431, 'attrib3: $8.269 / 19,189 sessions = $0.000431/session; low assumes 20% of sessions are shared between haystacks'),
    ('Letta ingest', 'measured', 0.0, 0.0, 'no LLM at ingest (the $0-cap proxy enforces it); 632 s/haystack'),
    ('Flux public ingest', 'measured', 0.0, 0.0, 'no LLM at ingest; about 101 s/haystack'),
]
qa_arms = ['flux_public', 'flux_evidence', 'mem0', 'letta', 'honcho_retrieval', 'honcho_chat']
lme.append(('Reader + standard judge, 6 memory arms', 'measured', len(qa_arms) * N * (READER + JUDGE), len(qa_arms) * N * (READER + JUDGE) * 2, '$0.0016/question measured; high doubles it for longer contexts (mem0 and Letta fact lists differ in size)'))
lme.append(('Closed-book arm', 'estimated', N * (READER + JUDGE) * 0.5, N * (READER + JUDGE), 'empty context, so no larger than a memory arm'))
fc_low = N * (FULLCTX_TOKENS * 0.30 / 1e6 * 0.5 + READER + JUDGE)
fc_high = N * (FULLCTX_TOKENS * 0.30 / 1e6 + READER * 2 + JUDGE)
lme.append(('Full-context arm', 'ESTIMATED, not measured', fc_low, fc_high, f'~{FULLCTX_TOKENS // 1000}k input tokens/question at the DeepSeek list price ($0.30/M miss; low = off-peak half price). Needs a reader window of >=150k tokens: verify before the run'))
lme.append(('Preference judge (Astra)', 'measured', 8 * PREF_Q * ASTRA, 8 * PREF_Q * ASTRA, '$0.00786/grade measured; 6 preference questions x 8 arms'))

lc_judge_q = LC_Q_JUDGED
HIGH = 1.5                     # LoCoMo reader/judge high-case multiplier
lc = [
    ('mem0 ingest', 'measured', LC_CONVS * 0.058, LC_CONVS * 0.058, 'h2h-oss 2026-09-30: $0.058/conversation, 371 s'),
    ('Honcho ingest', 'ESTIMATED, scaled', LC_CONVS * 0.093 * CHAR_RATIO, LC_CONVS * 0.093 * TURN_RATIO,
     'no private LoCoMo Honcho run. Low scales the measured $0.093/haystack by characters (x0.149), high by turns (x1.20). Stop rule on LoCoMo: pause if the mean over the first 3 conversations passes $0.18 (the $0.15 ceiling x1.20)'),
    ('Honcho dialectic (chat arm)', 'ESTIMATED, scaled', LC_Q * 0.001 * 0.5, LC_Q * 0.001 * 2, '$0.00098/question measured on a smaller corpus; LoCoMo workspaces are smaller than LME ones, so low halves it and high doubles it'),
    ('Flux evidence: fact extraction', 'measured', LC_SESSIONS * 0.000431 * 0.8, LC_SESSIONS * 0.000431, 'attrib3: $0.000431/session x 272 sessions'),
    ('Letta ingest', 'measured', 0.0, 0.0, 'no LLM at ingest; 298 s/conversation'),
    ('Flux public ingest', 'measured', 0.0, 0.0, 'no LLM at ingest; about 17 s/conversation'),
    ('Reader + judge, 6 memory arms', 'measured', len(qa_arms) * (LC_Q * LC_READER + lc_judge_q * JUDGE), len(qa_arms) * (LC_Q * LC_READER + lc_judge_q * JUDGE) * HIGH,
     f'reader ${LC_READER}/question measured on LoCoMo; judge ${JUDGE}/question on {lc_judge_q} judged questions (category 5 has no judge call); high adds 50% (measured on LoCoMo itself, so less slack than the LongMemEval line)'),
    ('Closed-book arm', 'estimated', 0.5 * (LC_Q * LC_READER + lc_judge_q * JUDGE), (LC_Q * LC_READER + lc_judge_q * JUDGE) * (HIGH - 0.5), 'empty context'),
    ('Full-context arm', 'ESTIMATED, not measured',
     LC_CONVS * LC_FULLCTX_TOKENS * 0.30 / 1e6 * 0.5 + LC_Q * (LC_FULLCTX_TOKENS * 0.006 / 1e6 * 0.5 + LC_READER) + lc_judge_q * JUDGE,
     LC_CONVS * LC_FULLCTX_TOKENS * 0.30 / 1e6 + LC_Q * (LC_FULLCTX_TOKENS * 0.006 / 1e6 + LC_READER * HIGH) + lc_judge_q * JUDGE,
     f'~{LC_FULLCTX_TOKENS // 1000}k-token conversation first in the prompt, so every question after the first per conversation reads it at the cache-hit price ($0.006/M vs $0.30/M miss); low = off-peak half price'),
]


def table(lines, title):
    lo = sum(l[2] for l in lines); hi = sum(l[3] for l in lines)
    out = [f'### {title}\n', '| Item | Basis | Low ($) | High ($) | Source |', '|---|---|---|---|---|']
    out += [f'| {n} | {b} | {a:.2f} | {c:.2f} | {s} |' for n, b, a, c, s in lines]
    out.append(f'| **Subtotal** | | **{lo:.2f}** | **{hi:.2f}** | |')
    return '\n'.join(out), lo, hi


if __name__ == '__main__':
    t1, l1, h1 = table(lme, 'LongMemEval-S, n=100')
    t2, l2, h2 = table(lc, f'LoCoMo, {LC_CONVS} conversations, {LC_Q:,} questions ({LC_Q_JUDGED:,} judged, {LC_Q_ADV} adversarial)')
    print(t1 + '\n\n' + t2)
    print(f'\n| **Both benchmarks** | | **{l1 + l2:.2f}** | **{h1 + h2:.2f}** | cap ${CAP:.0f}; headroom at the high figure ${CAP - h1 - h2:.2f} |')
