"""Draw the head-to-head question sample from LongMemEval-S.

Rule (fixed, published): stratify by question_type in proportion to the full 500 (largest-remainder
allocation; remainder ties go to the larger stratum, then alphabetical type name), then inside each stratum
take the question ids with the smallest sha256("<seed>:<question_id>"). That ranking does not depend on the
Python version, the dataset's row order, or any library. Nothing is excluded.

Only ids are written. The dataset text is not copied anywhere.

usage:
  LME_S_PATH=/path/to/longmemeval_s_cleaned.json python3 sample/draw_sample.py            # write the files
  LME_S_PATH=... python3 sample/draw_sample.py --check                                    # redraw and compare
"""
import argparse, hashlib, json, os, sys
from collections import Counter, defaultdict

SEED = 20261003
N = 100
DATASET_SHA256 = 'd6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442'
HERE = os.path.dirname(os.path.abspath(__file__))
IDS = os.path.join(HERE, 'lme_s_ids_n100.txt')
MANIFEST = os.path.join(HERE, 'sample_manifest.json')
PRIOR = os.path.join(HERE, 'prior_dev_subset_2026-09-30.ids')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def allocate(counts, n):
    """Largest-remainder allocation. counts: {type: size}. Returns {type: k} summing to n."""
    total = sum(counts.values())
    exact = {t: n * c / total for t, c in counts.items()}
    alloc = {t: int(v) for t, v in exact.items()}
    left = n - sum(alloc.values())
    order = sorted(counts, key=lambda t: (-(exact[t] - alloc[t]), -counts[t], t))
    for t in order[:left]:
        alloc[t] += 1
    return alloc


def rank_key(seed, qid):
    return hashlib.sha256(f'{seed}:{qid}'.encode()).hexdigest()


def draw(qtypes, n=N, seed=SEED):
    """qtypes: {question_id: question_type}. Returns (sorted ids, allocation)."""
    counts = Counter(qtypes.values())
    alloc = allocate(counts, n)
    by = defaultdict(list)
    for qid, t in qtypes.items():
        by[t].append(qid)
    picked = []
    for t in sorted(by):
        picked += sorted(by[t], key=lambda q: rank_key(seed, q))[:alloc[t]]
    return sorted(picked), alloc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    path = os.environ.get('LME_S_PATH')
    if not path:
        sys.exit('set LME_S_PATH to longmemeval_s_cleaned.json')
    sha = sha256_file(path)
    if sha != DATASET_SHA256:
        sys.exit(f'dataset sha256 mismatch: {sha} != {DATASET_SHA256}')
    data = json.load(open(path))
    qtypes = {q['question_id']: q['question_type'] for q in data}
    assert len(qtypes) == 500, len(qtypes)
    ids, alloc = draw(qtypes)
    if a.check:
        committed = open(IDS).read().split()
        print('MATCH' if committed == ids else 'MISMATCH', len(ids))
        sys.exit(0 if committed == ids else 1)
    prior = set(open(PRIOR).read().split())
    overlap = sorted(set(ids) & prior)
    manifest = {
        'dataset': 'LongMemEval-S (longmemeval_s_cleaned.json)', 'dataset_sha256': DATASET_SHA256,
        'seed': SEED, 'n': N, 'rank_rule': 'sha256("<seed>:<question_id>") ascending inside each type',
        'allocation_rule': 'largest remainder; ties -> larger stratum, then type name',
        'population_by_type': dict(sorted(Counter(qtypes.values()).items())),
        'drawn_by_type': dict(sorted(Counter(qtypes[i] for i in ids).items())),
        'abstention_questions_drawn': sum(i.endswith('_abs') for i in ids),
        'prior_dev_subset': {'file': os.path.basename(PRIOR), 'size': len(prior), 'overlap': len(overlap),
                             'overlap_ids': overlap},
        'ids_file': os.path.basename(IDS),
    }
    open(IDS, 'w').write('\n'.join(ids) + '\n')
    json.dump(manifest, open(MANIFEST, 'w'), indent=1)
    print(json.dumps({k: v for k, v in manifest.items() if k != 'prior_dev_subset'}, indent=1))
    print('overlap with 2026-09-30 dev subset:', len(overlap), 'of', len(prior))


if __name__ == '__main__':
    main()
