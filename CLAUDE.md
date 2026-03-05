# TruthLayer — AI Context for Claude

## What This Project Is
TruthLayer is a **production serverless API** that verifies AI-generated outputs against source documents using semantic similarity. It sits between AI models and end users, catching hallucinated claims in real time.

- **Not a toy.** This is a deployed AWS API used in a real competition (AWS 10,000 AIdeas — Top 1,000 Semi-Finalist).
- **Not frontend-heavy.** The core value is the verification engine and REST API. The dashboard is secondary.
- **Goal:** Sub-100ms latency, 94%+ precision, one-line developer integration.

---

## Architecture

```
TruthLayer/
├── template.yaml              # SAM IaC — single source of truth for all infra
├── samconfig.toml             # SAM deploy config (stack: truthlayer, region: us-east-1)
├── src/                       # Core verification engine → goes into Lambda Layer
│   ├── config.py              # All thresholds and env vars (VERIFIED: 0.80, UNCERTAIN: 0.55)
│   ├── embeddings/
│   │   ├── base.py            # EmbeddingProvider abstract base class
│   │   ├── bedrock_provider.py # Titan Embeddings V2 (amazon.titan-embed-text-v2:0, 1024-dim)
│   │   └── cached_provider.py # CachedEmbeddingProvider — DynamoDB cache wrapper (SHA-256)
│   ├── verifier/
│   │   ├── verifier.py        # TruthLayerVerifier — main orchestrator (returns cache_hits/misses)
│   │   ├── claim_extractor.py # Splits AI response into individual factual claims
│   │   ├── similarity_engine.py # Cosine similarity between claim and source vectors
│   │   └── confidence_scorer.py # Maps similarity score → VERIFIED/UNCERTAIN/UNSUPPORTED
│   ├── mocks/
│   │   └── embedding_provider.py # MockEmbeddingProvider (TF-IDF, no AWS needed for tests)
│   └── utils/
│       ├── auth.py            # API key: SHA-256 hash → DynamoDB + rate limit enforcement
│       └── text_splitter.py   # Chunk documents into MAX_CHUNK_SIZE=500, OVERLAP=50
├── lambda/                    # Lambda function handlers
│   ├── verify/handler.py      # POST /verify — supports source_documents AND document_ids
│   ├── documents/handler.py   # GET/POST/DELETE /documents
│   ├── analytics/handler.py   # GET /analytics
│   └── health/handler.py      # GET /health (no auth, public)
├── layer/                     # Lambda Layer build directory (GITIGNORED — auto-generated)
│   └── python/src/            # src/ is copied here before sam build
├── examples/                  # Integration demo scripts
│   ├── customer_support_chatbot.py  # Policy verification demo
│   ├── document_qa.py               # Upload-by-ID verification flow
│   └── legal_contract_analyzer.py  # Contract hallucination risk scoring
├── sdk/
│   ├── python/truthlayer.py   # Python SDK: verify(), upload/get/list/delete_document()
│   └── js/truthlayer.ts       # TypeScript SDK (native fetch)
├── dashboard/                 # Next.js 16 dashboard (deployed to Vercel)
│   └── src/
│       ├── app/               # App Router pages
│       └── lib/api.ts         # Dashboard API client
├── scripts/
│   ├── generate_api_key.py    # Creates tl_{token_urlsafe(32)}, stores SHA-256 in DynamoDB
│   ├── deploy.py              # Build + deploy orchestrator
│   └── test_api.sh            # End-to-end API test script
└── tests/                     # 32 pytest unit tests (MockEmbeddingProvider, no AWS needed)
```

---

## DynamoDB Tables

| Table | Partition Key | Purpose |
|-------|--------------|---------|
| `TruthLayerApiKeys` | `api_key_hash` (SHA-256) | API key storage — NEVER store raw keys |
| `TruthLayerDocuments` | `document_id` | Uploaded source documents |
| `TruthLayerEmbeddings` | `document_id` + `chunk_index` | Cached chunk embeddings |
| `TruthLayerVerifications` | `verification_id` | Verification history for analytics |

---

## Critical Rules

### NEVER do this:
- Commit real API keys (`tl_xxx`) to any file
- Commit `dashboard/.env.local`
- Commit anything inside `layer/python/` — it's gitignored (build artifact)
- Change `src/` without also running: `python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"`
- Add `--use-container` or `--guided` to sam commands
- Use `TruthLayerClient` — the class is `TruthLayer`
- Call `verify()` without either `source_documents` or `document_ids`

