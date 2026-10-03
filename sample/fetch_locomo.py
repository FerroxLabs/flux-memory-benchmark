"""Download LoCoMo (locomo10.json) from the Snap Research repository at a pinned commit and verify its sha256. The data is NEVER committed (data/ is git-ignored).

LoCoMo: Maharana et al., "Evaluating Very Long-Term Conversational Memory of LLM Agents", ACL 2024. Copyright Snap Research, CC BY-NC 4.0
(https://creativecommons.org/licenses/by-nc/4.0/). Non-commercial use only. This repository does not redistribute the data.
usage: python3 sample/fetch_locomo.py [--out data/locomo10.json]"""
import argparse, hashlib, os, sys, urllib.request

REPO = 'snap-research/locomo'
COMMIT = '3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376'
SHA256 = '79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4'
URL = f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/data/locomo10.json'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def verify(data, expected=SHA256):
    got = hashlib.sha256(data).hexdigest()
    if got != expected:
        raise ValueError(f'sha256 mismatch: got {got}, expected {expected}')
    return got


def fetch(out):
    with urllib.request.urlopen(URL, timeout=120) as r:
        data = r.read()
    verify(data)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(data)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'locomo10.json'))
    a = ap.parse_args()
    try:
        print('ok', fetch(a.out), SHA256)
    except ValueError as e:
        sys.exit(str(e))
    print('LoCoMo is (c) Snap Research, CC BY-NC 4.0, non-commercial use. Do not commit or redistribute it.')
