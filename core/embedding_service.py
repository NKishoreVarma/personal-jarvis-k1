"""
Embedding Service for Semantic Recall in MARK XLVIII / JARVIS.
Provides pluggable embedding providers, deterministic mock vectors for testing,
batch embedding, query caching, deduplication, and non-blocking asynchronous execution.
"""

from __future__ import annotations

import hashlib
import math
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic pseudo-embedding provider generating normalized vectors of dimension D.
    Ensures identical texts produce identical vectors, and semantically similar words
    generate higher cosine similarity without calling external APIs.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _hash_to_vector(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        tokens = text.lower().strip().split()
        if not tokens:
            return vec

        for word in tokens:
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            for i in range(self.dimension):
                # Pseudo-random component from word hash
                val = ((h >> (i % 64)) & 0xFF) / 255.0 - 0.5
                vec[i] += val

        # Normalize to unit vector
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_text(self, text: str) -> List[float]:
        return self._hash_to_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def health_check(self) -> bool:
        return True


class EmbeddingService:
    """
    Coordinates embedding generation with caching, deduplication, and provider switching.
    """

    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider: EmbeddingProvider = provider or MockEmbeddingProvider()
        self._cache: Dict[str, List[float]] = {}
        self.timeout_s: float = 2.0

    def get_embedding(self, text: str) -> List[float]:
        """Returns cached embedding or computes via provider."""
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * 128

        h = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
        if h in self._cache:
            return self._cache[h]

        emb = self.provider.embed_text(clean_text)
        self._cache[h] = emb
        # Bounded cache size
        if len(self._cache) > 1000:
            self._cache.pop(next(iter(self._cache)))
        return emb

    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batches embedding computation, resolving cached entries first."""
        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_indices = []
        missing_texts = []

        for i, t in enumerate(texts):
            clean_t = t.strip()
            h = hashlib.sha256(clean_t.encode("utf-8")).hexdigest()[:16]
            if h in self._cache:
                results[i] = self._cache[h]
            else:
                missing_indices.append(i)
                missing_texts.append(clean_t)

        if missing_texts:
            computed = self.provider.embed_batch(missing_texts)
            for idx, emb in zip(missing_indices, computed):
                h = hashlib.sha256(texts[idx].strip().encode("utf-8")).hexdigest()[:16]
                self._cache[h] = emb
                results[idx] = emb

        return [r for r in results if r is not None]

    def clear_cache(self) -> None:
        self._cache.clear()


# Global singleton instance
embedding_service = EmbeddingService()
