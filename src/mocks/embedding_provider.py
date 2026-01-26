"""Mock embedding provider using TF-IDF for deterministic embeddings."""

import hashlib
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import EMBEDDING_DIMENSION


class MockEmbeddingProvider:
    """
    Deterministic embedding provider using TF-IDF.
    Same text always produces the same vector.
    """
    
    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        """
        Initialize the mock embedding provider.
        
        Args:
            dimension: Target embedding dimension
        """
        self.dimension = dimension
        self.vectorizer = None
        self._corpus = []
    
    def _fit_vectorizer(self, texts: List[str]) -> None:
        """Fit TF-IDF vectorizer on corpus."""
        if not self.vectorizer:
            self.vectorizer = TfidfVectorizer(
                max_features=self.dimension,
                lowercase=True,
                stop_words='english'
            )
            self.vectorizer.fit(texts)
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of shape (len(texts), dimension)
        """
        if not texts:
            return np.array([])
        
        # Fit vectorizer if needed
        if not self.vectorizer:
            self._fit_vectorizer(texts)
        
        # Generate TF-IDF vectors
        vectors = self.vectorizer.transform(texts).toarray()
        
        # Pad or truncate to target dimension
        if vectors.shape[1] < self.dimension:
            padding = np.zeros((vectors.shape[0], self.dimension - vectors.shape[1]))
            vectors = np.hstack([vectors, padding])
        elif vectors.shape[1] > self.dimension:
            vectors = vectors[:, :self.dimension]
        
        # Normalize vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vectors = vectors / norms
        
        return vectors
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            numpy array of shape (dimension,)
        """
        return self.embed_batch([text])[0]
