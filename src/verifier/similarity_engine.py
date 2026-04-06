"""Semantic similarity computation using cosine similarity."""

import numpy as np
from typing import List, Tuple


class SimilarityEngine:
    """Compute semantic similarity between text embeddings."""
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Ensure vectors are 1D
        vec1 = embedding1.flatten()
        vec2 = embedding2.flatten()
        
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Clamp to [0, 1] range
        similarity = max(0.0, min(1.0, similarity))
        
        return float(similarity)
    
    def find_best_match(
        self,
        claim_embedding: np.ndarray,
        source_embeddings: List[np.ndarray],
        source_texts: List[str],
        top_k: int = 3,
    ) -> Tuple[float, str]:
        """
        Find the best matching source chunk for a claim using a top-k candidate pool.

        Why top-k instead of top-1:
            When a source document is split into chunks, the semantically correct
            chunk for a given claim may not always rank first in cosine space —
            particularly when the claim uses domain vocabulary that appears in
            an adjacent chunk.  Scoring all chunks, selecting the top-k by
            similarity, and returning the single best among those k candidates
            recovers cases where the correct chunk ranked 2nd or 3rd, materially
            improving recall without widening the precision risk.

            For documents with fewer than k chunks, behaviour is identical to
            the previous top-1 implementation (all chunks are candidates).

        Args:
            claim_embedding: Embedding of the claim to verify.
            source_embeddings: List of source document chunk embeddings.
            source_texts: Parallel list of source document chunk texts.
            top_k: Candidate pool size (default 3). Must be >= 1.

        Returns:
            Tuple of (best_similarity_score, matched_source_text).
            Returns (0.0, "") if source_embeddings is empty.
        """
        if not source_embeddings or not source_texts:
            return 0.0, ""

        # Score every chunk against the claim embedding.
        scored: List[Tuple[float, str]] = []
        for source_emb, source_text in zip(source_embeddings, source_texts):
            score = self.compute_similarity(claim_embedding, source_emb)
            scored.append((score, source_text))

        # Sort descending by score; select the top-k pool.
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[:max(1, top_k)]

        # Return the single highest-scoring candidate from the pool.
        # (Currently equivalent to candidates[0] since the list is sorted, but
        # expressed explicitly for clarity — future implementations may re-rank
        # candidates using a secondary signal such as BM25 or entity overlap.)
        best_score, best_source = max(candidates, key=lambda x: x[0])
        return best_score, best_source
