"""Confidence scoring and claim classification."""

from typing import Literal

from src.config import VERIFIED_THRESHOLD, UNCERTAIN_THRESHOLD


ClaimStatus = Literal["VERIFIED", "UNCERTAIN", "UNSUPPORTED"]


class ConfidenceScorer:
    """Score and classify claims based on similarity scores."""
    
    def __init__(
        self,
        verified_threshold: float = VERIFIED_THRESHOLD,
        uncertain_threshold: float = UNCERTAIN_THRESHOLD
    ):
        """
        Initialize the confidence scorer.
        
        Args:
            verified_threshold: Minimum score for VERIFIED status (default 0.80)
            uncertain_threshold: Minimum score for UNCERTAIN status (default 0.55)
        """
        self.verified_threshold = verified_threshold
        self.uncertain_threshold = uncertain_threshold
    
    def classify_claim(self, similarity_score: float) -> ClaimStatus:
        """
        Classify a claim based on its similarity score.
        
        Args:
            similarity_score: Similarity score between 0.0 and 1.0
            
        Returns:
            Classification: "VERIFIED", "UNCERTAIN", or "UNSUPPORTED"
        """
        if similarity_score >= self.verified_threshold:
            return "VERIFIED"
        elif similarity_score >= self.uncertain_threshold:
            return "UNCERTAIN"
        else:
            return "UNSUPPORTED"
    
    def get_confidence_percentage(self, similarity_score: float) -> float:
        """
        Convert similarity score to confidence percentage.
        
        Args:
            similarity_score: Similarity score between 0.0 and 1.0
            
        Returns:
            Confidence as percentage (0-100)
        """
        return round(similarity_score * 100, 2)
