"""Turns text into vectors. The default is a small Hugging Face model (downloaded the first time it is used)."""
import numpy as np

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class SentenceEmbedder:
    def __init__(self, model_name=DEFAULT_MODEL):
        from sentence_transformers import SentenceTransformer     # imported late: it is slow to load
        self.model = SentenceTransformer(model_name)
        self.name = model_name

    def encode(self, texts, batch_size=32):
        texts = list(texts)
        vecs = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                 show_progress_bar=len(texts) > 200)
        return np.asarray(vecs, dtype="float32")
