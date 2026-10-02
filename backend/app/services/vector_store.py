"""Vector index abstraction (MASTER_README §29).

The application talks to this interface only - FAISS is one optional
implementation, never a hard dependency. If `faiss` + `numpy` are installed
they are used automatically; otherwise the pure-Python index is used.
Both index normalized vectors and rank by cosine similarity (= dot product).
"""

from __future__ import annotations

import logging

logger = logging.getLogger("findback.vector")


class InMemoryVectorIndex:
    """Simple cosine index with dict storage - fine for development scale."""

    def __init__(self) -> None:
        self._store: dict[str, list[float]] = {}

    def add(self, key: str, vector: list[float]) -> None:
        self._store[str(key)] = vector

    def remove(self, key: str) -> None:
        self._store.pop(str(key), None)

    def clear(self) -> None:
        self._store.clear()

    def search(self, vector: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        from app.services.embedding_service import cosine

        scored = [
            (key, cosine(vector, stored))
            for key, stored in self._store.items()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def __len__(self) -> int:
        return len(self._store)


class FaissVectorIndex:
    """FAISS-backed index (used only when faiss + numpy are installed).

    Vectors are mirrored in a small dict so removals can rebuild the flat
    index (acceptable cost at this scale, and IndexFlatIP has no portable
    in-place delete across faiss versions).
    """

    def __init__(self) -> None:
        import faiss  # noqa: F401 - verified by create_index()
        import numpy as np

        self._np = np
        self._faiss = __import__("faiss")
        self._vectors: dict[str, list[float]] = {}
        self._keys: list[str] = []
        self._index = None  # built lazily once the dimension is known

    def _rebuild(self) -> None:
        if not self._vectors:
            self._index = None
            self._keys = []
            return
        self._keys = list(self._vectors.keys())
        rows = self._np.asarray(
            [self._vectors[k] for k in self._keys], dtype="float32"
        )
        self._index = self._faiss.IndexFlatIP(rows.shape[1])
        self._index.add(rows)

    def add(self, key: str, vector: list[float]) -> None:
        key = str(key)
        if key in self._vectors:
            del self._vectors[key]
        self._vectors[key] = list(vector)
        self._rebuild()

    def remove(self, key: str) -> None:
        if self._vectors.pop(str(key), None) is not None:
            self._rebuild()

    def clear(self) -> None:
        self._vectors.clear()
        self._keys = []
        self._index = None

    def search(self, vector: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        if self._index is None or not self._keys:
            return []
        np = self._np
        query = np.asarray([vector], dtype="float32")
        k = min(top_k, len(self._keys))
        scores, indexes = self._index.search(query, k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indexes[0]):
            if idx < 0:
                continue
            results.append((self._keys[int(idx)], float(score)))
        return results

    def __len__(self) -> int:
        return len(self._vectors)


def create_index():
    """Return the best available vector index (FAISS when possible)."""
    try:
        import faiss  # noqa: F401
        import numpy  # noqa: F401

        logger.info("Vector index backend: faiss")
        return FaissVectorIndex()
    except Exception:
        logger.info("Vector index backend: in-memory (faiss not installed)")
        return InMemoryVectorIndex()
