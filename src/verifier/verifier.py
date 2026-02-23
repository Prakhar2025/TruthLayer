"""Main verification engine for TruthLayer."""

import time
import logging
from typing import List, Dict, Any, Optional

from src.embeddings.base import EmbeddingProvider
from src.verifier.claim_extractor import ClaimExtractor
from src.verifier.similarity_engine import SimilarityEngine
from src.verifier.confidence_scorer import ConfidenceScorer
from src.utils.text_splitter import chunk_text

logger = logging.getLogger(__name__)


def get_default_provider() -> EmbeddingProvider:
    """
    Get the best available embedding provider.
    Uses Bedrock if AWS credentials are available, otherwise falls back to Mock.
    """
    try:
        from src.embeddings.bedrock_provider import BedrockEmbeddingProvider
        provider = BedrockEmbeddingProvider()
        logger.info("Using BedrockEmbeddingProvider (production)")
        return provider
    except Exception as e:
        logger.warning(f"Bedrock unavailable ({e}), falling back to MockEmbeddingProvider")
        from src.mocks.embedding_provider import MockEmbeddingProvider
        return MockEmbeddingProvider()


class TruthLayerVerifier:
    """
    Main verification engine that orchestrates claim extraction,
    embedding, similarity computation, and confidence scoring.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        claim_extractor: Optional[ClaimExtractor] = None,
        similarity_engine: Optional[SimilarityEngine] = None,
        confidence_scorer: Optional[ConfidenceScorer] = None,
        use_mock: bool = False
    ):
        """
        Initialize the verifier with optional custom components.

        Args:
            embedding_provider: Provider for text embeddings (auto-detected if None)
            claim_extractor: Extractor for claims from AI responses
            similarity_engine: Engine for computing semantic similarity
            confidence_scorer: Scorer for claim classification
            use_mock: Force use of mock embeddings (for testing/local dev)
        """
        if embedding_provider:
            self.embedding_provider = embedding_provider
        elif use_mock:
            from src.mocks.embedding_provider import MockEmbeddingProvider
            self.embedding_provider = MockEmbeddingProvider()
        else:
            self.embedding_provider = get_default_provider()

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
                - metadata: Timing and provider info
        """
        start_time = time.time()

        # Extract claims from AI response
        claims = self.claim_extractor.extract_claims(ai_response)

        if not claims:
            return {
                "claims": [],
                "summary": {
                    "verified": 0,
                    "uncertain": 0,
                    "unsupported": 0
                },
                "metadata": {
                    "latency_ms": round((time.time() - start_time) * 1000, 2),
                    "provider": type(self.embedding_provider).__name__,
                    "total_claims": 0
                }
            }

        # Prepare source documents (chunk if needed)
        source_chunks = []
        for doc in source_documents:
            chunks = chunk_text(doc)
            source_chunks.extend(chunks)

        if not source_chunks:
            # No sources to verify against
            result = self._create_unverified_result(claims)
            result["metadata"] = {
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "provider": type(self.embedding_provider).__name__,
                "total_claims": len(claims)
            }
            return result

        # Generate embeddings
        embed_start = time.time()
        all_texts = claims + source_chunks
        embeddings = self.embedding_provider.embed_batch(all_texts)
        embed_time = time.time() - embed_start

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
                "similarity_score": round(similarity, 4),
                "matched_source": matched_source[:200] if matched_source else ""
            })

            # Update summary
            summary[status.lower()] += 1

        total_time = time.time() - start_time

        return {
            "claims": verified_claims,
            "summary": summary,
            "metadata": {
                "latency_ms": round(total_time * 1000, 2),
                "embedding_ms": round(embed_time * 1000, 2),
                "provider": type(self.embedding_provider).__name__,
                "total_claims": len(claims),
                "source_chunks": len(source_chunks)
            }
        }

    def _create_unverified_result(self, claims: List[str]) -> Dict[str, Any]:
        """Create result when no sources are available."""
        verified_claims = []
        for claim in claims:
            verified_claims.append({
                "text": claim,
                "status": "UNSUPPORTED",
                "confidence": 0.0,
                "similarity_score": 0.0,
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
