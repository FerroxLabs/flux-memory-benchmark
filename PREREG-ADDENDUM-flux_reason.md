# Preregistration addendum: exploratory arm `flux_reason`

**Status: written and committed before any paid call of this arm.** The commit that contains this file is the preregistration of this arm; the public git history shows it precedes every result of the arm. The main run (2026-10-03) and the README preregistration are not changed by this addendum, and no number of the main run is changed by this arm.

## What this is, and what it is not

- **Exploratory and post hoc.** It was designed on 2026-10-04, after the main results were known, in particular after seeing that `honcho_chat` (83.8% on LoCoMo categories 1 to 4) is far above `flux_public` (70.6%) and `flux_evidence` (70.5%). It is not part of the preregistered comparison, it is not tuned on any test question, and it is labelled "added after the main run" everywhere it appears.
- **The question.** `honcho_chat` reasons over memory with a model and then our reader answers from that one synthesized item (two model passes; not held to the 20-item / 16 KiB budget). Flux has no "reason over memory, then answer" arm. How much of the gap does a reasoning pass over Flux's own retrieved memory close?

## The arm

`flux_reason`, per question:

1. **Input: the context `flux_evidence` already retrieved for that question in the finished run, as stored** (`retrieved.jsonl` of the `flux_evidence` arm on the run host). No re-ingest and no re-retrieval. So the retrieval is the `flux_evidence` retrieval (turns plus extracted facts, 32 KiB, in-process Flux build `c63e8d14`) exactly, and the paired comparison with `flux_evidence` isolates the reasoning pass.
2. **Pass 1 (reasoning).** One call to `deepseek-flash`, called directly at `https://api.deepseek.com` (the endpoint the main run's metering proxy forwarded Honcho's dialectic calls to; `infra/dsproxy.py` forces `model=deepseek-flash`, `thinking` disabled and drops `reasoning_effort`, and `compose/honcho/config.toml` sets every dialectic level to `deepseek-flash`). Pass 1 therefore uses **thinking disabled**. Prompt: `prompts/flux_reason_prompt.txt`, **sha256 `e52763d7923ce70d44df52b3fd37f5fbee5bd07f0c1e1fc6d6a56e62ede04e4f`**, fixed before the run. Given the raw question and the retrieved memory, the model reasons over dates, speakers, updates (latest wins) and multi-hop joins, and writes a short note (at most 150 words) that answers from the memory only, or says the memory does not contain it. For LongMemEval the question date is included in the prompt (the reader sees it too); for LoCoMo it is not. The raw question is used, never the option-augmented category 5 text.
   - **Temperature and max tokens.** The kit does not record the temperature or max tokens Honcho's dialectic sent, so they cannot be matched. This arm uses **temperature 0 and max_tokens 1500**. This is a stated difference from `honcho_chat`.
3. **Pass 2.** The kit's unchanged `runner/qa.py` reader and judges, given **only the pass-1 note as its single context item** (role `fact`, no session date), exactly as `honcho_chat` hands Honcho's answer to the reader. Same reader prompts (`prompt_sha256` equal to the one in the `honcho_chat` and `flux_evidence` qa summaries), same reader (`deepseek-flash`, temperature 0, 6,000 tokens, provider-default thinking), same judges (`gpt-5-mini` minimal reasoning; the 6 LongMemEval preference questions by `gpt-6-astra`; LoCoMo category 5 by the official string rule). An empty note gives the reader an empty context, as an empty Honcho answer did.
4. **One run, no re-rolls.** Failures (a pass-1 call that fails after the kit's retries, or any pass-2 error) are scored wrong. Same question sets: LongMemEval-S, the 100 ids of `sample/lme_s_ids_n100.txt`; LoCoMo, all 1,986 questions.
5. **Smoke first** (5 LongMemEval and 10 LoCoMo questions, spread over the file). The smoke only checks that notes and answers are non-empty and that spend is recorded. The prompt is not changed because of smoke accuracy. If the smoke shows a harness bug, the fix is committed and listed below; smoke items are reused as-is in the full run (no re-roll of items already done).

## Planned comparisons

- Accuracy with Wilson 95% interval: LongMemEval-S (n=100) and LoCoMo categories 1 to 4 (n=1,540, the headline), plus LoCoMo category 5 on its own (n=446, never mixed in), per-category LoCoMo accuracy, per-type LongMemEval accuracy.
- Paired differences, `flux_reason` minus the other arm, on identical items, against `flux_evidence`, `flux_public` and `honcho_chat`: percentage points, paired-bootstrap 95% interval (10,000 resamples over items, seed 20261003, as `analysis/report.py`), conversation-clustered interval for LoCoMo, exact two-sided McNemar p, Holm-adjusted across these 3 comparisons within each item set. These tests are not independent of the 8-arm family of the main report and are reported on their own.
- Cost of pass 1 and of pass 2 (reader plus judge), separately.

## Spend cap and stop rules

- **Spend cap for this arm: USD 10** (both benchmarks together; the main run's USD 75 cap is untouched). Enforced in `drivers/flux_reason.py`: a pass-1 call is not started if the arm's ledger spend plus 3 cents would pass the cap, and between pass-2 batches of 200 questions the run stops if the arm's spend plus a USD 0.60 batch reserve would pass it. Spend is booked in `results/ledger.jsonl` under arm `flux_reason`.
- Stop and report if more than 2% of pass-1 calls fail (checked from 50 calls on), or more than 2% of pass-2 rows are errors, or the kit's 429/503 breaker fires.
- Concurrency: at most 2 requests in flight and 3 starts per second in total, in each of the two stages (the stages run one after the other).
- Expected spend is about USD 3 to 5 (pass 1 reads about 2,100 stored contexts once; pass 2 reads one short note each).

## What counts as "closes most of the gap"

Stated before running. The gap is `honcho_chat` minus `flux_evidence` on LoCoMo categories 1 to 4: 1291/1540 (83.8%) against 1085/1540 (70.5%), 13.4 points.

- **Closes most of the gap:** `flux_reason` is within 5.0 points of `honcho_chat` on LoCoMo categories 1 to 4, that is **at least 1,214 of 1,540 correct (78.8%)**, which is at least 62% of the gap closed.
- **Does not close most of the gap:** fewer than 1,214 correct.
- The test is the point estimate on that one number. LongMemEval-S (n=100) is reported but cannot resolve a 5-point difference and plays no part in the verdict. Category 5 is reported separately and plays no part in the verdict. Differences vs `flux_evidence` and `flux_public` are reported with their intervals whatever the verdict.

## Known limits, declared in advance

It reuses stored retrieval (so any miss of the `flux_evidence` retrieval stays a miss); it is a single reasoning pass with no multi-step search or query rewriting; Flux runs in-process, not through the hosted API; temperature and max tokens differ from what Honcho used (unrecorded); the prompt was written after seeing the main results; one run, so run-to-run noise of the reasoning pass is not measured.

## Where it runs

On the main run's host (the judge key exists only there), from a copy of this kit's code (the `drivers/`, `runner/` and `prompts/` files of the host kit are byte-identical to this repository's, checked by sha256 before the run), writing to new directories `results/flux_reason` and `results/locomo/flux_reason`. Nothing of the main run's results is read for writing or changed.

## Changes after prereg

None yet.
