"""Updated main entry point for TruthLayer verification system."""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.verifier.verifier import TruthLayerVerifier


def main():
    """Run TruthLayer verification demo."""

    print("=" * 70)
    print("  TruthLayer — AI Hallucination Verification Engine")
    print("=" * 70)

    # Check for --mock flag
    use_mock = "--mock" in sys.argv

    # Initialize verifier (auto-detects Bedrock or falls back to mock)
    verifier = TruthLayerVerifier(use_mock=use_mock)
    provider_name = type(verifier.embedding_provider).__name__
    print(f"\n📡 Embedding Provider: {provider_name}")

    if "Mock" in provider_name:
        print("   ⚠️  Using mock embeddings (TF-IDF). Results will be approximate.")
        print("   ➡️  Set up AWS Bedrock for real semantic similarity.\n")
    else:
        print("   ✅ Using AWS Bedrock Titan Embeddings (production quality)\n")

    # Sample AI response to verify
    ai_response = """
    Python 3.11 was released in October 2022. It includes several performance 
    improvements, with speeds up to 25% faster than Python 3.10. The new version 
    introduces exception groups and the except* syntax for handling multiple 
    exceptions simultaneously. Python 3.11 also features improved error messages 
    with more precise location information.
    """

    # Source documents to verify against
    source_documents = [
        """
        Python 3.11 was officially released on October 24, 2022. This release 
        focuses on performance improvements and better error reporting. According 
        to the official benchmarks, Python 3.11 is up to 10-60% faster than 
        Python 3.10, with an average speedup of 25%.
        """,
        """
        New features in Python 3.11 include exception groups (PEP 654) which allow 
        programs to raise and handle multiple exceptions at once using the new 
        except* syntax. The error messages have been enhanced with fine-grained 
        error locations in tracebacks, making debugging easier.
        """
    ]

    print("📝 AI Response:")
    print(f"   {ai_response.strip()[:200]}...\n")
    print(f"📚 Source Documents: {len(source_documents)} provided\n")
    print("🔍 Verifying...\n")

    # Run verification
    result = verifier.verify(ai_response, source_documents)

    # Display results
    status_symbols = {
        "VERIFIED": "✅",
        "UNCERTAIN": "⚠️",
        "UNSUPPORTED": "❌"
    }

    print("-" * 70)
    print("  VERIFICATION RESULTS")
    print("-" * 70)

    for i, claim in enumerate(result["claims"], 1):
        symbol = status_symbols.get(claim["status"], "?")
        print(f"\n  {i}. {claim['text']}")
        print(f"     {symbol} {claim['status']} — {claim['confidence']}% confidence")
        if claim["matched_source"]:
            print(f"     📎 Source: \"{claim['matched_source'][:100]}...\"")

    print("\n" + "-" * 70)
    summary = result["summary"]
    print(f"  Summary: ✅ {summary['verified']} verified | "
          f"⚠️ {summary['uncertain']} uncertain | "
          f"❌ {summary['unsupported']} unsupported")

    # Show metadata
    meta = result.get("metadata", {})
    print(f"\n  ⏱️  Total Latency: {meta.get('latency_ms', 'N/A')} ms")
    if "embedding_ms" in meta:
        print(f"  ⏱️  Embedding Time: {meta['embedding_ms']} ms")
    print(f"  🧠 Provider: {meta.get('provider', 'N/A')}")
    print(f"  📊 Claims: {meta.get('total_claims', 'N/A')} | "
          f"Chunks: {meta.get('source_chunks', 'N/A')}")
    print("-" * 70)

    # Save result to JSON
    output_file = "verification_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Full result saved to {output_file}")

    return result


if __name__ == "__main__":
    main()
