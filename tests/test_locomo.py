"""LoCoMo loader, prompts, analysis and cost-table tests on synthetic data only (no dataset text, no network, no keys).
Run: python3 -m unittest discover -s tests -v"""
import json, os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ('analysis', 'sample', 'runner', 'drivers', 'prompts'):
    sys.path.insert(0, os.path.join(ROOT, p))
import analyze, analyze_locomo, cost_table, fetch_locomo, ledger, locomo_prompts as LP, prep_locomo  # noqa: E402

CATS = ['cat1-multi-hop', 'cat2-temporal', 'cat3-open-domain', 'cat4-single-hop', 'cat5-adversarial']


def synth_locomo():
    """Two conversations, three sessions (one empty), one photo turn, all five categories; cat 5 has adversarial_answer only."""
    def conv(sid, a, b):
        return {'sample_id': sid, 'conversation': {
            'speaker_a': a, 'speaker_b': b,
            'session_1_date_time': '1:56 pm on 8 May, 2023',
            'session_1': [{'speaker': a, 'text': 'hello', 'dia_id': 'D1:1'}, {'speaker': b, 'text': 'hi there', 'dia_id': 'D1:2', 'blip_caption': 'a red kite'}],
            'session_2_date_time': '9:30 am on 20 June, 2023', 'session_2': [{'speaker': a, 'text': 'later', 'dia_id': 'D2:1'}],
            'session_3_date_time': '2:00 pm on 1 July, 2023', 'session_3': []},
            'qa': [{'question': 'q1?', 'answer': 'x', 'category': 1, 'evidence': []}, {'question': 'q2?', 'answer': 2022, 'category': 2, 'evidence': []},
                   {'question': 'q3?', 'answer': 'y; z', 'category': 3, 'evidence': []}, {'question': 'q4?', 'answer': 'w', 'category': 4, 'evidence': []},
                   {'question': 'q5?', 'adversarial_answer': 'trap', 'category': 5, 'evidence': []}]}
    return [conv('conv-1', 'Ann', 'Bob'), conv('conv-2', 'Cy', 'Di')]


