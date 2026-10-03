#!/bin/sh
# One container, four processes (the lane allows at most 2 containers): embedder :18902, metering proxy :18901, Honcho API :8000 (runs migrations first), deriver.
set -eu
export FASTEMBED_CACHE=/cache/fastembed
/sidecar/bin/python /sidecar/infra/embed_server.py 18902 &
/sidecar/bin/python /sidecar/infra/dsproxy.py 18901 /results/honcho-proxy.log &
sleep 3
cd /app
/app/.venv/bin/python -m src.deriver &
exec sh docker/entrypoint.sh
