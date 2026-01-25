# Integration Guide

## 1. Quick Start

### 1.1 Prerequisites

- API Key from TruthLayer Dashboard
- Python 3.9+ or Node.js 18+
- Source document uploaded to TruthLayer

### 1.2 Basic Integration (5 minutes)

```python
import requests

API_KEY = "tlk_live_your_api_key_here"
BASE_URL = "https://api.truthlayer.io/v1"

# Verify an AI response
response = requests.post(
    f"{BASE_URL}/verify",
    headers={
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "document_id": "doc_abc123",
        "ai_response": "The company was founded in 2019 and has 500 employees."
    }
)

result = response.json()
print(f"Verdict: {result['overall_verdict']}")
print(f"Confidence: {result['overall_score']}")
```

---

## 2. Python SDK

### 2.1 Installation

```bash
pip install truthlayer
```

### 2.2 Configuration

```python
from truthlayer import TruthLayerClient

# Initialize client
client = TruthLayerClient(
    api_key="tlk_live_your_api_key_here",
    base_url="https://api.truthlayer.io/v1",  # Optional
    timeout=30  # Seconds
)
```

### 2.3 Document Upload

```python
# Upload a document
with open("report.pdf", "rb") as f:
    document = client.documents.upload(
        file=f,
        name="Q4 Financial Report",
        description="Official quarterly report",
        tags=["finance", "2024"]
    )

print(f"Document ID: {document.id}")
print(f"Status: {document.status}")

# Wait for processing to complete
document = client.documents.wait_for_ready(
    document_id=document.id,
    timeout=60  # Max wait time in seconds
)
```

### 2.4 Verification

```python
# Basic verification
result = client.verify(
    document_id="doc_abc123",
    ai_response="The company reported $4.2 billion in revenue."
)

print(f"Overall Score: {result.overall_score}")
print(f"Verdict: {result.verdict}")

# Iterate through claims
for claim in result.claims:
    print(f"  - {claim.text}")
    print(f"    Confidence: {claim.confidence}")
    print(f"    Verdict: {claim.verdict}")
    if claim.source_chunk:
        print(f"    Source: {claim.source_chunk[:100]}...")
```

### 2.5 Verification with Options

```python
result = client.verify(
    document_id="doc_abc123",
    ai_response=ai_output,
    options={
        "extract_claims": True,      # Auto-extract claims
        "min_confidence": 0.5,       # Minimum threshold
        "max_claims": 10,            # Limit claims processed
        "include_sources": True      # Include matched chunks
    }
)
```

### 2.6 Async Verification (High Volume)

```python
import asyncio
from truthlayer import AsyncTruthLayerClient

async def verify_multiple():
    client = AsyncTruthLayerClient(api_key="tlk_live_...")
    
    ai_responses = [
        "Response 1...",
        "Response 2...",
        "Response 3..."
    ]
    
    # Verify all concurrently
    tasks = [
        client.verify(
            document_id="doc_abc123",
            ai_response=response
        )
        for response in ai_responses
    ]
    
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results):
        print(f"Response {i+1}: {result.verdict}")

asyncio.run(verify_multiple())
```

### 2.7 Document Management

```python
# List documents
documents = client.documents.list(limit=20)
for doc in documents:
    print(f"{doc.id}: {doc.name} ({doc.status})")

# Get document details
doc = client.documents.get("doc_abc123")
print(f"Chunks: {doc.chunks_count}")
print(f"Created: {doc.created_at}")

# Delete document
client.documents.delete("doc_abc123")
```

### 2.8 Analytics

```python
# Get verification analytics
analytics = client.analytics.summary(period="24h")

print(f"Total Verifications: {analytics.total_verifications}")
print(f"Average Confidence: {analytics.average_confidence}")
print(f"Average Latency: {analytics.average_latency_ms}ms")

# Verdict breakdown
for verdict, count in analytics.verdicts.items():
    print(f"  {verdict}: {count}")
```

---

## 3. JavaScript/TypeScript SDK

### 3.1 Installation

```bash
npm install @truthlayer/sdk
# or
yarn add @truthlayer/sdk
```

### 3.2 Configuration

