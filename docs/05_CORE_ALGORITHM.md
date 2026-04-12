# TruthLayer v2 — Core Algorithm Specification

> **Version:** 2.0 (Five-Signal Engine)  
> **Last Updated:** April 2026  
> **Status:** Production — Deployed on AWS

This document is the authoritative technical specification for TruthLayer's verification pipeline. It supersedes all prior versions.

---

## 1. Pipeline Overview

```
AI Response Text
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Claim Extraction                              │
│  sentence-boundary split → filter → deduplicate         │
└────────────────────────┬────────────────────────────────┘
                         │  claims: List[str]
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 2: Embedding (Signal 1)                          │
│  Bedrock Titan V2 (1024-dim) + DynamoDB cache           │
│  embed_batch([claims, source_chunks])                   │
└────────────────────────┬────────────────────────────────┘
                         │  embeddings: List[List[float]]
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 3: Cosine Similarity Match                       │
│  find_best_match(claim_emb, source_embs) → sim, source  │
└────────────────────────┬────────────────────────────────┘
                         │  similarity: float, matched_source: str
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 4: Entity Contradiction Engine (Signals 2–4)     │
│  compute_alignment_penalty(claim, source)               │
│    ├── Numerical mismatch   (penalty=0.35, CRITICAL)    │
│    ├── Negation / antonym   (penalty=0.38, HIGH)        │
│    └── Temporal mismatch    (penalty=0.35, CRITICAL)    │
└────────────────────────┬────────────────────────────────┘
                         │  adjusted_score = sim × penalty
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 5: Platt Scaling Calibration                     │
│  confidence = σ(12.0724 × score − 6.6398) × 100        │
└────────────────────────┬────────────────────────────────┘
                         │  confidence: float (%)
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 6: Classification                                │
│  score ≥ 0.80 → VERIFIED                               │
│  score ≥ 0.55 → UNCERTAIN                              │
│  score  < 0.55 → UNSUPPORTED                           │
└────────────────────────┬────────────────────────────────┘
                         │  all claims classified
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 7: Intra-Response Consistency (Signal 5)         │
│  ∀ pairs (i,j) i<j: penalty(claim_i, claim_j) both dirs│
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
             API Response (claims + summary +
             internal_consistency + metadata)
```

**Design invariants:**
- `adjusted_score = sim × Π(all_penalties)` — multiplicative compounding
- All stages run on already-loaded claim strings — no redundant I/O after embedding
- Zero external dependencies in Stages 3–7 (stdlib only: `re`, `math`)

---

## 2. Claim Extraction

**File:** `src/verifier/claim_extractor.py`

Claims are extracted using sentence-boundary detection with lightweight factuality filtering. The implementation is deliberately rule-based (no NLP pipeline) to ensure sub-millisecond overhead and zero external dependencies.

```python
# Actual production logic (simplified)
def extract_claims(ai_response: str) -> List[str]:
    # Sentence tokenization (punctuation-based)
    sentences = _split_sentences(ai_response)
    # Filter: keep sentences with at least one content word
    claims = [s.strip() for s in sentences if len(s.strip()) > 10]
    # Deduplicate preserving order
    seen = set()
    return [c for c in claims if not (c in seen or seen.add(c))]
```

**Complexity:** O(n) where n = length of `ai_response`  
**Latency:** <2ms for typical responses

---

## 3. Embedding Generation and Caching (Signal 1)

**Files:** `src/embeddings/bedrock_provider.py`, `src/embeddings/cached_provider.py`

### 3.1 Bedrock Titan V2 Specification

| Parameter | Value |
|-----------|-------|
| Model ID | `amazon.titan-embed-text-v2:0` |
| Dimensions | **1024** (not 1536 — that was v1) |
| Max input | 8,192 tokens |
| Region | `us-east-1` |
| Latency p50 | ~720ms (batch embedding per call) |

```python
# BedrockEmbeddingProvider.embed_batch()
response = bedrock.invoke_model(
    modelId="amazon.titan-embed-text-v2:0",
    body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
)
```

Note: `"normalize": True` ensures returned vectors have unit L2 norm, making cosine similarity equivalent to dot product — required for correctness.

