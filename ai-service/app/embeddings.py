from __future__ import annotations

import logging
import zlib
from typing import List

import numpy as np

from . import config
from .text_utils import STOPWORDS, stem, tokenize

log = logging.getLogger("inkgrade.embeddings")
DIM = 2048


class HashEmbedder:
    """Dependency-free embedder: stemmed words + character trigrams hashed into a dense vector.
    Tolerant to inflection and OCR typos; does not capture true paraphrase (use SBERT for that)."""

    name = "hash"
    lo, hi = 0.05, 0.55
    concept_threshold = 0.62

    def encode(self, texts: List[str]) -> np.ndarray:
        return np.vstack([self._one(t) for t in texts]) if texts else np.zeros((0, DIM))

    def _one(self, text: str) -> np.ndarray:
        v = np.zeros(DIM, dtype=np.float32)
        for tok in tokenize(text):
            if tok in STOPWORDS:
                continue
            s = stem(tok)
            v[zlib.crc32(("w:" + s).encode()) % DIM] += 2.0
            padded = f"#{s}#"
            for i in range(len(padded) - 2):
                v[zlib.crc32(("c:" + padded[i:i + 3]).encode()) % DIM] += 0.5
        n = np.linalg.norm(v)
        return v / n if n else v


class SbertEmbedder:
    name = "sbert"
    lo, hi = 0.25, 0.80
    concept_threshold = 0.55

    def __init__(self):
        from sentence_transformers import SentenceTransformer  # lazy import

        self.model = SentenceTransformer(config.SBERT_MODEL)

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384))
        return np.asarray(self.model.encode(texts, normalize_embeddings=True))


_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        if config.EMBEDDING_BACKEND in ("auto", "sbert"):
            try:
                _embedder = SbertEmbedder()
            except Exception as exc:  # noqa: BLE001
                if config.EMBEDDING_BACKEND == "sbert":
                    raise
                log.warning("SBERT unavailable (%s); falling back to hash embedder", exc)
        if _embedder is None:
            _embedder = HashEmbedder()
    return _embedder


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if not na or not nb:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
