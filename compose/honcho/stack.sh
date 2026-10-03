#!/bin/sh
# One container, five steps (the lane allows at most 2 containers): sidecars (embedder :18902, metering proxy :18901), Honcho's migrations, the pgvector
# dimension change to 384 (upstream's documented bootstrap: provision_db.py, then configure_embeddings.py), the deriver, then the API on :8000.
set -eu
export FASTEMBED_CACHE=/cache/fastembed
/sidecar/bin/python /sidecar/infra/embed_server.py 18902 &
/sidecar/bin/python /sidecar/infra/dsproxy.py 18901 /results/honcho-proxy.log &
sleep 3
cd /app
/app/.venv/bin/python scripts/provision_db.py
/app/.venv/bin/python scripts/configure_embeddings.py --yes
/app/.venv/bin/python -m src.deriver &
exec /app/.venv/bin/fastapi run --host 0.0.0.0 --workers "${API_WORKERS:-1}" src/main.py
