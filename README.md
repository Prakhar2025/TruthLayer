<p align="center">
  <img src="https://img.shields.io/badge/AWS-Bedrock-FF9900?style=for-the-badge&logo=amazonaws" alt="AWS Bedrock"/>
  <img src="https://img.shields.io/badge/Precision-95.33%25-6366F1?style=for-the-badge" alt="Precision"/>
  <img src="https://img.shields.io/badge/F1_Score-90.79%25-22C55E?style=for-the-badge" alt="F1 Score"/>
  <img src="https://img.shields.io/badge/Tests-286_Passing-22C55E?style=for-the-badge" alt="Tests"/>
  <img src="https://img.shields.io/badge/Cost-$1.50%2Fmo-0EA5E9?style=for-the-badge" alt="Cost"/>
  <img src="https://img.shields.io/badge/Dependencies-Zero-8B5CF6?style=for-the-badge" alt="Zero Dependencies"/>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python" alt="Python"/>
</p>

<h1 align="center">🛡️ TruthLayer</h1>

<p align="center">
  <strong>The first AI verification engine to combine five deterministic signals<br>
  with statistically proven superiority over cosine-only baselines.</strong>
</p>

<p align="center">
  <a href="https://truth-layer.vercel.app">Live Demo</a> &nbsp;|&nbsp;
  <a href="BENCHMARK.md">Research Benchmark</a> &nbsp;|&nbsp;
  <a href="docs/03_API_SPECIFICATION.md">API Reference</a> &nbsp;|&nbsp;
  <a href="sdk/">SDKs</a>
</p>

---

## What TruthLayer Does

TruthLayer is a **production serverless API** that sits between your AI model and your users. Every AI output passes through a five-signal deterministic verification pipeline before it reaches production, catching hallucinations that embedding models fundamentally cannot see.

A single API call extracts claims, embeds them via Amazon Bedrock Titan V2, runs four independent contradiction detectors, applies calibrated confidence scoring, and checks the entire response for internal self-consistency — **all in under one second, at $1.50/month operational cost, with zero external Python dependencies.**

> **AWS 10,000 AIdeas Competition — Top 50 Finalist.** April 2026.

---

## The Five-Signal Engine

TruthLayer's architecture is built on a foundational insight: **no single signal is sufficient**. Cosine similarity catches semantic drift. Entity contradiction catches what embeddings cannot see by design. Platt scaling converts raw scores into calibrated probabilities. McNemar's test provides mathematical proof. Intra-response consistency catches what no source-document checker ever has.

### Signal 1 — Semantic Embedding (Titan V2, 1024-dim)

Claims and source chunks are embedded using **Amazon Bedrock Titan Embeddings V2** (1024-dimensional vectors). Cosine similarity determines topical relevance between each claim and its best-matching source chunk.

> Limitation by design: a model trained on language distribution cannot reliably distinguish "founded in 2003" from "founded in 2013". This is not a bug — it is a fundamental property of distributed representations. Signals 2–5 exist specifically to handle this.

### Signal 2 — Numerical Contradiction Engine

Unit-aware regex detection of value mismatches. Compares `(value, unit)` tuples — not raw substrings — eliminating false positives from substring collisions.

```
Claim:  "The SLA guarantees 99.9% uptime."
Source: "The SLA guarantees 99.99% uptime."
Signal: NUMERICAL_MISMATCH  |  Severity: CRITICAL  |  Penalty: ×0.35
```

### Signal 3 — Negation & Semantic Antonym Detection

Three-layer negation engine:
1. **S2A vicinity guard** — 3-stage decision tree distinguishing predicate negation (`"not permitted"`) from requirement-conditional language (`"not to exceed"`)
2. **Soft negation words** — `never`, `no`, `without`, `false` in a windowed anchor scan
3. **Semantic antonym pairs** — 46+ bidirectional pairs (`permitted↔prohibited`, `safe↔contraindicated`)

```
Claim:  "User data is not shared with third parties."
Source: "User data is shared with third parties."
Signal: S2A_NEGATION_POLARITY  |  Severity: HIGH  |  Penalty: ×0.38
```

### Signal 4 — Temporal Contradiction Engine

Deterministic regex-based detection of calendar year disjointness and relative-duration mismatches.

```
Claim:  "GDPR was adopted in 2014."
Source: "GDPR was adopted in 2016."
Signal: TEMPORAL_CONTRADICTION  |  Severity: CRITICAL  |  Penalty: ×0.35
```

### Signal 5 — Intra-Response Consistency Check *(Novel)*

