"""Honcho dialectic arm, reported separately and labelled as an answering agent (not a retrieval list): workspace-level chat, reasoning_level=low,
its answer text is the single memory item handed to the same reader. Normally run with --reuse-workspaces after honcho_retrieval.py has ingested."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import honcho_base  # noqa: E402

if __name__ == '__main__':
    honcho_base.run('chat')