### 3.2 DynamoDB Embedding Cache

**File:** `src/embeddings/cached_provider.py`

Cache key: `SHA-256(text)` — collision-resistant, fixed-length, deterministic.

```
Cache hit path:  DynamoDB GetItem (~15ms) ← 749ms savings vs Bedrock
Cache miss path: Bedrock invoke (~720ms) + DynamoDB PutItem (~5ms)
```

TTL: 7 days (DynamoDB TTL attribute). Non-fatal: cache failures fall through to Bedrock.

### 3.3 Cosine Similarity (stdlib, no numpy)

```python
def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b) if (norm_a and norm_b) else 0.0
```

**No numpy. No scipy. Pure stdlib.**

---

## 4. Entity Contradiction Engine (Signals 2–4)

**File:** `src/verifier/entity_checker.py`

### 4.1 Architecture

`compute_alignment_penalty(claim: str, matched_source: str) -> Tuple[float, Optional[ContradictionEvidence]]`

Returns:
- `(1.0, None)` — no contradiction detected
- `(penalty_product, ContradictionEvidence)` — contradiction detected with structured evidence

Multiple contradictions compound: if signals 2 and 3 both fire, `penalty = 0.35 × 0.38 = 0.133`.

### 4.2 Signal 2 — Numerical Contradiction

**Approach:** Unit-aware `(value, unit)` tuple comparison.

```
Regex: r'(\d+(?:\.\d+)?(?:,\d{3})*)\s*(mg|kg|%|ms|s|min|hour|year|...)'
```

**Anti-false-positive design:** Compares `(42, "mg")` vs `(42, "g")` — different unit → fires. Compares `(400, "mg")` vs `(40, "mg")` — same unit, different value → fires. Substring collision guard: `"1000"` inside `"10000"` is not a match.

```
Penalty: 0.35  (CRITICAL)
```

### 4.3 Signal 3 — Negation and Semantic Antonym

**Three-layer detection:**

**Layer A — S2A vicinity guard:** Prevents false positive on requirement-conditional negation (`"not to exceed"`, `"not less than"`). 3-stage decision tree:
1. Threshold equivalence: `"not exceed 250" ≡ "below 250"` → abort
2. Requirement-conditional: `"must not", "shall not", "do not"` → abort
3. Access-gate: `"not permitted", "not allowed"` → fire if source says permitted

**Layer B — Soft negation anchor scan:** Detects `never`, `no`, `none`, `false` within a 4-token window around extracted entities.

**Layer C — Semantic antonym pairs:** 46 bidirectional pairs:
`permitted↔prohibited`, `safe↔contraindicated`, `required↔optional`, `accept↔reject`, etc.

```
Penalty: 0.38  (HIGH)
```

### 4.4 Signal 4 — Temporal Contradiction

**Calendar year disjointness:**
```python
# Claim has year 2014, source has year 2016 → fire
years_claim  = set(re.findall(r'\b(19|20)\d{2}\b', claim))
years_source = set(re.findall(r'\b(19|20)\d{2}\b', source))
if years_claim and years_source and years_claim.isdisjoint(years_source):
    fire(TEMPORAL_CONTRADICTION)
```

**Duration mismatch** (same temporal unit, different magnitude):
```python
# "24 months" vs "24 years" → fire
# "5 hours" vs "5 minutes" → fire
```

```
Penalty: 0.35  (CRITICAL)
```

### 4.5 ContradictionEvidence

```python
@dataclass(frozen=True)
class ContradictionEvidence:
    signal:          Literal["NUMERICAL_MISMATCH", "S2A_NEGATION_POLARITY",
                             "SEMANTIC_ANTONYM", "SUPERLATIVE_SWAP",
                             "SUPERLATIVE_VS_SPECIFIC", "TEMPORAL_CONTRADICTION"]
    severity:        Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    penalty_applied: float
    claim_fragment:  str
    source_fragment: str
    explanation:     str
```

Frozen (immutable). JSON-serializable via `.to_dict()`. Returned in API response as `contradiction_evidence`.

---

## 5. Platt Scaling Calibration

