  <img src="https://img.shields.io/badge/AWS-Bedrock-FF9900?style=for-the-badge&logo=amazonaws" alt="AWS Bedrock"/>
  <img src="https://img.shields.io/badge/Latency-%3C500ms-22C55E?style=for-the-badge" alt="Latency"/>
  <img src="https://img.shields.io/badge/Precision-94%25-6366F1?style=for-the-badge" alt="Precision"/>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License"/>
</p>

# 🛡️ TruthLayer

**Real-time AI hallucination firewall. Verify AI outputs against source documents in under 100ms.**

TruthLayer is an invisible trust layer that sits between your AI model and your users, catching hallucinated claims before they cause harm. Built for the [AWS 10,000 AIdeas Competition](https://aws.amazon.com/events/aideas/).

---

## ⚡ Quick Start

### Python (zero dependencies)
```python
from truthlayer import TruthLayer

API_URL = "https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod"
tl = TruthLayer(api_key="tl_xxx", api_url=API_URL)

result = tl.verify(
    "Python 3.11 is 25% faster than 3.10.",
    ["Python 3.11 has up to 25% speedup over 3.10."]
)

print(f"Trust Score: {result.trust_score}%")
print(f"Hallucinations: {result.has_hallucinations}")

for claim in result.claims:
    print(f"  {claim.status}: {claim.text} ({claim.confidence}%)")
```

### JavaScript / TypeScript
```typescript
import { TruthLayer } from 'truthlayer';

const tl = new TruthLayer({ apiKey: 'tl_xxx' });
const result = await tl.verify(
  'The Eiffel Tower was built in 1889.',
  ['The Eiffel Tower was completed in 1889 in Paris.']
);

console.log(`Trust: ${result.trustScore}%`);
console.log(`Hallucinations: ${result.hasHallucinations}`);
```

### cURL
```bash
curl -X POST https://YOUR-API/prod/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: tl_xxx" \
  -d '{
    "ai_response": "The Eiffel Tower was built in 1889.",
    "source_documents": ["The Eiffel Tower was completed in 1889."]
  }'
```

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌───────────────────┐
│  Your App /  │────▶│  API Gateway │────▶│  Lambda: /verify  │
│  SDK Client  │◀────│  (REST API)  │◀────│  (1024MB, 60s)    │
└──────────────┘     └──────────────┘     └─────────┬─────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────┐
                     │                              │              │
              ┌──────▼──────┐  ┌────────────┐  ┌───▼────────┐    │
              │   Bedrock   │  │  DynamoDB   │  │  DynamoDB  │    │
              │  Titan V2   │  │  Documents  │  │ Verif. Log │    │
              │ (Embeddings)│  │             │  │            │    │
              └─────────────┘  └────────────┘  └────────────┘    │
```

### How Verification Works

1. **Claim Extraction** — AI response is split into individual factual claims
2. **Semantic Embedding** — Claims and source chunks are embedded using Bedrock Titan V2 (1024-dim)
3. **Similarity Matching** — Each claim is matched to the best source chunk via cosine similarity
4. **Classification** — Claims are classified as `VERIFIED` (≥0.80), `UNCERTAIN` (≥0.55), or `UNSUPPORTED` (<0.55)

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
| `GET` | `/health` | Health check |

### POST /verify — Request

```json
{
  "ai_response": "The Eiffel Tower was built in 1889 and stands 330m tall.",
  "source_documents": [
    "The Eiffel Tower was completed in 1889 in Paris, France.",
    "The tower is approximately 330 meters in height."
  ]
}
```

### POST /verify — Response

```json
{
  "claims": [
    {
      "text": "The Eiffel Tower was built in 1889",
      "status": "VERIFIED",
      "confidence": 94.2,
      "similarity_score": 0.942,
      "matched_source": "The Eiffel Tower was completed in 1889..."
    }
  ],
  "summary": { "verified": 2, "uncertain": 0, "unsupported": 0 },
  "metadata": {
    "latency_ms": 47.3,
    "embedding_ms": 32.1,
    "provider": "BedrockEmbeddingProvider",
    "total_claims": 2
  }
}
```

---

## 🚀 Deployment

### Prerequisites
- AWS CLI configured with credentials
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- Bedrock Titan Embeddings V2 enabled in AWS Console
- Python 3.12+, Node.js 18+

### Deploy Backend
```bash
# Step 1: Copy src/ into layer
python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"

# Step 2: Build
sam build

# Step 3: Deploy
sam deploy
```

### Generate API Key
```bash
python scripts/generate_api_key.py "YourName"
# Save the generated key — it cannot be retrieved later
```

### Run Dashboard
```bash
cd dashboard
cp .env.local.example .env.local
# Edit .env.local with your API URL and key
npm install
npm run dev
```

### Test Endpoints
```bash
bash scripts/test_api.sh https://YOUR-API/prod tl_your_key
```

---

## 📂 Project Structure

```
TruthLayer/
├── src/                          # Core verification engine
│   ├── embeddings/               # Embedding providers
│   │   ├── base.py               # Abstract provider interface
│   │   └── bedrock_provider.py   # AWS Bedrock Titan V2
│   ├── verifier/                 # Verification pipeline
│   │   ├── verifier.py           # Main orchestrator
│   │   ├── claim_extractor.py    # Claim extraction
│   │   ├── similarity_engine.py  # Cosine similarity
│   │   └── confidence_scorer.py  # Classification
│   ├── mocks/                    # Mock providers for testing
│   └── config.py                 # Configuration
├── lambda/                       # AWS Lambda handlers
│   ├── verify/handler.py         # POST /verify
│   ├── documents/handler.py      # CRUD /documents
│   ├── analytics/handler.py      # GET /analytics
│   └── health/handler.py         # GET /health
├── dashboard/                    # Next.js dashboard
│   └── src/app/
│       ├── page.tsx              # Landing page
│       └── dashboard/            # Dashboard pages
├── sdk/                          # Client SDKs
│   ├── python/truthlayer.py      # Python SDK
│   └── js/truthlayer.ts          # JS/TS SDK
├── scripts/                      # Deployment tools
├── tests/                        # Test suite
├── template.yaml                 # SAM infrastructure
└── samconfig.toml                # Deployment config
```

---

## 🧪 Testing

```bash
# Run unit tests (25 tests)
python -m pytest tests/ -v

# Run with Bedrock integration tests (requires AWS credentials)
python -m pytest tests/ -v --no-header

# Local verification demo
python main.py --mock
```

---

## 🔧 Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `BEDROCK_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock model |
| `BEDROCK_REGION` | `us-east-1` | AWS region |
| `BEDROCK_EMBEDDING_DIMENSION` | `1024` | Embedding dimensions |
| `VERIFIED_THRESHOLD` | `0.80` | Min similarity for VERIFIED |
| `UNCERTAIN_THRESHOLD` | `0.55` | Min similarity for UNCERTAIN |

---

## 💡 Why TruthLayer?

| Problem | TruthLayer Solution |
|---------|-------------------- |
| AI models hallucinate 15-30% of facts | Real-time verification catches them |
| Manual fact-checking is slow | Sub-100ms automated pipeline |
| No standard "trust API" exists | Drop-in REST API + SDKs |
| Enterprise AI adoption is blocked by trust | Invisible layer, zero UX friction |

---

## 🏆 Built For

**AWS 10,000 AIdeas Competition** — Building the trust infrastructure for AI.

Powered by:
- **Amazon Bedrock** — Titan Embeddings V2
- **AWS Lambda** — Serverless compute
- **Amazon DynamoDB** — Document and analytics storage
- **API Gateway** — REST API with CORS
- **Next.js** — Dashboard on Vercel

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>TruthLayer</strong> — Because AI should be trusted, not blindly followed.
</p>
