"""Flux Memory, public API arm (what /v1/memory/recall returns): hybrid + reranker, top-20, 16 KiB, session neighbours. The headline Flux number.
usage: FLUX_SRC=<flux checkout at a3b8a520> flux_public.py --units work/units_n100.jsonl --out results/flux_public [--procs 4 --threads 4]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    import flux_common
    flux_common.main('public')
