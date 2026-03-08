"""
TruthLayer LangChain Integration

Provides LangChain-compatible output parsers and callbacks that automatically
verify AI responses against source documents using the TruthLayer API.

Components:
    TruthLayerOutputParser   — Verifies LLM output inline, raises on hallucinations
    TruthLayerCallbackHandler — Passive listener, logs verification without blocking
    VerifiedOutput           — Structured result dataclass returned by the parser

Usage (Output Parser — blocks hallucinations):
    from integrations.langchain.truthlayer_langchain import TruthLayerOutputParser

    parser = TruthLayerOutputParser(
        api_key="tl_xxx",
        api_url="https://your-api.execute-api.us-east-1.amazonaws.com/prod",
        source_documents=["Your company policy text here..."],
        min_trust_score=75.0,
    )
    chain = prompt | llm | parser
    result = chain.invoke({"question": "What is the return policy?"})
    print(result.trust_score)    # 91.6
    print(result.is_safe)        # True

Usage (Callback Handler — passive monitoring):
    from integrations.langchain.truthlayer_langchain import TruthLayerCallbackHandler

    handler = TruthLayerCallbackHandler(
        api_key="tl_xxx",
        api_url="https://...",
        source_documents=["Policy text..."],
    )
    llm = ChatOpenAI(callbacks=[handler])
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Lazy LangChain imports (not a hard dependency) ──────────────────────────
# We don't want to force users to install langchain just to import this module.
# The parser will fail only when instantiated if langchain is missing.
try:
    from langchain_core.output_parsers import BaseOutputParser
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False
    # Provide stub base classes so the module can still be imported
    class BaseOutputParser:  # type: ignore
        pass
    class BaseCallbackHandler:  # type: ignore
        pass
    class LLMResult:  # type: ignore
        pass

# Add repo root so we can import the SDK without installation
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from sdk.python.truthlayer import TruthLayer, TruthLayerError, VerificationResult


# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class VerifiedOutput:
    """
    The output of TruthLayerOutputParser.

    Contains the original LLM text plus full verification results.

    Attributes:
        text:        The raw LLM response text
        result:      Full VerificationResult from TruthLayer
        trust_score: 0-100 score based on verified claim confidence
        is_safe:     True if trust_score >= min_trust_score threshold
    """
    text: str
    result: VerificationResult
    trust_score: float
    is_safe: bool
    min_trust_score: float

    @property
    def verified_claims(self) -> List:
        if self.result is None:
            return []
        return [c for c in self.result.claims if c.is_verified]

    @property
    def unsupported_claims(self) -> List:
        if self.result is None:
            return []
        return [c for c in self.result.claims if c.is_unsupported]

    @property
    def uncertain_claims(self) -> List:
        if self.result is None:
            return []
        return [c for c in self.result.claims if c.is_uncertain]

    def __repr__(self) -> str:
        claims_count = len(self.result.claims) if self.result else 0
        return (
            f"VerifiedOutput(trust={self.trust_score:.1f}%, safe={self.is_safe}, "
            f"claims={claims_count}, "
            f"V={len(self.verified_claims)} U={len(self.uncertain_claims)} "
            f"X={len(self.unsupported_claims)})"
        )


# ─── Exceptions ───────────────────────────────────────────────────────────────

class HallucinationDetectedError(Exception):
    """
    Raised by TruthLayerOutputParser when trust_score < min_trust_score.

    Attributes:
        output:  The VerifiedOutput with full claim details
        message: Human-readable explanation
    """
    def __init__(self, output: VerifiedOutput):
        self.output = output
        unsupported = output.unsupported_claims
        detail = f"{len(unsupported)} unsupported claim(s): " + "; ".join(
            f'"{c.text[:60]}..."' for c in unsupported[:3]
        )
        super().__init__(
            f"TruthLayer blocked response — trust score {output.trust_score:.1f}% "
            f"below threshold {output.min_trust_score:.1f}%. {detail}"
        )


# ─── Output Parser ────────────────────────────────────────────────────────────

class TruthLayerOutputParser(BaseOutputParser):
    """
    LangChain output parser that verifies LLM responses via TruthLayer.

    Acts as a drop-in parser in any LangChain chain. After the LLM generates
    text, this parser sends it to TruthLayer for claim-level verification
    against your source documents.

    Behavior:
        - If trust_score >= min_trust_score: returns VerifiedOutput
        - If trust_score < min_trust_score: raises HallucinationDetectedError
        - If TruthLayer API is unreachable: behavior controlled by fail_open

    Example:
        parser = TruthLayerOutputParser(
            api_key="tl_xxx",
            api_url="https://your-api.../prod",
            source_documents=["Company return policy: ..."],
            min_trust_score=75.0,
        )
        chain = prompt | llm | parser
        try:
            result = chain.invoke({"question": "What is the refund policy?"})
            send_to_customer(result.text)
        except HallucinationDetectedError as e:
            route_to_human_review(e.output)
    """

    def __init__(
        self,
        api_key: str,
        source_documents: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        api_url: str = "",
        min_trust_score: float = 70.0,
        fail_open: bool = False,
        timeout: int = 30,
    ):
        """
        Args:
            api_key:          TruthLayer API key (tl_xxx format)
            source_documents: List of source texts to verify against
            document_ids:     IDs of pre-uploaded documents (alternative to texts)
            api_url:          TruthLayer API base URL
            min_trust_score:  Block response if trust score below this (0-100)
            fail_open:        If True, verification errors pass through (default: False)
            timeout:          HTTP timeout in seconds
        """
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-core is required. Install it with: pip install langchain-core"
            )
        if not source_documents and not document_ids:
            raise ValueError(
                "Provide either source_documents (text) or document_ids (uploaded doc IDs)"
            )

        self._client = TruthLayer(
            api_key=api_key,
            api_url=api_url or os.environ.get("TRUTHLAYER_API_URL", ""),
            timeout=timeout,
        )
        self._source_documents = source_documents
        self._document_ids = document_ids
        self._min_trust_score = min_trust_score
        self._fail_open = fail_open

    @property
    def _type(self) -> str:
        return "truthlayer"

    def get_format_instructions(self) -> str:
        return (
            "Respond with accurate, factual information grounded in the provided "
            "source documents. Every claim you make will be automatically verified "
            "against the source material."
        )

    def parse(self, text: str) -> VerifiedOutput:
        """
        Verify LLM output text against source documents.

        Args:
            text: The raw LLM response to verify

        Returns:
            VerifiedOutput with trust score and claim breakdown

        Raises:
            HallucinationDetectedError: If trust_score < min_trust_score
        """
        try:
            result = self._client.verify(
                ai_response=text,
                source_documents=self._source_documents,
                document_ids=self._document_ids,
            )

            # Compute trust score: avg confidence of verified claims / total claims
            claims = result.claims
            if not claims:
                trust_score = 100.0
            else:
                verified_confidence_sum = sum(
                    c.confidence for c in claims if c.is_verified
                )
                trust_score = round(
                    (verified_confidence_sum / len(claims)) * 100, 2
                )

            is_safe = trust_score >= self._min_trust_score

            output = VerifiedOutput(
                text=text,
                result=result,
                trust_score=trust_score,
                is_safe=is_safe,
                min_trust_score=self._min_trust_score,
            )

            logger.info(
                f"TruthLayer verification: trust={trust_score:.1f}% "
                f"V={result.verified_count} U={result.uncertain_count} "
                f"X={result.unsupported_count} | {result.latency_ms:.0f}ms"
            )

            if not is_safe:
                raise HallucinationDetectedError(output)

            return output

        except HallucinationDetectedError:
            raise
        except TruthLayerError as e:
            if self._fail_open:
                logger.warning(f"TruthLayer verification failed (fail_open=True): {e}")
                # Return a pass-through result when fail_open
                return VerifiedOutput(
                    text=text,
                    result=None,   # type: ignore
                    trust_score=0.0,
                    is_safe=True,  # open = let through
                    min_trust_score=self._min_trust_score,
                )
            raise TruthLayerError(f"Verification failed: {e}") from e


# ─── Callback Handler ─────────────────────────────────────────────────────────

class TruthLayerCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback that passively verifies every LLM response.

    Unlike the output parser, this does NOT block low-trust responses.
    It runs verification in the background and logs results. Use this
    for monitoring and metrics without changing your chain's behavior.

    Example:
        handler = TruthLayerCallbackHandler(
            api_key="tl_xxx",
            api_url="https://your-api.../prod",
            source_documents=["Policy text..."],
        )
        llm = ChatOpenAI(model="gpt-4", callbacks=[handler])
        # Every LLM call will be verified and logged automatically
    """

    def __init__(
        self,
        api_key: str,
        source_documents: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        api_url: str = "",
        on_hallucination=None,
        timeout: int = 30,
    ):
        """
        Args:
            api_key:           TruthLayer API key
            source_documents:  Source text list
            document_ids:      Pre-uploaded document IDs
            api_url:           TruthLayer API URL
            on_hallucination:  Optional callable(VerificationResult) invoked when
                               unsupported_count > 0 (i.e. hallucination detected)
            timeout:           HTTP timeout in seconds
        """
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-core is required. Install it with: pip install langchain-core"
            )

        self._client = TruthLayer(
            api_key=api_key,
            api_url=api_url or os.environ.get("TRUTHLAYER_API_URL", ""),
            timeout=timeout,
        )
        self._source_documents = source_documents
        self._document_ids = document_ids
        self._on_hallucination = on_hallucination

        # Metrics accumulated across calls
        self.total_calls = 0
        self.hallucination_count = 0
        self.total_latency_ms = 0.0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called after every LLM call. Verifies the generated text."""
        try:
            for generation_list in response.generations:
                for generation in generation_list:
                    text = generation.text.strip()
                    if not text:
                        continue

                    result = self._client.verify(
                        ai_response=text,
                        source_documents=self._source_documents,
                        document_ids=self._document_ids,
                    )

                    self.total_calls += 1
                    self.total_latency_ms += result.latency_ms

                    has_issues = result.has_hallucinations
                    if has_issues:
                        self.hallucination_count += 1

                    logger.info(
                        f"[TruthLayer] Call #{self.total_calls} | "
                        f"V={result.verified_count} U={result.uncertain_count} "
                        f"X={result.unsupported_count} | "
                        f"{result.latency_ms:.0f}ms | "
                        f"{'⚠ HALLUCINATION' if has_issues else '✓ CLEAN'}"
                    )

                    if has_issues and self._on_hallucination:
                        self._on_hallucination(result)

        except TruthLayerError as e:
            logger.warning(f"[TruthLayer] Callback verification failed: {e}")

    @property
    def hallucination_rate(self) -> float:
        """Percentage of calls with hallucinations detected (0-100)."""
        if self.total_calls == 0:
            return 0.0
        return round(self.hallucination_count / self.total_calls * 100, 2)

    @property
    def avg_latency_ms(self) -> float:
        """Average TruthLayer verification latency across all calls."""
        if self.total_calls == 0:
            return 0.0
        return round(self.total_latency_ms / self.total_calls, 2)

    def summary(self) -> Dict[str, Any]:
        """Return a metrics summary dict."""
        return {
            "total_calls": self.total_calls,
            "hallucination_count": self.hallucination_count,
            "hallucination_rate_pct": self.hallucination_rate,
            "avg_latency_ms": self.avg_latency_ms,
        }