**File:** `src/verifier/calibration.py`

### 5.1 Formula

```python
def calibrate_confidence_pct(adjusted_similarity: float) -> float:
    A, B = 12.0724, -6.6398
    exponent = -(A * adjusted_similarity + B)
    sigmoid = 1.0 / (1.0 + math.exp(exponent))
    return round(sigmoid * 100, 1)
```

### 5.2 Parameter Derivation

Analytically solved from two benchmark boundary conditions:

```
BC1: σ(A × 0.80 + B) = 0.9533  [measured precision at VERIFIED threshold]
BC2: σ(A × 0.55 + B) = 0.5000  [50% at semantic uncertainty midpoint]

Solving: A = (logit(0.9533)) / (0.80 - 0.55) = 3.0206 / 0.25 = 12.0724
         B = -A × 0.55 = -6.6398
```

### 5.3 Guarantees

- **Monotone:** `∀ x₁ < x₂: σ(A·x₁+B) < σ(A·x₂+B)` — strictly increasing
- **Bounded:** output always in `[0, 100]`
- **Grounded:** confidence at VERIFIED threshold exactly equals benchmark precision
- **Deterministic:** same input → same output, no randomness

---

## 6. Classification

**File:** `src/verifier/confidence_scorer.py`

```
adjusted_score = cosine_similarity × Π(entity_penalties)

adjusted_score >= VERIFIED_THRESHOLD  (0.80)  →  "VERIFIED"    🟢
adjusted_score >= UNCERTAIN_THRESHOLD (0.55)  →  "UNCERTAIN"   🟡
adjusted_score <  UNCERTAIN_THRESHOLD          →  "UNSUPPORTED" 🔴
```

Thresholds are configurable via environment variables. Default values are calibrated to the 300-case adversarial benchmark.

---

## 7. Intra-Response Consistency Check (Signal 5)

**File:** `src/verifier/verifier.py` — `_check_internal_consistency()`

### 7.1 Algorithm

```python
def _check_internal_consistency(claims: List[str]) -> Dict:
    if len(claims) < 2:
        return {"consistent": True, "conflict_count": 0, "conflicts": []}
    
    conflicts = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            # Both directions — entity checker is asymmetric
            penalty_a, ev_a = compute_alignment_penalty(claims[i], claims[j])
            penalty_b, ev_b = compute_alignment_penalty(claims[j], claims[i])
            
            # Choose stronger signal
            if ev_a or ev_b:
                chosen = ev_a if (ev_a and (not ev_b or penalty_a <= penalty_b)) else ev_b
                chosen_penalty = min(filter(None, [penalty_a if ev_a else None,
                                                    penalty_b if ev_b else None]))
                conflicts.append({
                    "claim_a_index": i, "claim_b_index": j,
                    "signal": chosen.signal, "severity": chosen.severity,
                    "explanation": chosen.explanation, "penalty": round(chosen_penalty, 4)
                })
    
    return {"consistent": len(conflicts) == 0,
            "conflict_count": len(conflicts), "conflicts": conflicts}
```

### 7.2 Why Both Directions

`compute_alignment_penalty(x, y)` asks: "does x introduce something not in y?" Running `(claim_i, claim_j)` and `(claim_j, claim_i)` covers both orderings, ensuring all contradiction types are detected regardless of which claim comes first.

### 7.3 Complexity

- Pairs: `n(n-1)/2` — for 5 claims = 10 pairs
- Per pair: 2 × O(m) entity checks where m = text length
- Typical overhead: <2ms total for 5–10 claims

---

## 8. Test Coverage

```bash
pytest tests/ -v
# 286 passed in ~22s
```

| Test File | Cases | What Is Covered |
|-----------|-------|-----------------|
| `test_entity_checker.py` | 157 | All signals, S2A guard, antonyms, temporal |
| `test_verifier.py` | — | End-to-end orchestration, calibration integration |
| `test_calibration.py` | 44 | Sigmoid, boundary conditions, monotonicity |
| `test_mcnemar.py` | 46 | p-value math, contingency table, real 300-case run |
| `test_internal_consistency.py` | 39 | Pairwise, schema, all 3 code paths |
