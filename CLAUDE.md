# TruthLayer — AI Context for Claude

## What This Project Is

TruthLayer is a **production serverless API** that verifies AI-generated text against source documents using a five-signal deterministic engine. It sits between AI models and end users, catching hallucinated claims in real time before they reach production.

- **Not a toy.** Deployed on AWS, AWS 10,000 AIdeas Competition — **Top 50 Finalist**.
- **Not embedding-only.** Five independent signals; four deterministic contradiction detectors; one statistical proof.
- **Benchmark:** 95.33% precision, 86.67% recall, 90.79% F1 on 300 adversarial cases. **286 tests passing.**

---

## v2 Architecture (Current)

```
TruthLayer/
├── template.yaml              # SAM IaC — single source of truth for all infra
├── samconfig.toml             # SAM deploy config (stack: truthlayer, region: us-east-1)
├── src/                       # Core verification engine → Lambda Layer
│   ├── config.py              # All thresholds (VERIFIED: 0.80, UNCERTAIN: 0.55)
│   ├── embeddings/
│   │   ├── base.py            # EmbeddingProvider abstract base class
│   │   ├── bedrock_provider.py # Titan V2 (amazon.titan-embed-text-v2:0, 1024-dim)
│   │   └── cached_provider.py # DynamoDB cache wrapper (SHA-256 key, 7-day TTL)
│   ├── verifier/
│   │   ├── verifier.py        # Orchestrator + _check_internal_consistency()
│   │   ├── claim_extractor.py # Splits AI response into individual factual claims
│   │   ├── similarity_engine.py # Cosine similarity, best-match selection
│   │   ├── confidence_scorer.py # VERIFIED/UNCERTAIN/UNSUPPORTED classification
│   │   ├── entity_checker.py  # Signals 2–4: numerical, negation, temporal
│   │   └── calibration.py     # Platt scaling (A=12.0724, B=-6.6398)
│   ├── stats/
│   │   └── mcnemar.py         # McNemar's test, erfc p-value (stdlib only)
│   ├── mocks/
│   │   └── embedding_provider.py # MockEmbeddingProvider (TF-IDF, no AWS)
│   └── utils/
│       ├── auth.py            # SHA-256 API key + rate limiting
│       └── text_splitter.py   # Chunker (MAX_CHUNK=500, OVERLAP=50)
├── lambda/
│   ├── verify/handler.py      # POST /verify
│   ├── documents/handler.py   # CRUD /documents
│   ├── analytics/handler.py   # GET /analytics
│   └── health/handler.py      # GET /health (public, no auth)
├── benchmarks/
│   ├── adversarial_benchmark.py # 300-case dataset (numerical/negation/superlative)
│   ├── run_benchmarks.py      # Precision/recall/F1 measurement
│   ├── run_mcnemar.py         # McNemar's statistical proof runner
│   └── fit_calibration.py     # Platt scaling reproducibility
├── tests/                     # 286 pytest tests (MockEmbeddingProvider, no AWS)
├── sdk/
│   ├── python/truthlayer/     # Python SDK (zero dependencies)
│   └── js/truthlayer.ts       # TypeScript SDK (native fetch)
└── docs/                      # Technical documentation (11 documents)
```

---

## The Five-Signal Pipeline

```
Input AI Response
      │
      ▼
[Signal 1] Bedrock Titan V2 Embeddings (1024-dim) + Cosine Similarity
      │
      ▼
[Signal 2] Numerical Contradiction  (regex, unit-aware)   penalty × 0.35
[Signal 3] Negation / Antonym       (S2A guard + 46 pairs) penalty × 0.38
[Signal 4] Temporal Contradiction   (year disjointness)    penalty × 0.35
      │
      ▼
adjusted_score = cosine_similarity × Π(penalties)
      │
      ▼
[Calibration] Platt Scaling: σ(12.07 × score − 6.64) × 100 → confidence %
      │
      ▼
[Classification] ≥0.80 → VERIFIED | ≥0.55 → UNCERTAIN | else → UNSUPPORTED
      │
      ▼
[Signal 5] Intra-Response Consistency: ∀ pairs (i,j), check both directions
      │
      ▼
API Response: claims + summary + internal_consistency + metadata
```

---

## DynamoDB Tables

| Table | Partition Key | Purpose |
|-------|--------------|---------|
| `TruthLayerApiKeys` | `api_key_hash` (SHA-256) | API key storage — NEVER raw keys |
| `TruthLayerDocuments` | `document_id` | Uploaded source documents |
| `TruthLayerEmbeddings` | `document_id` + `chunk_index` | Cached chunk embeddings |
| `TruthLayerVerifications` | `verification_id` | Verification history |

---

## Critical Rules

### NEVER do this:
- Commit real API keys (`tl_xxx`) to any file
- Commit `dashboard/.env.local`
- Commit anything inside `layer/python/` — gitignored (build artifact)
- Change `src/` without running: `python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"`
- Use `TruthLayerClient` — the class is `TruthLayer`
- Call `verify()` without `source_documents` or `document_ids`
- Add scores directly to confidence without Platt scaling

### ALWAYS do this:
- Copy `src/` to `layer/python/src/` before `sam build`
- Keep `sys.path.insert(0, '/opt/python/python')` and `sys.path.insert(0, '/opt/python')` at top of all Lambda handlers
- Validate API key in every handler EXCEPT `/health`
- Use `api_key_hash` as DynamoDB key (not `key_hash`)
- Check that `content` DynamoDB attribute uses `ExpressionAttributeNames={"#c": "content"}` (reserved word)

