"""Text embeddings for AI matching (MASTER_README §28).

Backends, tried in order:
  1. sentence-transformers (`all-MiniLM-L6-v2`) - used when the optional
     dependency is installed.
  2. Local deterministic TF-hash fallback - pure Python, always available.

Every failure path degrades to the fallback instead of raising, so item
creation and matching keep working when AI services are unavailable (§68).
Embeddings are cached by content hash and only regenerated when the item's
meaningful fields change (§66).
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter

from app.config import settings

logger = logging.getLogger("findback.embedding")

EMBED_DIM = 384  # same dimensionality as all-MiniLM-L6-v2
_MAX_CACHE = 5000

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_st_model = None
_st_failed = False
_backend_name = "fallback-tfhash"
_text_cache: dict[str, list[float]] = {}


def _get_sentence_transformer_model():
    """Lazy-load sentence-transformers once; returns None when unavailable."""
    global _st_model, _st_failed
    if _st_failed:
        return None
    if _st_model is not None:
        return _st_model
    try:
        from sentence_transformers import SentenceTransformer  # optional (§29)

        _st_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        _backend_name = f"sentence-transformers:{settings.EMBEDDING_MODEL}"
        logger.info("Embedding backend: %s", _backend_name)
    except Exception as exc:  # ImportError, model download failure, torch issues...
        _st_failed = True
        logger.warning(
            "sentence-transformers unavailable (%s: %s) - using local fallback embeddings",
            exc.__class__.__name__,
            exc,
        )
    return _st_model


def backend_name() -> str:
    _get_sentence_transformer_model()
    return _backend_name


def _hash_into(vec: list[float], token: str, weight: float) -> None:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    index = value % len(vec)
    sign = 1.0 if (value >> 62) & 1 else -1.0
    vec[index] += sign * weight


def fallback_embedding(text: str) -> list[float]:
    """Deterministic pure-Python embedding: sublinear TF over hashed tokens,
    bigrams and character trigrams (catches typos/partials)."""
    vec = [0.0] * EMBED_DIM
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return vec

    counts = Counter(tokens)
    for token, count in counts.items():
        _hash_into(vec, token, 1.0 + math.log(count))
        # character trigrams for fuzzy partial matches (e.g. "wal" ~ "wallet")
        padded = f"^{token}$"
        for i in range(len(padded) - 2):
            _hash_into(vec, f"#{padded[i:i + 3]}", 0.3)

    for i in range(len(tokens) - 1):
        _hash_into(vec, f"{tokens[i]}_{tokens[i + 1]}", 0.6)

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def embed_text(text: str) -> list[float]:
    """Embed a piece of text; never raises (falls back on backend failure)."""
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cached = _text_cache.get(key)
    if cached is not None:
        return cached

    vector: list[float] | None = None
    model = _get_sentence_transformer_model()
    if model is not None:
        try:
            raw = model.encode(text)
            vector = [float(x) for x in raw]
            norm = math.sqrt(sum(x * x for x in vector))
            if norm > 0:
                vector = [x / norm for x in vector]
        except Exception:
            logger.exception("Embedding backend failed - using fallback")
            vector = None
    if vector is None:
        vector = fallback_embedding(text)

    if len(_text_cache) >= _MAX_CACHE:
        _text_cache.clear()
    _text_cache[key] = vector
    return vector


def item_text(item) -> str:
    """Searchable representation: name + description + category + location (§28)."""
    parts = [
        getattr(item, "name", "") or "",
        getattr(item, "description", "") or "",
        getattr(item, "category", "") or "",
        getattr(item, "location", "") or "",
    ]
    return " | ".join(p for p in parts if p)


def embed_item(item) -> list[float]:
    return embed_text(item_text(item))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))
