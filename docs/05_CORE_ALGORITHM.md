# Core Algorithm Specification

## 1. Algorithm Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    TruthLayer Verification Pipeline                       │
│                                                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐    │
│  │ Input   │──▶│ Claim   │──▶│ Embed   │──▶│ Match   │──▶│ Score   │    │
│  │ Parse   │   │ Extract │   │ Claims  │   │ Chunks  │   │ Output  │    │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘    │
│      5ms          15ms          30ms          25ms          5ms          │
│                                                                           │
│                    Total Target: < 100ms                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Claim Extraction Methodology

### 2.1 Algorithm Steps

```python
def extract_claims(ai_response: str) -> List[Claim]:
    """
    Extract atomic, verifiable claims from AI response.
    
    Args:
        ai_response: Raw AI-generated text
        
    Returns:
        List of Claim objects with text and metadata
    """
    # Step 1: Sentence tokenization
    sentences = sent_tokenize(ai_response)
    
    # Step 2: Filter non-factual sentences
    factual_sentences = [s for s in sentences if is_factual(s)]
    
    # Step 3: Split compound claims
    atomic_claims = []
    for sentence in factual_sentences:
        atomic_claims.extend(split_compound_claims(sentence))
    
    # Step 4: Normalize claims
    normalized = [normalize_claim(c) for c in atomic_claims]
    
    # Step 5: Deduplicate
    unique_claims = deduplicate_claims(normalized)
    
    return unique_claims[:MAX_CLAIMS]  # Default: 10
```

### 2.2 Factuality Detection

Claims must contain verifiable facts. Filter out:
- Questions ("What is the revenue?")
- Opinions ("I think the company is doing well")
- Imperatives ("Please review the document")
- Hedged statements ("The revenue might be around $4 billion")

**Factuality Signals:**
| Signal | Weight | Example |
|--------|--------|---------|
| Contains number | +0.3 | "Revenue was $4.2B" |
| Contains date | +0.2 | "Founded in 2019" |
| Contains proper noun | +0.2 | "Microsoft announced" |
| Contains hedge word | -0.4 | "might", "possibly", "around" |
| Is question | -1.0 | Ends with "?" |
| Contains "I think/believe" | -0.5 | Opinion marker |

```python
def is_factual(sentence: str) -> bool:
    score = 0.0
    
    # Positive signals
    if contains_number(sentence): score += 0.3
    if contains_date(sentence): score += 0.2
    if contains_proper_noun(sentence): score += 0.2
    
    # Negative signals
    if sentence.strip().endswith('?'): return False
    if contains_hedge_words(sentence): score -= 0.4
    if contains_opinion_markers(sentence): score -= 0.5
    
    return score >= 0.2  # Threshold
```

### 2.3 Compound Claim Splitting

Split sentences with multiple facts into atomic claims.

**Input:** "The company was founded in 2019 and has 500 employees in 12 countries."

**Output:**
1. "The company was founded in 2019"
2. "The company has 500 employees"
3. "The company operates in 12 countries"

**Splitting Rules:**
- Split on coordinating conjunctions ("and", "but", "or")
- Split on semicolons
- Preserve subject reference across splits
- Maintain numerical precision

---

## 3. Embedding Generation Process

### 3.1 Bedrock Integration

```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def generate_embedding(text: str) -> List[float]:
    """
    Generate 1536-dimensional embedding using Amazon Titan.
    
    Args:
        text: Input text (max 8192 tokens)
        
    Returns:
        List of 1536 float values
    """
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'inputText': text[:8000]  # Token limit safety
        })
    )
    
    result = json.loads(response['body'].read())
    return result['embedding']  # 1536 floats


def batch_generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Batch embedding generation for efficiency.
    Process up to 5 texts per batch to optimize latency.
    """
    embeddings = []
    for text in texts:
        embedding = generate_embedding(text)
        embeddings.append(embedding)
    return embeddings
```

### 3.2 Embedding Specifications

| Parameter | Value |
|-----------|-------|
| Model | amazon.titan-embed-text-v1 |
| Dimensions | 1536 |
| Max Input Tokens | 8,192 |
| Latency (p50) | 25ms |
| Latency (p99) | 80ms |
| Cost | $0.0001 per 1K tokens |

