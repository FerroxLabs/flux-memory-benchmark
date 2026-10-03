# DRAFT, NOT SENT. Notice to the Honcho maintainers (Plastic Labs)

Do not send, post, or open an issue from this file. Sean decides when and where it goes. Fill the placeholders first.

**To:** Honcho maintainers (issue, Discord or email, channel to be chosen)
**Subject:** We are about to benchmark Honcho on LongMemEval-S: please check our configuration

Hello,

On [RUN START DATE, at least 48 hours after this is sent] we plan to run a public, reproducible LongMemEval-S comparison of Flux Memory against mem0 OSS, Letta and Honcho. The same reader model and the same grader are used for every system. We will publish the code, the question ids, the pinned versions, the raw outputs and the results, whatever they are, including ties and losses. The repository is here: [LINK TO PUBLIC REPO, to be filled in when it is published].

We run Honcho unmodified, self-hosted, and publish only our own driver code (none of Honcho's code is copied into our repository; we build the upstream Dockerfile at the pinned commit). We want it run the way you intend. Below is exactly what we will use. If any of it is wrong or suboptimal, please tell us before [DEADLINE = send time + 48 h]. Corrections that arrive before then are applied before the freeze. Later ones are noted in the report next to the results.

**Version:** v3.2.2, commit 06ed1929cf017c333a87c41d130bb6a0605d91c0, `uv.lock` frozen, upstream Dockerfile, PostgreSQL 17 with pgvector.

**Settings changed from defaults (everything else is default):**
- `deriver.FLUSH_ENABLED = true` (otherwise the deriver waits up to 30 minutes to batch; a benchmark needs prompt processing), `deriver.WORKERS = 8`
- `dream.ENABLED = false` and `summary.ENABLED = false` (idle-time consolidation and session summaries are not part of the retrieval under test; they would add LLM spend that the question never reads)
- `auth.USE_AUTH = false`, `cache.ENABLED = false`
- internal LLM for deriver and dialectic: `deepseek-flash` (DeepSeek, direct) through a local metering proxy that disables thinking and forces `json_object` structured output (DeepSeek has no `json_schema` mode)
- embeddings: `bge-small-en-v1.5` served locally over an OpenAI-compatible endpoint, `VECTOR_DIMENSIONS = 384`, no query instruction prefix
- `vector_store.TYPE = pgvector`

The complete `config.toml` is in the repository at `compose/honcho/config.toml`.

**Ingest (one workspace per question):** peers `user` and `assistant`; one Honcho session per conversation session; every turn posted as a message with `created_at` set to the session date (plus 1 ms per turn). We wait until the workspace queue is drained before querying.

**Two arms, reported separately:**
- *Retrieval arm (the primary Honcho arm):* `GET peers/{peer}/context` with `target` = the same peer, `search_query` = the question, `search_top_k=9`, `max_conclusions=9`, `include_most_frequent=false`, for each of the two peers, plus the peer card; at most 20 items, capped at 16 KiB.
- *Dialectic arm (labelled as an answering agent, not a retrieval list):* workspace `chat` with `reasoning_level=low`; its answer text is the single memory item given to the same reader.

**Questions for you:**
1. Is `peer.context` with a `search_query` the right retrieval call for "what is known that is relevant to this question"? Are the parameters sensible, or is there a better documented call or setting (for example for temporal questions)?
2. Is the peer layout (user and assistant as peers, observation on defaults) what you intend for chat-history memory?
3. Would you run the dialectic at a higher reasoning level, or with the DeepSeek thinking mode on, for a fair result?
4. Anything else you would change?

Reader: DeepSeek flash, temperature 0. Grader: the official LongMemEval judge prompt on gpt-5-mini (preference questions on GPT-6 Astra). Sample: 100 LongMemEval-S questions drawn with a published seed. Ingest time, LLM cost per haystack and dropped items are reported.

Thank you,
[NAME, ROLE, CONTACT]
