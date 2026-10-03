FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 \
 && pip install --no-cache-dir transformers==4.56.2 numpy==2.4.4 usearch==2.26.2 cryptography==48.0.1 httpx==0.28.1 pydantic==2.13.4 prometheus-client==0.20.0
ENV PYTHONUNBUFFERED=1 FLUX_SRC=/flux-src EMB_CACHE=/work/emb HF_HOME=/cache/hf
WORKDIR /repo
