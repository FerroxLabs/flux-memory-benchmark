"""Unit tests on synthetic data only (no dataset text, no network, no keys). Run: python3 -m unittest discover -s tests -v"""
import json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ('analysis', 'sample', 'runner', 'drivers', 'prompts'):
    sys.path.insert(0, os.path.join(ROOT, p))
import analyze, draw_sample, ledger  # noqa: E402

TYPES = ['multi-session', 'temporal-reasoning', 'knowledge-update', 'single-session-user', 'single-session-assistant', 'single-session-preference']


def make_ids(n=100):
    return [f'q{i:03d}' for i in range(n)], {f'q{i:03d}': TYPES[i % len(TYPES)] for i in range(n)}


def write_arm(root, arm, labels, types, units=None, retrieved=None, sha=None, error_qids=()):
    d = os.path.join(root, arm); os.makedirs(os.path.join(d, 'qa'))
    with open(os.path.join(d, 'qa', 'answers.jsonl'), 'w') as f:
        for q, v in labels.items():
            r = {'qid': q, 'type': types[q], 'label': bool(v)}
            if q in error_qids:
                r['error'] = 'boom'
            f.write(json.dumps(r) + '\n')
    json.dump({'prompt_sha256': sha or analyze.prompt_sha()}, open(os.path.join(d, 'qa', 'summary.json'), 'w'))
    if units is not None:
        open(os.path.join(d, 'units.jsonl'), 'w').write(''.join(json.dumps(u) + '\n' for u in units))
    if retrieved is not None:
        open(os.path.join(d, 'retrieved.jsonl'), 'w').write(''.join(json.dumps(r) + '\n' for r in retrieved))


class Stats(unittest.TestCase):
    def test_wilson_known_value(self):
        self.assertEqual(analyze.wilson(50, 100), (0.404, 0.596))
        self.assertEqual(analyze.wilson(0, 0), (0.0, 0.0))

    def test_mcnemar_exact_known_values(self):
        a = {i: 1 for i in range(10)}; b = {i: 0 for i in range(10)}
        x, y, p = analyze.mcnemar_exact(a, b, list(range(10)))
        self.assertEqual((x, y), (10, 0)); self.assertAlmostEqual(p, 2 / 1024)
        x, y, p = analyze.mcnemar_exact({0: 1, 1: 0}, {0: 0, 1: 1}, [0, 1])
        self.assertEqual(p, 1.0)
        self.assertEqual(analyze.mcnemar_exact({0: 1}, {0: 1}, [0])[2], 1.0)

    def test_holm(self):
        adj = analyze.holm({'a': 0.01, 'b': 0.04, 'c': 0.03})
        self.assertAlmostEqual(adj['a'], 0.03); self.assertAlmostEqual(adj['c'], 0.06); self.assertAlmostEqual(adj['b'], 0.06)
        self.assertTrue(all(v <= 1 for v in adj.values()))

    def test_bootstrap_is_deterministic_and_contains_mean(self):
        d = [1] * 10 + [0] * 80 + [-1] * 10
        self.assertEqual(analyze.paired_bootstrap(d, 2000), analyze.paired_bootstrap(d, 2000))
        lo, hi = analyze.paired_bootstrap([1] * 20 + [0] * 80, 2000)
        self.assertLess(lo, 0.2); self.assertGreater(hi, 0.2)


