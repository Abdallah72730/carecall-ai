"""Sentence-transformers wrapper. Loads the model lazily and once per process."""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME") or None
    logger.info("Loading sentence-transformer model %s (cache=%s)", MODEL_NAME, cache_dir)
    return SentenceTransformer(MODEL_NAME, cache_folder=cache_dir)


def get_embedding(text: str) -> list[float]:
    vec = get_model().encode(text, normalize_embeddings=True, show_progress_bar=False)
    return vec.tolist()


def batch_encode(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vecs = get_model().encode(
        texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
    )
    return [v.tolist() for v in vecs]
