# DRAFT, NOT SENT. Notice to the mem0 maintainers

Do not send, post, or open an issue from this file. Sean decides when and where it goes. Fill the placeholders first.

**To:** mem0 maintainers (issue or email, channel to be chosen)
**Subject:** We are about to benchmark mem0 OSS on LongMemEval-S: please check our configuration

Hello,

On [RUN START DATE, at least 48 hours after this is sent] we plan to run a public, reproducible LongMemEval-S comparison of Flux Memory against mem0 OSS, Letta and Honcho. The same reader model and the same grader are used for every system. We will publish the code, the question ids, the pinned versions, the raw outputs and the results, whatever they are, including ties and losses. The repository is here: [LINK TO PUBLIC REPO, to be filled in when it is published].

We want mem0 to be run the way you intend it to be run. Below is exactly what we will use. If any of it is wrong or suboptimal for your documented defaults, please tell us before [DEADLINE = send time + 48 h]. Corrections that arrive before then are applied before the freeze. Later ones are noted in the report next to the results.

**Version:** mem0ai 2.2.1 (PyPI), the open-source `Memory` class, in-process, no hosted platform.

**Per haystack (one isolated store per question):** a fresh `Memory.from_config` with a private on-disk Qdrant directory and history database.

**Configuration:**
- vector store: `qdrant`, local path, `on_disk: True`, collection `h2h`, `embedding_model_dims: 384`
- LLM (mem0's own extraction): provider `openai` (OpenAI-compatible), model `deepseek-flash` (DeepSeek, direct), `temperature: 0`, `max_tokens: 8000`
- embedder: provider `openai` (OpenAI-compatible), `bge-small-en-v1.5` served locally, `embedding_dims: 384`, no query instruction prefix
- everything else is the shipped default (extraction on, no reranker)

**Ingest:** one `add()` per conversation session, with the session's turns as role-tagged messages (`user` or `assistant`), `user_id` set to the question id, and `metadata={'session_date': '<date>'}`. Sessions are added in haystack order. A failed `add()` is retried once, then counted as dropped and reported.

**Retrieval:** `search(question, filters={'user_id': <question id>}, top_k=20)`. The returned memories (with their `session_date` metadata) are rendered into the reader prompt, capped at 16 KiB.

**Questions for you:**
1. The OSS SDK rejected a `timestamp=` argument on `add()` in our tests, so the historical session date travels in metadata only. Is there a documented way to give OSS mem0 the real time of a conversation so it can use it for temporal questions? If so, we will use it.
2. Is `search()` with the default settings the retrieval path you want measured, or is there a documented option (reranker, a different search call, thresholds) that you consider the intended default?
3. Is one `add()` per session the intended granularity, or would you batch or split differently?
4. Anything else in the configuration above that you would change?

Reader: DeepSeek flash, temperature 0. Grader: the official LongMemEval judge prompt on gpt-5-mini (preference questions on GPT-6 Astra). Sample: 100 LongMemEval-S questions drawn with a published seed. Spend and per-system ingest time and cost are reported.

Thank you,
[NAME, ROLE, CONTACT]
