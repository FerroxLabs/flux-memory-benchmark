# Budget estimate, n=100

Plan limits (decision 17): **$40 cap**, and the Honcho stop rule (if Honcho's ingest cost passes $0.15 per haystack after the first 10, pause and find out why before continuing).
Regenerate this table with `python3 analysis/cost_estimate.py`. Every input is either measured in the private runs (source named in the table) or flagged ESTIMATED.

| Item | Basis | Low ($) | High ($) | Source |
|---|---|---|---|---|
| mem0 ingest | measured | 8.10 | 8.10 | h2h-oss 2026-09-30: $0.081/haystack, 778 s |
| Honcho ingest | measured | 9.30 | 15.00 | honcho 2026-10-02 clean run: $0.093/haystack ($2.79 for 30). High = the stop-rule ceiling ($0.15 averaged over the first 10); the cancelled extension ran near $0.29 |
| Honcho dialectic (chat arm) | measured, scaled | 0.10 | 0.50 | $0.00098/question measured on a smaller corpus; high allows 5x for LongMemEval-size workspaces |
| Flux evidence: fact extraction | measured | 1.64 | 2.05 | attrib3: $8.269 / 19,189 sessions = $0.000431/session; low assumes 20% of sessions are shared between haystacks |
| Letta ingest | measured | 0.00 | 0.00 | no LLM at ingest (the $0-cap proxy enforces it); 632 s/haystack |
| Flux public ingest | measured | 0.00 | 0.00 | no LLM at ingest; about 101 s/haystack |
| Reader + standard judge, 6 memory arms | measured | 0.96 | 1.92 | $0.0016/question measured; high doubles it for longer contexts (mem0 and Letta fact lists differ in size) |
| Closed-book arm | estimated | 0.08 | 0.16 | empty context, so no larger than a memory arm |
| Full-context arm | ESTIMATED, not measured | 1.99 | 3.95 | ~122k input tokens/question at the DeepSeek list price ($0.30/M miss; low = off-peak half price). Needs a reader window of >=150k tokens: verify before the run |
| Preference judge (Astra) | measured | 0.38 | 0.38 | $0.00786/grade measured; 6 preference questions x 8 arms |
| **Total** | | **22.54** | **32.05** | cap $40; headroom at the high figure $7.95 |

## Reading the estimate

- **Low case about $23, high case about $32, against the $40 cap.** Headroom at the high figure is about $8.
- **The Honcho stop rule is what keeps the high case under the cap.** Without it the cancelled extension's rate ($0.29 per haystack) would put Honcho alone near $29 and the total near $46. With it, Honcho is bounded near $15 (and the run pauses after at most 10 haystacks, about $1.5 to $3, if the rule fires). The code enforces it: `python3 runner/ledger.py honcho-rule --dir results/honcho_retrieval`, and `analysis/analyze.py` raises the same flag.
- **A full restart of the mem0 arm does not fit in the high case** (32.05 + 8.10 = 40.15). The 2% dropped-item stop rule allows restarting an arm from a clean store. A restart caught in the first 10 to 20 haystacks costs under $2 and fits. One caught late does not: that is a decision for Sean at the time (raise the cap, or stop and report the arm as incomplete).
- **The one unmeasured line is the full-context arm** (about $2 to $4). It also needs a reader window of at least 150k tokens. If the reader's window is smaller, the arm is dropped from the run and reported as "does not fit", which also removes its cost.
- **Judge pricing assumption.** The measured judge costs come from FluxRouter billing. Direct gpt-5-mini and GPT-6 Astra prices were not checked against the provider's price list, and the judge lines are under $1.50 in total, so the error is small against the cap. Set `JUDGE_USD_PER_M_IN` and `JUDGE_USD_PER_M_OUT` so the ledger records real judge spend.
- **Reader price.** DeepSeek list price at call time (peak Monday to Friday 01 to 04 and 06 to 10 UTC is full price, otherwise half). Running mem0 and Honcho ingest off-peak lowers the figures above, which are computed from per-haystack costs measured at mixed times.
- Wall time (sequential, one lane at a time, at most 2 containers per lane): mem0 about 778 s per haystack (about 22 h for 100) and Letta about 632 s per haystack (about 18 h) dominate. Honcho about 98 s per haystack at concurrency 1 (about 2.7 h). Flux about 101 s per haystack (about 3 h), plus extraction for the evidence arm.
