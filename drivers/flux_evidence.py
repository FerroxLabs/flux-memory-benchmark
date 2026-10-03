"""Flux Memory, evidence arm (facts + raw turns, labelled as such): the public path's turns plus extracted facts, 32 KiB, product aggregation/advice branches.
Needs the facts file from flux_extract_facts.py. usage: FLUX_SRC=<flux checkout at c63e8d14> flux_evidence.py --units work/units_n100.jsonl --facts work/facts_n100.jsonl --out results/flux_evidence"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    import flux_common
    flux_common.main('evidence')