**No hallucination verifier in existence implements this.** After all claims are verified against source documents, TruthLayer runs `compute_alignment_penalty()` in both directions for every ordered pair of claims `(i, j)` within the same AI response:

```
∀ i < j :  detect_contradiction(claim_i, claim_j)
           detect_contradiction(claim_j, claim_i)
```

An AI could pass every source-document check and still internally contradict itself. Only TruthLayer catches that. The new `internal_consistency` field is present in every API response.

```json
"internal_consistency": {
  "consistent": false,
  "conflict_count": 1,
  "conflicts": [{
    "claim_a_index": 0,
    "claim_b_index": 1,
    "signal": "NUMERICAL_MISMATCH",
    "severity": "CRITICAL",
    "explanation": "Claim states 400mg; other claim states 40mg.",
    "penalty": 0.35
  }]
}
```

---

## Architecture

```mermaid
flowchart TD
    A[Client SDK / cURL] -->|x-api-key header| B[API Gateway\nAuth + Rate Limit]
    B --> C[Lambda: /verify]

    C --> D[Claim Extractor]
    D --> E{Claims?}
    E -->|None| Z1[Return: trivially consistent]
    E -->|1+| F[Bedrock Titan V2\n1024-dim Embeddings]

    F --> G[DynamoDB\nEmbedding Cache\nSHA-256 / 7-day TTL]
    G -->|cache hit| H
    G -->|cache miss → Bedrock| F2[Bedrock API]
    F2 --> H

    H[Cosine Similarity\nSimilarityEngine] --> I

    subgraph "Entity Contradiction Engine — O(n) deterministic"
        I[Signal 2: Numerical\nUnit-aware regex] --> J
        J[Signal 3: Negation\nS2A guard + antonyms] --> K
        K[Signal 4: Temporal\nYear + duration regex]
    end

    K --> L[Adjusted Similarity\nsim × penalty_1 × penalty_2 × ...]
    L --> M[Platt Scaling\nσ(12.07·x − 6.64) × 100]
    M --> N[Classification\n≥0.80 VERIFIED · ≥0.55 UNCERTAIN · else UNSUPPORTED]
    N --> O

    subgraph "Signal 5 — Intra-Response Consistency"
        O[Pairwise claim check\n∀ i < j: penalty both dirs]
    end

    O --> P[API Response\nclaims · summary · internal_consistency · metadata]
    P --> A
```

---

## Statistical Proof of Superiority

TruthLayer's superiority over a cosine-only baseline is not a claim — it is a **statistical proof** computed by McNemar's test on the 300-case adversarial benchmark.

| Metric | TruthLayer (Dual-Signal) | Cosine-Only Baseline |
|--------|--------------------------|----------------------|
| **Accuracy** | 90.33% | 86.67% |
| **Precision** | 95.33% | 82.00% |
| **Recall** | 86.67% | 84.00% |
| **F1 Score** | 90.79% | 83.00% |
| **Avg Latency** | ~925ms | ~925ms |

**McNemar's Test** (300-case benchmark, Yates' continuity correction):

| | Cosine Correct | Cosine Wrong |
|---|---|---|
| **TruthLayer Correct** | a | **b ← entity engine wins** |
| **TruthLayer Wrong** | c | d |

- H₀: b = c (classifiers equivalent)
- H₁: b > c (TruthLayer superior)
- χ² statistic computed — see [BENCHMARK.md](BENCHMARK.md) for exact contingency table
- **p < 0.05 → H₀ rejected** with real Bedrock embeddings

> See [BENCHMARK.md](BENCHMARK.md) for the full research-grade whitepaper: adversarial case design, Platt scaling derivation, and the complete McNemar contingency table.

---

## Calibrated Confidence Scores

Every claim receives a **Platt-scaled probability**, not a rescaled cosine similarity.

```
Before: confidence = similarity_score × 100      ← a rescaled distance, not a probability
After:  confidence = σ(12.07 × sim − 6.64) × 100 ← a calibrated probability
```

Boundary conditions derived analytically from the 300-case benchmark:
- `σ(12.07 × 0.80 − 6.64) = 0.9533` — matches measured precision at VERIFIED threshold
- `σ(12.07 × 0.55 − 6.64) = 0.5000` — 50% at the uncertain midpoint

When TruthLayer reports **95.3% confidence**, it means: of all claims scored at this level on the benchmark, 95.3% are factually correct. This is a **calibrated posterior probability**, not a cosine distance.

---

## Quick Start

### Install the SDK
```bash
pip install truthlayer-sdk
```

