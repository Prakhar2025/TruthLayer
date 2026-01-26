"""Main entry point for TruthLayer verification system."""

import json
from src.verifier.verifier import TruthLayerVerifier


def main():
    """Demonstrate TruthLayer verification with example data."""
    
    # Initialize verifier
    verifier = TruthLayerVerifier()
    
    # Example AI response
    ai_response = """
    Python 3.11 was released in October 2022. It includes several performance 
    improvements, with speeds up to 25% faster than Python 3.10. The new version 
    introduces exception groups and the except* syntax for handling multiple 
    exceptions simultaneously. Python 3.11 also features improved error messages 
    with more precise location information.
    """
    
    # Example source documents
    source_documents = [
        """
        Python 3.11 was officially released on October 24, 2022. This release 
        focuses on performance improvements and better error reporting. According 
        to the official benchmarks, Python 3.11 is between 10-60% faster than 
        Python 3.10, with an average speedup of 25%.
        """,
        """
        New features in Python 3.11 include exception groups (PEP 654) which allow 
        programs to raise and handle multiple exceptions at once using the new 
        except* syntax. The error messages have been significantly improved with 
        fine-grained error locations in tracebacks.
        """
    ]
    
    # Perform verification
    print("=" * 70)
    print("TruthLayer Verification System - Demo")
    print("=" * 70)
    print("\nAI Response:")
    print(ai_response.strip())
    print("\n" + "-" * 70)
    
    result = verifier.verify(ai_response, source_documents)
    
    # Display results
    print("\nVerification Results:")
    print("-" * 70)
    
    for i, claim in enumerate(result["claims"], 1):
        status_symbol = {
            "VERIFIED": "✅",
            "UNCERTAIN": "⚠️",
            "UNSUPPORTED": "❌"
        }
        
        print(f"\nClaim {i}: {claim['text']}")
        print(f"Status: {status_symbol.get(claim['status'], '?')} {claim['status']}")
        print(f"Confidence: {claim['confidence']}%")
        if claim['matched_source']:
            print(f"Matched Source: {claim['matched_source'][:100]}...")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  ✅ Verified: {result['summary']['verified']}")
    print(f"  ⚠️  Uncertain: {result['summary']['uncertain']}")
    print(f"  ❌ Unsupported: {result['summary']['unsupported']}")
    print("=" * 70)
    
    # Save results to JSON
    with open("verification_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nResults saved to verification_result.json")


if __name__ == "__main__":
    main()