### 3.3 Text Preprocessing

Before embedding generation:
```python
def preprocess_for_embedding(text: str) -> str:
    # Lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters (keep alphanumeric, spaces, basic punctuation)
    text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
    
    # Truncate to token limit
    tokens = text.split()[:1500]  # ~6000 chars safety margin
    
    return ' '.join(tokens)
```

---

## 4. Semantic Similarity Matching

### 4.1 Cosine Similarity Calculation

```python
import numpy as np

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two embeddings.
    
    Returns:
        Similarity score between -1 and 1 (typically 0 to 1 for text)
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)
```

### 4.2 Matching Algorithm

```python
def find_best_match(
    claim_embedding: List[float],
    chunk_embeddings: List[Dict],
    top_k: int = 3
) -> List[MatchResult]:
    """
    Find the best matching document chunks for a claim.
    
    Args:
        claim_embedding: 1536-dim vector for the claim
        chunk_embeddings: List of {chunk_id, embedding, text} dicts
        top_k: Number of top matches to return
        
    Returns:
        List of MatchResult with scores and chunk info
    """
    similarities = []
    
    for chunk in chunk_embeddings:
        score = cosine_similarity(claim_embedding, chunk['embedding'])
        similarities.append({
            'chunk_id': chunk['chunk_id'],
            'text': chunk['text'],
            'score': score
        })
    
    # Sort by score descending
    similarities.sort(key=lambda x: x['score'], reverse=True)
    
    return similarities[:top_k]
```

### 4.3 Optimized Batch Matching

For performance, use vectorized operations:

```python
def batch_match_claims(
    claim_embeddings: np.ndarray,  # Shape: (num_claims, 1536)
    chunk_embeddings: np.ndarray,  # Shape: (num_chunks, 1536)
) -> np.ndarray:
    """
    Vectorized similarity matching using matrix multiplication.
    
    Returns:
        Similarity matrix of shape (num_claims, num_chunks)
    """
    # Normalize embeddings
    claim_norms = np.linalg.norm(claim_embeddings, axis=1, keepdims=True)
    chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    
    claim_normalized = claim_embeddings / claim_norms
    chunk_normalized = chunk_embeddings / chunk_norms
    
    # Matrix multiplication for all similarities at once
    similarity_matrix = np.dot(claim_normalized, chunk_normalized.T)
    
    return similarity_matrix
```

---

## 5. Confidence Scoring Calculation

### 5.1 Score Components

The confidence score combines multiple signals:

```python
def calculate_confidence(
    similarity_score: float,
    claim_specificity: float,
    chunk_coverage: float
) -> float:
    """
    Calculate final confidence score (0.0 to 1.0).
    
    Components:
    - similarity_score: Cosine similarity (0-1)
    - claim_specificity: How specific/verifiable the claim is (0-1)
    - chunk_coverage: What % of claim tokens appear in chunk (0-1)
    """
    weights = {
        'similarity': 0.60,
        'specificity': 0.20,
        'coverage': 0.20
    }
    
    confidence = (
        weights['similarity'] * similarity_score +
        weights['specificity'] * claim_specificity +
        weights['coverage'] * chunk_coverage
    )
    
    return min(1.0, max(0.0, confidence))
```

### 5.2 Claim Specificity Calculation

```python
def calculate_specificity(claim: str) -> float:
    """
    Higher specificity for claims with concrete, verifiable details.
    """
    score = 0.5  # Base score
    
    # Boost for specific elements
    if contains_number(claim): score += 0.2
    if contains_date(claim): score += 0.15
    if contains_percentage(claim): score += 0.15
    if contains_proper_noun(claim): score += 0.1
    
    # Penalize vague claims
    if len(claim.split()) < 5: score -= 0.1
    if contains_vague_words(claim): score -= 0.2
    
    return min(1.0, max(0.0, score))
```

### 5.3 Chunk Coverage Calculation

```python
def calculate_coverage(claim: str, chunk: str) -> float:
    """
    What percentage of claim tokens appear in the matched chunk.
    """
    claim_tokens = set(claim.lower().split())
    chunk_tokens = set(chunk.lower().split())
    
    # Remove stop words
    stop_words = {'the', 'a', 'an', 'is', 'was', 'are', 'were', 'and', 'or'}
    claim_tokens -= stop_words
    
    if not claim_tokens:
        return 0.0
    
    matched = claim_tokens.intersection(chunk_tokens)
    return len(matched) / len(claim_tokens)
```

