# Preregistration addendum: exploratory arm `flux_temporal`

**Status: written and committed before any paid call of this arm.** The commit that contains this file is the preregistration of this arm; the public git history shows it precedes every result of the arm. The main run (2026-10-03), the README preregistration and the `flux_reason` arm are not changed by this addendum, and no number of any earlier arm is changed by this arm.

## What this is, and what it is not

- **Exploratory, post hoc and in-sample.** The hypothesis was formed on 2026-10-04 from the `flux_reason` results on the very questions this arm is scored on: one reasoning pass raised LoCoMo temporal questions (category 2) from 43.9% to 72.3%, lowered open-domain (category 3) and single-hop (category 4), and cost 11 points on LongMemEval-S. The hypothesis is: apply the reasoning pass only to questions that depend on dates, time, order or duration, and use the plain evidence arm for everything else.
- **Because it is in-sample, a PASS is a reason to run an out-of-sample confirmation, not a result to quote.** A FAIL is reported just as plainly. Nothing here is part of the preregistered comparison, and it is labelled "added after the main run" everywhere it appears.

## The arm

`flux_temporal`, per question:

1. **Router.** One call per question to `deepseek-flash`, with the same endpoint and configuration as `flux_reason` pass 1: `https://api.deepseek.com` direct, **thinking disabled, temperature 0**, **max_tokens 8** (the answer is one word). Prompt: `prompts/flux_temporal_router_prompt.txt`, **sha256 `9a28f21b326eed60f92631120f2766460f9c3c60e05a9ff141bbd6dc1bd067db`**, fixed before the run. The model answers exactly `TEMPORAL` or `OTHER`: TEMPORAL if answering requires working out a date, time, order of events, duration, age, or "how long / when / before / after / latest" style reasoning. **Unparseable output (anything but TEMPORAL or OTHER after removing non-letters and upper-casing) is counted as OTHER.** A router call that fails after the kit's retries is also counted as OTHER and is counted as an error for the stop rule.
2. **The router never sees labels.** Its prompt contains the question text and nothing else: not the LoCoMo category, not the LongMemEval question type, not the gold answer, not the question date, not any retrieved memory, not any arm's output. The raw question (never the option-augmented category 5 text) is used. The question texts are read on the run host from the stored `retrieved.jsonl` of `flux_reason`; they are never written to any output file.
3. **Composition, no new reader or judge calls.** For a question routed TEMPORAL, the graded result of `flux_temporal` is that question's **existing `flux_reason` result**; otherwise it is that question's **existing `flux_evidence` result**. Both are taken from the stored per-item graded outputs (`qa/answers.jsonl`) of the finished runs. Nothing is re-read, re-judged or re-rolled.
4. **Cost.** The router call, plus the chosen path's calls for that item: for a `flux_evidence` path the reader and judge calls; for a `flux_reason` path the pass-1 call, the reader and the judge. The shared ingest, fact extraction and retrieval (identical for both paths, and already booked to `flux_evidence`) are not counted again.
5. **Same question sets.** LoCoMo: all 1,986 questions (categories 1 to 4, n=1,540, the headline set; category 5, n=446, always separate). LongMemEval-S: the 100 ids of `sample/lme_s_ids_n100.txt`.
6. **Smoke first**: 10 LoCoMo and 5 LongMemEval questions, evenly spaced, only to check that the outputs parse. The prompt is not changed because of the smoke. Smoke items are kept as-is in the full run.

## Bars, stated before running

All three are about `flux_temporal` against `flux_evidence` on identical items. Statistics are those of `analysis/report.py` (paired item bootstrap and conversation-clustered bootstrap, 10,000 resamples, seed 20261003).

