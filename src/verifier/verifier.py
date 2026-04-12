"""Main verification engine for TruthLayer."""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.embeddings.base import EmbeddingProvider
from src.verifier.claim_extractor import ClaimExtractor
from src.verifier.similarity_engine import SimilarityEngine
from src.verifier.confidence_scorer import ConfidenceScorer
from src.verifier.entity_checker import compute_alignment_penalty, ContradictionEvidence
from src.verifier.calibration import calibrate_confidence_pct
from src.utils.text_splitter import chunk_text

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Intra-response consistency engine
# ═══════════════════════════════════════════════════════════════════════════════

def _check_internal_consistency(claims: List[str]) -> Dict[str, Any]:
    """
    Detect logical contradictions *between* claims in the same AI response.

    For every ordered pair (i, j) where i < j, the entity contradiction
    engine is run in both directions:

        direction A: compute_alignment_penalty(claims[i], claims[j])
                     — treats claims[j] as the reference for claims[i]
        direction B: compute_alignment_penalty(claims[j], claims[i])
                     — treats claims[i] as the reference for claims[j]

    A conflict is recorded when either direction produces evidence
    (penalty < 1.0).  The stronger signal (lower penalty) is chosen
    as the authoritative evidence for the conflict record.

    Why both directions?
    The entity checker is intentionally asymmetric: it asks
    "does the claim introduce something not in the source?"
    Running both directions ensures that contradictions surfaced
    by either ordering are captured.

    Complexity:
        O(n²) pairs × O(m) entity checker → for typical responses
        (3-15 claims) this is 3-105 pairs, negligible overhead.
        All claims are already in memory; no additional I/O.

    Zero new dependencies.  Zero additional cost.  Zero latency overhead
    proportional to source-document length.

    Args:
        claims: List of claim strings extracted from the AI response.

    Returns:
        Dict with three keys:
            consistent     : bool  — True iff no conflicts found
            conflict_count : int   — number of conflicting pairs
            conflicts      : list  — each entry is a conflict descriptor:
                {
                    claim_a_index : int    (index into claims list)
                    claim_b_index : int
                    claim_a_text  : str    (first 200 chars)
                    claim_b_text  : str
                    signal        : str    (NUMERICAL_MISMATCH | ...)
                    severity      : str    (CRITICAL | MODERATE | ...)
                    explanation   : str
                    penalty       : float  (0.0-1.0, lower = stronger)
                }
    """
    if len(claims) < 2:
        # Fewer than 2 claims → no pairs to check.
        return {"consistent": True, "conflict_count": 0, "conflicts": []}

    conflicts: List[Dict[str, Any]] = []
    n = len(claims)

    for i in range(n):
        for j in range(i + 1, n):
            claim_i = claims[i]
            claim_j = claims[j]

            # Direction A: claim_i as the assertion; claim_j as the reference.
            penalty_a, evidence_a = compute_alignment_penalty(claim_i, claim_j)

            # Direction B: claim_j as the assertion; claim_i as the reference.
            penalty_b, evidence_b = compute_alignment_penalty(claim_j, claim_i)

            # Pick the strongest signal (lowest penalty).
            if evidence_a is not None and evidence_b is not None:
                chosen_evidence = evidence_a if penalty_a <= penalty_b else evidence_b
                chosen_penalty  = min(penalty_a, penalty_b)
            elif evidence_a is not None:
                chosen_evidence = evidence_a
                chosen_penalty  = penalty_a
            elif evidence_b is not None:
                chosen_evidence = evidence_b
                chosen_penalty  = penalty_b
            else:
                continue  # no contradiction in either direction

            conflicts.append({
                "claim_a_index": i,
                "claim_b_index": j,
                "claim_a_text":  claim_i[:200],
                "claim_b_text":  claim_j[:200],
                "signal":        chosen_evidence.signal,
                "severity":      chosen_evidence.severity,
                "explanation":   chosen_evidence.explanation,
                "penalty":       round(chosen_penalty, 4),
            })

    return {
        "consistent":     len(conflicts) == 0,
        "conflict_count": len(conflicts),
        "conflicts":      conflicts,
    }


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
                    "unsupported": 0,
                },
                # No claims → trivially internally consistent.
                "internal_consistency": {"consistent": True, "conflict_count": 0, "conflicts": []},
                "metadata": {
                    "latency_ms": round((time.time() - start_time) * 1000, 2),
                    "provider": type(self.embedding_provider).__name__,
                    "total_claims": 0,
                    "calibration_model": "platt_scaling_n300",
                },
            }

        # Prepare source documents (chunk if needed)
        source_chunks = []
        for doc in source_documents:
            chunks = chunk_text(doc)
            source_chunks.extend(chunks)

        if not source_chunks:
            # No sources to verify against — still run internal consistency check.
            result = self._create_unverified_result(claims)
            result["metadata"] = {
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "provider": type(self.embedding_provider).__name__,
                "total_claims": len(claims),
                "calibration_model": "platt_scaling_n300",
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
            # Find best matching source (semantic similarity)
            similarity, matched_source = self.similarity_engine.find_best_match(
                claim_emb,
                source_embeddings_list,
                source_chunks
            )

            # Apply entity contradiction check (catches what embeddings miss).
            # Numbers, negations, and superlatives are compared literally.
            # A penalty < 1.0 means a contradiction was detected; evidence
            # carries the structured proof of which signal fired and why.
            alignment, evidence = compute_alignment_penalty(claim, matched_source)
            adjusted_similarity = similarity * alignment

            # Classify using the adjusted score (thresholds unchanged).
            status = self.confidence_scorer.classify_claim(adjusted_similarity)

            # Calibrated confidence: Platt scaling converts the raw score into
            # a true probability — validated against the 300-case benchmark.
            # When we report 95.3%, it means 95.3% of claims at this score
            # are factually correct, not merely a rescaled similarity value.
            confidence = calibrate_confidence_pct(adjusted_similarity)

            verified_claims.append({
                "text": claim,
                "status": status,
                "confidence": confidence,
                "similarity_score": round(adjusted_similarity, 4),
                "matched_source": matched_source[:200] if matched_source else "",
                "contradiction_evidence": evidence.to_dict() if evidence is not None else None,
            })

            # Update summary
            summary[status.lower()] += 1

        total_time = time.time() - start_time

        # Intra-response consistency: check every claim pair for self-contradiction.
        # This runs entirely on the text of extracted claims — no source documents,
        # no embedding calls.  Novel capability: detects self-contradictory AI output
        # that passes all source-document checks.
        internal_consistency = _check_internal_consistency(claims)

        return {
            "claims": verified_claims,
            "summary": summary,
            "internal_consistency": internal_consistency,
            "metadata": {
                "latency_ms": round(total_time * 1000, 2),
                "embedding_ms": round(embed_time * 1000, 2),
                "provider": type(self.embedding_provider).__name__,
                "total_claims": len(claims),
                "source_chunks": len(source_chunks),
                "cache_hits": getattr(self.embedding_provider, 'last_cache_hits', 0),
                "cache_misses": getattr(self.embedding_provider, 'last_cache_misses', 0),
                "calibration_model": "platt_scaling_n300",
            }
        }

    def _create_unverified_result(self, claims: List[str]) -> Dict[str, Any]:
        """Create result when no sources are available.

        Still runs the intra-response consistency check — internal
        contradictions can be caught even when there are no source documents.
        """
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
            },
            "internal_consistency": _check_internal_consistency(claims),
        }
