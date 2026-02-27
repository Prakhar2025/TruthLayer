# API Specification

## 1. Base Configuration

```
Base URL: https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod
Content-Type: application/json
Authentication: API Key (x-api-key header)
Rate Limit: Serverless auto-scaling (Lambda concurrency limits apply)
```

---

## 2. REST Endpoints

### 2.1 POST /verify

Verify AI-generated content against source documents.

**Request:**
```json
{
  "ai_response": "The company was founded in 2019 and has 500 employees.",
  "source_documents": [
    "Founded in 2019, the company currently employs over 500 staff.",
    "The company was established in San Francisco in 2019."
  ]
}
```

**Response (200 OK):**
```json
{
  "verification_id": "ver_xyz789",
  "document_id": "doc_abc123",
  "overall_score": 0.78,
  "overall_verdict": "PARTIALLY_VERIFIED",
  "claims": [
    {
      "claim_id": "clm_001",
      "text": "The company was founded in 2019",
      "confidence": 0.92,
      "verdict": "VERIFIED",
      "source_chunk": "Founded in 2019, the company...",
      "chunk_id": "chk_045"
    },
    {
      "claim_id": "clm_002", 
      "text": "has 500 employees",
      "confidence": 0.45,
      "verdict": "UNSUPPORTED",
      "source_chunk": null,
      "chunk_id": null
    }
  ],
  "metadata": {
    "processing_time_ms": 87,
    "claims_extracted": 2,
    "chunks_searched": 45
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Curl Example:**
```bash
curl -X POST https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: tl_your_api_key" \
  -d '{
    "ai_response": "The company was founded in 2019.",
    "source_documents": ["Founded in 2019, the company currently employs over 500 staff."]
  }'
```

---

### 2.2 POST /documents

Upload a source document for verification.

**Request (multipart/form-data):**
```
Content-Type: multipart/form-data

file: [binary file data]
name: "Company Overview Q4 2024"
description: "Official company documentation"
tags: ["finance", "quarterly", "2024"]
```

**Response (201 Created):**
```json
{
  "document_id": "doc_abc123",
  "name": "Company Overview Q4 2024",
  "status": "PROCESSING",
  "file_size_bytes": 245678,
  "mime_type": "application/pdf",
  "chunks_count": 0,
  "created_at": "2024-01-15T10:00:00Z",
  "processing_eta_seconds": 30
}
```

**Curl Example:**
```bash
curl -X POST https://api.truthlayer.io/v1/documents \
  -H "x-api-key: tlk_live_abc123xyz" \
  -F "file=@company_overview.pdf" \
  -F "name=Company Overview Q4 2024" \
  -F "tags=finance,quarterly"
```

---

### 2.3 GET /documents/{document_id}

Retrieve document metadata and processing status.

**Response (200 OK):**
```json
{
  "document_id": "doc_abc123",
  "name": "Company Overview Q4 2024",
  "status": "READY",
  "file_size_bytes": 245678,
  "mime_type": "application/pdf",
  "chunks_count": 45,
  "embeddings_generated": true,
  "created_at": "2024-01-15T10:00:00Z",
  "processed_at": "2024-01-15T10:00:28Z"
}
```

---

### 2.4 GET /documents

List all uploaded documents.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 20 | Max items (1-100) |
| cursor | string | null | Pagination cursor |
| status | string | null | Filter: PROCESSING, READY, FAILED |

**Response (200 OK):**
```json
{
  "documents": [
    {
      "document_id": "doc_abc123",
      "name": "Company Overview Q4 2024",
      "status": "READY",
      "chunks_count": 45,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiZG9jXzEyMyJ9",
    "has_more": true
  }
}
```

---

### 2.5 DELETE /documents/{document_id}

Delete a document and its embeddings.

**Response (204 No Content)**

---

### 2.6 GET /analytics/summary

Get verification analytics summary.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| period | string | 24h | Time window: 1h, 24h, 7d, 30d |

**Response (200 OK):**
```json
{
  "period": "24h",
  "total_verifications": 1247,
  "verdicts": {
    "VERIFIED": 823,
    "PARTIALLY_VERIFIED": 312,
    "UNSUPPORTED": 112
  },
  "average_confidence": 0.76,
  "average_latency_ms": 72,
  "claims_processed": 4521,
  "top_documents": [
    {"document_id": "doc_abc123", "verifications": 234}
  ]
}
```

---

### 2.7 GET /analytics/verifications

Get detailed verification history.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 50 | Max items (1-100) |
| cursor | string | null | Pagination cursor |
| document_id | string | null | Filter by document |
| verdict | string | null | Filter by verdict |

**Response (200 OK):**
```json
{
  "verifications": [
    {
      "verification_id": "ver_xyz789",
      "document_id": "doc_abc123",
      "overall_score": 0.78,
      "verdict": "PARTIALLY_VERIFIED",
      "claims_count": 2,
      "processing_time_ms": 87,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoidmVyXzc4OSJ9",
    "has_more": true
  }
}
```

---

## 3. Authentication

### API Key Structure
```
Format: tl_{32_char_random}
Example: tl_eX1gQKMZW5_ooax2OCl0G81oj7rkntPFR37SHg05mXk

Generate a key:
  python scripts/generate_api_key.py "YourName"
```

### Authentication Flow
```
┌──────────┐    ┌─────────────┐    ┌────────────────┐
│  Client  │───▶│ API Gateway │───▶│ API Key        │
│          │    │             │    │ Validator      │
└──────────┘    └─────────────┘    └────────────────┘
                                           │
                      ┌────────────────────┼────────────────────┐
                      ▼                    ▼                    ▼
               ┌─────────────┐     ┌─────────────┐      ┌─────────────┐
               │ Valid Key   │     │ Invalid Key │      │ Missing Key │
               │ → Continue  │     │ → 401 Error │      │ → 401 Error │
               └─────────────┘     └─────────────┘      └─────────────┘
```

### Key Storage
- Keys stored in DynamoDB `ApiKeys` table
- Hashed using SHA-256 before storage
- Associated with user_id and rate limit tier

---

## 4. Rate Limiting

### Limits by Tier
| Tier | Burst | Sustained | Monthly |
|------|-------|-----------|---------|
| Free | 10/sec | 5/sec | 10,000 |
| Developer | 100/sec | 50/sec | 100,000 |
| Enterprise | 1000/sec | 500/sec | Unlimited |

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1705312200
```

### Rate Limit Exceeded (429)
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please retry after 60 seconds.",
    "retry_after": 60
  }
}
```

---

## 5. Error Handling

### Error Response Schema
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {},
    "request_id": "req_abc123"
  }
}
```

### Error Codes
| HTTP | Code | Description |
|------|------|-------------|
| 400 | INVALID_REQUEST | Malformed JSON or missing required fields |
| 400 | INVALID_DOCUMENT_ID | Document ID format invalid |
| 401 | UNAUTHORIZED | Missing or invalid API key |
| 403 | FORBIDDEN | API key lacks permission |
| 404 | DOCUMENT_NOT_FOUND | Document does not exist |
| 413 | FILE_TOO_LARGE | Upload exceeds 10MB limit |
| 415 | UNSUPPORTED_MEDIA | File type not supported |
| 422 | DOCUMENT_NOT_READY | Document still processing |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |
| 503 | SERVICE_UNAVAILABLE | Bedrock or DynamoDB unavailable |

### Example Error Response
```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The document 'doc_invalid' does not exist.",
    "details": {
      "document_id": "doc_invalid"
    },
    "request_id": "req_1705312200_abc"
  }
}
```
