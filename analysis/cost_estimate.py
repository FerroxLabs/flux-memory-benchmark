"""Budget estimate for n=100 from the figures measured in the private runs (2026-09-30 to 2026-10-03). Prints the markdown table used in COST.md.
Every input below is either MEASURED (source in the comment) or ESTIMATED (flagged). usage: python3 analysis/cost_estimate.py"""
N = 100
CAP = 40.0
SESSIONS_UPPER = 4753          # session slots across the 100 drawn haystacks (counted from the drawn units); distinct sessions are fewer, so this is an upper bound
READER, JUDGE, ASTRA = 0.001326, 0.000271, 0.00786   # $/question MEASURED: attrib3 LME-500 evidence arm, reader mean, gpt-5-mini judge mean, Astra preference grade mean
PREF_Q = 6                     # preference questions in the sample
FULLCTX_TOKENS = 122_000       # ESTIMATED: chars/4 over the 100 drawn haystacks (48.8M chars)

lines = [
    ('mem0 ingest', 'measured', N * 0.081, N * 0.081, 'h2h-oss 2026-09-30: $0.081/haystack, 778 s'),
    ('Honcho ingest', 'measured', N * 0.093, N * 0.15, 'honcho 2026-10-02 clean run: $0.093/haystack ($2.79 for 30). High = the stop-rule ceiling ($0.15 averaged over the first 10); the cancelled extension ran near $0.29'),
    ('Honcho dialectic (chat arm)', 'measured, scaled', N * 0.001, N * 0.005, '$0.00098/question measured on a smaller corpus; high allows 5x for LongMemEval-size workspaces'),
    ('Flux evidence: fact extraction', 'measured', SESSIONS_UPPER * 0.000431 * 0.8, SESSIONS_UPPER * 0.000431, 'attrib3: $8.269 / 19,189 sessions = $0.000431/session; low assumes 20% of sessions are shared between haystacks'),
    ('Letta ingest', 'measured', 0.0, 0.0, 'no LLM at ingest (the $0-cap proxy enforces it); 632 s/haystack'),
    ('Flux public ingest', 'measured', 0.0, 0.0, 'no LLM at ingest; about 101 s/haystack'),
]
qa_arms = ['flux_public', 'flux_evidence', 'mem0', 'letta', 'honcho_retrieval', 'honcho_chat']
lines.append(('Reader + standard judge, 6 memory arms', 'measured', len(qa_arms) * N * (READER + JUDGE), len(qa_arms) * N * (READER + JUDGE) * 2, '$0.0016/question measured; high doubles it for longer contexts (mem0 and Letta fact lists differ in size)'))
lines.append(('Closed-book arm', 'estimated', N * (READER + JUDGE) * 0.5, N * (READER + JUDGE), 'empty context, so no larger than a memory arm'))
fc_low = N * (FULLCTX_TOKENS * 0.30 / 1e6 * 0.5 + READER + JUDGE)
fc_high = N * (FULLCTX_TOKENS * 0.30 / 1e6 + READER * 2 + JUDGE)
lines.append(('Full-context arm', 'ESTIMATED, not measured', fc_low, fc_high, f'~{FULLCTX_TOKENS // 1000}k input tokens/question at the DeepSeek list price ($0.30/M miss; low = off-peak half price). Needs a reader window of >=150k tokens: verify before the run'))
lines.append(('Preference judge (Astra)', 'measured', 8 * PREF_Q * ASTRA, 8 * PREF_Q * ASTRA, '$0.00786/grade measured; 6 preference questions x 8 arms'))
lo = sum(l[2] for l in lines); hi = sum(l[3] for l in lines)
print('| Item | Basis | Low ($) | High ($) | Source |\n|---|---|---|---|---|')
for n, b, a, c, s in lines:
    print(f'| {n} | {b} | {a:.2f} | {c:.2f} | {s} |')
print(f'| **Total** | | **{lo:.2f}** | **{hi:.2f}** | cap ${CAP:.0f}; headroom at the high figure ${CAP - hi:.2f} |')
