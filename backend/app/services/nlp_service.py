"""
NLP utilities: normalization, keyword extraction, Sentence-BERT embeddings and similarity.

Uses lazy singleton model load to keep startup fast and memory bounded in dev.
"""

from __future__ import annotations

import re
import threading
from functools import lru_cache
from typing import Iterable

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.config import get_settings

_model_lock = threading.Lock()
_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            name = get_settings().sbert_model_name
            _model = SentenceTransformer(name)
    return _model


def normalize_text(text: str, language_hint: str = "en") -> str:
    """Lowercase, collapse whitespace, strip noise characters."""
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s\u0900-\u097F.,%\-]", " ", t)
    return t.strip()


def extract_keywords_keybert(text: str, top_n: int = 12) -> list[str]:
    """
    Extract keyphrases using KeyBERT with the same SBERT backbone.

    Falls back to simple word frequency if KeyBERT fails (short text, etc.).
    """
    norm = normalize_text(text)
    if len(norm) < 20:
        return _fallback_keywords(norm, top_n)
    try:
        from keybert import KeyBERT

        kw_model = KeyBERT(model=_get_model())
        kws = kw_model.extract_keywords(norm, keyphrase_ngram_range=(1, 2), top_n=top_n)
        return [k[0] for k in kws]
    except Exception:
        return _fallback_keywords(norm, top_n)


def _fallback_keywords(norm: str, top_n: int) -> list[str]:
    words = [w for w in re.split(r"\W+", norm) if len(w) > 2]
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in ranked[:top_n]]


def encode_texts(texts: list[str]) -> np.ndarray:
    """Batch encode to normalized embeddings."""
    model = _get_model()
    return np.asarray(model.encode(texts, normalize_embeddings=True))


def semantic_similarity(a: str, b: str) -> float:
    """Cosine similarity in embedding space, in [0, 1] after clipping."""
    if not a.strip() or not b.strip():
        return 0.0
    emb = encode_texts([normalize_text(a), normalize_text(b)])
    sim = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
    return max(0.0, min(1.0, sim))


def keyword_overlap_score(student_keywords: Iterable[str], reference_keywords: Iterable[str]) -> float:
    """Jaccard-like overlap on keyword sets."""
    s = {k.lower().strip() for k in student_keywords if k.strip()}
    r = {k.lower().strip() for k in reference_keywords if k.strip()}
    if not r:
        return 0.5
    inter = len(s & r)
    union = len(s | r) or 1
    return inter / union