### Verify in 3 lines
```python
from truthlayer import TruthLayer

tl = TruthLayer(api_key="tl_your_key")

result = tl.verify(
    ai_response="Python 3.11 was released in October 2022. It is 25% faster than 3.10.",
    source_documents=["Python 3.11 was released on October 24, 2022, with up to 25% performance gains."]
)

for claim in result.claims:
    print(f"{claim.status:12} {claim.confidence:5.1f}%  {claim.text}")

# Output:
# VERIFIED      89.4%  Python 3.11 was released in October 2022.
# VERIFIED      84.2%  It is 25% faster than 3.10.

# Internal consistency
print("Self-consistent:", result.internal_consistency["consistent"])
```

### cURL
```bash
curl -X POST https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: tl_your_key" \
  -d '{
    "ai_response": "GDPR fines can be up to 4% of annual revenue.",
    "source_documents": ["GDPR non-compliance can lead to fines of up to 4% of annual global turnover."]
  }'
```

---

## API Response Schema

```json
{
  "claims": [
    {
      "text": "GDPR fines can be up to 4% of annual revenue.",
      "status": "VERIFIED",
      "confidence": 87.6,
      "similarity_score": 0.8241,
      "matched_source": "GDPR non-compliance can lead to fines of up to 4%...",
      "contradiction_evidence": null
    }
  ],
  "summary": {
    "verified": 1,
    "uncertain": 0,
    "unsupported": 0
  },
  "internal_consistency": {
    "consistent": true,
    "conflict_count": 0,
    "conflicts": []
  },
  "metadata": {
    "latency_ms": 893,
    "embedding_ms": 720,
    "provider": "BedrockEmbeddingProvider",
    "total_claims": 1,
    "source_chunks": 3,
    "cache_hits": 2,
    "cache_misses": 1,
    "calibration_model": "platt_scaling_n300"
  }
}
```

When a contradiction is detected, claim-level `contradiction_evidence` is populated:

```json
"contradiction_evidence": {
  "signal": "NUMERICAL_MISMATCH",
  "severity": "CRITICAL",
  "penalty_applied": 0.35,
  "claim_fragment": "400mg",
  "source_fragment": "40mg",
  "explanation": "Claim states 400mg; source specifies 40mg. Numerical value mismatch."
}
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/verify` | ✅ | Verify AI response against sources |
| `POST` | `/documents` | ✅ | Upload a source document |
| `GET` | `/documents` | ✅ | List all documents |
| `GET` | `/documents/{id}` | ✅ | Get a specific document |
| `DELETE` | `/documents/{id}` | ✅ | Delete a document |
| `GET` | `/analytics?action=summary` | ✅ | Aggregate verification statistics |
| `GET` | `/analytics?action=trends&days=7` | ✅ | Daily trend data |
| `GET` | `/health` | ❌ | Health check (no auth) |

---

## Project Structure

```
TruthLayer/
├── src/                             # Core verification engine (Lambda Layer)
│   ├── embeddings/
│   │   ├── base.py                  # EmbeddingProvider abstract interface
│   │   ├── bedrock_provider.py      # Titan V2 (1024-dim, us-east-1)
│   │   └── cached_provider.py       # DynamoDB cache (SHA-256, 7-day TTL)
│   ├── verifier/
│   │   ├── verifier.py              # Orchestrator + _check_internal_consistency()
│   │   ├── claim_extractor.py       # Sentence-boundary claim splitter
│   │   ├── similarity_engine.py     # Cosine similarity, best-match selection
│   │   ├── confidence_scorer.py     # Threshold classifier (VERIFIED/UNCERTAIN/UNSUPPORTED)
│   │   ├── entity_checker.py        # Signals 2–4: numerical, negation, temporal
│   │   └── calibration.py           # Platt scaling (A=12.07, B=-6.64)
│   ├── stats/
│   │   └── mcnemar.py               # McNemar's test, erfc-based p-value (stdlib only)
│   ├── mocks/
│   │   └── embedding_provider.py    # MockEmbeddingProvider (TF-IDF, no AWS needed)
│   ├── utils/
│   │   ├── auth.py                  # SHA-256 API key validation + rate limiting
│   │   └── text_splitter.py         # Document chunker (500 chars, 50 overlap)
│   └── config.py                    # All thresholds and environment variables
├── lambda/                          # AWS Lambda handlers
│   ├── verify/handler.py            # POST /verify
│   ├── documents/handler.py         # CRUD /documents
│   ├── analytics/handler.py         # GET /analytics
│   └── health/handler.py            # GET /health
├── benchmarks/
│   ├── adversarial_benchmark.py     # 300-case test suite (numerical/negation/superlative)
│   ├── run_benchmarks.py            # Precision/recall/F1 measurement
│   ├── run_mcnemar.py               # McNemar's statistical proof runner
│   └── fit_calibration.py           # Platt scaling reproducibility script
├── tests/                           # 286 pytest unit tests
│   ├── test_entity_checker.py       # Contradiction engine (157 cases)
│   ├── test_calibration.py          # Platt scaling (44 cases)
│   ├── test_mcnemar.py              # Statistical test (46 cases)
│   └── test_internal_consistency.py # Intra-response (39 cases)
├── sdk/
│   ├── python/truthlayer/           # Python SDK (zero dependencies)
│   └── js/truthlayer.ts             # TypeScript SDK (native fetch)
├── integrations/
│   ├── langchain_integration.py     # LangChain output verifier
│   └── fastapi_middleware.py        # FastAPI request middleware
├── dashboard/                       # Next.js 16 (deployed on Vercel)
├── docs/                            # Technical documentation (11 documents)
├── examples/                        # Integration demos (LangChain, FastAPI, legal)
├── BENCHMARK.md                     # Research-grade benchmark whitepaper
├── template.yaml                    # AWS SAM IaC (single source of truth)
└── samconfig.toml                   # SAM deployment configuration
```

