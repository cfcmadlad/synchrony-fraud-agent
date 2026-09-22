from functools import lru_cache

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache
def get_embedder() -> SentenceTransformer:
    # local_files_only avoids ~15 Hugging Face Hub network calls on every load, but
    # only works once the model is actually cached on this machine. A fresh
    # deployment has no cache yet, so fall back to a real (one-time) download rather
    # than fail startup entirely; the cache then makes every later load on this same
    # instance fast again.
    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    except OSError:
        return SentenceTransformer(EMBEDDING_MODEL_NAME)
