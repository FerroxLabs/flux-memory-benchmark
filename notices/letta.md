# DRAFT, NOT SENT. Notice to the Letta maintainers

Do not send, post, or open an issue from this file. Sean decides when and where it goes. Fill the placeholders first.

**To:** Letta maintainers (issue, Discord or email, channel to be chosen)
**Subject:** We are about to benchmark Letta on LongMemEval-S: please check our configuration

Hello,

On [RUN START DATE, at least 48 hours after this is sent] we plan to run a public, reproducible LongMemEval-S comparison of Flux Memory against mem0 OSS, Letta and Honcho. The same reader model and the same grader are used for every system. We will publish the code, the question ids, the pinned versions, the raw outputs and the results, whatever they are, including ties and losses. The repository is here: [LINK TO PUBLIC REPO, to be filled in when it is published].

We want Letta to be run the way you intend. Below is exactly what we will use. If any of it is wrong or suboptimal, please tell us before [DEADLINE = send time + 48 h]. Corrections that arrive before then are applied before the freeze. Later ones are noted in the report next to the results.

**Version:** letta 0.16.8 server (pip, extras `postgres,server`, pgvector database) with letta-client 1.11.0. We measured this version in earlier private tests. We see that newer releases exist (letta 0.34.2 on PyPI). **Which version do you want measured?** If you name a newer one we will re-pin and re-test before the freeze.

**Per haystack (one agent per question, hard isolation):** a new agent with one `persona` memory block, an LLM config pointing at a proxy that refuses every call (a $0 cap), and an OpenAI-endpoint embedding config for `bge-small-en-v1.5` served locally (`embedding_dim: 384`, `embedding_chunk_size: 300`).

**Ingest (archival memory only):** every conversation turn is inserted as one archival passage through `agents.passages.create(text=<turn>, tags=[<session date>, <role>])`. No LLM call is made at ingest or search. A failed insert is retried twice, then counted as dropped and reported. We know a turn above the 8,192-token embedding limit is rejected; we report such drops.

**Retrieval:** `agents.passages.search(query=<question>, top_k=20)`. The returned passages (with their date tag) are rendered into the reader prompt, capped at 16 KiB.

**Questions for you:**
1. We measure archival passage search because it is the documented memory retrieval path that does not depend on an agent's LLM loop, so the reader model is the only model that answers. Is that the path you want measured? If you would rather have the full agent (with its own memory tools) measured, tell us how you would configure it, and we will report it as a separate, labelled arm.
2. Are one passage per turn, chunk size 300 and `top_k=20` reasonable defaults for conversational history?
3. Anything else you would change?

Reader: DeepSeek flash, temperature 0. Grader: the official LongMemEval judge prompt on gpt-5-mini (preference questions on GPT-6 Astra). Sample: 100 LongMemEval-S questions drawn with a published seed. Ingest time, dropped items and spend are reported.

Thank you,
[NAME, ROLE, CONTACT]