```typescript
import { TruthLayerClient } from '@truthlayer/sdk';

const client = new TruthLayerClient({
  apiKey: 'tlk_live_your_api_key_here',
  baseUrl: 'https://api.truthlayer.io/v1', // Optional
  timeout: 30000 // Milliseconds
});
```

### 3.3 Document Upload

```typescript
import fs from 'fs';

// Upload a document
const file = fs.createReadStream('report.pdf');
const document = await client.documents.upload({
  file,
  name: 'Q4 Financial Report',
  description: 'Official quarterly report',
  tags: ['finance', '2024']
});

console.log(`Document ID: ${document.id}`);
console.log(`Status: ${document.status}`);

// Wait for processing
const readyDoc = await client.documents.waitForReady(document.id, {
  timeout: 60000 // ms
});
```

### 3.4 Verification

```typescript
// Basic verification
const result = await client.verify({
  documentId: 'doc_abc123',
  aiResponse: 'The company reported $4.2 billion in revenue.'
});

console.log(`Overall Score: ${result.overallScore}`);
console.log(`Verdict: ${result.verdict}`);

// Process claims
result.claims.forEach(claim => {
  console.log(`  - ${claim.text}`);
  console.log(`    Confidence: ${claim.confidence}`);
  console.log(`    Verdict: ${claim.verdict}`);
});
```

### 3.5 React Integration Example

```tsx
import { useState } from 'react';
import { TruthLayerClient, VerificationResult } from '@truthlayer/sdk';

const client = new TruthLayerClient({
  apiKey: process.env.REACT_APP_TRUTHLAYER_API_KEY!
});

function VerificationForm() {
  const [aiResponse, setAiResponse] = useState('');
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    setLoading(true);
    try {
      const verification = await client.verify({
        documentId: 'doc_abc123',
        aiResponse
      });
      setResult(verification);
    } catch (error) {
      console.error('Verification failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea
        value={aiResponse}
        onChange={(e) => setAiResponse(e.target.value)}
        placeholder="Enter AI response to verify..."
      />
      <button onClick={handleVerify} disabled={loading}>
        {loading ? 'Verifying...' : 'Verify'}
      </button>
      
      {result && (
        <div className={`verdict-${result.verdict.toLowerCase()}`}>
          <h3>Result: {result.verdict}</h3>
          <p>Confidence: {(result.overallScore * 100).toFixed(1)}%</p>
          
          <ul>
            {result.claims.map(claim => (
              <li key={claim.claimId} className={`claim-${claim.verdict.toLowerCase()}`}>
                {claim.text} - {claim.verdict}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

## 4. REST API Direct Integration

### 4.1 cURL Examples

**Upload Document:**
```bash
curl -X POST https://api.truthlayer.io/v1/documents \
  -H "x-api-key: tlk_live_abc123xyz" \
  -F "file=@report.pdf" \
  -F "name=Q4 Financial Report" \
  -F "tags=finance,quarterly"
```

**Check Document Status:**
```bash
curl -X GET https://api.truthlayer.io/v1/documents/doc_abc123 \
  -H "x-api-key: tlk_live_abc123xyz"
```

**Verify AI Response:**
```bash
curl -X POST https://api.truthlayer.io/v1/verify \
  -H "x-api-key: tlk_live_abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_abc123",
    "ai_response": "The company was founded in 2019 with 500 employees."
  }'
```

**Get Analytics:**
```bash
curl -X GET "https://api.truthlayer.io/v1/analytics/summary?period=24h" \
  -H "x-api-key: tlk_live_abc123xyz"
```

---

## 5. Configuration Requirements

### 5.1 Environment Variables

```bash
# Required
TRUTHLAYER_API_KEY=tlk_live_your_api_key_here

# Optional
TRUTHLAYER_BASE_URL=https://api.truthlayer.io/v1
TRUTHLAYER_TIMEOUT=30000
TRUTHLAYER_MAX_RETRIES=3
```

### 5.2 Python Configuration File

```python
# config.py
import os