### 5.4 Verdict Classification

```python
def classify_verdict(confidence: float) -> str:
    """
    Classify claim into verification verdict.
    
    Thresholds:
    - VERIFIED: >= 0.85 (Green)
    - UNCERTAIN: 0.60 - 0.84 (Yellow)  
    - UNSUPPORTED: < 0.60 (Red)
    """
    if confidence >= 0.85:
        return "VERIFIED"
    elif confidence >= 0.60:
        return "UNCERTAIN"
    else:
        return "UNSUPPORTED"
```

### 5.5 Overall Score Aggregation

```python
def aggregate_overall_score(claims: List[ClaimResult]) -> Tuple[float, str]:
    """
    Calculate overall document verification score and verdict.
    """
    if not claims:
        return 0.0, "UNSUPPORTED"
    
    # Weighted average (lower scores weighted more heavily)
    weights = [1.0 / (1.0 + c.confidence) for c in claims]
    total_weight = sum(weights)
    
    weighted_sum = sum(c.confidence * w for c, w in zip(claims, weights))
    overall_score = weighted_sum / total_weight
    
    # Overall verdict based on claim distribution
    verified_count = sum(1 for c in claims if c.verdict == "VERIFIED")
    unsupported_count = sum(1 for c in claims if c.verdict == "UNSUPPORTED")
    
    verified_ratio = verified_count / len(claims)
    unsupported_ratio = unsupported_count / len(claims)
    
    if verified_ratio >= 0.8 and unsupported_ratio == 0:
        return overall_score, "VERIFIED"
    elif unsupported_ratio >= 0.5:
        return overall_score, "UNSUPPORTED"
    else:
        return overall_score, "PARTIALLY_VERIFIED"
```

---

## 6. Performance Optimization Strategies

### 6.1 Embedding Caching

```python
# Cache claim embeddings for repeated verifications
CLAIM_CACHE = {}  # In production: use Redis or DynamoDB

def get_or_create_embedding(text: str) -> List[float]:
    cache_key = hashlib.md5(text.encode()).hexdigest()
    
    if cache_key in CLAIM_CACHE:
        return CLAIM_CACHE[cache_key]
    
    embedding = generate_embedding(text)
    CLAIM_CACHE[cache_key] = embedding
    
    return embedding
```

### 6.2 Chunk Pre-filtering

```python
def prefilter_chunks(
    claim: str,
    chunks: List[Dict],
    top_n: int = 20
) -> List[Dict]:
    """
    Use keyword overlap to pre-filter chunks before embedding comparison.
    Reduces embedding comparisons from 100s to ~20.
    """
    claim_keywords = extract_keywords(claim)
    
    scores = []
    for chunk in chunks:
        chunk_keywords = extract_keywords(chunk['text'])
        overlap = len(claim_keywords.intersection(chunk_keywords))
        scores.append((overlap, chunk))
    
    scores.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scores[:top_n]]
```

### 6.3 Approximate Nearest Neighbor (Future Optimization)

For documents with 1000+ chunks, consider:
- FAISS index for sub-linear similarity search
- Product quantization for memory efficiency
- Inverted file index for clustering

```python
# Future: FAISS integration for large-scale matching
import faiss

def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    dimension = 1536
    index = faiss.IndexFlatIP(dimension)  # Inner product
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    return index

def search_faiss(index: faiss.Index, query: np.ndarray, k: int = 5):
    faiss.normalize_L2(query)
    distances, indices = index.search(query, k)
    return distances, indices
```

### 6.4 Latency Budget Allocation

| Stage | Target | Optimization |
|-------|--------|--------------|
| Input Parsing | 5ms | Regex pre-compiled |
| Claim Extraction | 15ms | Rule-based, no ML |
| Embedding Generation | 30ms | Bedrock Titan optimized |
| Similarity Matching | 25ms | Vectorized NumPy |
| Scoring & Response | 5ms | Pre-computed lookups |
| **Total** | **80ms** | 20ms buffer |
