"""Integration tests for Bedrock embedding provider."""

import pytest
import numpy as np
import os

# Skip all Bedrock tests if no AWS credentials are configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("AWS_ACCESS_KEY_ID") and not os.path.exists(
        os.path.expanduser("~/.aws/credentials")
    ),
    reason="AWS credentials not configured — skipping Bedrock integration tests"
)


class TestBedrockEmbeddingProvider:
    """Integration tests for real Bedrock Titan Embeddings."""

    @pytest.fixture
    def provider(self):
        """Create a Bedrock provider instance."""
        from src.embeddings.bedrock_provider import BedrockEmbeddingProvider
        return BedrockEmbeddingProvider()

    def test_embed_single_text(self, provider):
        """Test embedding a single text returns correct shape."""
        text = "Python is a programming language."
        embedding = provider.embed(text)
        assert embedding.shape == (provider.dimension,)
        assert np.linalg.norm(embedding) > 0

    def test_embed_batch(self, provider):
        """Test batch embedding returns correct shape."""
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = provider.embed_batch(texts)
        assert embeddings.shape == (3, provider.dimension)

    def test_similar_texts_high_similarity(self, provider):
        """Test that semantically similar texts get high similarity."""
        from src.verifier.similarity_engine import SimilarityEngine

        engine = SimilarityEngine()

        text1 = "The Eiffel Tower is located in Paris, France."
        text2 = "Paris, France is home to the Eiffel Tower."

        emb1 = provider.embed(text1)
        emb2 = provider.embed(text2)

        similarity = engine.compute_similarity(emb1, emb2)
        assert similarity > 0.7, f"Similar texts should have high similarity, got {similarity}"

    def test_different_texts_low_similarity(self, provider):
        """Test that semantically different texts get low similarity."""
        from src.verifier.similarity_engine import SimilarityEngine

        engine = SimilarityEngine()

        text1 = "The Eiffel Tower is located in Paris, France."
        text2 = "Quantum computing uses qubits for parallel processing."

        emb1 = provider.embed(text1)
        emb2 = provider.embed(text2)

        similarity = engine.compute_similarity(emb1, emb2)
        assert similarity < 0.5, f"Different texts should have low similarity, got {similarity}"

    def test_empty_text_returns_zeros(self, provider):
        """Test that empty text returns zero vector."""
        embedding = provider.embed("")
        assert embedding.shape == (provider.dimension,)
        assert np.allclose(embedding, 0.0)

    def test_end_to_end_verification(self, provider):
        """Test full verification pipeline with Bedrock embeddings."""
        from src.verifier.verifier import TruthLayerVerifier

        verifier = TruthLayerVerifier(embedding_provider=provider)

        ai_response = "The Eiffel Tower, located in Paris, was completed in 1889."
        sources = ["The Eiffel Tower is a wrought-iron lattice tower in Paris, France. It was completed in 1889."]

        result = verifier.verify(ai_response, sources)

        assert "claims" in result
        assert "summary" in result
        assert "metadata" in result
        assert result["metadata"]["provider"] == "BedrockEmbeddingProvider"
        assert len(result["claims"]) > 0

        # With real embeddings, matching text should get high confidence
        for claim in result["claims"]:
            assert claim["confidence"] > 50, (
                f"Claim '{claim['text']}' should have decent confidence with "
                f"matching source, got {claim['confidence']}%"
            )


class TestBedrockAvailability:
    """Tests for Bedrock availability checking."""

    def test_is_bedrock_available(self):
        """Test the availability check function."""
        from src.embeddings.bedrock_provider import is_bedrock_available
        # Should return True if credentials are configured
        result = is_bedrock_available()
        assert isinstance(result, bool)
