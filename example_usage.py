"""Example usage showing TruthLayer with well-matched content."""

from src.verifier.verifier import TruthLayerVerifier


def example_verified():
    """Example showing verified claims."""
    print("=" * 70)
    print("Example 1: Verified Claims")
    print("=" * 70)
    
    verifier = TruthLayerVerifier()
    
    ai_response = """
    The Eiffel Tower is located in Paris, France. It was completed in 1889.
    The tower stands 330 meters tall and was designed by Gustave Eiffel.
    """
    
    source_documents = [
        "The Eiffel Tower is located in Paris, France and was completed in 1889.",
        "The tower stands 330 meters tall and was designed by Gustave Eiffel."
    ]
    
    result = verifier.verify(ai_response, source_documents)
    print_results(result)


def example_mixed():
    """Example showing mixed verification results."""
    print("\n" + "=" * 70)
    print("Example 2: Mixed Results")
    print("=" * 70)
    
    verifier = TruthLayerVerifier()
    
    ai_response = """
    The company was founded in 2020 and has 500 employees.
    It operates in 15 countries worldwide.
    The CEO is John Smith and revenue reached $100 million last year.
    """
    
    source_documents = [
        "The company was founded in 2020 and currently has 500 employees.",
        "Operations span across 15 countries globally."
    ]
    
    result = verifier.verify(ai_response, source_documents)
    print_results(result)


def example_unsupported():
    """Example showing unsupported claims."""
    print("\n" + "=" * 70)
    print("Example 3: Unsupported Claims")
    print("=" * 70)
    
    verifier = TruthLayerVerifier()
    
    ai_response = """
    The product was launched in March 2023.
    It has received over 10,000 downloads in the first month.
    """
    
    source_documents = [
        "Our company focuses on software development and cloud services.",
        "We have a team of experienced engineers working on various projects."
    ]
    
    result = verifier.verify(ai_response, source_documents)
    print_results(result)


def print_results(result):
    """Print verification results in a readable format."""
    status_symbols = {
        "VERIFIED": "✅",
        "UNCERTAIN": "⚠️",
        "UNSUPPORTED": "❌"
    }
    
    print("\nClaims:")
    for i, claim in enumerate(result["claims"], 1):
        symbol = status_symbols.get(claim["status"], "?")
        print(f"\n{i}. {claim['text']}")
        print(f"   {symbol} {claim['status']} ({claim['confidence']}%)")
    
    print(f"\nSummary: ✅ {result['summary']['verified']} | "
          f"⚠️ {result['summary']['uncertain']} | "
          f"❌ {result['summary']['unsupported']}")


if __name__ == "__main__":
    example_verified()
    example_mixed()
    example_unsupported()
    
    print("\n" + "=" * 70)
    print("Note: TF-IDF embeddings have limitations. Real semantic embeddings")
    print("(like AWS Bedrock) will provide much better accuracy.")
    print("=" * 70)