### ALWAYS do this:
- Copy `src/` to `layer/python/src/` before `sam build`
- Keep `sys.path.insert(0, '/opt/python/python')` and `sys.path.insert(0, '/opt/python')` at top of Lambda handlers
- Validate API keys in every handler EXCEPT `/health`
- Use `api_key_hash` as DynamoDB key (not `key_hash`)

---

## Key Commands

```bash
# Deploy to AWS
python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"
sam build
sam deploy

# Generate a new API key
python scripts/generate_api_key.py "OwnerName"

# Run all 32 unit tests (no AWS needed)
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src

# Run dashboard locally
cd dashboard && npm run dev

# Test API health
curl https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/health

# Run integration demos (set env vars first)
export TRUTHLAYER_API_URL=https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod
export TRUTHLAYER_API_KEY=tl_your_key
python examples/legal_contract_analyzer.py
python examples/customer_support_chatbot.py
python examples/document_qa.py
```

---

## Environment Variables (Lambda — set in template.yaml Globals)

| Variable | Value | Notes |
|----------|-------|-------|
| `BEDROCK_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Do not change |
| `BEDROCK_REGION` | `us-east-1` | Bedrock only in us-east-1 |
| `BEDROCK_EMBEDDING_DIMENSION` | `1024` | Vec dimension for Titan V2 |
| `DOCUMENTS_TABLE` | `TruthLayerDocuments` | |
| `VERIFICATIONS_TABLE` | `TruthLayerVerifications` | |
| `EMBEDDINGS_TABLE` | `TruthLayerEmbeddings` | |
| `APIKEYS_TABLE` | `TruthLayerApiKeys` | |
| `VERIFIED_THRESHOLD` | `0.80` | Cosine similarity cutoff |
| `UNCERTAIN_THRESHOLD` | `0.55` | Cosine similarity cutoff |

---

## API Reference

### POST /verify
```json
{
  "ai_response": "Text to verify",
  "source_documents": ["Source doc 1"],   // optional if document_ids provided
  "document_ids": ["uuid-from-documents"], // optional if source_documents provided
  "options": { "verified_threshold": 0.80, "uncertain_threshold": 0.55 }
}
```
Returns: `claims[]` with `status`, `confidence`, `similarity_score`, `matched_source`
+ `summary` + `metadata` (includes `cache_hits`, `cache_misses`, `latency_ms`).

Response metadata fields:
- `cache_hits` — how many embeddings came from DynamoDB cache
- `cache_misses` — how many required a Bedrock API call
- `embedding_ms` — time spent on embeddings only
- `latency_ms` — total verification time

### POST /documents
Upload a source document. Returns `document_id` for future reference.

### GET /health
Public endpoint. No API key required.

### All other endpoints
Require `x-api-key: tl_xxx` header.

---

## Classification Logic
```
similarity_score >= VERIFIED_THRESHOLD (0.80)   → VERIFIED   🟢
similarity_score >= UNCERTAIN_THRESHOLD (0.55)  → UNCERTAIN  🟡
similarity_score < UNCERTAIN_THRESHOLD           → UNSUPPORTED 🔴
```

---

## AWS Budget Alert
Set to **$20/month** — alerts at 85% ($17) and 100% ($20) and forecasted 100%.
Email: prakhar230125@gmail.com

## What's Done (Production-Ready)
1. **Embedding caching** — `CachedEmbeddingProvider` wraps Bedrock with DynamoDB cache
   - SHA-256 text hash as key, 7-day TTL, non-fatal cache failures
   - Response includes `cache_hits`/`cache_misses` in metadata
2. **Document ID in /verify** — pass `document_ids` instead of raw text
   - Resolves content from `TruthLayerDocuments`, merges with inline sources
3. **Rate limiting** — `usage_count >= rate_limit` returns 429 with `Retry-After`
   - Atomic DynamoDB UpdateItem increment on every valid request
4. **3 integration demos** — `examples/` directory
5. **Python SDK** — `verify(document_ids=...)`, `upload_document()`, `delete_document()`
6. **32 tests passing** — full regression suite

---

## Tech Stack
- **Runtime:** Python 3.9 (Lambda) — upgrade to 3.12 planned
- **IaC:** AWS SAM (CloudFormation)
- **Embeddings:** Amazon Bedrock Titan Embeddings V2
- **Storage:** DynamoDB (on-demand billing)
- **Dashboard:** Next.js 16 + Turbopack (Vercel)
- **SDKs:** Python (stdlib only), TypeScript (fetch only)
- **Tests:** pytest + MockEmbeddingProvider (no AWS needed)
- **Competition:** AWS 10,000 AIdeas — Top 1,000 Semi-Finalist, deadline March 13 2026
