#!/usr/bin/env python3
"""
TruthLayer Integration: Document QA System

Demonstrates how a document question-answering system uses TruthLayer
to verify that AI answers are actually grounded in the source documents.

Flow:
    1. Upload knowledge base documents to TruthLayer
    2. User asks a question → AI generates an answer
    3. TruthLayer verifies the answer against uploaded documents (by ID)
    4. Returns claim-level attribution to source sentences

Usage:
    export TRUTHLAYER_API_URL="https://your-api.execute-api.us-east-1.amazonaws.com/prod"
    export TRUTHLAYER_API_KEY="tl_your_key_here"
    python examples/document_qa.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.python.truthlayer import TruthLayer


# ─── Knowledge base documents ───────────────────────────────────────────────
DOCUMENTS = [
    {
        "title": "Company Overview — Q4 2025",
        "content": (
            "TechCorp reported revenue of $4.2 billion in Q4 2025, representing "
            "a 15% year-over-year increase. The company has 12,000 employees "
            "across 8 countries. Operating margin improved to 22%, up from 18% "
            "in the previous year. The board approved a $500 million share buyback "
            "program. Cloud services division grew 32% and now represents 45% of "
            "total revenue."
        ),
    },
    {
        "title": "Product Roadmap — 2026",
        "content": (
            "TechCorp plans to launch three new products in 2026: an AI-powered "
            "analytics platform in Q1, a federated data mesh solution in Q2, and "
            "a real-time collaboration suite in Q3. R&D spending will increase to "
            "18% of revenue, up from 15%. The company plans to hire 2,000 additional "
            "engineers. All new products will be cloud-native with SOC 2 Type II "
            "compliance from day one."
        ),
    },
]

# ─── Simulated QA pairs ─────────────────────────────────────────────────────
QA_PAIRS = [
    {
        "question": "What was TechCorp's Q4 2025 revenue?",
        "ai_answer": (
            "TechCorp's Q4 2025 revenue was $4.2 billion, a 15% increase year-over-year. "
            "The cloud services division was the biggest growth driver at 32% growth. "
            "The company is now valued at $50 billion."
        ),
    },
    {
        "question": "What new products is TechCorp launching?",
        "ai_answer": (
            "TechCorp is launching an AI analytics platform in Q1 2026, "
            "a data mesh solution in Q2, and a collaboration suite in Q3. "
            "They plan to hire 2,000 engineers. "
            "All products will support on-premise deployment."
        ),
    },
]


def run_document_qa_demo():
    """Run the document QA verification demo."""
    api_url = os.environ.get("TRUTHLAYER_API_URL", "")
    api_key = os.environ.get("TRUTHLAYER_API_KEY", "")

    if not api_url or not api_key:
        print("Error: Set TRUTHLAYER_API_URL and TRUTHLAYER_API_KEY environment variables")
        sys.exit(1)

    client = TruthLayer(api_url=api_url, api_key=api_key)

    print("=" * 70)
    print("  TruthLayer — Document QA Verification Demo")
    print("=" * 70)

    # Step 1: Upload documents
    print("\n  Step 1: Uploading knowledge base documents...\n")
    doc_ids = []
    for doc in DOCUMENTS:
        try:
            result = client.upload_document(
                title=doc["title"],
                content=doc["content"],
            )
            doc_id = result.get("document_id", "unknown")
            doc_ids.append(doc_id)
            print(f"    ✓ Uploaded: {doc['title']} → ID: {doc_id[:8]}...")
        except Exception as e:
            print(f"    ✗ Failed to upload {doc['title']}: {e}")

    if not doc_ids:
        print("\n  Error: No documents uploaded. Exiting.")
        sys.exit(1)

    # Step 2: Verify QA pairs against uploaded documents
    print(f"\n  Step 2: Verifying AI answers against {len(doc_ids)} documents...\n")

    for i, qa in enumerate(QA_PAIRS, 1):
        print(f"  {'─' * 60}")
        print(f"  Q{i}: {qa['question']}")
        print(f"  AI Answer: {qa['ai_answer'][:100]}...")
        print()

        try:
            # Use document_ids (not raw text) — the real-API pattern
            result = client.verify(
                ai_response=qa["ai_answer"],
                document_ids=doc_ids,
            )

            for claim in result.claims:
                status = claim.status
                matched = claim.matched_source[:60] if claim.matched_source else ""
                icon = {"VERIFIED": "✓", "UNCERTAIN": "?", "UNSUPPORTED": "✗"}.get(status, "?")
                print(f"    {icon} [{status}] {claim.text[:70]}")
                if matched:
                    print(f"      ↳ Source: \"{matched}...\"")

            print(f"\n    Result: {result.summary.get('verified', 0)}V / "
                  f"{result.summary.get('uncertain', 0)}U / "
                  f"{result.summary.get('unsupported', 0)}X "
                  f"| {result.metadata.get('latency_ms', 0):.0f}ms")

        except Exception as e:
            print(f"    Error: {e}")

    # Step 3: Cleanup
    print(f"\n  Step 3: Cleaning up uploaded documents...")
    for doc_id in doc_ids:
        try:
            client.delete_document(doc_id)
            print(f"    ✓ Deleted: {doc_id[:8]}...")
        except Exception as e:
            print(f"    ✗ Failed to delete {doc_id[:8]}...: {e}")

    print(f"\n{'=' * 70}")
    print("  Demo complete. Hallucinated claims were caught and attributed.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_document_qa_demo()
