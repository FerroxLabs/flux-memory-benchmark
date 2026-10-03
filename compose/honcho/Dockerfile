# Honcho's own image (built unmodified by fetch-honcho.sh) plus our sidecars in a SEPARATE venv: the local bge-small embedder and the DeepSeek metering proxy.
FROM honcho-pinned:v3.2.2
USER root
RUN python3 -m venv /sidecar && /sidecar/bin/pip install --no-cache-dir fastembed==0.8.1 aiohttp==3.14.3 numpy==2.5.3 httpx==0.28.1
COPY infra/ /sidecar/infra/
COPY compose/honcho/stack.sh /stack.sh
USER app
