"""
TruthLayer SDK — One-line AI hallucination verification.

Usage:
    from truthlayer import TruthLayer

    tl = TruthLayer(api_key="tl_xxx", api_url="https://your-api/prod")
    result = tl.verify("AI says X", ["Source says X"])
    print(result.trust_score)

For LangChain integration:
    pip install truthlayer-sdk[langchain]

    from truthlayer.langchain import TruthLayerOutputParser
"""

# Re-export all public symbols from the core module so that
# `from truthlayer import TruthLayer` works after `pip install truthlayer-sdk`.

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError


__version__ = "0.1.0"
__all__ = [
    "TruthLayer",
    "TruthLayerError",
    "Claim",
    "VerificationResult",
    "__version__",
]


@dataclass
class Claim:
    """A single verified claim extracted from the AI response."""

    text: str
    status: str  # VERIFIED | UNCERTAIN | UNSUPPORTED
    confidence: float
    similarity_score: float
    matched_source: str

    @property
    def is_verified(self) -> bool:
        return self.status == "VERIFIED"

    @property
    def is_uncertain(self) -> bool:
        return self.status == "UNCERTAIN"

    @property
    def is_unsupported(self) -> bool:
        return self.status == "UNSUPPORTED"


@dataclass
class VerificationResult:
    """
    Result of a verification request.

    Attributes:
        claims:   List of Claim objects with individual verdicts.
        summary:  Dict with counts: {"verified": N, "uncertain": N, "unsupported": N}
        metadata: Dict with latency_ms, cache_hits, cache_misses, etc.
        raw:      The full raw API response (hidden from repr).
    """

    claims: List[Claim]
    summary: Dict[str, int]
    metadata: Dict[str, Any]
    raw: Dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def verified_count(self) -> int:
        return self.summary.get("verified", 0)

    @property
    def uncertain_count(self) -> int:
        return self.summary.get("uncertain", 0)

    @property
    def unsupported_count(self) -> int:
        return self.summary.get("unsupported", 0)

    @property
    def total_claims(self) -> int:
        return len(self.claims)

    @property
    def trust_score(self) -> float:
        """Overall trust score (0-100). Higher is better."""
        if not self.claims:
            return 0.0
        return round(
            sum(c.confidence for c in self.claims if c.is_verified)
            / max(len(self.claims), 1),
            2,
        )

    @property
    def latency_ms(self) -> float:
        return self.metadata.get("latency_ms", 0)

    @property
    def has_hallucinations(self) -> bool:
        return self.unsupported_count > 0


class TruthLayerError(Exception):
    """Base exception for TruthLayer SDK errors."""
    pass


class TruthLayer:
    """
    TruthLayer SDK Client.

    Verifies AI-generated text against source documents in real time.
    Only stdlib dependencies — no requests/httpx needed.

    Example::

        tl = TruthLayer(api_key="tl_xxx", api_url="https://your-api/prod")

        result = tl.verify(
            "The Eiffel Tower was built in 1889.",
            ["The Eiffel Tower was completed in 1889 in Paris."]
        )
        print(f"Trust score: {result.trust_score}%")
        print(f"Hallucinations: {result.has_hallucinations}")

    Args:
        api_key:  Your TruthLayer API key (starts with ``tl_``)
        api_url:  Base URL of the TruthLayer API deployment
        timeout:  HTTP request timeout in seconds (default: 30)
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://your-api.execute-api.us-east-1.amazonaws.com/prod",
        timeout: int = 30,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def verify(
        self,
        ai_response: str,
        source_documents: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
    ) -> VerificationResult:
        """
        Verify an AI response against source documents.

        Args:
            ai_response:      The AI-generated text to verify.
            source_documents:  List of source document texts.
            document_ids:      List of pre-uploaded document IDs.

        Returns:
            VerificationResult with claims, summary, and metadata.

        Raises:
            TruthLayerError: On API errors.
            ValueError: If neither source_documents nor document_ids given.
        """
        if not source_documents and not document_ids:
            raise ValueError(
                "At least one of source_documents or document_ids is required"
            )

        payload: Dict[str, Any] = {"ai_response": ai_response}
        if source_documents:
            payload["source_documents"] = source_documents
        if document_ids:
            payload["document_ids"] = document_ids

        data = self._request("POST", "/verify", payload)

        claims = [
            Claim(
                text=c["text"],
                status=c["status"],
                confidence=c["confidence"],
                similarity_score=c["similarity_score"],
                matched_source=c.get("matched_source", ""),
            )
            for c in data.get("claims", [])
        ]

        return VerificationResult(
            claims=claims,
            summary=data.get("summary", {}),
            metadata=data.get("metadata", {}),
            raw=data,
        )

    def upload_document(
        self,
        content: str,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a source document for later verification by ID.

        Args:
            content:   Full text of the document.
            title:     Optional title.
            metadata:  Optional metadata dict.

        Returns:
            Dict with document_id.
        """
        payload: Dict[str, Any] = {"content": content}
        if title:
            payload["title"] = title
        if metadata:
            payload["metadata"] = metadata
        return self._request("POST", "/documents", payload)

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get a document by ID."""
        return self._request("GET", f"/documents/{document_id}")

    def list_documents(self) -> Dict[str, Any]:
        """List all uploaded documents."""
        return self._request("GET", "/documents")

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document by ID."""
        return self._request("DELETE", f"/documents/{document_id}")

    def health(self) -> Dict[str, Any]:
        """Check API health status."""
        return self._request("GET", "/health")

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated HTTP request to the TruthLayer API."""
        url = f"{self.api_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        body = json.dumps(payload).encode("utf-8") if payload else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                error_data = json.loads(error_body)
                msg = error_data.get("message", error_body)
            except json.JSONDecodeError:
                msg = error_body
            raise TruthLayerError(f"API error {e.code}: {msg}") from e
        except Exception as e:
            raise TruthLayerError(f"Request failed: {e}") from e
