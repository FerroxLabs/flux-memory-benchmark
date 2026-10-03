# Publish checklist (a human confirms every item before this repository is made public)

Kept as the record of what was checked before this repository was made public on 2026-10-03 (see the verification section at the end).

Status of each item as of the commit that added this file is given in brackets; it is a check by the author of the commit, not a confirmation.

## Data and licences
- [ ] LoCoMo (Snap Research, CC BY-NC 4.0 per README): confirm the licence text yourself at `github.com/snap-research/locomo`, that the credit to Snap Research and the paper (Maharana et al., ACL 2024) in README.md and REPORT.md is acceptable, and that no LoCoMo conversation, question or gold answer is in the repo. [`results-public/locomo/` holds only qid, category, arm, correct, verdict, judge kind, error class, costs; full outputs are in git-ignored `results/`.]
- [ ] LongMemEval: the kit docs state no licence for the data. Decide whether to redistribute per-item outputs. [Stripped the same way as LoCoMo; full files git-ignored.]
- [ ] Question ids of both benchmarks (`sample/lme_s_ids_n100.txt`, `sample/locomo_qids.tsv`) are acceptable to publish.
- [ ] No dataset file in git history. [`git log --all --name-only` lists no dataset, units or retrieved file; the largest blob is `sample/locomo_qids.tsv`, 58 KB, ids and category numbers only. `work/`, `data/` and `results/*` are ignored. The local `work/` directory does contain dataset text: never `git add -f` it.]
- [ ] Honcho is AGPL-3.0: the repo contains no Honcho source. [Only `drivers/honcho_*.py` (HTTP calls), `compose/honcho/` (our config, Dockerfile, fetch script that clones upstream at a pinned commit into the ignored `honcho-src/`), and results. Searched the files to be committed for `honcho-src` paths and AGPL text: only mentions in prose.] Confirm with counsel if in doubt.

## Secrets
- [ ] Re-run a secrets scan on the exact tree to publish (also on full git history), for example `gitleaks detect` or a grep for `sk-`, `Bearer `, `api_key=`. [Author's grep over all 62 files to be committed found no key-like string. `run.sh` only reads keys from files on the run host; `compose/honcho/config.toml` contains placeholders (`proxy-key-not-a-secret`, `honcho-local-only` database password for a throwaway container).] Nothing was copied from the run host's `keys/` directory.
- [ ] `results-public/run-logs/` (progress.log, qa summaries, build logs, run.sh) contain no hostnames or paths you do not want public.

## Numbers
- [ ] Every number in REPORT.md and the Honcho block of COST.md is produced by `python3 analysis/report.py` from `results-public/`. Run `python3 analysis/report.py --check` (exit 0) on the final tree. Regenerating from full outputs: `python3 analysis/make_public.py` first.
- [ ] Read the "Deviations from the preregistration" section of REPORT.md and agree with it. Items to confirm: the exact commit of the kit that ran on the run host (the log says only "archive"), and the Flux build commit `c63e8d14` (not verifiable from the copied build log).
- [ ] The Honcho chat result (85.6% on LoCoMo, above every Flux arm and full context) is stated plainly in REPORT.md and is not softened or removed.

## Use
- [ ] The repo and its numbers are not used in paid advertising or other commercial promotion for LoCoMo figures (CC BY-NC 4.0 and the README: research reporting only).
- [ ] No claim of "best" or "winner" appears in any public text derived from REPORT.md.
- [ ] Decide separately before publishing whether to rerun Letta on a current release (README known limit) and whether Flux's in-process runs need an HTTP-path rerun.

## Verification on 2026-10-03 (before publishing)
- LoCoMo licence read at github.com/snap-research/locomo/LICENSE.txt: Attribution-NonCommercial 4.0 International. LongMemEval repository licence: MIT.
- Secrets: pattern search over every commit in the history found nothing.
- Kit that ran: file hashes on the run host equal commit `a9a65be`. Flux build: `src/flux_memory` on the run host equals `c63e8d14` file for file.
- `python3 analysis/report.py --check` exits 0 on the published tree.
- No Honcho source, no dataset text, no host names or private paths in tracked files (one Docker cache path inside a build log).
- Commit author e-mail normalised to the company address before the first push.
