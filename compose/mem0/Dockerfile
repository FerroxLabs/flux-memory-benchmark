FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
RUN pip install --no-cache-dir mem0ai==2.2.1 fastembed==0.8.1 aiohttp==3.14.3 httpx==0.28.1 numpy==2.5.3
ENV PYTHONUNBUFFERED=1 FASTEMBED_CACHE=/cache/fastembed MEM0_TMP=/work/tmp/mem0
WORKDIR /repo