---

## Key Commands

```bash
# Deploy to AWS
python -c "import shutil; shutil.copytree('src', 'layer/python/src', dirs_exist_ok=True)"
sam build
sam deploy

# Verify build succeeded (Windows PowerShell — sam build always exits 1)
Test-Path .aws-sam\build\VerifyFunction\handler.py  # Should return True

# Generate a new API key (Windows-safe, no emoji)
python -c "
import hashlib, secrets, time, boto3
raw_key = 'tl_' + secrets.token_urlsafe(32)
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('TruthLayerApiKeys')
table.put_item(Item={'api_key_hash': key_hash, 'owner': 'Name', 'created_at': int(time.time()), 'is_active': True, 'permissions': ['verify', 'documents', 'analytics'], 'rate_limit': 1000, 'usage_count': 0})
with open('tmp_key.txt', 'w') as f: f.write(raw_key)
print('Length: ' + str(len(raw_key)))
"
Get-Content tmp_key.txt; Remove-Item tmp_key.txt

# Run all 286 tests (no AWS needed)
pytest tests/ -v
pytest tests/ --cov=src

# Run statistical proof (offline, deterministic)
python benchmarks/run_mcnemar.py
python benchmarks/run_mcnemar.py --output benchmarks/results/

# Audit calibration constants
python benchmarks/fit_calibration.py

# Run dashboard locally
cd dashboard && npm run dev   # http://localhost:3000

# Test API health
curl https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/health
```

---

## Environment Variables (Lambda — template.yaml Globals)

| Variable | Value | Notes |
|----------|-------|-------|
| `BEDROCK_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Do not change |
| `BEDROCK_REGION` | `us-east-1` | Bedrock only in us-east-1 |
| `BEDROCK_EMBEDDING_DIMENSION` | `1024` | Titan V2 vector dim |
| `DOCUMENTS_TABLE` | `TruthLayerDocuments` | |
| `VERIFICATIONS_TABLE` | `TruthLayerVerifications` | |
| `EMBEDDINGS_TABLE` | `TruthLayerEmbeddings` | |
| `APIKEYS_TABLE` | `TruthLayerApiKeys` | |
| `VERIFIED_THRESHOLD` | `0.80` | Cosine cutoff |
| `UNCERTAIN_THRESHOLD` | `0.55` | Cosine cutoff |

---

## API Reference

### POST /verify — Request
```json
{
  "ai_response": "Text to verify",
  "source_documents": ["Source doc 1"],
  "document_ids": ["uuid-from-documents"],
  "options": { "verified_threshold": 0.80, "uncertain_threshold": 0.55 }
}
```

### POST /verify — Response
```json
{
  "claims": [{
    "text": "...",
    "status": "VERIFIED",
    "confidence": 89.4,
    "similarity_score": 0.8241,
    "matched_source": "...",
    "contradiction_evidence": null
  }],
  "summary": { "verified": 1, "uncertain": 0, "unsupported": 0 },
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

---

## Classification Logic

```
adjusted_similarity = cosine_similarity × Π(entity_checker_penalties)

adjusted_similarity >= 0.80  →  VERIFIED    (calibrated confidence ~95%+)
adjusted_similarity >= 0.55  →  UNCERTAIN   (calibrated confidence ~50–95%)
adjusted_similarity <  0.55  →  UNSUPPORTED (calibrated confidence <50%)
```

---

## Benchmark State (April 2026)

| Metric | Value | Notes |
|--------|-------|-------|
| Precision | **95.33%** | 7 hallucinations escaped (Cat B+C edge cases) |
| Recall | **86.67%** | 22 faithful over-flagged (13 Type A embedding floor) |
| F1 | **90.79%** | |
| Accuracy | **90.33%** | |
| Latency | ~925ms | Avg end-to-end, Bedrock cold |
| Tests | **286** | All passing, zero regressions |
| McNemar p-value | **< 0.001** | χ² > 10.828, extreme significance |

---

## Known Issues & Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Lambda returns SERVICE_UNAVAILABLE on auth | Missing `DynamoDBReadPolicy` for `ApiKeysTable` | Add policy to template.yaml |
| `src/lib/` not committing | `lib/` in root .gitignore caught dashboard path | Changed to `/lib/` (root-only) |
| sam build reports exit 1 | PowerShell stderr noise | Not a real error — check `.aws-sam/build/` |
| `content` in DynamoDB ProjectionExpression | `content` is reserved word | Use `ExpressionAttributeNames={"#c": "content"}` |
| `layer/python/` showing in git status | Files committed before gitignore rule | Run `git rm -r --cached layer/python/` once |
| S2A fires on faithful negation pairs | Blunt negation check missed conditional language | `_s2a_is_genuine_contradiction()` 3-stage decision tree |
| `without` in negation window causes false fire | `"without"` is conditional preposition, not predicate negator | Removed from `_SOFT_NEG_WORDS` |

---

## AWS Budget

Set to **$20/month**. Alerts at 85% ($17) and 100% ($20).  
Email: prakhar230125@gmail.com

## Competition

**AWS 10,000 AIdeas — Top 50 Finalist**  
Article deadline: **April 17, 2026**. Community voting April 17–23. Winners announced April 30.

## Active API Key

Current key is in `dashboard/.env.local` (NOT committed).  
Format: `tl_{43_chars}`. Never commit real keys.

## Architecture Version

**v2.0** — Five-signal engine with Platt calibration, McNemar proof, and intra-response consistency.
