"""One FAISS search index per company, saved under rag_store/<TICKER>/."""
import json
import os

import numpy as np

STORE_DIR = os.environ.get("RAG_STORE_DIR", "rag_store")


def _paths(ticker, store=None):
    base = os.path.join(store or STORE_DIR, ticker.upper())
    return base, os.path.join(base, "index.faiss"), os.path.join(base, "chunks.json")


def build_index(ticker, chunks, embedder, store=None, meta=None):
    import faiss                                      # imported here so the backend starts even before faiss-cpu is installed
    base, ipath, cpath = _paths(ticker, store)
    os.makedirs(base, exist_ok=True)
    vecs = embedder.encode([c["text"] for c in chunks])
    index = faiss.IndexFlatIP(vecs.shape[1])          # inner product of unit vectors = cosine similarity
    index.add(vecs)
    faiss.write_index(index, ipath)
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump({"ticker": ticker.upper(), "embedder": getattr(embedder, "name", "unknown"),
                   "meta": meta or {}, "chunks": chunks}, f)
    return len(chunks)


def load_index(ticker, store=None):
    _, ipath, cpath = _paths(ticker, store)
    if not (os.path.exists(ipath) and os.path.exists(cpath)):
        raise FileNotFoundError(
            f"The {ticker.upper()} annual report has not been indexed yet. "
            f"Run: python scripts/build_rag_index.py --only {ticker.upper()}")
    import faiss
    index = faiss.read_index(ipath)
    with open(cpath, encoding="utf-8") as f:
        data = json.load(f)
    return index, data


def search(index, data, query_vec, k=6):
    k = min(k, index.ntotal)
    scores, ids = index.search(np.asarray(query_vec, dtype="float32").reshape(1, -1), k)
    return [dict(data["chunks"][i], score=float(s)) for s, i in zip(scores[0], ids[0]) if i >= 0]


def available(store=None):
    base = store or STORE_DIR
    if not os.path.isdir(base):
        return []
    return sorted(t for t in os.listdir(base) if os.path.exists(os.path.join(base, t, "index.faiss")))


def info(ticker, store=None):
    _, _, cpath = _paths(ticker, store)
    with open(cpath, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta", {})
    return {"ticker": data["ticker"], "chunks": len(data["chunks"]), "pages": meta.get("pages"),
            "embedder": data.get("embedder")}