class TestLoader(unittest.TestCase):
    def test_units(self):
        us = prep_locomo.build_units(synth_locomo())
        self.assertEqual([u['unit_id'] for u in us], ['conv-1', 'conv-2'])
        u = us[0]
        self.assertEqual(len(u['sessions']), 2)                                   # the empty session is dropped
        self.assertEqual(u['sessions'][0]['date'], '2023/05/08 (Mon) 13:56')
        self.assertEqual(u['sessions'][1]['date'], '2023/06/20 (Tue) 09:30')
        t0, t1 = u['sessions'][0]['turns']
        self.assertEqual(t0, {'role': 'Ann', 'speaker': 'Ann', 'content': 'Ann: hello'})
        self.assertEqual(t1['content'], 'Bob: hi there [shares a photo: a red kite]')
        self.assertEqual(u['sessions'][0]['session_id'], 'conv-1__session_1')
        qs = u['questions']
        self.assertEqual([q['type'] for q in qs], CATS)
        self.assertEqual([q['qid'] for q in qs], [f'conv-1__q{i}' for i in range(5)])
        self.assertEqual(qs[1]['answer'], '2022')                                  # numeric gold answers become strings
        self.assertEqual(qs[4]['answer'], 'trap')                                  # cat 5: the adversarial answer
        self.assertTrue(all(q['question_date'] == '2023/06/20 (Tue) 09:30' for q in qs))
        self.assertTrue(all(q['abstention'] is False for q in qs))

    def test_qid_table_counts(self):
        tab = prep_locomo.qid_table(prep_locomo.build_units(synth_locomo()))
        self.assertEqual(len(tab), 10)
        self.assertEqual(sum(1 for _, t in tab if t == 'cat5-adversarial'), 2)

    def test_units_are_driver_compatible(self):
        """The LongMemEval drivers read exactly these keys."""
        for u in prep_locomo.build_units(synth_locomo()):
            self.assertTrue({'unit_id', 'sessions', 'questions'} <= set(u))
            for s in u['sessions']:
                self.assertTrue({'session_id', 'date', 'turns'} <= set(s))
                self.assertTrue(all({'role', 'content'} <= set(t) for t in s['turns']))
            for q in u['questions']:
                self.assertTrue({'qid', 'type', 'question', 'question_date', 'answer', 'abstention'} <= set(q))

    def test_fetch_sha_check(self):
        data = b'{"x": 1}'
        import hashlib
        self.assertEqual(fetch_locomo.verify(data, hashlib.sha256(data).hexdigest()), hashlib.sha256(data).hexdigest())
        with self.assertRaises(ValueError):
            fetch_locomo.verify(data + b' ', hashlib.sha256(data).hexdigest())
        self.assertIn(fetch_locomo.COMMIT, fetch_locomo.URL)
        self.assertEqual(len(fetch_locomo.SHA256), 64)

    def test_data_is_git_ignored(self):
        r = subprocess.run(['git', 'check-ignore', 'data/locomo10.json', 'work/locomo_units.jsonl'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.stdout.split(), ['data/locomo10.json', 'work/locomo_units.jsonl'])


class TestPrompts(unittest.TestCase):
    def test_cat5_options_deterministic_and_balanced(self):
        self.assertEqual(LP.cat5_options('a', 'trap'), LP.cat5_options('a', 'trap'))
        firsts = {LP.cat5_options(f'q{i}', 'trap')['a'] for i in range(40)}
        self.assertEqual(firsts, {'trap', LP.NOT_MENTIONED})
        for i in range(10):
            self.assertEqual(set(LP.cat5_options(f'q{i}', 'trap').values()), {'trap', LP.NOT_MENTIONED})

    def test_score_cat5_official_rule(self):
        qid = next(f'q{i}' for i in range(50) if LP.cat5_options(f'q{i}', 'trap')['a'] == LP.NOT_MENTIONED)   # a = declines
        self.assertTrue(LP.score_cat5('a', qid, 'trap')); self.assertTrue(LP.score_cat5('(a)', qid, 'trap'))
        self.assertFalse(LP.score_cat5('b', qid, 'trap')); self.assertFalse(LP.score_cat5('(b)', qid, 'trap'))
        self.assertTrue(LP.score_cat5('Not mentioned in the conversation', qid, 'trap'))
        self.assertTrue(LP.score_cat5('No information available', qid, 'trap'))
        self.assertFalse(LP.score_cat5('trap', qid, 'trap'))
        self.assertFalse(LP.score_cat5('', qid, 'trap'))
        qid2 = next(f'q{i}' for i in range(50) if LP.cat5_options(f'q{i}', 'trap')['a'] == 'trap')           # a = the trap
        self.assertFalse(LP.score_cat5('a', qid2, 'trap')); self.assertTrue(LP.score_cat5('b', qid2, 'trap'))

    def test_parse_label(self):
        self.assertTrue(LP.parse_label('{"label": "CORRECT"}'))
        self.assertFalse(LP.parse_label('Different date. {"label": "WRONG"}'))
        self.assertTrue(LP.parse_label('same topic, so CORRECT'))
        self.assertTrue(LP.parse_label('{"label": "correct"}'))
        for bad in ('', 'maybe', 'CORRECT or WRONG', '{"label": "INCORRECT"}'):
            with self.assertRaises(ValueError):
                LP.parse_label(bad)

    def test_render_groups_by_date_and_lists_facts(self):
        ctx = [{'session_date': '2023/06/20 (Tue) 09:30', 'role': 'Ann', 'content': 'Ann: later'},
               {'session_date': '2023/05/08 (Mon) 13:56', 'role': 'Bob', 'content': 'Bob: hi'},
               {'session_date': '2023/05/08 (Mon) 13:56', 'role': 'fact', 'content': 'Bob greeted Ann'}]
        out = LP.render(ctx)
        self.assertLess(out.index('2023/05/08'), out.index('2023/06/20'))
        self.assertIn('FACTS:\n- Bob greeted Ann', out); self.assertIn('CONVERSATION:\nBob: hi', out)

    def test_reader_prompt(self):
        row = {'qid': 'q1', 'type': 'cat1-multi-hop', 'question': 'Who?', 'answer': 'x', 'context': [{'session_date': 'd', 'role': 'A', 'content': 'A: hi'}]}
        p = LP.reader_prompt(row)
        self.assertIn('A: hi', p); self.assertIn('Question: Who? Short answer:', p); self.assertNotIn('Select the correct answer', p)
        p5 = LP.reader_prompt(dict(row, type=LP.ADVERSARIAL, answer='trap'))
        self.assertIn('Select the correct answer: (a)', p5); self.assertIn(LP.NOT_MENTIONED, p5); self.assertIn('trap', p5)

    def test_judge_prompt_is_the_published_one(self):
        p = LP.judge_prompt('Q', 'G', 'A')
        self.assertIn('Question: Q\nGold answer: G\nGenerated answer: A', p)
        self.assertIn('label CORRECT or WRONG', p)

    def test_prompt_hash_differs_by_bench(self):
        self.assertNotEqual(analyze.prompt_sha('lme'), analyze.prompt_sha('locomo'))
        sys.path.insert(0, os.path.join(ROOT, 'runner'))
        import qa  # noqa: E402  (imports llm only; no network at import)
        self.assertEqual(qa.prompt_sha('locomo'), analyze.prompt_sha('locomo'))
        self.assertEqual(qa.prompt_sha('lme'), analyze.prompt_sha('lme'))


def write_arm(root, arm, labels, types, units=None, retrieved=None, sha=None, reader=0.0005, judge=0.0003):
    d = os.path.join(root, arm); os.makedirs(os.path.join(d, 'qa'))
    with open(os.path.join(d, 'qa', 'answers.jsonl'), 'w') as f:
        for q, v in labels.items():
            f.write(json.dumps({'qid': q, 'type': types[q], 'label': bool(v), 'reader_cost': reader, 'judge_cost': 0 if types[q] == LP.ADVERSARIAL else judge}) + '\n')
    json.dump({'prompt_sha256': sha or analyze.prompt_sha('locomo')}, open(os.path.join(d, 'qa', 'summary.json'), 'w'))
    if units is not None:
        open(os.path.join(d, 'units.jsonl'), 'w').write(''.join(json.dumps(u) + '\n' for u in units))
    if retrieved is not None:
        open(os.path.join(d, 'retrieved_meta.jsonl'), 'w').write(''.join(json.dumps(r) + '\n' for r in retrieved))


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = os.path.join(self.tmp.name, 'locomo'); os.makedirs(self.root)
        # 100 questions: cats 1-4 get 20 each, cat 5 gets 20 (so the split is checkable)
        self.tab = [(f'c{i:03d}', CATS[i % 5]) for i in range(100)]
        self.ids = os.path.join(self.tmp.name, 'ids.tsv')
        open(self.ids, 'w').write(''.join(f'{q}\t{t}\n' for q, t in self.tab))
        self.types = dict(self.tab)

    def tearDown(self):
        self.tmp.cleanup()

    def test_split_and_tables(self):
        qs = [q for q, _ in self.tab]
        base = {q: 1 if i < 70 else 0 for i, q in enumerate(qs)}             # 70/100 overall
        worse = {q: 0 for q in qs}
        units = [{'unit_id': f'conv-{i}', 'ingest': {'seconds': 10.0, 'llm_usd': 0.05, 'items_total': 100, 'items_dropped': 0}} for i in range(10)]
        write_arm(self.root, 'flux_public', base, self.types, units, [{'n_context': 5, 'search_ms': 10.0}])
        write_arm(self.root, 'mem0', worse, self.types, units)
        write_arm(self.root, 'letta', {q: base[q] for q in qs[:60]}, self.types)       # incomplete
        r = analyze_locomo.analyse(self.root, self.ids, bootstrap_n=200)
        main, adv = r['main'], r['adversarial']
        self.assertEqual((r['n_main'], r['n_adv']), (80, 20))
        n_base_main = sum(base[q] for q, t in self.tab if t != LP.ADVERSARIAL)
        n_base_adv = sum(base[q] for q, t in self.tab if t == LP.ADVERSARIAL)
        self.assertEqual(main['arms']['flux_public']['correct'], n_base_main)
        self.assertEqual(adv['arms']['flux_public']['correct'], n_base_adv)
        self.assertEqual(n_base_main + n_base_adv, 70)
        self.assertEqual(sorted(main['types']), sorted(CATS[:4]))                       # category 5 is not among the main categories
        self.assertEqual(sum(v[1] for v in main['arms']['flux_public']['by_type'].values()), 80)
        self.assertFalse(main['arms']['letta']['complete'])
        self.assertNotIn('letta', main['comparisons'])
        self.assertEqual(main['comparisons']['mem0']['verdict'], 'worse than baseline')
        self.assertEqual(adv['comparisons']['mem0']['arm_only'], 0)
        self.assertNotIn('ops', adv)
        self.assertEqual(main['ops']['mem0']['haystacks'], 10)
        self.assertTrue(any('letta: INCOMPLETE' in f for f in main['flags']))
        md = analyze_locomo.tables(r)
        for h in ('## 1. Overall, categories 1 to 4 (n=80', '## 2. Per category', '## 3. Category 5, adversarial (n=20', 'INCOMPLETE (48/80)'):
            self.assertIn(h, md)
        self.assertIn('cat1-multi-hop', md); self.assertIn('Ingest LLM $/conversation', md)

    def test_prompt_hash_flag_uses_locomo_hash(self):
        qs = [q for q, _ in self.tab]
        write_arm(self.root, 'flux_public', {q: 1 for q in qs}, self.types)
        write_arm(self.root, 'mem0', {q: 1 for q in qs}, self.types, sha=analyze.prompt_sha('lme'))      # the LME hash is wrong for LoCoMo
        r = analyze_locomo.analyse(self.root, self.ids, bootstrap_n=50)
        flags = ' | '.join(r['main']['flags'])
        self.assertIn('mem0: prompt hash', flags); self.assertNotIn('flux_public: prompt hash', flags)

    def test_spend_by_bench_and_cap(self):
        qs = [q for q, _ in self.tab]
        write_arm(self.root, 'flux_public', {q: 1 for q in qs}, self.types)
        led = os.path.join(self.tmp.name, 'ledger.jsonl')
        open(led, 'w').write(json.dumps({'arm': 'mem0', 'stage': 'ingest', 'usd': 30.0, 'bench': 'lme'}) + '\n' +
                             json.dumps({'arm': 'mem0', 'stage': 'ingest', 'usd': 20.0, 'bench': 'locomo'}) + '\n' + json.dumps({'arm': 'letta', 'stage': 'qa', 'usd': 6.0}) + '\n')
        r = analyze_locomo.analyse(self.root, self.ids, bootstrap_n=50, ledger=led)
        s = r['main']['spend']
        self.assertEqual(s['by_bench'], {'lme': 36.0, 'locomo': 20.0})                  # a row without a bench counts as lme
        self.assertEqual(s['cap'], 55.0)
        self.assertTrue(any('over the $55 cap' in f for f in r['main']['flags']))


class TestCostTable(unittest.TestCase):
    def test_monthly_profile(self):
        self.assertEqual(cost_table.TURNS_PER_MONTH, 600)
        # $0.10 per 500-turn haystack -> $0.0002/turn -> 600 turns = $0.12; 100 recalls at $0.001 = $0.10
        self.assertAlmostEqual(cost_table.monthly(0.10, 500, 0.001), 0.22, places=6)
        self.assertAlmostEqual(cost_table.monthly(0.0, 500, None), 0.0)
        self.assertIsNone(cost_table.monthly(None, 500, 0.001)); self.assertIsNone(cost_table.monthly(0.1, None, 0.0))

    def test_mean_turns(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'u.jsonl')
            open(p, 'w').write(json.dumps({'sessions': [{'turns': [1, 2, 3]}]}) + '\n' + json.dumps({'sessions': [{'turns': [1]}, {'turns': [1, 2]}]}) + '\n')
            self.assertEqual(cost_table.mean_turns(p), 3.0)
            self.assertIsNone(cost_table.mean_turns(os.path.join(d, 'nope.jsonl')))

    def test_rows_and_render(self):
        with tempfile.TemporaryDirectory() as d:
            res = os.path.join(d, 'locomo'); os.makedirs(res)
            tab = [(f'c{i}', CATS[i % 4]) for i in range(10)]
            types = dict(tab)
            units = [{'unit_id': f'conv-{i}', 'ingest': {'seconds': 20.0, 'llm_usd': 0.06, 'items_total': 100, 'items_dropped': 2}} for i in range(4)]
            units.append({'unit_id': 'conv-x', 'error': 'boom'})
            retrieved = [{'n_context': 3, 'search_ms': float(m)} for m in range(1, 101)]
            write_arm(res, 'mem0', {q: 1 for q, _ in tab}, types, units, retrieved)
            with open(os.path.join(res, 'mem0', 'qa', 'answers.jsonl'), 'a') as f:
                f.write(json.dumps({'qid': 'bad', 'type': CATS[0], 'label': False, 'error': 'x'}) + '\n')
            led = os.path.join(d, 'ledger.jsonl')
            open(led, 'w').write(json.dumps({'arm': 'mem0', 'stage': 'query', 'usd': 0.11, 'bench': 'locomo'}) + '\n' +
                                 json.dumps({'arm': 'mem0', 'stage': 'query', 'usd': 9.0, 'bench': 'lme'}) + '\n')
            rows = cost_table.build(res, 'locomo', 600.0, led)
            self.assertEqual(len(rows), 1); r = rows[0]
            self.assertEqual(r['ingest_usd'], 0.06)
            self.assertAlmostEqual(r['query_usd'], 0.01)                       # 0.11 over the 11 answered rows; the lme row is ignored
            self.assertAlmostEqual(r['unit_fail'], 0.2); self.assertAlmostEqual(r['drop_rate'], 0.02)
            self.assertAlmostEqual(r['q_fail'], 1 / 11)
            self.assertEqual((r['p50'], r['p95']), (51.0, 96.0))
            self.assertAlmostEqual(r['monthly'], 600 * 0.06 / 600 + 100 * 0.01)
            prices = {'systems': {'mem0': {'list_price_usd_per_month': None}}}
            md = cost_table.render(rows, prices, 'LoCoMo', 'conversation', 600.0)
            self.assertIn('| mem0 | 0.0600 |', md); self.assertIn('TODO', md); self.assertIn('51.0 / 96.0', md)
            self.assertIn('30 sessions x 20 turns = 600 turns', md)

    def test_price_cell(self):
        p = {'systems': {'a': {'list_price_usd_per_month': 19, 'unit': 'seat', 'url': 'https://x.test/p', 'date': '2026-10-04'}, 'b': {'list_price_usd_per_month': None},
                         'c': {'list_price_usd_per_month': 0, 'unit': 'n/a'}}}
        self.assertEqual(cost_table.price_cell(p, 'a'), '$19/month per seat (https://x.test/p, 2026-10-04)')
        self.assertEqual(cost_table.price_cell(p, 'b'), 'TODO'); self.assertEqual(cost_table.price_cell(p, 'missing'), 'TODO')
        self.assertEqual(cost_table.price_cell(p, 'c'), '$0/month')

    def test_shipped_prices_json_is_todo(self):
        pr = json.load(open(os.path.join(ROOT, 'analysis', 'prices.json')))
        for arm in ('flux_public', 'mem0', 'letta', 'honcho_retrieval'):
            e = pr['systems'][arm]
            self.assertIsNone(e['list_price_usd_per_month']); self.assertIsNone(e['url']); self.assertIsNone(e['date']); self.assertIn('TODO', e['todo'])


class TestLedgerAndEstimate(unittest.TestCase):
    def test_cap_and_bench_tag(self):
        self.assertEqual(ledger.CAP, 55.0)
        with tempfile.TemporaryDirectory() as d:
            old, ledger.LEDGER = ledger.LEDGER, os.path.join(d, 'l.jsonl')
            try:
                os.environ.pop('BENCH', None)
                ledger.add('mem0', 'ingest', 1.0); ledger.add('mem0', 'qa', 2.0, bench='locomo')
                os.environ['BENCH'] = 'locomo'; ledger.add('letta', 'qa', 3.0)
                self.assertEqual([r['bench'] for r in ledger.read()], ['lme', 'locomo', 'locomo'])
                self.assertTrue(ledger.over_cap(50.0)); self.assertFalse(ledger.over_cap(48.0))
            finally:
                ledger.LEDGER = old; os.environ.pop('BENCH', None)

    def test_honcho_rule_after_and_limit(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, 'units.jsonl'), 'w').write(''.join(json.dumps({'llm_usd': 0.2}) + '\n' for _ in range(3)))
            self.assertFalse(ledger.honcho_rule(d)[0])                                           # only 3 seen, the LME rule waits for 10
            self.assertTrue(ledger.honcho_rule(d, ledger.LOCOMO_AFTER, ledger.LOCOMO_LIMIT)[0])  # 0.2 > 0.18 after 3
            self.assertFalse(ledger.honcho_rule(d, 3, 0.25)[0])
        self.assertAlmostEqual(ledger.LOCOMO_LIMIT, 0.18, places=2)

    def test_estimate_fits_cap_and_has_both_benchmarks(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, 'analysis', 'cost_estimate.py')], capture_output=True, text=True, check=True).stdout
        self.assertIn('### LongMemEval-S, n=100', out); self.assertIn('### LoCoMo, 10 conversations, 1,986 questions', out)
        last = [l for l in out.splitlines() if l.startswith('| **Both benchmarks**')][0].split('|')
        lo, hi = float(last[3].strip(' *')), float(last[4].strip(' *'))
        self.assertLess(lo, hi); self.assertLess(hi, 55.0)


if __name__ == '__main__':
    unittest.main()
