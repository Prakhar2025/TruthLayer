# TruthLayer Python SDK

> One-line AI hallucination verification. Zero dependencies.

[![PyPI](https://img.shields.io/pypi/v/truthlayer-sdk)](https://pypi.org/project/truthlayer-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/truthlayer-sdk)](https://pypi.org/project/truthlayer-sdk/)
[![License](https://img.shields.io/github/license/prakhar230620/TruthLayer)](LICENSE)

## Install

```bash
pip install truthlayer-sdk
```

With LangChain integration:

```bash
pip install truthlayer-sdk[langchain]
```

## Quick Start

```python
from truthlayer import TruthLayer

tl = TruthLayer(
    api_key="tl_your_key_here",
    api_url="https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"
)

# Verify an AI response against source documents
result = tl.verify(
    ai_response="Refunds are processed within 5-7 business days.",
    source_documents=["Our refund policy allows returns within 30 days. Refunds are processed within 5-7 business days."]
)

print(f"Trust Score: {result.trust_score}%")
print(f"Claims: {result.total_claims}")
print(f"Hallucinations: {result.has_hallucinations}")
print(f"Latency: {result.latency_ms}ms")
```

## API Reference

### `TruthLayer(api_key, api_url, timeout=30)`

Initialize the client.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_key` | str | Yes | Your API key (starts with `tl_`) |
| `api_url` | str | Yes | Base URL of your TruthLayer deployment |
| `timeout` | int | No | HTTP timeout in seconds (default: 30) |

### `tl.verify(ai_response, source_documents=None, document_ids=None)`

Verify AI output against source documents.

**Returns** `VerificationResult` with:

| Property | Type | Description |
|----------|------|-------------|
| `claims` | `List[Claim]` | Individual claim verdicts |
| `trust_score` | `float` | Overall trust score (0-100) |
| `has_hallucinations` | `bool` | True if any unsupported claims |
| `verified_count` | `int` | Number of verified claims |
| `unsupported_count` | `int` | Number of unsupported claims |
| `latency_ms` | `float` | API response time |

### `tl.upload_document(content, title="", metadata=None)`

Upload a document for later verification by ID.

### `tl.get_document(document_id)` / `tl.list_documents()` / `tl.delete_document(document_id)`

Document management endpoints.

### `tl.health()`

Check API health status.

## LangChain Integration

```python
from truthlayer.langchain import TruthLayerOutputParser

parser = TruthLayerOutputParser(
    api_key="tl_xxx",
    api_url="https://your-api/prod",
    source_documents=["Your source text here."],
    min_trust_score=70.0,
)

# Use in a chain — blocks hallucinations automatically
chain = llm | parser
result = chain.invoke("What is our refund policy?")
print(result.trust_score)  # VerifiedOutput with trust score
```

## Error Handling

```python
from truthlayer import TruthLayer, TruthLayerError

tl = TruthLayer(api_key="tl_xxx", api_url="https://your-api/prod")

try:
    result = tl.verify("AI response", ["Source text"])
except TruthLayerError as e:
    print(f"API error: {e}")
except ValueError as e:
    print(f"Invalid input: {e}")
```

## Get an API Key

Visit your TruthLayer dashboard or use the API directly:

```python
import requests

response = requests.post(
    "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/keys",
    json={"owner": "Your Name", "email": "you@company.com", "use_case": "Chatbot"}
)
key = response.json()["api_key"]  # Save this — shown once only
```

## License

MIT
