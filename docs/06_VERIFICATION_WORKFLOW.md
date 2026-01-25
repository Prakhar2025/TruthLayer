# Verification Workflow

## 1. End-to-End Process Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        TRUTHLAYER VERIFICATION WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │ AI Response │
    │   Input     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐     ┌─────────────┐
    │  Validate   │────▶│   Return    │  (Invalid input)
    │   Input     │ NO  │   Error     │
    └──────┬──────┘     └─────────────┘
           │ YES
           ▼
    ┌─────────────┐     ┌─────────────┐
    │   Check     │────▶│   Return    │  (Document not found/processing)
    │  Document   │ NO  │   Error     │
    └──────┬──────┘     └─────────────┘
           │ YES
           ▼
    ┌─────────────┐
    │   Extract   │
    │   Claims    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐     ┌─────────────┐
    │   Claims    │────▶│  Return:    │  (No verifiable claims)
    │   Found?    │ NO  │  UNCERTAIN  │
    └──────┬──────┘     └─────────────┘
           │ YES
           ▼
    ┌─────────────┐
    │  Generate   │
    │  Embeddings │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │    Load     │
    │  Document   │
    │  Chunks     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Compute    │
    │ Similarity  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Calculate  │
    │ Confidence  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Classify   │
    │  Verdicts   │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Aggregate  │
    │   Score     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   Store     │
    │   Result    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   Return    │
    │  Response   │
    └─────────────┘
```

---

## 2. Step-by-Step Process

### Step 1: Input Validation (5ms)

```python
def validate_verification_request(event: dict) -> ValidationResult:
    """
    Validate incoming verification request.
    """
    required_fields = ['document_id', 'ai_response']
    
    # Check required fields
    for field in required_fields:
        if field not in event:
            return ValidationResult(
                valid=False,
                error=f"Missing required field: {field}"
            )
    
    # Validate document_id format
    if not re.match(r'^doc_[a-zA-Z0-9]{16,}$', event['document_id']):
        return ValidationResult(
            valid=False,
            error="Invalid document_id format"
        )
    
    # Validate ai_response length
    if len(event['ai_response']) > 10000:
        return ValidationResult(
            valid=False,
            error="ai_response exceeds 10,000 character limit"
        )
    
    if len(event['ai_response']) < 10:
        return ValidationResult(
            valid=False,
            error="ai_response too short (minimum 10 characters)"
        )
    
    return ValidationResult(valid=True)
```

### Step 2: Document Verification (10ms)

```python
def verify_document_ready(document_id: str) -> DocumentStatus:
    """
    Check if document exists and is ready for verification.
    """
    response = documents_table.get_item(
        Key={'document_id': document_id}
    )
    
    if 'Item' not in response:
        return DocumentStatus(
            exists=False,
            error="DOCUMENT_NOT_FOUND"
        )
    
    doc = response['Item']
    
    if doc['status'] == 'PROCESSING':
        return DocumentStatus(
            exists=True,
            ready=False,
            error="DOCUMENT_STILL_PROCESSING"
        )
    
    if doc['status'] == 'FAILED':
        return DocumentStatus(
            exists=True,
            ready=False,
            error="DOCUMENT_PROCESSING_FAILED"
        )
    
    return DocumentStatus(
        exists=True,
        ready=True,
        chunks_count=doc['chunks_count']
    )
```

### Step 3: Claim Extraction (15ms)

```python
def extract_claims_from_response(ai_response: str) -> List[Claim]:
    """
    Extract atomic, verifiable claims from AI response.
    """
    # Tokenize into sentences
    sentences = sent_tokenize(ai_response)
    
    claims = []
    for sentence in sentences:
        # Skip non-factual sentences
        if not is_factual_sentence(sentence):
            continue
        
        # Split compound claims
        atomic = split_compound_claims(sentence)
        
        for claim_text in atomic:
            # Normalize
            normalized = normalize_claim(claim_text)
            
            if len(normalized) >= 10:  # Minimum claim length
                claims.append(Claim(
                    claim_id=generate_claim_id(),
                    text=normalized,
                    original=claim_text
                ))
    
    # Limit to max claims
    return deduplicate_claims(claims)[:10]
```

### Step 4: Embedding Generation (30ms)

```python
def generate_claim_embeddings(claims: List[Claim]) -> List[ClaimWithEmbedding]:
    """
    Generate embeddings for all claims using Bedrock Titan.
    """
    results = []
    
    for claim in claims:
        # Check cache first
        cached = get_cached_embedding(claim.text)
        if cached:
            embedding = cached
        else:
            embedding = bedrock_generate_embedding(claim.text)
            cache_embedding(claim.text, embedding)
        
        results.append(ClaimWithEmbedding(
            claim=claim,
            embedding=embedding
        ))
    
    return results
