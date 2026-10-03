# Flux Memory vs mem0, Letta and Honcho on LongMemEval-S and LoCoMo

**Status: prepared, not run, not published.** Nothing in this repository has been run against a paid API. No result exists yet. No marketing claim is made before the run is finished and the results are published here.

## The claim we want to be able to make, or not

On LongMemEval-S, with the same answering model, the same grader and the same context budget, Flux Memory scores X; mem0, Letta and Honcho score Y, Z and W. The code, the question list and the raw outputs are here; run it yourself.

We publish whatever comes out, including ties and losses. At 100 questions a paired test can only separate systems that are about 12 points apart. Gaps smaller than that are reported as ties, not as wins.

## What is under test

**Flux build: `integration/phaseb` @ `c63e8d14`** (fact extraction PROMPT_VERSION 4). This is the same code as `a3b8a520` plus one manifests-only commit. The commit is fixed before the draw. No Flux change is made between the draw and the run.

| Arm | What it is |
|---|---|
| `flux_public` | Flux Memory as a customer gets it from `/v1/memory/recall`: hybrid lexical and dense search, reranker over the top 30, top 20 results with neighbouring turns, 16 KiB. The headline Flux number. |
| `flux_evidence` | Flux Memory's evidence path: the same turns plus extracted facts, **32 KiB** (the Flux product setting). Reported next to `flux_public` and labelled. It is not part of the equal-budget comparison. |
| `mem0` | mem0 OSS 2.2.1 on its documented default path. |
| `letta` | Letta 0.16.8, archival memory (the passages API). |
| `honcho_retrieval` | Honcho v3.2.2, `peer.context` with a search query. The primary Honcho arm. |
| `honcho_chat` | Honcho v3.2.2 dialectic chat. Reported separately and labelled as an answering agent, not a retrieval list. |
| `closed_book` | The reader with no memory at all (the contamination floor). |
| `full_context` | The reader sees the whole haystack (a ceiling), where it fits the reader's window. |

Exact versions, commits and image digests: `compose/VERSIONS.md`.

## Held equal for every arm

