"""
Tests for TruthLayer LangChain integration.

These tests use a MockTruthLayerClient to avoid real API calls,
testing all parser and callback behavior in isolation.
"""

import pytest
import sys
import os
from typing import List
from unittest.mock import MagicMock, patch

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.langchain.truthlayer_langchain import (
    TruthLayerOutputParser,
    TruthLayerCallbackHandler,
    VerifiedOutput,
    HallucinationDetectedError,
)
from sdk.python.truthlayer import Claim, VerificationResult


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_claim(status: str, confidence: float = 0.9, text: str = "Test claim") -> Claim:
    return Claim(
        text=text,
        status=status,
        confidence=confidence,
        similarity_score=confidence,
        matched_source="Source text.",
    )


def make_result(claims: List[Claim], latency_ms: float = 50.0) -> VerificationResult:
    summary = {
        "verified": sum(1 for c in claims if c.status == "VERIFIED"),
        "uncertain": sum(1 for c in claims if c.status == "UNCERTAIN"),
        "unsupported": sum(1 for c in claims if c.status == "UNSUPPORTED"),
    }
    return VerificationResult(
        claims=claims,
        summary=summary,
        metadata={"latency_ms": latency_ms, "cache_hits": 0, "cache_misses": len(claims)},
        raw={},
    )


# ─── TruthLayerOutputParser Tests ────────────────────────────────────────────

class TestTruthLayerOutputParser:

    def _make_parser(self, min_trust_score=70.0, fail_open=False):
        """Create a parser with a mocked TruthLayer client."""
        with patch("integrations.langchain.truthlayer_langchain.TruthLayer"):
            parser = TruthLayerOutputParser(
                api_key="tl_test_key",
                api_url="https://test.example.com/prod",
                source_documents=["Test source document."],
                min_trust_score=min_trust_score,
                fail_open=fail_open,
            )
        return parser

    def test_parse_all_verified_returns_verified_output(self):
        """All VERIFIED claims → returns VerifiedOutput, no exception."""
        parser = self._make_parser()
        claims = [make_claim("VERIFIED", 0.9), make_claim("VERIFIED", 0.85)]
        parser._client.verify = MagicMock(return_value=make_result(claims))

        result = parser.parse("Test response text.")

        assert isinstance(result, VerifiedOutput)
        assert result.is_safe is True
        assert result.trust_score > 70.0
        assert result.text == "Test response text."

    def test_parse_unsupported_claims_raises_hallucination_error(self):
        """UNSUPPORTED claims → HallucinationDetectedError raised."""
        parser = self._make_parser(min_trust_score=70.0)
        claims = [
            make_claim("VERIFIED", 0.9),
            make_claim("UNSUPPORTED", 0.1, "This claim is not in the source."),
        ]
        parser._client.verify = MagicMock(return_value=make_result(claims))

        with pytest.raises(HallucinationDetectedError) as exc_info:
            parser.parse("Some response with a hallucinated claim.")

        err = exc_info.value
        assert err.output.is_safe is False
        assert len(err.output.unsupported_claims) == 1
        assert "trust score" in str(err).lower()

    def test_parse_trust_score_calculation(self):
        """Trust score = sum(confidence of VERIFIED) / total_claims * 100."""
        parser = self._make_parser(min_trust_score=0.0)  # never raise
        claims = [
            make_claim("VERIFIED", 0.8),
            make_claim("VERIFIED", 0.9),
            make_claim("UNSUPPORTED", 0.1),
        ]
        parser._client.verify = MagicMock(return_value=make_result(claims))

        result = parser.parse("Test.")

        # (0.8 + 0.9) / 3 * 100 = 56.67
        assert abs(result.trust_score - 56.67) < 0.01

    def test_parse_no_claims_returns_100_trust(self):
        """Empty claims list → 100% trust score."""
        parser = self._make_parser()
        parser._client.verify = MagicMock(return_value=make_result([]))

        result = parser.parse("Response with no extractable claims.")
        assert result.trust_score == 100.0
        assert result.is_safe is True

    def test_fail_open_returns_passthrough_on_api_error(self):
        """fail_open=True → API errors return safe VerifiedOutput instead of raising."""
        from sdk.python.truthlayer import TruthLayerError
        parser = self._make_parser(fail_open=True)
        parser._client.verify = MagicMock(side_effect=TruthLayerError("API down"))

        result = parser.parse("Test response.")
        assert result.is_safe is True
        assert result.trust_score == 0.0

    def test_fail_closed_raises_on_api_error(self):
        """fail_open=False (default) → API errors propagate."""
        from sdk.python.truthlayer import TruthLayerError
        parser = self._make_parser(fail_open=False)
        parser._client.verify = MagicMock(side_effect=TruthLayerError("API down"))

        with pytest.raises(TruthLayerError):
            parser.parse("Test response.")

    def test_get_format_instructions_returns_string(self):
        """get_format_instructions() returns a non-empty string."""
        parser = self._make_parser()
        instructions = parser.get_format_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 10

    def test_type_property(self):
        """_type returns 'truthlayer'."""
        parser = self._make_parser()
        assert parser._type == "truthlayer"

    def test_missing_source_raises_value_error(self):
        """No source_documents or document_ids → ValueError at init."""
        with patch("integrations.langchain.truthlayer_langchain.TruthLayer"):
            with pytest.raises(ValueError, match="source_documents"):
                TruthLayerOutputParser(
                    api_key="tl_test",
                    api_url="https://test.example.com/prod",
                )