- **(i) LoCoMo categories 1 to 4 (n=1,540):** `flux_temporal` minus `flux_evidence` is at least **+4.0 points** AND the conversation-clustered 95% interval of that difference excludes zero (its lower end is above 0).
- **(ii) LongMemEval-S (n=100):** `flux_temporal` minus `flux_evidence` is at least **-2.0 points** (that is, at most 2 of the 100 questions net worse).
- **(iii) No LoCoMo category 1, 3 or 4 falls by more than 2.0 points** against `flux_evidence` (a difference below -2.0 points in any of the three fails the bar).

**PASS needs all three.** Otherwise FAIL. The point estimates decide; category 2 and category 5 play no part in the verdict. A PASS does not make `flux_temporal` a result: see above.

## Secondary readouts, reported only (no bar)

- **Router agreement:** precision and recall of the TEMPORAL label against LoCoMo category 2 (all 1,986 questions, and categories 1 to 4 only), and against the LongMemEval `temporal-reasoning` question type. The category and type labels are used only here, after the run, never by the router.
- The **share routed TEMPORAL** on each benchmark (and the count of unparseable and failed router calls).
- Paired differences of `flux_temporal` against `flux_evidence`, `flux_public`, `flux_reason` and `honcho_chat`, with item-bootstrap and (LoCoMo) conversation-clustered intervals and exact McNemar p, Holm-adjusted across these 4 comparisons within each item set. These tests stand on their own and are not part of the main report's Holm family. The gap to `honcho_chat` is reported whatever the verdict.
- Per-category LoCoMo and per-type LongMemEval accuracy, and the cost of the arm.

## Spend cap and stop rules

- **Spend cap for this arm: USD 3.** Enforced in `drivers/flux_temporal.py`: a router call is not started if the arm's ledger spend plus 1 cent would pass the cap. Spend is booked in `results/ledger.jsonl` under arm `flux_temporal`. The only paid calls are the router calls (about 2,086, expected well under USD 1).
- **Stop if more than 2% of router calls error** (checked from 50 calls on, and the kit's 429/503 breaker applies).
- Concurrency: at most 2 requests in flight and 3 starts per second, in one blocking command.

## Known limits, declared in advance

In-sample (the hypothesis was formed on these questions); a composition of stored outputs, not a fresh run, so reader and judge noise is whatever it was in the two stored runs; a single router run with one prompt, no variants tried; it reuses stored retrieval, so any miss of the `flux_evidence` retrieval stays a miss; Flux runs in-process, not through the hosted API; the `flux_reason` prompt, which the TEMPORAL path inherits, was written after the main results were known.

## Planned, not run: the out-of-sample confirmation a PASS would justify

If, and only if, the arm passes all three bars, the follow-up would be a new preregistration, not part of this addendum and not run here: fresh LongMemEval-S questions that are not among the 100 used so far, ingested with Flux (turns plus extracted facts, as `flux_evidence`), run through the same router prompt (unchanged, same sha256) and the unchanged `flux_reason` and `flux_evidence` paths, with bars fixed before that run. LoCoMo has no unused questions, so it could not be used for that confirmation.

## Where it runs

The router runs on the main run's host (the DeepSeek key exists only there), from a copy of this kit's `drivers/`, `runner/` and `prompts/` files, writing only to new directories `results/flux_temporal` and `results/locomo/flux_temporal`. Nothing of the host's other results is changed or deleted. The router output (labels and costs only) is copied back and the composition, the public per-item files and the report section are produced locally from the stored per-item outputs.

## Changes after prereg

None to the arm, prompt, model settings, composition rule, bars, caps or stop rules. After the preregistration commit the analysis code (`analysis/report.py`, `analysis/make_public.py`) and the report section were written; they implement the bars exactly as stated above (bar (i) uses the report's conversation-clustered bootstrap, bar (iii) fails on a difference below -2.0 points). The smoke (10 LoCoMo and 5 LongMemEval questions) showed no harness bug and all outputs parsed; its items were kept as-is in the full run. Spend was 0.0475 USD of the 3 USD cap, with 0 router failures. Results are in REPORT.md, section "Exploratory arm added after the flux_reason arm: flux_temporal".