TRUTHLAYER_CONFIG = {
    "api_key": os.environ.get("TRUTHLAYER_API_KEY"),
    "base_url": os.environ.get("TRUTHLAYER_BASE_URL", "https://api.truthlayer.io/v1"),
    "timeout": int(os.environ.get("TRUTHLAYER_TIMEOUT", 30)),
    "max_retries": int(os.environ.get("TRUTHLAYER_MAX_RETRIES", 3)),
    "retry_backoff": 2.0  # Exponential backoff multiplier
}
```

### 5.3 Node.js Configuration

```typescript
// config.ts
export const truthLayerConfig = {
  apiKey: process.env.TRUTHLAYER_API_KEY,
  baseUrl: process.env.TRUTHLAYER_BASE_URL || 'https://api.truthlayer.io/v1',
  timeout: parseInt(process.env.TRUTHLAYER_TIMEOUT || '30000'),
  maxRetries: parseInt(process.env.TRUTHLAYER_MAX_RETRIES || '3')
};
```

---

## 6. Testing Methodology

### 6.1 Unit Testing (Python)

```python
import pytest
from unittest.mock import Mock, patch
from truthlayer import TruthLayerClient

@pytest.fixture
def client():
    return TruthLayerClient(api_key="test_key")

@pytest.fixture
def mock_verification_response():
    return {
        "verification_id": "ver_123",
        "overall_score": 0.87,
        "overall_verdict": "VERIFIED",
        "claims": [
            {
                "claim_id": "clm_001",
                "text": "Founded in 2019",
                "confidence": 0.92,
                "verdict": "VERIFIED"
            }
        ]
    }

def test_verify_success(client, mock_verification_response):
    with patch.object(client, '_request') as mock_request:
        mock_request.return_value = mock_verification_response
        
        result = client.verify(
            document_id="doc_123",
            ai_response="The company was founded in 2019."
        )
        
        assert result.verdict == "VERIFIED"
        assert result.overall_score == 0.87
        assert len(result.claims) == 1

def test_verify_handles_error(client):
    with patch.object(client, '_request') as mock_request:
        mock_request.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            client.verify(
                document_id="doc_123",
                ai_response="Test"
            )
```

### 6.2 Integration Testing

```python
import os
import pytest
from truthlayer import TruthLayerClient

@pytest.fixture(scope="module")
def live_client():
    api_key = os.environ.get("TRUTHLAYER_TEST_API_KEY")
    if not api_key:
        pytest.skip("No test API key configured")
    return TruthLayerClient(api_key=api_key)

@pytest.fixture(scope="module")
def test_document(live_client):
    """Upload a test document for integration tests."""
    with open("tests/fixtures/sample.txt", "rb") as f:
        doc = live_client.documents.upload(
            file=f,
            name="Integration Test Document"
        )
    
    # Wait for processing
    live_client.documents.wait_for_ready(doc.id, timeout=60)
    
    yield doc
    
    # Cleanup
    live_client.documents.delete(doc.id)

def test_end_to_end_verification(live_client, test_document):
    """Test complete verification workflow."""
    result = live_client.verify(
        document_id=test_document.id,
        ai_response="This is a test sentence from the document."
    )
    
    assert result.verification_id is not None
    assert result.overall_score >= 0.0
    assert result.overall_score <= 1.0
    assert result.verdict in ["VERIFIED", "PARTIALLY_VERIFIED", "UNSUPPORTED"]
```

### 6.3 Load Testing

```python
import asyncio
import time
from truthlayer import AsyncTruthLayerClient

async def load_test(requests_count: int = 100):
    client = AsyncTruthLayerClient(api_key="tlk_test_...")
    
    start = time.time()
    
    tasks = [
        client.verify(
            document_id="doc_test",
            ai_response=f"Test claim number {i}."
        )
        for i in range(requests_count)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed = time.time() - start
    success = sum(1 for r in results if not isinstance(r, Exception))
    
    print(f"Completed {success}/{requests_count} requests in {elapsed:.2f}s")
    print(f"Throughput: {success/elapsed:.1f} req/sec")
    print(f"Avg latency: {elapsed/success*1000:.1f}ms")

asyncio.run(load_test(100))
```

### 6.4 Mocking for Development

```python
from truthlayer.mock import MockTruthLayerClient

# Use mock client for development/testing
client = MockTruthLayerClient()

# Configure mock responses
client.set_verification_response(
    document_id="doc_test",
    response={
        "overall_score": 0.9,
        "verdict": "VERIFIED",
        "claims": [...]
    }
)

# Use as normal
result = client.verify(
    document_id="doc_test",
    ai_response="Test input"
)
```
