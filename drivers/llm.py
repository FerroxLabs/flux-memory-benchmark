"""Model calls for reader and judges. Everything is configured from the environment; no key is ever stored in this repo.

Reader   (all arms, held equal): READER_BASE_URL (default https://api.deepseek.com), key in DEEPSEEK_API_KEY (or the file named by
         DEEPSEEK_API_KEY_FILE), model READER_MODEL (default deepseek-flash), temperature 0, max_tokens 6000, thinking at the provider default.
Judge    (non-preference): JUDGE_BASE_URL (default https://api.openai.com/v1), JUDGE_API_KEY, JUDGE_MODEL (default gpt-5-mini),
         reasoning_effort minimal, max_completion_tokens 10.
Pref     (single-session-preference, decision 14): PREF_JUDGE_BASE_URL / PREF_JUDGE_API_KEY (default to the JUDGE_* values),
         PREF_JUDGE_MODEL (default gpt-6-astra), reasoning_effort low, max_completion_tokens 2000.
Limits:  READER_INFLIGHT (default 8), JUDGE_INFLIGHT (default 2), <=2 retries on 429/5xx, a breaker that aborts once 429+503 pass 2% of >=50 calls.
Cost:    DeepSeek calls are priced at DeepSeek list price at call time (peak Mon-Fri 01-04 and 06-10 UTC x1, otherwise x0.5; $0.006 cache hit,
         $0.30 miss, $1.20 output per 1M). Judge cost uses JUDGE_USD_PER_M_IN / JUDGE_USD_PER_M_OUT if you set them; tokens are always recorded.
"""
import json, os, random, threading, time, urllib.error, urllib.request
from datetime import datetime, timezone


class Breaker(Exception):
    pass


class OffModel(Exception):
    pass


class Gate:
    def __init__(self, name, inflight, rps):
        self.name, self.sem, self.rps = name, threading.BoundedSemaphore(inflight), rps
        self.lock, self.last = threading.Lock(), 0.0
        self.attempts = self.bad = self.calls = 0
        self.cost = 0.0
        self.offmodel = []

    def pace(self):
        with self.lock:
            wait = self.last + 1.0 / self.rps - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()

    def record(self, status):
        with self.lock:
            self.attempts += 1
            self.bad += status in (429, 503)
            if self.attempts >= 50 and self.bad / self.attempts > 0.02:
                raise Breaker(f'{self.name}: 429/503 {self.bad}/{self.attempts} > 2%')

    def add_cost(self, c):
        with self.lock:
            self.cost += c
            self.calls += 1


READER = Gate('reader', int(os.environ.get('READER_INFLIGHT', '8')), 10.0)
JUDGE = Gate('judge', int(os.environ.get('JUDGE_INFLIGHT', '2')), 3.0)


def _key(env, file_env=None):
    if os.environ.get(env):
        return os.environ[env].strip()
    if file_env and os.environ.get(file_env):
        return open(os.path.expanduser(os.environ[file_env])).read().strip()
    raise RuntimeError(f'set {env}')


def ds_price(u, t):
    d = datetime.fromtimestamp(t, timezone.utc)
    k = 1.0 if d.weekday() < 5 and (1 <= d.hour < 4 or 6 <= d.hour < 10) else 0.5
    hit = u.get('prompt_cache_hit_tokens', 0) or 0
    miss = u.get('prompt_cache_miss_tokens', (u.get('prompt_tokens', 0) or 0) - hit) or 0
    return k * (hit * 0.006 + miss * 0.30 + (u.get('completion_tokens', 0) or 0) * 1.20) / 1e6


def _post(gate, url, key, body, timeout):
    data = json.dumps(body).encode()
    for i in range(3):
        req = urllib.request.Request(url, data=data, method='POST', headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        retry_after = None
        try:
            gate.pace()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                gate.record(200)
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            gate.record(e.code)
            retry_after = e.headers.get('Retry-After') if e.headers else None
            if not (e.code == 429 or e.code >= 500) or i == 2:
                raise RuntimeError(f'http_{e.code}') from None
        try:
            delay = float(retry_after) if retry_after else 2.0 * 2 ** i
        except ValueError:
            delay = 2.0 * 2 ** i
        time.sleep(min(60.0, delay) + random.uniform(0, 1.0))


def reader(prompt, max_tokens=6000):
    """The held-equal reader. -> {content, cost, usage}. A reply from a non-deepseek model is refused when READER_REQUIRE_DEEPSEEK=1 (default)."""
    base = os.environ.get('READER_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    model = os.environ.get('READER_MODEL', 'deepseek-flash')
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0, 'max_tokens': max_tokens}
    t0 = time.time()
    with READER.sem:
        d = _post(READER, base + '/chat/completions', _key('DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY_FILE'), body, 600)
    u = d.get('usage') or {}
    cost = ds_price(u, t0)
    READER.add_cost(cost)
    if os.environ.get('READER_REQUIRE_DEEPSEEK', '1') == '1' and 'deepseek' not in str(d.get('model', '')).lower():
        READER.offmodel.append({'asked': model, 'served': d.get('model'), 'cost': cost})
        raise OffModel(str(d.get('model')))
    return {'content': d['choices'][0]['message'].get('content') or '', 'cost': cost, 'usage': u}


def judge(prompt, preference=False):
    """-> {content, cost, usage, model}. preference=True uses the decision-14 preference judge."""
    p = 'PREF_' if preference else ''
    base = os.environ.get(p + 'JUDGE_BASE_URL', os.environ.get('JUDGE_BASE_URL', 'https://api.openai.com/v1')).rstrip('/')
    key = os.environ.get(p + 'JUDGE_API_KEY') or _key('JUDGE_API_KEY')
    model = os.environ.get(p + 'JUDGE_MODEL', 'gpt-6-astra' if preference else 'gpt-5-mini')
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}],
            'max_completion_tokens': 2000 if preference else 10, 'reasoning_effort': 'low' if preference else 'minimal'}
    with JUDGE.sem:
        d = _post(JUDGE, base + '/chat/completions', key, body, 300)
    u = d.get('usage') or {}
    cost = (u.get('prompt_tokens', 0) * float(os.environ.get('JUDGE_USD_PER_M_IN', 0)) +
            u.get('completion_tokens', 0) * float(os.environ.get('JUDGE_USD_PER_M_OUT', 0))) / 1e6
    JUDGE.add_cost(cost)
    return {'content': (d['choices'][0]['message'].get('content') or '') if d.get('choices') else '', 'cost': cost, 'usage': u,
            'model': str(d.get('model') or model)}


def deepseek(prompt, max_tokens, thinking=True, json_mode=False, timeout=600):
    """Used only by drivers/flux_extract_facts.py (Flux's own fact extraction, thinking off, JSON mode)."""
    base = os.environ.get('READER_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    body = {'model': os.environ.get('READER_MODEL', 'deepseek-flash'), 'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0 if not thinking else 1.0, 'max_tokens': max_tokens}
    if not thinking:
        body['thinking'] = {'type': 'disabled'}
    if json_mode:
        body['response_format'] = {'type': 'json_object'}
    t0 = time.time()
    with READER.sem:
        d = _post(READER, base + '/chat/completions', _key('DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY_FILE'), body, timeout)
    u = d.get('usage') or {}
    cost = ds_price(u, t0)
    READER.add_cost(cost)
    return {'content': d['choices'][0]['message'].get('content') or '', 'cost': cost, 'usage': u}