# ─── VerifiedOutput Tests ─────────────────────────────────────────────────────

class TestVerifiedOutput:

    def _make_output(self, statuses: List[str]) -> VerifiedOutput:
        claims = [make_claim(s) for s in statuses]
        result = make_result(claims)
        return VerifiedOutput(
            text="Test",
            result=result,
            trust_score=80.0,
            is_safe=True,
            min_trust_score=70.0,
        )

    def test_verified_claims_property(self):
        output = self._make_output(["VERIFIED", "VERIFIED", "UNSUPPORTED"])
        assert len(output.verified_claims) == 2

    def test_unsupported_claims_property(self):
        output = self._make_output(["VERIFIED", "UNSUPPORTED", "UNSUPPORTED"])
        assert len(output.unsupported_claims) == 2

    def test_uncertain_claims_property(self):
        output = self._make_output(["VERIFIED", "UNCERTAIN"])
        assert len(output.uncertain_claims) == 1

    def test_repr_contains_key_info(self):
        output = self._make_output(["VERIFIED"])
        r = repr(output)
        assert "trust=" in r
        assert "safe=" in r
        assert "claims=" in r


# ─── TruthLayerCallbackHandler Tests ─────────────────────────────────────────

class TestTruthLayerCallbackHandler:

    def _make_handler(self, on_hallucination=None):
        with patch("integrations.langchain.truthlayer_langchain.TruthLayer"):
            handler = TruthLayerCallbackHandler(
                api_key="tl_test_key",
                api_url="https://test.example.com/prod",
                source_documents=["Test source."],
                on_hallucination=on_hallucination,
            )
        return handler

    def _make_llm_result(self, text: str):
        """Create a minimal LLMResult-like object."""
        generation = MagicMock()
        generation.text = text
        return MagicMock(generations=[[generation]])

    def test_metrics_accumulate_across_calls(self):
        handler = self._make_handler()
        claims = [make_claim("VERIFIED", 0.9)]
        handler._client.verify = MagicMock(return_value=make_result(claims, latency_ms=80.0))

        handler.on_llm_end(self._make_llm_result("Response 1."))
        handler.on_llm_end(self._make_llm_result("Response 2."))

        assert handler.total_calls == 2
        assert handler.avg_latency_ms == 80.0

    def test_hallucination_count_increments(self):
        handler = self._make_handler()
        claims_clean = [make_claim("VERIFIED", 0.9)]
        claims_bad = [make_claim("UNSUPPORTED", 0.1)]

        handler._client.verify = MagicMock(return_value=make_result(claims_clean))
        handler.on_llm_end(self._make_llm_result("Clean response."))

        handler._client.verify = MagicMock(return_value=make_result(claims_bad))
        handler.on_llm_end(self._make_llm_result("Hallucinated response."))

        assert handler.hallucination_count == 1
        assert handler.hallucination_rate == 50.0

    def test_on_hallucination_callback_called(self):
        callback_mock = MagicMock()
        handler = self._make_handler(on_hallucination=callback_mock)
        claims = [make_claim("UNSUPPORTED", 0.1)]
        handler._client.verify = MagicMock(return_value=make_result(claims))

        handler.on_llm_end(self._make_llm_result("Bad response."))

        callback_mock.assert_called_once()

    def test_summary_returns_dict(self):
        handler = self._make_handler()
        s = handler.summary()
        assert "total_calls" in s
        assert "hallucination_rate_pct" in s
        assert "avg_latency_ms" in s

    def test_api_error_does_not_raise(self):
        """Callback errors must be silent — not crash the LLM call."""
        from sdk.python.truthlayer import TruthLayerError
        handler = self._make_handler()
        handler._client.verify = MagicMock(side_effect=TruthLayerError("API down"))

        # Should NOT raise
        handler.on_llm_end(self._make_llm_result("Some response."))
        assert handler.total_calls == 0  # errored before increment

    def test_hallucination_rate_zero_when_no_calls(self):
        handler = self._make_handler()
        assert handler.hallucination_rate == 0.0
        assert handler.avg_latency_ms == 0.0