```

### Step 5: Load Document Chunks (10ms)

```python
def load_document_embeddings(document_id: str) -> List[ChunkEmbedding]:
    """
    Load pre-computed chunk embeddings from DynamoDB.
    """
    response = embeddings_table.query(
        KeyConditionExpression='document_id = :doc_id',
        ExpressionAttributeValues={':doc_id': document_id}
    )
    
    chunks = []
    for item in response['Items']:
        chunks.append(ChunkEmbedding(
            chunk_id=item['chunk_id'],
            text=item['chunk_text'],
            embedding=item['embedding'],
            index=item['chunk_index']
        ))
    
    return chunks
```

### Step 6: Similarity Matching (25ms)

```python
def match_claims_to_chunks(
    claims: List[ClaimWithEmbedding],
    chunks: List[ChunkEmbedding]
) -> List[ClaimMatch]:
    """
    Compute cosine similarity between each claim and all chunks.
    Return best match for each claim.
    """
    # Convert to numpy arrays for vectorized computation
    claim_vectors = np.array([c.embedding for c in claims])
    chunk_vectors = np.array([c.embedding for c in chunks])
    
    # Normalize vectors
    claim_norms = np.linalg.norm(claim_vectors, axis=1, keepdims=True)
    chunk_norms = np.linalg.norm(chunk_vectors, axis=1, keepdims=True)
    
    claim_normalized = claim_vectors / claim_norms
    chunk_normalized = chunk_vectors / chunk_norms
    
    # Compute similarity matrix
    similarity_matrix = np.dot(claim_normalized, chunk_normalized.T)
    
    # Find best match for each claim
    matches = []
    for i, claim in enumerate(claims):
        best_idx = np.argmax(similarity_matrix[i])
        best_score = similarity_matrix[i][best_idx]
        
        matches.append(ClaimMatch(
            claim=claim.claim,
            best_chunk=chunks[best_idx],
            similarity_score=float(best_score),
            top_3_chunks=get_top_k_matches(similarity_matrix[i], chunks, k=3)
        ))
    
    return matches
```

### Step 7: Confidence Calculation (5ms)

```python
def calculate_claim_confidence(match: ClaimMatch) -> ClaimResult:
    """
    Calculate final confidence score for a claim.
    """
    # Base similarity score (60% weight)
    similarity = match.similarity_score
    
    # Claim specificity (20% weight)
    specificity = calculate_specificity(match.claim.text)
    
    # Token coverage (20% weight)
    coverage = calculate_coverage(
        match.claim.text,
        match.best_chunk.text
    )
    
    # Weighted combination
    confidence = (
        0.60 * similarity +
        0.20 * specificity +
        0.20 * coverage
    )
    
    # Classify verdict
    if confidence >= 0.85:
        verdict = "VERIFIED"
    elif confidence >= 0.60:
        verdict = "UNCERTAIN"
    else:
        verdict = "UNSUPPORTED"
    
    return ClaimResult(
        claim_id=match.claim.claim_id,
        text=match.claim.text,
        confidence=round(confidence, 3),
        verdict=verdict,
        matched_chunk_id=match.best_chunk.chunk_id if confidence >= 0.60 else None,
        matched_text=match.best_chunk.text[:200] if confidence >= 0.60 else None
    )
```

### Step 8: Score Aggregation (2ms)

```python
def aggregate_verification_result(
    claim_results: List[ClaimResult]
) -> VerificationResult:
    """
    Aggregate individual claim results into overall verdict.
    """
    if not claim_results:
        return VerificationResult(
            overall_score=0.0,
            verdict="UNCERTAIN",
            message="No verifiable claims found"
        )
    
    # Calculate weighted average (penalize low scores more)
    scores = [c.confidence for c in claim_results]
    weights = [1.0 / (1.0 + s) for s in scores]  # Lower scores = higher weight
    
    weighted_sum = sum(s * w for s, w in zip(scores, weights))
    overall_score = weighted_sum / sum(weights)
    
    # Count verdicts
    verified = sum(1 for c in claim_results if c.verdict == "VERIFIED")
    unsupported = sum(1 for c in claim_results if c.verdict == "UNSUPPORTED")
    total = len(claim_results)
    
    # Determine overall verdict
    if verified / total >= 0.8 and unsupported == 0:
        verdict = "VERIFIED"
    elif unsupported / total >= 0.5:
        verdict = "UNSUPPORTED"
    else:
        verdict = "PARTIALLY_VERIFIED"
    
    return VerificationResult(
        overall_score=round(overall_score, 3),
        verdict=verdict,
        claims=claim_results
    )
