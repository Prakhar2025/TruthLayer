# TruthLayer - Phase 1: Local Core Engine

AI hallucination verification system that validates AI outputs against source documents using semantic similarity and confidence scoring.

## Features

- **Claim Extraction**: Automatically extracts atomic factual claims from AI responses
- **Semantic Similarity**: Computes similarity between claims and source documents
- **Confidence Scoring**: Classifies claims as VERIFIED, UNCERTAIN, or UNSUPPORTED
- **Mock Embeddings**: Deterministic TF-IDF based embeddings (ready for AWS Bedrock swap)
- **Production Ready**: Clean, testable code with comprehensive unit tests

## Project Structure

```
truthlayer/
├── src/
│   ├── verifier/
│   │   ├── claim_extractor.py      # Extract claims from AI text
│   │   ├── similarity_engine.py    # Cosine similarity computation
│   │   ├── confidence_scorer.py    # Claim classification logic
│   │   └── verifier.py             # Main verification orchestrator
│   ├── mocks/
│   │   └── embedding_provider.py   # Mock TF-IDF embeddings
│   ├── utils/
│   │   └── text_splitter.py        # Text chunking utilities
│   └── config.py                   # Configuration settings
├── tests/
│   └── test_verifier.py            # Comprehensive unit tests
├── main.py                         # Demo entry point
└── requirements.txt                # Python dependencies
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

```bash
python main.py
```

### Programmatic Usage

```python
from src.verifier.verifier import TruthLayerVerifier

# Initialize verifier
verifier = TruthLayerVerifier()

# Prepare data
ai_response = "Python 3.11 was released in October 2022 with 25% performance improvements."
source_documents = [
    "Python 3.11 was officially released on October 24, 2022.",
    "Python 3.11 is 10-60% faster than 3.10, averaging 25% speedup."
]

# Verify
result = verifier.verify(ai_response, source_documents)

# Access results
for claim in result["claims"]:
    print(f"{claim['status']}: {claim['text']} ({claim['confidence']}%)")

print(f"Summary: {result['summary']}")
```

### Output Format

```json
{
  "claims": [
    {
      "text": "Python 3.11 was released in October 2022.",
      "status": "VERIFIED",
      "confidence": 91.5,
      "matched_source": "Python 3.11 was officially released on October 24, 2022..."
    }
  ],
  "summary": {
    "verified": 3,
    "uncertain": 1,
    "unsupported": 0
  }
}
```

## Testing

Run all tests:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=src --cov-report=html
```

## Configuration

Edit `src/config.py` to adjust thresholds:

```python
VERIFIED_THRESHOLD = 0.80    # Minimum score for VERIFIED
UNCERTAIN_THRESHOLD = 0.55   # Minimum score for UNCERTAIN
EMBEDDING_DIMENSION = 384    # Embedding vector size
```

## Classification Logic

- **✅ VERIFIED**: Similarity ≥ 0.80
- **⚠️ UNCERTAIN**: Similarity 0.55 - 0.79
- **❌ UNSUPPORTED**: Similarity < 0.55

## Future Integration

The mock embedding provider can be easily swapped with AWS Bedrock:

```python
# Current (mock)
from src.mocks.embedding_provider import MockEmbeddingProvider
provider = MockEmbeddingProvider()

# Future (AWS Bedrock)
from src.aws.bedrock_provider import BedrockEmbeddingProvider
provider = BedrockEmbeddingProvider()

# Same interface
verifier = TruthLayerVerifier(embedding_provider=provider)
```

## Design Principles

- **Deterministic**: Same input always produces same output
- **Testable**: Comprehensive unit test coverage
- **Modular**: Easy to swap components (embeddings, scoring logic)
- **Production Ready**: No placeholders, complete implementations
- **Clean Code**: Type hints, docstrings, clear naming

## Next Steps (Phase 2)

- Integrate AWS Bedrock for embeddings
- Add DynamoDB for result storage
- Implement REST API
- Add batch processing support
- Build web dashboard