| Setting | Value |
|---|---|
| Dataset | LongMemEval-S (`longmemeval_s_cleaned.json`, sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`). Question ids only are published here, not dataset text. |
| Reader | DeepSeek flash, called directly, temperature 0, max 6,000 tokens (one retry at 12,000 if the answer is empty), provider-default thinking |
| Grader | The official LongMemEval judge prompt, verbatim (`prompts/lme_prompts.py`), on gpt-5-mini with minimal reasoning |
| Preference questions | Same official preference prompt, graded by GPT-6 Astra at low reasoning (decision 14), for every arm alike |
| Reader prompt | The official LongMemEval chain-of-thought reader template, verbatim; the "history chats plus facts" variant only when the context contains extracted facts |
| Context budget | At most 20 items and 16 KiB per question (200 B envelope plus 260 B per item plus the item text), `drivers/common.py`. Exceptions, all labelled: `flux_evidence` (32 KiB), `full_context` (the whole haystack), `closed_book` (none), `honcho_chat` (one answer item) |
| Embedder | `bge-small-en-v1.5` (384-d) wherever the system lets us choose (mem0, Letta, Honcho, Flux) |
| Competitor's internal LLM | DeepSeek flash, called directly, through a metering proxy that records cost per haystack |
| Isolation | One store per question (one haystack per store); no store is reused between questions |
| Errors and empty answers | Score wrong (every sampled question counts) |

Each system's own settings come from its own documentation and are not tuned by us on the test questions. Each system's settings are published in `compose/` and `drivers/`. Corrections are welcome via issues once the repository is public.

## The sample

100 questions, drawn from all 500 by `sample/draw_sample.py`: stratified by question type in proportion to the 500 (largest-remainder allocation), then, inside each type, the ids with the smallest `sha256("<seed>:<question_id>")`. **Seed: 20261003.** Nothing is excluded. Check with `LME_S_PATH=... python3 sample/draw_sample.py --check`.

| Question type | In the 500 | Drawn |
|---|---|---|
| multi-session | 133 | 27 |
| temporal-reasoning | 133 | 27 |
| knowledge-update | 78 | 15 |
| single-session-user | 70 | 14 |
| single-session-assistant | 56 | 11 |
| single-session-preference | 30 | 6 |
| **Total** | **500** | **100** (5 of them abstention questions) |

The committed list is `sample/lme_s_ids_n100.txt`; the rule, seed and counts are in `sample/sample_manifest.json`.

**Disclosures.**
- A 100-question subset was used in private development on 2026-09-30. It is not reused as-is: the 100 here are drawn fresh from all 500. By chance the two overlap on **23 of 100** questions (about 20 expected). The earlier ids are in `sample/prior_dev_subset_2026-09-30.ids` so this can be checked.
- Flux has already been run on all 500 questions during development, so no question is unseen by Flux. Flux is re-run on these 100 from a clean ingest, like every other system.
- The competitors were run privately on earlier subsets with the same reader and grader. Those runs informed which settings to document, not the settings of any system.

## Statistics

- Accuracy per arm, overall and per question type, with a Wilson 95% interval.
- Every other arm is compared with `flux_public` on the same question ids by a **paired exact McNemar test**, **Holm-corrected** across all comparisons made, and a **paired-bootstrap 95% interval** (10,000 resamples over questions, seed 0) for the accuracy difference.
- One run per arm. No re-rolls. A difference whose Holm-adjusted p is 0.05 or more is reported as a tie.
- Also reported per system: ingest time and LLM cost per haystack, retrieval latency (p50 and p95), items dropped or failed at ingest, and the share of empty retrievals.
- `analysis/analyze.py` rebuilds every table from the raw per-question outputs, and is unit-tested on synthetic data (`python3 -m unittest discover -s tests`).

## LoCoMo (second benchmark)

The same arms run on LoCoMo (Maharana et al., "Evaluating Very Long-Term Conversational Memory of LLM Agents", ACL 2024), with the same reader, judge model, context budget, embedder and competitor LLM as above.

**Attribution and licence.** LoCoMo is copyright **Snap Research** and is released under **CC BY-NC 4.0** (Attribution-NonCommercial). **The data is not redistributed here.** `sample/fetch_locomo.py` downloads `locomo10.json` from `github.com/snap-research/locomo` at the pinned commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376` and refuses a file whose sha256 is not `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`. It lands in `data/`, which is git-ignored, and so is the units file built from it. Only question ids and category numbers (`sample/locomo_qids.tsv`) are committed. **The LoCoMo numbers here are for research reporting.** They are not for advertising or other commercial use.

| Category (data-file number) | Questions |
|---|---|
| 1 multi-hop | 282 |
| 2 temporal | 321 |
| 3 open-domain | 96 |
| 4 single-hop | 841 |
| **1 to 4, judged** | **1,540** |
| 5 adversarial, reported separately | 446 |
| **All** | **1,986** (10 conversations, 272 sessions, 5,882 turns) |

- **Questions.** All 10 conversations and every question. Nothing is sampled or excluded. A conversation is one unit (one isolated store per conversation, all of its questions asked against it), built by `sample/prep_locomo.py` in the unit format the LongMemEval drivers already read, so every driver runs unchanged. A turn is `Speaker: text` (with the photo caption when there is one); dates are normalised to the LongMemEval format.
- **Categories 1 to 4.** The reader prompt is Snap's own (`prompts/locomo_prompts.py`). The grader is the published LLM-judge prompt used in the mem0 LoCoMo evaluation (it originates in the Zep evaluation), run on the same judge model and settings as LongMemEval (gpt-5-mini, minimal reasoning). The prompt is not ours; its source commit is cited in the file header.
- **Category 5 (adversarial)** is reported separately and never mixed into the overall figure. It uses the official LoCoMo handling: the reader is shown the question with two options, "Not mentioned in the conversation" and the adversarial answer, and scores 1 when it declines (the official string rule, no judge call). One departure: the official code shuffles the option order with `random.random()`; we derive it from `sha256(question id)` so a rerun gives the same prompts.
- **Tables** (`python3 analysis/analyze_locomo.py`): overall excluding category 5, per category, and category 5 on its own, each with Wilson 95% intervals, paired exact McNemar against `flux_public` (Holm) and paired-bootstrap intervals. Questions inside one conversation are not independent and the paired test treats them as if they were, so the intervals are, if anything, too narrow.
- **Retrieval query** is the raw question, never the option-augmented text.
- **Speakers.** Every turn carries its speaker name, which Flux's fact extraction reads (multi-party); the other arms see the `Speaker:` prefix in the text. mem0's ingestion maps both speakers to its `user` role, so for mem0 the name is in the text only.

## Cost table and usage profile

`python3 analysis/cost_table.py` writes `analysis/tables/cost_table.md` from the raw outputs, per system and benchmark: measured ingest cost per haystack (LongMemEval) or per conversation (LoCoMo), the memory system's own LLM cost per query, the reader and judge cost per query, retrieval latency p50 and p95, failure rates (failed units, dropped ingest items, failed or empty questions), a derived monthly cost, and each vendor's list price.

**The one usage profile for the derived figure:** a user has **30 sessions a month of 20 turns each (600 turns ingested)** and the application makes **100 recalls a month**. Memory cost per active user per month = 600 x (measured ingest $ per haystack / turns in that haystack) + 100 x (memory-system LLM $ per query). It counts the memory system's own LLM spend only: not the reader or judge, and not servers, storage or embeddings that we ran ourselves. It is therefore a cost of running the system as measured here, not a price. The vendor list-price column comes from `analysis/prices.json`, which is hand-edited with a url and a date per entry; the values are `null` (printed as TODO) until someone reads each pricing page.

## Stop rules

- An arm with more than 2% of ingest items failed or dropped is stopped, the setup is fixed and that arm is restarted from a clean store. This is a setup fix, not a re-roll, and is logged.
- Spend cap **$75** (raised from $55 by the owner on 2026-10-03, before the run started; both benchmarks together): when it is reached, stop and report what is complete. A partial arm is not reported as a result (`analyze.py` marks it INCOMPLETE and leaves it out of every comparison). `runner/ledger.py` keeps the ledger and refuses to start a stage that would pass the cap.
- Honcho: if its ingest cost passes **$0.15 per haystack** (averaged over the first 10), pause and find out why before continuing. On LoCoMo the rule is checked after the first 3 conversations against $0.18 per conversation.
- The Flux build is fixed before the draw.

Budget: `COST.md` (low about $35, high about $54 for both benchmarks).

## How to reproduce

You need your own keys: `DEEPSEEK_API_KEY` (reader, competitor LLMs), `JUDGE_API_KEY` (gpt-5-mini), and `PREF_JUDGE_API_KEY` plus `PREF_JUDGE_MODEL` if the preference judge is on a different endpoint. Keys are read from the environment only and are never stored in this repository. Competitor systems run in Docker on a Linux host, at most 2 containers per lane, one system after another.

```
# 1. Draw and prepare (needs your local copy of the dataset; the units file contains dataset text and is git-ignored)
export LME_S_PATH=/path/to/longmemeval_s_cleaned.json
python3 sample/draw_sample.py --check
python3 sample/prep_units.py --out work/units_n100.jsonl

# 2. Baselines (no memory system)
python3 drivers/closed_book.py  --units work/units_n100.jsonl --out results/closed_book
python3 drivers/full_context.py --units work/units_n100.jsonl --out results/full_context

# 3. Flux: needs a checkout of the Flux repo at c63e8d14 in FLUX_SRC
export FLUX_SRC=/path/to/flux-checkout
python3 drivers/flux_public.py --units work/units_n100.jsonl --out results/flux_public
python3 drivers/flux_extract_facts.py --units work/units_n100.jsonl --out work/facts_n100.jsonl     # about $2
python3 drivers/flux_evidence.py --units work/units_n100.jsonl --facts work/facts_n100.jsonl --out results/flux_evidence

# 4. Competitors, one at a time (see the header of each compose file for the exact commands)
#    compose/mem0/   compose/letta/   compose/honcho/    ->  results/mem0  results/letta  results/honcho_retrieval  results/honcho_chat

# 5. Reader and grader for every arm (the arm name inside retrieved.jsonl equals the directory name)
python3 runner/qa.py --inputs results/<arm>/retrieved.jsonl --arm <arm> --out results/<arm>/qa --reserve 3
python3 runner/ledger.py status

# 6. Tables
python3 analysis/analyze.py            # writes analysis/tables/tables.md and tables.json

# 7. LoCoMo (same arms; BENCH=locomo tags the spend ledger; results go under results/locomo/)
python3 sample/fetch_locomo.py                                   # pinned commit and sha256, into data/ (git-ignored)
python3 sample/prep_locomo.py --out work/locomo_units.jsonl      # one unit per conversation
export BENCH=locomo
python3 drivers/closed_book.py --units work/locomo_units.jsonl --out results/locomo/closed_book     # and every other arm, same commands as above
python3 runner/qa.py --bench locomo --inputs results/locomo/<arm>/retrieved.jsonl --arm <arm> --out results/locomo/<arm>/qa --reserve 3
python3 analysis/analyze_locomo.py     # writes analysis/tables/locomo_tables.md
python3 analysis/cost_table.py         # both benchmarks
```

Notes: `honcho_chat` has no ingest of its own and reads the Honcho workspaces made by the retrieval run; the analysis takes its ingest figures from `results/honcho_retrieval`. Raw per-question outputs (`qa/answers.jsonl`, `units.jsonl`, and `retrieved_meta.jsonl` made by `python3 runner/strip_retrieved.py results/<arm>/retrieved.jsonl`) are committed with the results. The full `retrieved.jsonl` holds retrieved haystack text, so it is not committed. Model answers in `answers.jsonl` may quote short passages of the dataset.

## Repository layout

| Path | Contents |
|---|---|
| `sample/` | the draw script, the id list, the seed, the manifest, the 2026-09-30 ids used for the overlap disclosure, the units builders, the LoCoMo downloader and the LoCoMo id table (ids and categories only) |
| `drivers/` | one driver per arm plus shared helpers and the model-call module (`llm.py`) |
| `infra/` | the local embedder server and the DeepSeek metering proxy used by the competitor containers |
| `compose/` | a docker-compose per competitor and `VERSIONS.md` |
| `prompts/` | the reader prompts, the official LongMemEval judge prompt and the published LoCoMo judge prompt (both verbatim, sources cited in the file headers), the judge settings and their hashes |
| `runner/` | the reader and grader runner and the spend ledger |
| `analysis/` | the table-rebuilding scripts (`analyze.py`, `analyze_locomo.py`), the cost table (`cost_table.py`, `prices.json`) and the budget estimate |
| `tests/` | unit tests on synthetic data |

## Known limits of this preparation

- **Flux arms run in-process, not over HTTP.** `flux_public` and `flux_evidence` run the release build's own retrieval and assembly modules from a checkout (the code the API serves, and the path behind the earlier 500-question numbers), not through a live `/v1/memory/recall` call. An HTTP route exists in the private tier-2 harness and has not been ported. Flux's source is not part of this repository.
- **Smoke-tested, not run.** A 2-haystack smoke run of all eight arms (built and run on a Linux host, one system at a time) passed on 2026-10-03 after the setup fixes in the commit log; the 100-question run has not started. The Flux arms run in a CPU container (`compose/flux/`). On a Docker host whose default address pools are used up, set `LANE_SUBNET` (the compose files default to 10.77.0.0/24).
- **The judges run on the provider endpoints you configure.** The private runs graded through FluxRouter. A direct `gpt-5-mini` call here does not send a temperature (the model rejects non-default values), and the GPT-6 Astra model id differs between APIs, so `PREF_JUDGE_MODEL` must be set. The frozen preference judge is therefore the one place a reader of this repository cannot reproduce exactly without access to that model.
- **Letta**: 0.16.8 is pinned to match earlier measurements, but newer releases exist (see `compose/VERSIONS.md`).
- **Honcho** is AGPL. We run it unmodified and ship only our driver and our `config.toml`.
- **Dataset text.** Only ids are published. Model answers may quote short passages of the haystacks; decide before publishing whether that is acceptable under the dataset's licence.
- **mem0 extraction is not deterministic.** The same input produced 445 memories in one run and 415 in another, so mem0's scores vary between runs even at temperature 0. One run per arm is reported, so a mem0 result carries run-to-run noise on top of the sampling interval.
- **License of this repository:** Apache-2.0 (`LICENSE`). It covers our code only, not LoCoMo or LongMemEval data.
