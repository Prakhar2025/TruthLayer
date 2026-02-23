"""
TruthLayer Python SDK — One-line AI hallucination verification.

Usage:
    from truthlayer import TruthLayer

    tl = TruthLayer(api_key="tl_xxx", api_url="https://your-api/prod")
    result = tl.verify("AI says X", ["Source says X"])
    print(result.summary)
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError


@dataclass
class Claim:
    """A single verified claim."""
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
    """Result of a verification request."""
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
        """Overall trust score (0-100)."""
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
    """Base exception for TruthLayer SDK."""
    pass


class TruthLayer:
    """
    TruthLayer SDK Client.

    Example:
        tl = TruthLayer(api_key="tl_xxx")
        result = tl.verify(
            "The Eiffel Tower was built in 1889.",
            ["The Eiffel Tower was completed in 1889 in Paris."]
        )
        print(f"Trust score: {result.trust_score}%")
        print(f"Hallucinations: {result.has_hallucinations}")
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://your-api.execute-api.us-east-1.amazonaws.com/prod",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def verify(
        self,
        ai_response: str,
        source_documents: List[str],
    ) -> VerificationResult:
        """
        Verify an AI response against source documents.

        Args:
            ai_response: The AI-generated text to verify
            source_documents: List of source documents

        Returns:
            VerificationResult with claims, summary, and metadata

        Raises:
            TruthLayerError: If the API request fails
        """
        payload = {
            "ai_response": ai_response,
            "source_documents": source_documents,
        }

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

    def health(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the TruthLayer API."""
        url = f"{self.api_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        body = json.dumps(payload).encode() if payload else None

        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            error_body = e.read().decode()
            try:
                error_data = json.loads(error_body)
                msg = error_data.get("message", error_body)
            except json.JSONDecodeError:
                msg = error_body
            raise TruthLayerError(f"API error {e.code}: {msg}") from e
        except Exception as e:
            raise TruthLayerError(f"Request failed: {e}") from e
