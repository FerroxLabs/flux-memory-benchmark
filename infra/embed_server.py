"""OpenAI-compatible /v1/embeddings over BAAI/bge-small-en-v1.5 (fastembed ONNX), 127.0.0.1 only. No query instruction prefix
(Honcho's client cannot send one), same as the other competitor arms. usage: embed_server.py <port>   (cache dir: $FASTEMBED_CACHE)"""
import base64, os, sys, threading
import numpy as np
from aiohttp import web
from fastembed import TextEmbedding

M = TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir=os.environ.get('FASTEMBED_CACHE', '/cache/fastembed'), threads=4)
LOCK = threading.Lock()
N = [0]


async def emb(req):
    b = await req.json(); inp = b.get('input', [])
    texts = [inp] if isinstance(inp, str) else [t if isinstance(t, str) else ' '.join(map(str, t)) for t in inp]
    texts = [t if t.strip() else ' ' for t in texts]
    loop = __import__('asyncio').get_running_loop()
    vecs = await loop.run_in_executor(None, lambda: np.array(list(M.embed(texts)), dtype=np.float32))
    N[0] += len(texts)
    b64 = b.get('encoding_format') == 'base64'
    data = [{'object': 'embedding', 'index': i, 'embedding': base64.b64encode(v.tobytes()).decode() if b64 else v.tolist()} for i, v in enumerate(vecs)]
    n = sum(len(t) // 4 + 1 for t in texts)
    return web.json_response({'object': 'list', 'data': data, 'model': b.get('model', 'bge-small-en-v1.5'), 'usage': {'prompt_tokens': n, 'total_tokens': n}})

app = web.Application(client_max_size=64 * 1024 * 1024)
app.add_routes([web.post('/v1/embeddings', emb)])
web.run_app(app, host='127.0.0.1', port=int(sys.argv[1]), print=None)
