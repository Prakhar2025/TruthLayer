"""Main verification engine for TruthLayer."""

from typing import List, Dict, Any

from src.verifier.claim_extractor import ClaimExtractor
from src.verifier.similarity_engine import SimilarityEngine
from src.verifier.confidence_scorer import ConfidenceScorer
from src.mocks.embedding_provider import MockEmbeddingProvider
from src.utils.text_splitter import chunk_text


class TruthLayerVerifier:
    """
    Main verification engine that orchestrates claim extraction,
    embedding, similarity computation, and confidence scoring.
    """
    
    def __init__(
        self,
        embedding_provider: MockEmbeddingProvider = None,
        claim_extractor: ClaimExtractor = None,
        similarity_engine: SimilarityEngine = None,
        confidence_scorer: ConfidenceScorer = None
    ):
        """
        Initialize the verifier with optional custom components.
        
        Args:
            embedding_provider: Provider for text embeddings
            claim_extractor: Extractor for claims from AI responses
            similarity_engine: Engine for computing semantic similarity
            confidence_scorer: Scorer for claim classification
        """
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.similarity_engine = similarity_engine or SimilarityEngine()
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
    
    def verify(
        self,
        ai_response: str,
        source_documents: List[str]
    ) -> Dict[str, Any]:
        """
        Verify AI response against source documents.
        
        Args:
            ai_response: The AI-generated text to verify
            source_documents: List of source document texts
            
        Returns:
            Dictionary containing:
                - claims: List of claim verification results
                - summary: Aggregate statistics
        """
        # Extract claims from AI response
        claims = self.claim_extractor.extract_claims(ai_response)
        
        if not claims:
            return {
                "claims": [],
                "summary": {
                    "verified": 0,
                    "uncertain": 0,
                    "unsupported": 0
                }
            }
        
        # Prepare source documents (chunk if needed)
        source_chunks = []
        for doc in source_documents:
            chunks = chunk_text(doc)
            source_chunks.extend(chunks)
        
        if not source_chunks:
            # No sources to verify against
            return self._create_unverified_result(claims)
        
        # Generate embeddings
        all_texts = claims + source_chunks
        embeddings = self.embedding_provider.embed_batch(all_texts)
        
        claim_embeddings = embeddings[:len(claims)]
        source_embeddings = embeddings[len(claims):]
        
        # Convert to list of individual embeddings
        source_embeddings_list = [emb for emb in source_embeddings]
        
        # Verify each claim
        verified_claims = []
        summary = {"verified": 0, "uncertain": 0, "unsupported": 0}
        
        for claim, claim_emb in zip(claims, claim_embeddings):
            # Find best matching source
            similarity, matched_source = self.similarity_engine.find_best_match(
                claim_emb,
                source_embeddings_list,
                source_chunks
            )
            
            # Classify and score
            status = self.confidence_scorer.classify_claim(similarity)
            confidence = self.confidence_scorer.get_confidence_percentage(similarity)
            
            verified_claims.append({
                "text": claim,
                "status": status,
                "confidence": confidence,
                "matched_source": matched_source[:200] if matched_source else ""
            })
            
            # Update summary
            summary[status.lower()] += 1
        
        return {
            "claims": verified_claims,
            "summary": summary
        }
    
    def _create_unverified_result(self, claims: List[str]) -> Dict[str, Any]:
        """Create result when no sources are available."""
        verified_claims = []
        for claim in claims:
            verified_claims.append({
                "text": claim,
                "status": "UNSUPPORTED",
                "confidence": 0.0,
                "matched_source": ""
            })
        
        return {
            "claims": verified_claims,
            "summary": {
                "verified": 0,
                "uncertain": 0,
                "unsupported": len(claims)
            }
        }
