# Flux Memory vs mem0, Letta and Honcho on LongMemEval-S

**Status: prepared, not run, not published.** Nothing in this repository has been run against a paid API. No result exists yet. No marketing claim is made before the run is finished and the results are published here.

## The claim we want to be able to make, or not

On LongMemEval-S, with the same answering model, the same grader and the same context budget, Flux Memory scores X; mem0, Letta and Honcho score Y, Z and W. The code, the question list and the raw outputs are here; run it yourself.

We publish whatever comes out, including ties and losses. At 100 questions a paired test can only separate systems that are about 12 points apart. Gaps smaller than that are reported as ties, not as wins.

## What is under test

**Flux build: `integration/phaseb` @ `a3b8a520`** (fact extraction PROMPT_VERSION 4). The commit is fixed before the draw. No Flux change is made between the draw and the run.

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

Each system's own settings come from its own documentation and are not tuned by us on the test questions. The settings are in `drivers/` and `compose/`, and a notice with the exact configuration goes to each project 48 hours before the run (`notices/`, drafts only).

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

## Stop rules

- An arm with more than 2% of ingest items failed or dropped is stopped, the setup is fixed and that arm is restarted from a clean store. This is a setup fix, not a re-roll, and is logged.
- Spend cap **$40**: when it is reached, stop and report what is complete. A partial arm is not reported as a result (`analyze.py` marks it INCOMPLETE and leaves it out of every comparison). `runner/ledger.py` keeps the ledger and refuses to start a stage that would pass the cap.
- Honcho: if its ingest cost passes **$0.15 per haystack** (averaged over the first 10), pause and find out why before continuing.
- The Flux build is fixed before the draw.

Budget: `COST.md` (low about $23, high about $32).

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

# 3. Flux: needs a checkout of the Flux repo at a3b8a520 in FLUX_SRC
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
```

Notes: `honcho_chat` has no ingest of its own and reads the Honcho workspaces made by the retrieval run; the analysis takes its ingest figures from `results/honcho_retrieval`. Raw per-question outputs (`qa/answers.jsonl`, `units.jsonl`, and `retrieved_meta.jsonl` made by `python3 runner/strip_retrieved.py results/<arm>/retrieved.jsonl`) are committed with the results. The full `retrieved.jsonl` holds retrieved haystack text, so it is not committed. Model answers in `answers.jsonl` may quote short passages of the dataset.

## Repository layout

| Path | Contents |
|---|---|
| `sample/` | the draw script, the id list, the seed, the manifest, the 2026-09-30 ids used for the overlap disclosure, the units builder |
| `drivers/` | one driver per arm plus shared helpers and the model-call module (`llm.py`) |
| `infra/` | the local embedder server and the DeepSeek metering proxy used by the competitor containers |
| `compose/` | a docker-compose per competitor and `VERSIONS.md` |
| `prompts/` | the reader prompts, the official judge prompt (verbatim), the judge settings and their hashes |
| `runner/` | the reader and grader runner and the spend ledger |
| `analysis/` | the table-rebuilding script and the cost estimate |
| `notices/` | drafts of the pre-run notices to mem0, Letta and Honcho (not sent) |
| `tests/` | unit tests on synthetic data |

## Known limits of this preparation

- **Flux arms run in-process, not over HTTP.** `flux_public` and `flux_evidence` run the release build's own retrieval and assembly modules from a checkout (the code the API serves, and the path behind the earlier 500-question numbers), not through a live `/v1/memory/recall` call. An HTTP route exists in the private tier-2 harness and has not been ported. Flux's source is not part of this repository.
- **Nothing here has been run end to end.** The drivers are adapted from private drivers that were run; the adaptations (environment configuration, naming) and the compose files have not been exercised. The unit tests cover the analysis, the sampling and the runner with stubbed models only. No Docker on the development machine and no remote run was permitted at this stage. First step on the build host: `docker compose build` for each system and a 2-haystack smoke run, then freeze.
- **The judges run on the provider endpoints you configure.** The private runs graded through FluxRouter. A direct `gpt-5-mini` call here does not send a temperature (the model rejects non-default values), and the GPT-6 Astra model id differs between APIs, so `PREF_JUDGE_MODEL` must be set. The frozen preference judge is therefore the one place a reader of this repository cannot reproduce exactly without access to that model.
- **Letta**: 0.16.8 is pinned to match earlier measurements, but newer releases exist. The Letta notice asks which to measure.
- **Honcho** is AGPL. We run it unmodified and ship only our driver and our `config.toml`.
- **Dataset text.** Only ids are published. Model answers may quote short passages of the haystacks; decide before publishing whether that is acceptable under the dataset's licence.
- **License of this repository:** not yet chosen.
