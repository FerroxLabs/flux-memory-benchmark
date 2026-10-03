"""retrieved.jsonl holds retrieved haystack text (dataset text), so it is never committed. This writes retrieved_meta.jsonl next to it
(qid, arm, n_retrieved, n_context, search_ms only), which is what the analysis reads and what is committed.
usage: python3 runner/strip_retrieved.py results/<arm>/retrieved.jsonl"""
import json, os, sys

for path in sys.argv[1:]:
    out = os.path.join(os.path.dirname(path), 'retrieved_meta.jsonl')
    with open(path) as f, open(out, 'w') as g:
        for line in f:
            r = json.loads(line)
            g.write(json.dumps({k: r.get(k) for k in ('qid', 'arm', 'n_retrieved', 'n_context', 'search_ms')}) + '\n')
    print('wrote', out)
