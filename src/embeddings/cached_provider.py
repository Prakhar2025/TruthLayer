"""DynamoDB-backed embedding cache wrapper for TruthLayer.

Wraps any EmbeddingProvider with a cache layer that stores computed
embeddings in DynamoDB. On cache hit, skips the expensive Bedrock API call
and returns the stored vector in ~5ms instead of ~150ms.

Cache key: SHA-256 hash of normalized text → stored as document_id
Cache value: JSON list of floats → stored as embedding_vector
TTL: 7 days (configurable)
"""

import hashlib
import os
import time
import logging
from typing import List, Optional

import numpy as np

from src.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

# Cache TTL: 7 days in seconds
DEFAULT_CACHE_TTL = 7 * 24 * 60 * 60


class CachedEmbeddingProvider(EmbeddingProvider):
    """
    Caching wrapper around any EmbeddingProvider.

    Checks DynamoDB for cached embeddings before calling the inner provider.
    Stores new embeddings after computation for future cache hits.

    Usage:
        inner = BedrockEmbeddingProvider()
        provider = CachedEmbeddingProvider(inner_provider=inner)
        verifier = TruthLayerVerifier(embedding_provider=provider)
    """

    def __init__(
        self,
        inner_provider: EmbeddingProvider,
        table_name: Optional[str] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        """
        Args:
            inner_provider: The real embedding provider (e.g. BedrockEmbeddingProvider)
            table_name: DynamoDB table for cache (default: EMBEDDINGS_TABLE env var)
            cache_ttl: Time-to-live in seconds for cached entries (default: 7 days)
        """
        self._inner = inner_provider
        self._cache_ttl = cache_ttl
        self._table_name = table_name or os.environ.get(
            "EMBEDDINGS_TABLE", "TruthLayerEmbeddings"
        )

        # Per-request counters (reset on each embed_batch call)
        self.last_cache_hits = 0
        self.last_cache_misses = 0

        # Lazy-init DynamoDB table
        self._table = None

    def _get_table(self):
        """Lazy-initialize DynamoDB table (reused across warm invocations)."""
        if self._table is None:
            import boto3
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=os.environ.get("AWS_REGION", "us-east-1"),
            )
            self._table = dynamodb.Table(self._table_name)
        return self._table

    @property
    def dimension(self) -> int:
        """Delegate dimension to inner provider."""
        return self._inner.dimension

    @staticmethod
    def _text_hash(text: str) -> str:
        """Create a deterministic cache key from text content."""
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _cache_get(self, text_hash: str) -> Optional[np.ndarray]:
        """Look up cached embedding in DynamoDB. Returns None on miss."""
        try:
            table = self._get_table()
            response = table.get_item(
                Key={"document_id": text_hash, "chunk_index": 0},
                ProjectionExpression="embedding_vector",
            )
            item = response.get("Item")
            if item and "embedding_vector" in item:
                vector = [float(v) for v in item["embedding_vector"]]
                return np.array(vector, dtype=np.float32)
        except Exception as e:
            # Cache read failure is non-fatal — just skip cache
            logger.warning(f"Cache read failed for {text_hash[:16]}...: {e}")
        return None

    def _cache_put(self, text_hash: str, embedding: np.ndarray) -> None:
        """Store embedding in DynamoDB cache."""
        try:
            from decimal import Decimal

            table = self._get_table()
            # Convert numpy floats to Python Decimal for DynamoDB
            vector = [Decimal(str(round(float(v), 6))) for v in embedding]
            ttl = int(time.time()) + self._cache_ttl

            table.put_item(
                Item={
                    "document_id": text_hash,
                    "chunk_index": 0,
                    "embedding_vector": vector,
                    "cached_at": int(time.time()),
                    "ttl": ttl,
                }
            )
        except Exception as e:
            # Cache write failure is non-fatal — embedding still returned
            logger.warning(f"Cache write failed for {text_hash[:16]}...: {e}")

    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        """L2-normalize a single vector. Matches BedrockEmbeddingProvider behavior."""
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def embed(self, text: str) -> np.ndarray:
        """
        Embed text with cache lookup.

        1. Hash the text → check DynamoDB
        2. Cache HIT → return stored normalized vector (~5ms)
        3. Cache MISS → call inner provider (~150ms), normalize, cache, return

        All cached vectors are stored post-normalization so they are
        ready to use directly without further processing.
        """
        if not text or not text.strip():
            return np.zeros(self._inner.dimension)

        text_hash = self._text_hash(text)

        # Try cache first
        cached = self._cache_get(text_hash)
        if cached is not None:
            self.last_cache_hits += 1
            return cached

        # Cache miss — call the real provider
        self.last_cache_misses += 1
        embedding = self._inner.embed(text)

        # Normalize before caching so cached vectors are ready-to-use
        embedding = self._normalize(embedding)

        # Store normalized vector in cache
        self._cache_put(text_hash, embedding)

        return embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed a batch of texts with per-item cache lookup.

        Each vector returned by embed() is already normalized
        (either from cache or freshly normalized after Bedrock call),
        so no batch-level normalization is needed here.

        Resets cache counters at the start of each batch call
        so callers can read last_cache_hits / last_cache_misses.
        """
        if not texts:
            return np.array([])

        # Reset counters for this batch
        self.last_cache_hits = 0
        self.last_cache_misses = 0

        all_embeddings = []
        for text in texts:
            embedding = self.embed(text)
            all_embeddings.append(embedding)

        result = np.array(all_embeddings, dtype=np.float32)

        logger.info(
            f"Embedding batch: {len(texts)} texts, "
            f"{self.last_cache_hits} cache hits, "
            f"{self.last_cache_misses} cache misses"
        )

        return result