class Tables(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = self.tmp.name
        self.ids, self.types = make_ids()
        self.ids_path = os.path.join(self.root, 'ids.txt'); open(self.ids_path, 'w').write('\n'.join(self.ids))

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_pipeline(self):
        ids, types, root = self.ids, self.types, self.root
        base = {q: 1 if i < 80 else 0 for i, q in enumerate(ids)}               # 80/100
        same = dict(base)                                                          # identical -> tie, diff 0
        worse = {q: 1 if i < 50 else 0 for i, q in enumerate(ids)}               # 50/100, 30 baseline-only
        better = {q: 1 if i < 95 else 0 for i, q in enumerate(ids)}              # 15 arm-only, 0 baseline-only
        part = {q: 1 for q in ids[:60]}                                            # incomplete
        units = [{'unit_id': f'u{i}', 'ingest': {'seconds': 10.0, 'llm_usd': 0.2, 'items_total': 100, 'items_dropped': 3}} for i in range(12)]
        write_arm(root, 'flux_public', base, types, [{'unit_id': 'u', 'ingest': {'seconds': 5.0, 'llm_usd': 0.0, 'items_total': 10, 'items_dropped': 0}}],
                  [{'n_context': 5, 'search_ms': 20.0}, {'n_context': 0, 'search_ms': 40.0}])
        write_arm(root, 'mem0', same, types, units)
        write_arm(root, 'letta', worse, types)
        write_arm(root, 'flux_evidence', better, types)
        write_arm(root, 'honcho_retrieval', part, types, units)
        write_arm(root, 'closed_book', {q: 0 for q in ids}, types, sha='deadbeef')
        res = analyze.analyse(root, self.ids_path)
        a = res['arms']
        self.assertEqual(a['flux_public']['correct'], 80); self.assertEqual(a['flux_public']['wilson95'], analyze.wilson(80, 100))
        self.assertFalse(a['honcho_retrieval']['complete'])
        self.assertNotIn('honcho_retrieval', res['comparisons'])
        c = res['comparisons']
        self.assertEqual(c['mem0']['diff'], 0.0); self.assertEqual(c['mem0']['verdict'], 'tie'); self.assertEqual(c['mem0']['p'], 1.0)
        self.assertEqual((c['letta']['arm_only'], c['letta']['baseline_only']), (0, 30)); self.assertEqual(c['letta']['verdict'], 'worse than baseline')
        self.assertLess(c['letta']['p_holm'], 0.001)
        self.assertGreater(c['flux_evidence']['diff'], 0.1)
        self.assertEqual(c['closed_book']['verdict'], 'worse than baseline')
        for v in c.values():
            self.assertGreaterEqual(v['p_holm'], v['p'])
        flags = ' | '.join(res['flags'])
        self.assertIn('honcho_retrieval: INCOMPLETE (60/100', flags)
        self.assertIn('closed_book: prompt hash', flags)
        self.assertIn('mem0: 3.0% of ingest items dropped', flags)           # 36/1200 = 3% > 2%
        self.assertNotIn('flux_public: 0', flags)
        o = res['ops']
        self.assertEqual(o['mem0']['haystacks'], 12); self.assertEqual(o['mem0']['ingest_usd_mean'], 0.2)
        self.assertEqual(o['flux_public']['empty_retrieval_share'], 0.5); self.assertEqual(o['flux_public']['retrieval_ms_p50'], 40.0)
        md = analyze.tables(res)
        self.assertIn('INCOMPLETE (60/100)', md); self.assertIn('| mem0 | 80/100 | 80.0 |', md)

    def test_honcho_stop_rule_and_chat_ingest_alias(self):
        ids, types, root = self.ids, self.types, self.root
        lab = {q: 1 for q in ids}
        units = [{'unit_id': f'u{i}', 'ingest': {'seconds': 90.0, 'llm_usd': 0.20, 'items_total': 100, 'items_dropped': 0}} for i in range(10)]
        write_arm(root, 'flux_public', lab, types)
        write_arm(root, 'honcho_retrieval', lab, types, units)
        write_arm(root, 'honcho_chat', lab, types)
        res = analyze.analyse(root, self.ids_path)
        self.assertTrue(any('honcho_retrieval' in f and 'first 10' in f for f in res['flags']))
        self.assertEqual(res['ops']['honcho_chat']['ingest_usd_mean'], 0.2)   # read from honcho_retrieval

    def test_error_rows_score_wrong_and_make_arm_incomplete(self):
        ids, types, root = self.ids, self.types, self.root
        write_arm(root, 'flux_public', {q: 1 for q in ids}, types)
        write_arm(root, 'mem0', {q: 1 for q in ids}, types, error_qids=ids[:3])
        res = analyze.analyse(root, self.ids_path)
        self.assertFalse(res['arms']['mem0']['complete']); self.assertEqual(res['arms']['mem0']['errors'], 3)
        self.assertEqual(res['comparisons'], {})

    def test_spend_flag(self):
        ids, types, root = self.ids, self.types, self.root
        write_arm(root, 'flux_public', {q: 1 for q in ids}, types)
        open(os.path.join(root, 'ledger.jsonl'), 'w').write(json.dumps({'arm': 'mem0', 'usd': 56.0}) + '\n')
        res = analyze.analyse(root, self.ids_path)
        self.assertEqual(res['spend']['total'], 56.0); self.assertTrue(any('over the $55 cap' in f for f in res['flags']))


class Sample(unittest.TestCase):
    def test_allocation_matches_published_counts(self):
        a = draw_sample.allocate({'multi-session': 133, 'temporal-reasoning': 133, 'knowledge-update': 78, 'single-session-user': 70,
                                  'single-session-assistant': 56, 'single-session-preference': 30}, 100)
        self.assertEqual(a, {'multi-session': 27, 'temporal-reasoning': 27, 'knowledge-update': 15, 'single-session-user': 14,
                             'single-session-assistant': 11, 'single-session-preference': 6})
        self.assertEqual(sum(a.values()), 100)

    def test_draw_is_deterministic_stratified_and_order_independent(self):
        ids, types = make_ids(500)
        d1, al = draw_sample.draw(types, 100, 7)
        d2, _ = draw_sample.draw(dict(reversed(list(types.items()))), 100, 7)
        d3, _ = draw_sample.draw(types, 100, 8)
        self.assertEqual(d1, d2); self.assertNotEqual(d1, d3); self.assertEqual(len(set(d1)), 100)
        for t, k in al.items():
            self.assertEqual(sum(1 for q in d1 if types[q] == t), k)

    def test_committed_ids_match_manifest(self):
        ids = open(os.path.join(ROOT, 'sample', 'lme_s_ids_n100.txt')).read().split()
        m = json.load(open(os.path.join(ROOT, 'sample', 'sample_manifest.json')))
        self.assertEqual(len(ids), 100); self.assertEqual(len(set(ids)), 100); self.assertEqual(sum(m['drawn_by_type'].values()), 100)
        prior = set(open(os.path.join(ROOT, 'sample', 'prior_dev_subset_2026-09-30.ids')).read().split())
        self.assertEqual(len(set(ids) & prior), m['prior_dev_subset']['overlap'])


class Runner(unittest.TestCase):
    def test_qa_with_stubbed_models(self):
        import qa, llm
        tmp = tempfile.TemporaryDirectory(); ledger.LEDGER = os.path.join(tmp.name, 'ledger.jsonl')
        rows = [{'arm': 'x', 'qid': 'a', 'type': 'multi-session', 'question': 'Q?', 'question_date': '2023/05/01 (Mon) 10:00', 'answer': 'blue',
                 'abstention': False, 'context': [{'session_date': '2023/04/01 (Sat) 09:00', 'role': 'user', 'content': 'I like blue'}]},
                {'arm': 'x', 'qid': 'b', 'type': 'single-session-preference', 'question': 'Q2?', 'question_date': '2023/05/01 (Mon) 10:00', 'answer': 'rubric',
                 'abstention': False, 'context': [{'session_date': '2023/04/01 (Sat) 09:00', 'role': 'fact', 'content': 'likes tea'}]}]
        inp = os.path.join(tmp.name, 'r.jsonl'); open(inp, 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
        seen = []
        llm.reader = lambda prompt, mt=6000: (seen.append(prompt), {'content': 'blue', 'cost': 0.001, 'usage': {'completion_tokens': 3}})[1]
        llm.judge = lambda prompt, preference=False: {'content': 'yes' if not preference else 'no', 'cost': 0.0, 'usage': {}, 'model': 'stub-pref' if preference else 'stub'}
        sys.argv = ['qa', '--inputs', inp, '--arm', 'x', '--out', os.path.join(tmp.name, 'qa')]
        qa.main()
        ans = {json.loads(l)['qid']: json.loads(l) for l in open(os.path.join(tmp.name, 'qa', 'answers.jsonl'))}
        self.assertTrue(ans['a']['label']); self.assertEqual(ans['a']['judge_kind'], 'standard')
        self.assertFalse(ans['b']['label']); self.assertEqual(ans['b']['judge_kind'], 'preference'); self.assertEqual(ans['b']['judge_model'], 'stub-pref')
        self.assertIn('Session Facts:', [p for p in seen if 'likes tea' in p][0])   # facts switch to the merge template
        self.assertEqual(json.load(open(os.path.join(tmp.name, 'qa', 'summary.json')))['prompt_sha256'], analyze.prompt_sha())
        self.assertEqual(len([json.loads(l) for l in open(ledger.LEDGER)]), 1)
        tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
