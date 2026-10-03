FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "letta[postgres,server]==0.16.8" letta-client==1.11.0 fastembed==0.8.1 aiohttp==3.14.3 httpx==0.28.1 numpy==2.5.3
ENV PYTHONUNBUFFERED=1 FASTEMBED_CACHE=/cache/fastembed
WORKDIR /repo
