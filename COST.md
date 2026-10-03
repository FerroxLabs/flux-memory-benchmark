# Budget estimate, LongMemEval-S n=100 plus LoCoMo

Plan limits (decisions 9 and 17): one **$55 cap** for both benchmarks together (LongMemEval about $23 to $32, LoCoMo about $12 to $22), and the Honcho stop rule.
Regenerate the tables with `python3 analysis/cost_estimate.py`. Every input is either measured in the private runs (source named in the row; no accuracy figure is used) or flagged ESTIMATED.

### LongMemEval-S, n=100

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
| **Subtotal** | | **22.54** | **32.05** | |

### LoCoMo, 10 conversations, 1,986 questions (1,540 judged, 446 adversarial)

| Item | Basis | Low ($) | High ($) | Source |
|---|---|---|---|---|
| mem0 ingest | measured | 0.58 | 0.58 | h2h-oss 2026-09-30: $0.058/conversation, 371 s |
| Honcho ingest | ESTIMATED, scaled | 0.14 | 1.11 | no private LoCoMo Honcho run. Low scales the measured $0.093/haystack by characters (x0.149), high by turns (x1.20). Stop rule on LoCoMo: pause if the mean over the first 3 conversations passes $0.18 (the $0.15 ceiling x1.20) |
| Honcho dialectic (chat arm) | ESTIMATED, scaled | 0.99 | 3.97 | $0.00098/question measured on a smaller corpus; LoCoMo workspaces are smaller than LME ones, so low halves it and high doubles it |
| Flux evidence: fact extraction | measured | 0.09 | 0.12 | attrib3: $0.000431/session x 272 sessions |
| Letta ingest | measured | 0.00 | 0.00 | no LLM at ingest; 298 s/conversation |
| Flux public ingest | measured | 0.00 | 0.00 | no LLM at ingest; about 17 s/conversation |
| Reader + judge, 6 memory arms | measured | 8.32 | 12.48 | reader $0.000488/question measured on LoCoMo; judge $0.000271/question on 1540 judged questions (category 5 has no judge call); high adds 50% (measured on LoCoMo itself, so less slack than the LongMemEval line) |
| Closed-book arm | estimated | 0.69 | 1.39 | empty context |
| Full-context arm | ESTIMATED, not measured | 1.52 | 2.14 | ~18k-token conversation first in the prompt, so every question after the first per conversation reads it at the cache-hit price ($0.006/M vs $0.30/M miss); low = off-peak half price |
| **Subtotal** | | **12.34** | **21.79** | |

| **Both benchmarks** | | **34.88** | **53.85** | cap $55; headroom at the high figure $1.15 |

## Reading the estimate

- **Low case about $35, high case about $54, against the $55 cap.** Headroom at the high figure is about $1, so the high case leaves no room for a restart. The ledger (`runner/ledger.py`, one ledger for both benchmarks, rows tagged `bench`) refuses to start a stage that would pass the cap. If the cap is the binding constraint, drop in this order: the LoCoMo full-context arm (about $2), the Honcho chat arm on LoCoMo (about $1 to $4), then reduce nothing else: a partial arm is not reported.
- **Honcho stop rule (both benchmarks).** LongMemEval: if Honcho's ingest cost averages more than **$0.15 per haystack** over the first 10, pause and find out why before continuing (the cancelled extension ran near $0.29 per haystack and was never explained). Without the rule Honcho alone would be near $29 and the total near $68. LoCoMo has only 10 conversations, so the rule is checked after the first **3**, against **$0.18 per conversation** ($0.15 scaled by turns, 588 vs 491). Commands: `python3 runner/ledger.py honcho-rule --dir results/honcho_retrieval` and `... --dir results/locomo/honcho_retrieval --locomo`. `analysis/analyze.py` raises the LongMemEval flag too.
- **Run DeepSeek-heavy ingest off-peak.** Since 2026-08-16 DeepSeek bills peak (2x) only Monday to Friday 01:00-04:00 and 06:00-10:00 UTC; every other hour, and all weekend, is off-peak (half). mem0 and Honcho ingest and the Flux fact-extraction pass are the DeepSeek-heavy stages; schedule them off-peak. `drivers/llm.py` `ds_price` implements this same schedule, so the ledger prices spend correctly.
- **A full restart of the mem0 arm does not fit in the high case** (LME $8.10 plus LoCoMo $0.58 on top of a $53.85 total). A restart caught in the first 10 to 20 haystacks costs under $2 and fits. A late one is a decision for Sean at the time (raise the cap, or stop and report the arm as incomplete).
- **Unmeasured lines:** the two full-context arms (LME about $2 to $4, LoCoMo about $1.5 to $2.1) and the LoCoMo Honcho lines (scaled from the LongMemEval measurement, no private LoCoMo Honcho run exists). The LME full-context arm needs a reader window of at least 150k tokens: if smaller, the arm is dropped and reported as "does not fit".
- **LoCoMo reader cost** is measured on LoCoMo itself ($0.000488 per question, short answers) and is about a third of the LongMemEval reader cost, because the answers are short. Category 5 questions (446) have no judge call: the official rule is a string match.
- **Judge pricing.** Measured judge costs come from FluxRouter billing; direct gpt-5-mini and GPT-6 Astra prices were not checked against the provider's price list. The judge lines are small, so the error is small against the cap. Set `JUDGE_USD_PER_M_IN` and `JUDGE_USD_PER_M_OUT` so the ledger records real judge spend.
- Wall time (sequential, one lane at a time, at most 2 containers per lane): LongMemEval is dominated by mem0 (about 778 s per haystack, about 22 h) and Letta (about 632 s, about 18 h); Honcho about 98 s (about 2.7 h); Flux about 101 s (about 3 h). LoCoMo adds about 10 conversations x (371 s mem0 + 298 s Letta + 17 s Flux + Honcho) which is under 3 hours in total.
