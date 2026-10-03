"""LoCoMo prompts, scoring rules and context rendering. Do not edit: the analysis flags a run whose prompt hash differs from the one in its summary.json.

Sources (all public; pinned):
  Reader prompts: QA_PROMPT and QA_PROMPT_CAT_5 are verbatim from snap-research/locomo task_eval/gpt_utils.py at commit
    3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376 (Snap Research, CC BY-NC 4.0 repository). The conversation header is the same file's CONV_START_PROMPT
    reworded for retrieved excerpts (the excerpts are not a whole conversation). The category 5 option suffix is the same file, lines 245-252.
  Judge prompt (categories 1 to 4): ACCURACY_PROMPT is verbatim from mem0ai/mem0 evaluation/metrics/llm_judge.py at commit
    aae5989e78a6188b3b047c104d960c9ad0927e75 (Apache-2.0), the LLM-judge prompt used in the mem0 LoCoMo evaluation; it originates in the Zep LoCoMo
    evaluation. It is a published prompt that is not ours. The typographic quotes around CORRECT and WRONG are as published. Only the judge MODEL
    follows the LongMemEval setup (judges.json: gpt-5-mini, minimal reasoning), so the judge is held equal across both benchmarks.
  Category 5 (adversarial): scored with the official LoCoMo rule, no LLM judge: task_eval/gpt_utils.py get_cat_5_answer maps a bare 'a'/'b' or '(a)'/'(b)'
    reply to the option text, then task_eval/evaluation.py eval_question_answering scores 1 when the text contains 'no information available' or
    'not mentioned', else 0. One departure: the official code draws the option order with random.random(); we derive it from sha256(qid) so it is reproducible.
Category numbers follow the data file: 1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop, 5 adversarial.
"""
import hashlib, json, re

CAT_NAMES = {1: 'cat1-multi-hop', 2: 'cat2-temporal', 3: 'cat3-open-domain', 4: 'cat4-single-hop', 5: 'cat5-adversarial'}
ADVERSARIAL = 'cat5-adversarial'
NOT_MENTIONED = 'Not mentioned in the conversation'

CONV_HEADER = ("Below are excerpts from a conversation between two people. The conversation takes place over multiple days and the date of each "
               "excerpt is written at the beginning of it.\n\n")

QA_PROMPT = """
Based on the above context, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.

Question: {} Short answer:
"""

QA_PROMPT_CAT_5 = """
Based on the above context, answer the following question.

Question: {} Short answer:
"""

CAT5_SUFFIX = " Select the correct answer: (a) {} (b) {}. "

ACCURACY_PROMPT = """
Your task is to label an answer to a question as ’CORRECT’ or ’WRONG’. You will be given the following data:
    (1) a question (posed by one user to another user),
    (2) a ’gold’ (ground truth) answer,
    (3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Do you remember what I got the last time I went to Hawaii?
Gold answer: A shell necklace
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label".
"""


def cat5_options(qid, adversarial_answer):
    """-> {'a': text, 'b': text}. The order is a fixed function of the question id (official code: random.random() < 0.5)."""
    if hashlib.sha256(qid.encode()).digest()[0] % 2 == 0:
        return {'a': NOT_MENTIONED, 'b': str(adversarial_answer)}
    return {'a': str(adversarial_answer), 'b': NOT_MENTIONED}


def render(context):
    """context: [{'session_date', 'role', 'content'}] -> the context block (turns grouped by session date, oldest first; extracted facts, when
    an arm has them, are listed under their session). Turn content already starts with 'Speaker: '."""
    by, facts = {}, {}
    for t in context:
        if t['role'] == 'fact':
            facts.setdefault(t['session_date'], []).append(t['content']); by.setdefault(t['session_date'], [])
        else:
            by.setdefault(t['session_date'], []).append(t['content'])
    parts = []
    for date, turns in sorted(by.items()):
        s = f'DATE: {date}\n'
        if facts.get(date):
            s += 'FACTS:\n' + ''.join(f'- {x}\n' for x in facts[date])
        if turns:
            s += 'CONVERSATION:\n' + '\n'.join(turns) + '\n'
        parts.append(s)
    return '\n'.join(parts)


def reader_prompt(row):
    """The full reader prompt for one retrieved row (a cat 5 row carries the adversarial answer in 'answer')."""
    ctx = CONV_HEADER + render(row['context'])
    if row['type'] == ADVERSARIAL:
        o = cat5_options(row['qid'], row['answer'])
        return ctx + '\n' + QA_PROMPT_CAT_5.format(row['question'] + CAT5_SUFFIX.format(o['a'], o['b']))
    return ctx + '\n' + QA_PROMPT.format(row['question'])


def judge_prompt(question, gold, generated):
    return ACCURACY_PROMPT.format(question=question, gold_answer=gold, generated_answer=generated)


def parse_label(text):
    """The judge reply -> True (CORRECT) / False (WRONG). Raises ValueError if it is not exactly one of the two."""
    m = re.search(r'\{.*?\}', text, re.S)
    if m:
        try:
            lab = str(json.loads(m.group(0)).get('label', ''))
            text = lab or text
        except ValueError:
            pass
    found = {w.upper() for w in re.findall(r'\b(CORRECT|WRONG)\b', text, re.I)}
    if len(found) != 1:
        raise ValueError(f'judge_unparseable:{text[:60]!r}')
    return found == {'CORRECT'}


def score_cat5(reply, qid, adversarial_answer):
    """Official LoCoMo adversarial scoring. -> True when the reader declined (chose 'not mentioned')."""
    key = cat5_options(qid, adversarial_answer)
    p = reply.strip().lower()
    if len(p) == 1:
        p = key['a' if 'a' in p else 'b'].lower()
    elif len(p) == 3:
        p = key['a' if '(a)' in p else 'b'].lower()
    return 'no information available' in p or 'not mentioned' in p
