# TruthLayer - Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Run Demo

```bash
# Run main demo
python main.py

# Run examples with different scenarios
python example_usage.py
```

## Basic Usage

```python
from src.verifier.verifier import TruthLayerVerifier

# Initialize
verifier = TruthLayerVerifier()

# Verify AI response
result = verifier.verify(
    ai_response="Your AI generated text here.",
    source_documents=["Source document 1", "Source document 2"]
)

# Check results
print(f"Verified: {result['summary']['verified']}")
print(f"Uncertain: {result['summary']['uncertain']}")
print(f"Unsupported: {result['summary']['unsupported']}")

# Inspect individual claims
for claim in result["claims"]:
    print(f"{claim['status']}: {claim['text']} ({claim['confidence']}%)")
```

## Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src
```

## Output Format

```json
{
  "claims": [
    {
      "text": "The claim text",
      "status": "VERIFIED|UNCERTAIN|UNSUPPORTED",
      "confidence": 85.5,
      "matched_source": "Best matching source snippet"
    }
  ],
  "summary": {
    "verified": 2,
    "uncertain": 1,
    "unsupported": 0
  }
}
```

## Configuration

Edit `src/config.py`:

```python
VERIFIED_THRESHOLD = 0.80    # Minimum for VERIFIED
UNCERTAIN_THRESHOLD = 0.55   # Minimum for UNCERTAIN
EMBEDDING_DIMENSION = 384    # Vector size
```

## Next Steps

1. Test with your own data
2. Adjust thresholds based on your needs
3. Ready to swap mock embeddings with AWS Bedrock
4. Integrate into your application

## Notes

- Mock embeddings use TF-IDF (deterministic but limited)
- Real semantic embeddings (AWS Bedrock) will be much more accurate
- All components are modular and swappable
