"""Unit tests for TruthLayer verification system."""

import pytest
import numpy as np

from src.verifier.claim_extractor import ClaimExtractor
from src.verifier.similarity_engine import SimilarityEngine
from src.verifier.confidence_scorer import ConfidenceScorer
from src.verifier.verifier import TruthLayerVerifier
from src.mocks.embedding_provider import MockEmbeddingProvider
from src.utils.text_splitter import split_into_sentences, chunk_text


class TestTextSplitter:
    """Tests for text splitting utilities."""
    
    def test_split_into_sentences_basic(self):
        text = "This is sentence one. This is sentence two! Is this sentence three?"
        sentences = split_into_sentences(text)
        assert len(sentences) == 3
        assert "This is sentence one." in sentences[0]
    
    def test_split_into_sentences_empty(self):
        assert split_into_sentences("") == []
        assert split_into_sentences("   ") == []
    
    def test_chunk_text_small(self):
        text = "Short text"
        chunks = chunk_text(text, max_size=500)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_large(self):
        text = "a" * 1000
        chunks = chunk_text(text, max_size=500, overlap=50)
        assert len(chunks) > 1
        assert all(len(chunk) <= 500 for chunk in chunks)


class TestClaimExtractor:
    """Tests for claim extraction."""
    
    def test_extract_claims_basic(self):
        extractor = ClaimExtractor()
        text = "Python 3.11 was released in 2022. It is 25% faster than Python 3.10."
        claims = extractor.extract_claims(text)
        assert len(claims) >= 1
        assert any("2022" in claim for claim in claims)
    
    def test_extract_claims_filters_questions(self):
        extractor = ClaimExtractor()
        text = "What is Python? It is a programming language."
        claims = extractor.extract_claims(text)
        assert not any(claim.endswith("?") for claim in claims)
    
    def test_extract_claims_empty(self):
        extractor = ClaimExtractor()
        assert extractor.extract_claims("") == []
        assert extractor.extract_claims("   ") == []
    
    def test_extract_claims_removes_markdown(self):
        extractor = ClaimExtractor()
        text = "**Python** is a *programming* language with `syntax` support."
        claims = extractor.extract_claims(text)
        if claims:
            assert "**" not in claims[0]
            assert "*" not in claims[0]


class TestMockEmbeddingProvider:
    """Tests for mock embedding provider."""
    
    def test_embed_single_text(self):
        provider = MockEmbeddingProvider(dimension=128)
        text = "This is a test sentence."
        embedding = provider.embed(text)
        assert embedding.shape == (128,)
        assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-5)
    
    def test_embed_batch(self):
        provider = MockEmbeddingProvider(dimension=128)
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = provider.embed_batch(texts)
        assert embeddings.shape == (3, 128)
        assert all(np.isclose(np.linalg.norm(emb), 1.0, atol=1e-5) for emb in embeddings)
    
    def test_deterministic_embeddings(self):
        provider = MockEmbeddingProvider(dimension=128)
        text = "Deterministic test."
        emb1 = provider.embed(text)
        emb2 = provider.embed(text)
        assert np.allclose(emb1, emb2)
    
    def test_embed_empty(self):
        provider = MockEmbeddingProvider()
        result = provider.embed_batch([])
        assert result.shape == (0,)


class TestSimilarityEngine:
    """Tests for similarity computation."""
    
    def test_compute_similarity_identical(self):
        engine = SimilarityEngine()
        vec = np.array([1.0, 0.0, 0.0])
        similarity = engine.compute_similarity(vec, vec)
        assert np.isclose(similarity, 1.0)
    
    def test_compute_similarity_orthogonal(self):
        engine = SimilarityEngine()
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        similarity = engine.compute_similarity(vec1, vec2)
        assert np.isclose(similarity, 0.0)
    
    def test_compute_similarity_range(self):
        engine = SimilarityEngine()
        vec1 = np.array([1.0, 1.0])
        vec2 = np.array([1.0, 0.0])
        similarity = engine.compute_similarity(vec1, vec2)
        assert 0.0 <= similarity <= 1.0
    
    def test_find_best_match(self):
        engine = SimilarityEngine()
        claim_emb = np.array([1.0, 0.0, 0.0])
        source_embs = [
            np.array([0.0, 1.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0])
        ]
        source_texts = ["Source 1", "Source 2", "Source 3"]
        
        score, text = engine.find_best_match(claim_emb, source_embs, source_texts)
        assert text == "Source 2"
        assert np.isclose(score, 1.0)


class TestConfidenceScorer:
    """Tests for confidence scoring."""
    
    def test_classify_verified(self):
        scorer = ConfidenceScorer()
        assert scorer.classify_claim(0.85) == "VERIFIED"
        assert scorer.classify_claim(0.80) == "VERIFIED"
    
    def test_classify_uncertain(self):
        scorer = ConfidenceScorer()
        assert scorer.classify_claim(0.70) == "UNCERTAIN"
        assert scorer.classify_claim(0.55) == "UNCERTAIN"
    
    def test_classify_unsupported(self):
        scorer = ConfidenceScorer()
        assert scorer.classify_claim(0.50) == "UNSUPPORTED"
        assert scorer.classify_claim(0.20) == "UNSUPPORTED"
    
    def test_get_confidence_percentage(self):
        scorer = ConfidenceScorer()
        assert scorer.get_confidence_percentage(0.85) == 85.0
        assert scorer.get_confidence_percentage(0.5) == 50.0
        assert scorer.get_confidence_percentage(1.0) == 100.0


class TestTruthLayerVerifier:
    """Tests for main verification engine."""
    
    def test_verify_basic(self):
        verifier = TruthLayerVerifier()
        ai_response = "Python 3.11 was released in October 2022."
        sources = ["Python 3.11 was officially released on October 24, 2022."]
        
        result = verifier.verify(ai_response, sources)
        
        assert "claims" in result
        assert "summary" in result
        assert len(result["claims"]) > 0
        assert result["summary"]["verified"] + result["summary"]["uncertain"] + result["summary"]["unsupported"] == len(result["claims"])
    
    def test_verify_empty_response(self):
        verifier = TruthLayerVerifier()
        result = verifier.verify("", ["Some source"])
        
        assert result["claims"] == []
        assert result["summary"]["verified"] == 0
    
    def test_verify_no_sources(self):
        verifier = TruthLayerVerifier()
        ai_response = "Python is a programming language."
        result = verifier.verify(ai_response, [])
        
        assert all(claim["status"] == "UNSUPPORTED" for claim in result["claims"])
    
    def test_verify_claim_structure(self):
        verifier = TruthLayerVerifier()
        ai_response = "Python 3.11 includes performance improvements."
        sources = ["Python 3.11 has significant performance enhancements."]
        
        result = verifier.verify(ai_response, sources)
        
        if result["claims"]:
            claim = result["claims"][0]
            assert "text" in claim
            assert "status" in claim
            assert "confidence" in claim
            assert "matched_source" in claim
            assert claim["status"] in ["VERIFIED", "UNCERTAIN", "UNSUPPORTED"]
            assert 0.0 <= claim["confidence"] <= 100.0
    
    def test_verify_deterministic(self):
        verifier = TruthLayerVerifier()
        ai_response = "Python 3.11 was released in 2022."
        sources = ["Python 3.11 was released on October 24, 2022."]
        
        result1 = verifier.verify(ai_response, sources)
        result2 = verifier.verify(ai_response, sources)
        
        assert len(result1["claims"]) == len(result2["claims"])
        for c1, c2 in zip(result1["claims"], result2["claims"]):
            assert c1["status"] == c2["status"]
            assert c1["confidence"] == c2["confidence"]
