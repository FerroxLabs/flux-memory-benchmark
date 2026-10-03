# Pinned versions (recorded 2026-10-03)

| System | Pin | Source of the pin |
|---|---|---|
| Flux Memory (build under test) | repo integration/phaseb @ a3b8a520 (extraction PROMPT_VERSION 4) | the build named in the plan; the commit is fixed before the draw |
| mem0 OSS | mem0ai==2.2.1 (PyPI; also the current release on 2026-10-03) | used in the private runs of 2026-09-30 and 2026-10-01 |
| Letta | letta==0.16.8 server (pip, extras postgres,server) with letta-client==1.11.0 | used in the private runs; **newer releases exist** (PyPI letta 0.34.2, letta-client 1.12.1 on 2026-10-03), see note below |
| Honcho | tag v3.2.2, commit 06ed1929cf017c333a87c41d130bb6a0605d91c0 (released 2026-10-01; the current release on 2026-10-03), built from source with uv.lock frozen, unmodified | used in the private run of 2026-10-02 |
| pgvector (Letta and Honcho database) | pgvector/pgvector:pg17@sha256:ac08538c6f8b9904c33c8224c5e5706dbe760aca29db1d096972b4052c22a75d | tag pg17 as of 2026-10-03; the private runs used the pg17 tag, the digest was not recorded then |
| Python base image | python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016 (Honcho builds its own on 3.13 per its .python-version) | new pin for this repo |
| Embedder | BAAI/bge-small-en-v1.5 via fastembed==0.8.1 (ONNX build of the same model) | fastembed version is NOT from the private runs (not recorded there); pinned to the 2026-10-03 release |
| Embedder client libs | aiohttp==3.14.3, httpx==0.28.1, numpy==2.5.3 | 2026-10-03 releases, not from the private runs |
| Reader | deepseek-flash, DeepSeek API direct | as in the plan |
| Judge | gpt-5-mini (reasoning minimal) for all types except preference; GPT-6 Astra (reasoning low) for preference | as in the plan, decision 14 |

Letta note: the private measurements used 0.16.8. Pinning to it keeps this run comparable with those, but the Letta notice (notices/letta.md) must say a newer release exists and ask the maintainers which they want measured. If they name the newer release, re-pin before the freeze and re-run the Letta smoke test.

Smoke test 2026-10-03 (Hetzner, 2 haystacks, Flux build c63e8d14, which has the same code as a3b8a520 plus a manifests-only commit): all eight arms built, ran and were graded. Image sizes: flux 1.71 GB (python:3.12-slim, torch 2.8.0 CPU, transformers 4.56.2, numpy 2.4.4, usearch 2.26.2, cryptography 48.0.1, pydantic 2.13.4, prometheus-client 0.20.0), mem0 644 MB, letta 1.96 GB, honcho-pinned 580 MB plus our stack layer 902 MB total. The flux image pins are new in this repo (the Flux arms need them; compose/flux/Dockerfile).
