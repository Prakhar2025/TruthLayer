<p align="center">
  <img src="https://img.shields.io/badge/AWS-Bedrock-FF9900?style=for-the-badge&logo=amazonaws" alt="AWS Bedrock"/>
  <img src="https://img.shields.io/badge/Latency-Sub--1s-22C55E?style=for-the-badge" alt="Latency"/>
  <img src="https://img.shields.io/badge/Precision-100%25-6366F1?style=for-the-badge" alt="Precision"/>
  <img src="https://img.shields.io/badge/Tests-87_Passing-22C55E?style=for-the-badge" alt="Tests"/>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License"/>
</p>

# 🛡️ TruthLayer

**Real-time AI hallucination detection. Verify every AI output against source documents before it reaches your users.**

TruthLayer is an invisible verification layer between your AI model and your users. It extracts claims, computes semantic similarity via Amazon Bedrock Titan Embeddings, and runs entity contradiction detection — flagging hallucinations in real time with confidence scores.

> **Live Demo:** [truth-layer.vercel.app](https://truth-layer.vercel.app) &nbsp;|&nbsp; **87 tests passing** &nbsp;|&nbsp; **100% precision** &nbsp;|&nbsp; **Sub-1s latency**

---

## ⚡ Quick Start

### 1. Install the SDK
```bash
pip install truthlayer-sdk
```

### 2. Get an API Key
Visit [truth-layer.vercel.app/get-api-key](https://truth-layer.vercel.app/get-api-key) or generate via CLI:
```bash
python scripts/generate_api_key.py "YourName"
```

### 3. Verify AI Outputs
```python
from truthlayer import TruthLayer

tl = TruthLayer(api_key="tl_your_key", api_url="https://YOUR-API.execute-api.us-east-1.amazonaws.com/prod")

result = tl.verify(
    "Python 3.11 was released in October 2022. It is 25% faster than 3.10.",
    ["Python 3.11 was officially released on October 24, 2022. Performance improvements of up to 25% faster."]
)

for claim in result.claims:
    print(f"  {claim.status}: {claim.text} ({claim.confidence}%)")
    # VERIFIED: Python 3.11 was released in October 2022. (89.4%)
```

### cURL
```bash
curl -X POST https://YOUR-API/prod/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: tl_your_key" \
  -d '{
    "ai_response": "GDPR fines can be up to 4% of annual revenue.",
    "source_documents": ["GDPR non-compliance can lead to fines of up to 4% of annual global turnover."]
  }'
```

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌───────────────────┐
│  Your App    │────▶│  API Gateway │────▶│  Lambda Function  │
│  (SDK/API)   │◀────│  (Auth+CORS) │◀────│  (Verification)   │
└──────────────┘     └──────────────┘     └─────────┬─────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────┐
                     │                              │              │
              ┌──────▼──────┐  ┌────────────┐  ┌───▼────────┐    │
              │   Bedrock   │  │  DynamoDB   │  │  DynamoDB  │    │
              │  Titan V2   │  │  Embeddings │  │  Verif.    │    │
              │ (1024-dim)  │  │  (Cache)    │  │  (Logs)    │    │
              └─────────────┘  └────────────┘  └────────────┘    │
                     │                                            │
              ┌──────▼──────────────────────────────────────┐    │
              │         Entity Contradiction Checker          │    │
              │  (Numbers · Negations · Superlatives · Dates) │    │
              └───────────────────────────────────────────────┘    │
```

### Dual-Signal Verification Pipeline

1. **Claim Extraction** — AI response is split into individual factual claims
2. **Semantic Embedding** — Claims and source chunks embedded via Bedrock Titan V2 (1024-dim)
3. **Cosine Similarity** — Each claim matched to best source chunk
4. **Entity Contradiction Detection** — Catches numerical, negation, and superlative contradictions that embeddings miss
5. **Classification** — `VERIFIED` (≥0.80) · `UNCERTAIN` (≥0.55) · `UNSUPPORTED` (<0.55)

> **Key Innovation:** Unlike single-signal approaches, TruthLayer combines semantic similarity with rule-based entity checking. Embeddings catch meaning mismatches; the entity checker catches when "founded by Elon Musk" should be "founded by Martin Eberhard" — a factual contradiction that embeddings often miss.

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/verify` | Verify AI response against sources |
| `POST` | `/documents` | Upload a source document |
| `GET` | `/documents` | List all documents |
| `GET` | `/documents/{id}` | Get a specific document |
| `DELETE` | `/documents/{id}` | Delete a document |
| `GET` | `/analytics?action=summary` | Get verification statistics |
| `GET` | `/analytics?action=trends&days=7` | Get daily trends |
| `GET` | `/health` | Health check (no auth) |

### POST /verify — Request
```json
{
  "ai_response": "GDPR fines can be up to 4% of annual revenue.",
  "source_documents": ["GDPR non-compliance leads to fines of up to 4% of annual global turnover."],
  "document_ids": ["optional-uuid-from-documents-api"],
  "options": { "verified_threshold": 0.80, "uncertain_threshold": 0.55 }
}
```

### POST /verify — Response
```json
{
  "claims": [
    {
      "text": "GDPR fines can be up to 4% of annual revenue.",
      "status": "VERIFIED",
      "confidence": 87.6,
      "similarity_score": 0.876,
      "matched_source": "GDPR non-compliance leads to fines of up to 4%..."
    }
  ],
  "summary": { "verified": 1, "uncertain": 0, "unsupported": 0 },
  "metadata": {
    "latency_ms": 890,
    "embedding_ms": 720,
    "cache_hits": 2,
    "cache_misses": 1,
    "provider": "BedrockEmbeddingProvider",
    "total_claims": 1
  }
}
```

---

## 🧪 Benchmark Results

| Metric | Value |
|--------|-------|
| **Warm Latency** (live Bedrock) | ~900ms |
| **Cached Latency** (DynamoDB) | ~750ms |
| **Cache Speedup** | 1.4x |
| **Precision** | 100% (zero false positives) |
| **Cache Hit Rate** | 100% on repeated content |
| **Test Suite** | 87 tests passing |

---

## 📂 Project Structure

```
TruthLayer/
├── src/                          # Core verification engine
│   ├── embeddings/               # Embedding providers
│   │   ├── base.py               # Abstract provider interface
│   │   ├── bedrock_provider.py   # AWS Bedrock Titan V2
│   │   └── cached_provider.py    # DynamoDB embedding cache (SHA-256, 7-day TTL)
│   ├── verifier/                 # Verification pipeline
│   │   ├── verifier.py           # Main orchestrator
│   │   ├── claim_extractor.py    # Claim extraction from AI responses
│   │   ├── similarity_engine.py  # Cosine similarity matching
│   │   ├── confidence_scorer.py  # Threshold-based classification
│   │   └── entity_checker.py     # Entity contradiction detection
│   ├── mocks/                    # Mock providers for testing
│   └── config.py                 # Configuration & thresholds
├── lambda/                       # AWS Lambda handlers
│   ├── verify/handler.py         # POST /verify
│   ├── documents/handler.py      # CRUD /documents
│   ├── analytics/handler.py      # GET /analytics
│   └── health/handler.py         # GET /health
├── dashboard/                    # Next.js 16 dashboard (Vercel)
│   └── src/app/
│       ├── page.tsx              # Landing page (12 premium sections)
│       └── dashboard/            # Dashboard, analytics, verify, documents
├── sdk/                          # Client SDKs
│   ├── python/truthlayer.py      # Python SDK (zero dependencies)
│   └── js/truthlayer.ts          # TypeScript SDK (native fetch)
├── integrations/                 # Framework integrations
│   ├── langchain_integration.py  # LangChain wrapper
│   └── fastapi_middleware.py     # FastAPI middleware
├── examples/                     # Integration demos
│   ├── customer_support_chatbot.py
│   ├── document_qa.py
│   └── legal_contract_analyzer.py
├── benchmarks/                   # Performance benchmarks
│   └── run_benchmarks.py         # Latency, precision, cache benchmarks
├── tests/                        # 87 unit tests
├── docs/                         # Technical documentation (11 docs)
├── scripts/                      # Deployment & utility scripts
├── template.yaml                 # AWS SAM infrastructure (IaC)
└── samconfig.toml                # SAM deployment config
```

---

## 🚀 Deployment

### Prerequisites
- AWS CLI configured with credentials
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Bedrock Titan Embeddings V2 enabled in AWS Console
- Python 3.9+, Node.js 18+

### Deploy Backend
```bash
# Copy source into Lambda Layer
python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"

# Build and deploy
sam build
sam deploy
```

### Run Dashboard Locally
```bash
cd dashboard
cp .env.local.example .env.local  # Edit with your API URL and key
npm install && npm run dev         # Opens at http://localhost:3000
```

### Run Tests
```bash
# All 87 unit tests (no AWS credentials needed)
pytest tests/ -v

# With coverage
pytest tests/ --cov=src
```

---

## 🔧 Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `BEDROCK_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock embedding model |
| `BEDROCK_REGION` | `us-east-1` | AWS region |
| `BEDROCK_EMBEDDING_DIMENSION` | `1024` | Embedding vector dimensions |
| `VERIFIED_THRESHOLD` | `0.80` | Min similarity for VERIFIED |
| `UNCERTAIN_THRESHOLD` | `0.55` | Min similarity for UNCERTAIN |

---

## 💡 Why TruthLayer?

| Problem | TruthLayer Solution |
|---------|---------------------|
| AI models hallucinate 15–30% of facts | Real-time dual-signal verification catches them |
| Manual fact-checking doesn't scale | Sub-1s automated pipeline with caching |
| No standard "trust API" exists | Drop-in REST API + Python/TypeScript SDKs |
| Embeddings miss entity contradictions | Entity checker catches numbers, dates, negations |
| Enterprise AI adoption blocked by trust | Invisible layer, zero UX friction |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Verification Engine** | Python 3.9, Amazon Bedrock Titan V2 |
| **Infrastructure** | AWS Lambda, API Gateway, DynamoDB |
| **IaC** | AWS SAM (CloudFormation) |
| **Dashboard** | Next.js 16, TypeScript, Framer Motion |
| **Hosting** | Vercel (frontend), AWS (backend) |
| **SDKs** | Python (stdlib), TypeScript (fetch) |
| **Tests** | pytest (87 tests, MockEmbeddingProvider) |

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📬 Contact

**Prakhar Shukla** — [prakhar230125@gmail.com](mailto:prakhar230125@gmail.com)

---

<p align="center">
  <strong>TruthLayer</strong> — Because AI should be trusted, not blindly followed.
</p>
