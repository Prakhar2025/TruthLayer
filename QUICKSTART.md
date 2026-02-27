# 🛡️ TruthLayer — Quick Start Guide

Get up and running with TruthLayer in under 5 minutes.

---

## Option 1: Use the Live API (Recommended)

TruthLayer is already deployed on AWS. Just get an API key and start verifying.

### Step 1 — Generate an API Key

```bash
python scripts/generate_api_key.py "YourName"
# Save the printed key — it cannot be retrieved later
```

### Step 2 — Verify with Python SDK

```python
from sdk.python.truthlayer import TruthLayer

tl = TruthLayer(
    api_key="tl_your_key_here",
    api_url="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod"
)

result = tl.verify(
    ai_response="Python 3.11 was released in October 2022 and is 25% faster than 3.10.",
    source_documents=[
        "Python 3.11 was officially released on October 24, 2022. It is up to 25% faster than Python 3.10."
    ]
)

print(f"Trust Score: {result.trust_score}%")
print(f"Hallucinations: {result.has_hallucinations}")

for claim in result.claims:
    print(f"  [{claim.status}] {claim.text} — {claim.confidence:.1f}%")
```

### Step 3 — Verify with cURL

```bash
curl -X POST https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: tl_your_key_here" \
  -d '{
    "ai_response": "Python 3.11 is 25% faster than 3.10.",
    "source_documents": ["Python 3.11 has up to 25% speedup over 3.10, released October 2022."]
  }'
```

---

## Option 2: Run Locally (Mock Mode — No AWS Required)

```bash
# Install dependencies
pip install -r requirements.txt

# Run with mock embeddings (no AWS credentials needed)
python main.py --mock
```

---

## Option 3: Local with Real Bedrock

```bash
# Configure AWS credentials
aws configure

# Run with real Bedrock Titan V2 embeddings
python main.py
```

---

## Response Format

```json
{
  "claims": [
    {
      "text": "The claim text",
      "status": "VERIFIED",
      "confidence": 94.53,
      "similarity_score": 0.9453,
      "matched_source": "Best matching source snippet..."
    }
  ],
  "summary": {
    "verified": 1,
    "uncertain": 0,
    "unsupported": 0
  },
  "metadata": {
    "latency_ms": 460,
    "embedding_ms": 380,
    "provider": "BedrockEmbeddingProvider",
    "total_claims": 1
  }
}
```

---

## Thresholds

| Score | Status | Meaning |
|-------|--------|---------|
| ≥ 0.80 | 🟢 VERIFIED | Claim is supported by sources |
| ≥ 0.55 | 🟡 UNCERTAIN | Partial or weak match |
| < 0.55 | 🔴 UNSUPPORTED | No supporting evidence found |

---

## Run Tests

```bash
# Run all 25 unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src
```

---

## Health Check

```bash
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/health
# {"status": "healthy", "service": "TruthLayer", "version": "1.0.0"}
```

---

## Dashboard

```bash
cd dashboard
# Create .env.local with your API URL and key
npm install
npm run dev
# Open http://localhost:3000
```
