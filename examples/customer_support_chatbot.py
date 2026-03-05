#!/usr/bin/env python3
"""
TruthLayer Integration: Customer Support Chatbot

Demonstrates how a customer support system uses TruthLayer to verify
AI-generated responses before sending them to customers.

Flow:
    1. Customer asks a question about product returns
    2. AI generates a response based on the company policy docs
    3. TruthLayer verifies the response against the actual policy
    4. Only VERIFIED claims are sent to the customer
    5. UNCERTAIN/UNSUPPORTED claims are flagged for human review

Usage:
    export TRUTHLAYER_API_URL="https://your-api.execute-api.us-east-1.amazonaws.com/prod"
    export TRUTHLAYER_API_KEY="tl_your_key_here"
    python examples/customer_support_chatbot.py
"""

import os
import sys

# Add parent dir so we can import the SDK
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.python.truthlayer import TruthLayer


# ─── Simulated company knowledge base ───────────────────────────────────────
RETURN_POLICY = """
Our return policy allows customers to return products within 30 days of purchase.
Items must be in original packaging and unused condition.
Refunds are processed within 5-7 business days after we receive the item.
Digital products and gift cards are non-refundable.
Shipping costs for returns are the responsibility of the customer,
unless the item arrived damaged or defective.
Expedited shipping refunds are not available.
"""

SHIPPING_POLICY = """
Standard shipping takes 5-7 business days within the continental US.
Express shipping (2-day) is available for an additional $12.99.
Free shipping is offered on orders over $50.
International shipping is available to select countries with 10-15 business day delivery.
Orders placed before 2 PM EST ship the same day.
"""

# ─── Simulated AI chatbot responses ─────────────────────────────────────────
CUSTOMER_QUERIES = [
    {
        "question": "What is your return policy?",
        "ai_response": (
            "You can return any product within 30 days of purchase. "
            "Items must be in their original packaging. "
            "Refunds are processed within 5-7 business days. "
            "We offer free return shipping on all orders."
        ),
        "source_docs": [RETURN_POLICY],
    },
    {
        "question": "How long does shipping take?",
        "ai_response": (
            "Standard shipping takes 5-7 business days. "
            "Express 2-day shipping costs $12.99. "
            "Free shipping is available on orders over $50. "
            "All orders ship the same day regardless of time."
        ),
        "source_docs": [SHIPPING_POLICY],
    },
]


def run_chatbot_demo():
    """Run the customer support chatbot verification demo."""
    api_url = os.environ.get("TRUTHLAYER_API_URL", "")
    api_key = os.environ.get("TRUTHLAYER_API_KEY", "")

    if not api_url or not api_key:
        print("Error: Set TRUTHLAYER_API_URL and TRUTHLAYER_API_KEY environment variables")
        print("Example:")
        print('  export TRUTHLAYER_API_URL="https://your-api.execute-api.us-east-1.amazonaws.com/prod"')
        print('  export TRUTHLAYER_API_KEY="tl_your_key_here"')
        sys.exit(1)

    client = TruthLayer(api_url=api_url, api_key=api_key)

    print("=" * 70)
    print("  TruthLayer — Customer Support Chatbot Demo")
    print("=" * 70)

    for i, query in enumerate(CUSTOMER_QUERIES, 1):
        print(f"\n{'─' * 70}")
        print(f"  Customer Question {i}: {query['question']}")
        print(f"{'─' * 70}")
        print(f"\n  AI Response (before verification):")
        print(f"  {query['ai_response']}\n")

        try:
            result = client.verify(
                ai_response=query["ai_response"],
                source_documents=query["source_docs"],
            )

            print(f"  Verification Results:")
            print(f"  {'Status':<14} {'Confidence':>10}  Claim")
            print(f"  {'─' * 60}")

            safe_claims = []
            flagged_claims = []

            for claim in result.claims:
                status = claim.status
                confidence = claim.confidence
                text = claim.text[:80]

                icon = {"VERIFIED": "✓", "UNCERTAIN": "?", "UNSUPPORTED": "✗"}.get(status, "?")
                print(f"  {icon} {status:<12} {confidence:>8.1%}  {text}")

                if status == "VERIFIED":
                    safe_claims.append(claim.text)
                else:
                    flagged_claims.append(claim)

            print(f"\n  Summary: {result.summary.get('verified', 0)} verified, "
                  f"{result.summary.get('uncertain', 0)} uncertain, "
                  f"{result.summary.get('unsupported', 0)} unsupported")
            print(f"  Latency: {result.metadata.get('latency_ms', 0):.0f}ms | "
                  f"Cache: {result.metadata.get('cache_hits', 0)} hits, "
                  f"{result.metadata.get('cache_misses', 0)} misses")

            if flagged_claims:
                print(f"\n  ⚠ ACTION: {len(flagged_claims)} claim(s) flagged for human review")
                print(f"  → Only verified claims will be sent to the customer")

        except Exception as e:
            print(f"  Error: {e}")

    print(f"\n{'=' * 70}")
    print("  Demo complete. In production, only VERIFIED claims reach the customer.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_chatbot_demo()