```

---

## 3. Decision Trees

### 3.1 Claim Verdict Classification

```
                        ┌─────────────────┐
                        │ Confidence Score│
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       ┌────────────┐     ┌────────────┐     ┌────────────┐
       │  >= 0.85   │     │ 0.60-0.84  │     │   < 0.60   │
       └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
             │                  │                  │
             ▼                  ▼                  ▼
       ┌────────────┐     ┌────────────┐     ┌────────────┐
       │  VERIFIED  │     │ UNCERTAIN  │     │UNSUPPORTED │
       │   🟢 Green │     │  🟡 Yellow │     │   🔴 Red   │
       └────────────┘     └────────────┘     └────────────┘
```

### 3.2 Overall Verdict Classification

```
                    ┌─────────────────────────┐
                    │  Count Claim Verdicts   │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
  │ 80%+ VERIFIED│        │ 50%+ UNSUP.  │        │   Otherwise  │
  │ 0% UNSUPPORT │        │              │        │              │
  └──────┬───────┘        └──────┬───────┘        └──────┬───────┘
         │                       │                       │
         ▼                       ▼                       ▼
  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
  │   VERIFIED   │        │ UNSUPPORTED  │        │  PARTIALLY   │
  │              │        │              │        │   VERIFIED   │
  └──────────────┘        └──────────────┘        └──────────────┘
```

---

## 4. Edge Case Handling

### 4.1 No Claims Extracted

```python
if not claims:
    return VerificationResponse(
        verification_id=generate_id(),
        overall_score=0.5,
        verdict="UNCERTAIN",
        claims=[],
        metadata={
            "message": "No verifiable factual claims found in the input",
            "suggestion": "Ensure the AI response contains specific facts"
        }
    )
```

### 4.2 Empty Document (No Chunks)

```python
if chunks_count == 0:
    return VerificationResponse(
        verification_id=generate_id(),
        overall_score=0.0,
        verdict="UNSUPPORTED",
        claims=[create_unsupported_claim(c) for c in claims],
        metadata={
            "message": "Document contains no text content",
            "suggestion": "Upload a document with extractable text"
        }
    )
```

### 4.3 Very Short Claims

```python
# Claims under 5 words get reduced confidence
if len(claim.text.split()) < 5:
    confidence *= 0.8  # 20% penalty for vague claims
```

### 4.4 Numeric Mismatch Handling

```python
def check_numeric_match(claim: str, chunk: str) -> float:
    """
    Special handling for numeric claims.
    Numbers must match exactly for high confidence.
    """
    claim_numbers = extract_numbers(claim)
    chunk_numbers = extract_numbers(chunk)
    
    if not claim_numbers:
        return 1.0  # No numbers to check
    
    matched = 0
    for num in claim_numbers:
        if num in chunk_numbers:
            matched += 1
        elif any(is_close_match(num, cn) for cn in chunk_numbers):
            matched += 0.5  # Partial match for close numbers
    
    return matched / len(claim_numbers)
```

---

## 5. Fallback Mechanisms

### 5.1 Bedrock Timeout Fallback

```python
async def generate_embedding_with_fallback(text: str) -> List[float]:
    """
    Fallback to keyword matching if Bedrock times out.
    """
    try:
        async with asyncio.timeout(3.0):  # 3 second timeout
            return await bedrock_generate_embedding(text)
    except asyncio.TimeoutError:
        logger.warning("Bedrock timeout, using fallback")
        return keyword_based_pseudo_embedding(text)
```

### 5.2 DynamoDB Read Fallback

```python
def load_embeddings_with_retry(document_id: str) -> List[ChunkEmbedding]:
    """
    Retry with exponential backoff on DynamoDB errors.
    """
    for attempt in range(3):
        try:
            return load_document_embeddings(document_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            raise
    
    # Final fallback: return empty and mark as uncertain
    return []
```

### 5.3 Partial Result Return

```python
def process_with_partial_results(claims: List[Claim]) -> VerificationResult:
    """
    Return partial results if some claims fail processing.
    """
    results = []
    errors = []
    
    for claim in claims:
        try:
            result = process_single_claim(claim)
            results.append(result)
        except Exception as e:
            errors.append({
                "claim_id": claim.claim_id,
                "error": str(e)
            })
            results.append(ClaimResult(
                claim_id=claim.claim_id,
                text=claim.text,
                confidence=0.5,
                verdict="UNCERTAIN",
                error="Processing failed"
            ))
    
    return VerificationResult(
        claims=results,
        metadata={"partial_errors": errors} if errors else {}
    )
```