---

## Deployment

### Prerequisites
- AWS CLI configured (`us-east-1`, Bedrock enabled)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.9+, Node.js 18+

### Deploy Backend (AWS)
```bash
# Step 1: Sync source into Lambda Layer
python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"

# Step 2: Build and deploy
sam build
sam deploy

# Verify deployment
curl https://YOUR-API.execute-api.us-east-1.amazonaws.com/prod/health
```

### Run Tests (No AWS Needed)
```bash
# All 286 tests — MockEmbeddingProvider, zero AWS calls
pytest tests/ -v

# Statistical proof (offline, deterministic)
python benchmarks/run_mcnemar.py

# Calibration audit (reproduce Platt constants)
python benchmarks/fit_calibration.py
```

### Run Dashboard Locally
```bash
cd dashboard
cp .env.local.example .env.local   # Add your API URL and key
npm install && npm run dev          # http://localhost:3000
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Embedding model |
| `BEDROCK_REGION` | `us-east-1` | AWS region |
| `BEDROCK_EMBEDDING_DIMENSION` | `1024` | Vector dimensions |
| `VERIFIED_THRESHOLD` | `0.80` | VERIFIED classification floor |
| `UNCERTAIN_THRESHOLD` | `0.55` | UNCERTAIN classification floor |
| `DOCUMENTS_TABLE` | `TruthLayerDocuments` | DynamoDB table |
| `EMBEDDINGS_TABLE` | `TruthLayerEmbeddings` | Embedding cache table |
| `APIKEYS_TABLE` | `TruthLayerApiKeys` | API key table |

---

## Why TruthLayer

| Limitation | What TruthLayer Does |
|---|---|
| Cosine similarity is blind to numerical transpositions | Signal 2 catches `$400` vs `$40`, `99.9%` vs `99.99%` |
| Embeddings encode negation into similar vector space | Signal 3 catches `"not permitted"` vs `"permitted"` explicitly |
| No verifier catches self-contradictory AI output | Signal 5 checks every claim pair for internal coherence |
| Reported confidence scores are not probabilities | Platt scaling makes confidence a calibrated posterior |
| "Better performance" claims can't be trusted | McNemar's test provides formal statistical proof |
| High operational cost | $1.50/month on AWS serverless with DynamoDB caching |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Verification Engine** | Python 3.9, stdlib only (re, math, dataclasses) |
| **Embeddings** | Amazon Bedrock Titan Embeddings V2 (1024-dim) |
| **Inference** | AWS Lambda (arm64, 512 MB) |
| **Gateway** | AWS API Gateway (REST, usage plans) |
| **Storage** | AWS DynamoDB (on-demand, 4 tables) |
| **IaC** | AWS SAM (CloudFormation) |
| **Dashboard** | Next.js 16, TypeScript, Framer Motion (Vercel) |
| **SDKs** | Python (stdlib), TypeScript (fetch) |
| **Tests** | pytest, 286 tests, MockEmbeddingProvider |

---

## License

**© 2026 Prakhar Shukla. All Rights Reserved.**  
Provided for portfolio and competition review. See [LICENSE](LICENSE).

**Contact:** [prakhar230125@gmail.com](mailto:prakhar230125@gmail.com)

---

<p align="center">
  <strong>TruthLayer</strong> — Five signals. Mathematical proof. $1.50/month.<br>
  <em>The only AI verification engine with statistically proven superiority.</em>
</p>
