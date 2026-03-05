#!/usr/bin/env python3
"""
TruthLayer Integration: Legal Contract Analyzer

Demonstrates how a legal AI assistant uses TruthLayer to verify
AI-generated contract summaries against the actual contract text,
ensuring no hallucinated terms or obligations.

Flow:
    1. Upload the full contract text as a source document
    2. AI generates a summary of key terms
    3. TruthLayer verifies every claim in the summary
    4. Legal team reviews only the flagged (unverified) items

Usage:
    export TRUTHLAYER_API_URL="https://your-api.execute-api.us-east-1.amazonaws.com/prod"
    export TRUTHLAYER_API_KEY="tl_your_key_here"
    python examples/legal_contract_analyzer.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.python.truthlayer import TruthLayer


# ─── Simulated contract text ────────────────────────────────────────────────
CONTRACT_TEXT = """
MASTER SERVICES AGREEMENT

This agreement is entered into between Acme Corp ("Client") and TechVendor Inc
("Provider") effective January 1, 2026.

1. TERM: This agreement has an initial term of 24 months, with automatic renewal
   for successive 12-month periods unless either party provides 90 days written
   notice of non-renewal.

2. FEES: Client shall pay Provider $15,000 per month for the base platform.
   Additional usage beyond 1 million API calls per month is billed at $0.002
   per call. Payment is due within Net 30 of invoice date.

3. SLA: Provider guarantees 99.9% uptime for production services. Downtime
   credits are calculated at 10x the hourly rate for each hour below the SLA.
   Scheduled maintenance windows (Sundays 2-6 AM EST) are excluded from SLA
   calculations.

4. DATA: All client data remains the property of the Client. Provider shall
   not use client data for training machine learning models without explicit
   written consent. Data is encrypted at rest (AES-256) and in transit (TLS 1.3).

5. LIABILITY: Provider's total aggregate liability shall not exceed 12 months
   of fees paid. Neither party shall be liable for indirect, consequential,
   or punitive damages.

6. TERMINATION: Either party may terminate for cause with 30 days written notice
   if the other party materially breaches and fails to cure within the notice
   period. Upon termination, Provider shall return all client data within 30 days.
"""

# ─── Simulated AI-generated summary ─────────────────────────────────────────
AI_SUMMARY = (
    "This is a 24-month agreement between Acme Corp and TechVendor Inc starting "
    "January 2026. The monthly fee is $15,000 with overage at $0.002 per API call "
    "beyond 1 million calls. The SLA guarantees 99.99% uptime with 10x credits for "
    "downtime. All data is encrypted with AES-256 and TLS 1.2. The contract auto-renews "
    "annually with 60 days notice required. Liability is capped at 24 months of fees. "
    "Either party can terminate with 30 days notice for material breach."
)


def run_legal_demo():
    """Run the legal contract analyzer verification demo."""
    api_url = os.environ.get("TRUTHLAYER_API_URL", "")
    api_key = os.environ.get("TRUTHLAYER_API_KEY", "")

    if not api_url or not api_key:
        print("Error: Set TRUTHLAYER_API_URL and TRUTHLAYER_API_KEY environment variables")
        sys.exit(1)

    client = TruthLayer(api_url=api_url, api_key=api_key)

    print("=" * 70)
    print("  TruthLayer — Legal Contract Analyzer Demo")
    print("=" * 70)

    print("\n  Contract: Master Services Agreement (Acme Corp ↔ TechVendor Inc)")
    print(f"  AI Summary Length: {len(AI_SUMMARY)} characters")
    print(f"  Contract Length: {len(CONTRACT_TEXT)} characters")

    print(f"\n  {'─' * 60}")
    print("  AI-Generated Summary (before verification):")
    print(f"  {AI_SUMMARY}")
    print(f"  {'─' * 60}")

    print("\n  Verifying summary against contract text...\n")

    try:
        result = client.verify(
            ai_response=AI_SUMMARY,
            source_documents=[CONTRACT_TEXT],
        )

        claims = result.claims

        # Categorize claims
        verified = [c for c in claims if c.status == "VERIFIED"]
        uncertain = [c for c in claims if c.status == "UNCERTAIN"]
        unsupported = [c for c in claims if c.status == "UNSUPPORTED"]

        print(f"  {'Status':<14} {'Score':>6}  Claim")
        print(f"  {'─' * 64}")
        for claim in claims:
            icon = {"VERIFIED": "✓", "UNCERTAIN": "?", "UNSUPPORTED": "✗"}.get(claim.status, "?")
            score = claim.similarity_score
            print(f"  {icon} {claim.status:<12} {score:>5.1%}  {claim.text[:65]}")

        print(f"\n  {'─' * 64}")
        print(f"  Accuracy Report:")
        print(f"    Verified:    {len(verified)}/{len(claims)} claims grounded in contract")
        print(f"    Uncertain:   {len(uncertain)}/{len(claims)} claims need human review")
        print(f"    Unsupported: {len(unsupported)}/{len(claims)} claims NOT in contract")
        print(f"    Precision:   {len(verified) / len(claims) * 100:.1f}%" if claims else "    N/A")
        print(f"    Latency:     {result.metadata.get('latency_ms', 0):.0f}ms")

        if unsupported:
            print(f"\n  ⚠ LEGAL REVIEW REQUIRED — {len(unsupported)} claim(s) not in contract:")
            for c in unsupported:
                print(f"    ✗ \"{c.text[:80]}\"")
            print("    → These claims may contain hallucinated contract terms")

        # Risk assessment
        risk_score = len(unsupported) / len(claims) * 100 if claims else 0
        risk_level = "LOW" if risk_score < 10 else "MEDIUM" if risk_score < 30 else "HIGH"
        print(f"\n  Risk Level: {risk_level} ({risk_score:.0f}% unverified)")

    except Exception as e:
        print(f"  Error: {e}")

    print(f"\n{'=' * 70}")
    print("  Demo complete. In production, flagged items go to legal review queue.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_legal_demo()
