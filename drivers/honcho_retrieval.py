"""Honcho retrieval arm (the primary Honcho arm): peer.context(search_query=question, search_top_k=9, max_conclusions=9) for every peer, <=20 items, 16 KiB cap.
Parameters were fixed before the private run and are not tuned here. Pass --arms ctx,chat to also collect the dialectic arm from the same ingest."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import honcho_base  # noqa: E402

if __name__ == '__main__':
    honcho_base.run('ctx')
