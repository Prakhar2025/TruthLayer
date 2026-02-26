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
        source_texts: List[str]
    ) -> Tuple[float, str]:
        """
        Find the best matching source for a claim.
        
        Args:
            claim_embedding: Embedding of the claim to verify
            source_embeddings: List of source document embeddings
            source_texts: List of source document texts (parallel to embeddings)
            
        Returns:
            Tuple of (best_similarity_score, matched_source_text)
        """
        if len(source_embeddings) == 0 or len(source_texts) == 0:
            return 0.0, ""
        
        best_score = 0.0
        best_source = ""
        
        for source_emb, source_text in zip(source_embeddings, source_texts):
            score = self.compute_similarity(claim_embedding, source_emb)
            if score > best_score:
                best_score = score
                best_source = source_text
        
        return best_score, best_source
