# Database Schema Design

## 1. DynamoDB Tables Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TruthLayer DynamoDB Schema                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ Documents       │  │ Embeddings      │  │ Verifications   │     │
│  │ PK: document_id │  │ PK: document_id │  │ PK: user_id     │     │
│  │                 │  │ SK: chunk_id    │  │ SK: verify_id   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐                           │
│  │ ApiKeys         │  │ Analytics       │                           │
│  │ PK: key_hash    │  │ PK: metric_type │                           │
│  │                 │  │ SK: timestamp   │                           │
│  └─────────────────┘  └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Table: Documents

Stores document metadata and processing status.

### Schema
```json
{
  "TableName": "TruthLayer_Documents",
  "KeySchema": [
    { "AttributeName": "document_id", "KeyType": "HASH" }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "document_id", "AttributeType": "S" },
    { "AttributeName": "user_id", "AttributeType": "S" },
    { "AttributeName": "created_at", "AttributeType": "S" }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "UserDocumentsIndex",
      "KeySchema": [
        { "AttributeName": "user_id", "KeyType": "HASH" },
        { "AttributeName": "created_at", "KeyType": "RANGE" }
      ],
      "Projection": { "ProjectionType": "ALL" }
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### Item Structure
| Attribute | Type | Description |
|-----------|------|-------------|
| document_id | String (PK) | Unique ID: `doc_{ulid}` |
| user_id | String | Owner user ID |
| name | String | User-provided document name |
| description | String | Optional description |
| status | String | PROCESSING, READY, FAILED |
| file_key | String | S3 object key |
| file_size_bytes | Number | Original file size |
| mime_type | String | application/pdf, text/plain, etc. |
| chunks_count | Number | Total chunks generated |
| tags | List<String> | User-defined tags |
| created_at | String | ISO 8601 timestamp |
| processed_at | String | ISO 8601 timestamp |
| error_message | String | Failure reason if status=FAILED |
| ttl | Number | Unix timestamp for expiration (optional) |

### Sample Item
```json
{
  "document_id": "doc_01HQ3KXYZ123ABC",
  "user_id": "usr_456def",
  "name": "Q4 2024 Financial Report",
  "description": "Official quarterly financial statements",
  "status": "READY",
  "file_key": "documents/usr_456def/doc_01HQ3KXYZ123ABC.pdf",
  "file_size_bytes": 2457834,
  "mime_type": "application/pdf",
  "chunks_count": 127,
  "tags": ["finance", "quarterly", "2024"],
  "created_at": "2024-01-15T10:00:00Z",
  "processed_at": "2024-01-15T10:00:45Z"
}
```

---

## 3. Table: Embeddings

Stores pre-computed chunk embeddings for similarity matching.

### Schema
```json
{
  "TableName": "TruthLayer_Embeddings",
  "KeySchema": [
    { "AttributeName": "document_id", "KeyType": "HASH" },
    { "AttributeName": "chunk_id", "KeyType": "RANGE" }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "document_id", "AttributeType": "S" },
    { "AttributeName": "chunk_id", "AttributeType": "S" }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### Item Structure
| Attribute | Type | Description |
|-----------|------|-------------|
| document_id | String (PK) | Parent document ID |
| chunk_id | String (SK) | Unique chunk: `chk_{sequence}` |
| chunk_text | String | Original text (512 tokens max) |
| chunk_index | Number | Position in document (0-indexed) |
| embedding | List<Number> | 1536-dimensional vector |
| token_count | Number | Tokens in this chunk |
| created_at | String | ISO 8601 timestamp |
| ttl | Number | 30-day expiration (Unix timestamp) |

### Sample Item
```json
{
  "document_id": "doc_01HQ3KXYZ123ABC",
  "chunk_id": "chk_0042",
  "chunk_text": "The company reported revenue of $4.2 billion for Q4 2024, representing a 15% year-over-year increase. Operating margins improved to 23.4% driven by cost optimization initiatives...",
  "chunk_index": 42,
  "embedding": [0.0234, -0.0891, 0.1234, ...], // 1536 floats
  "token_count": 487,
  "created_at": "2024-01-15T10:00:30Z",
  "ttl": 1739520000
}
```

---

## 4. Table: Verifications

Stores verification request history and results.

### Schema
```json
{
  "TableName": "TruthLayer_Verifications",
  "KeySchema": [
    { "AttributeName": "user_id", "KeyType": "HASH" },
    { "AttributeName": "verification_id", "KeyType": "RANGE" }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "user_id", "AttributeType": "S" },
    { "AttributeName": "verification_id", "AttributeType": "S" },
    { "AttributeName": "document_id", "AttributeType": "S" },
    { "AttributeName": "created_at", "AttributeType": "S" }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "DocumentVerificationsIndex",
      "KeySchema": [
        { "AttributeName": "document_id", "KeyType": "HASH" },
        { "AttributeName": "created_at", "KeyType": "RANGE" }
      ],
      "Projection": { "ProjectionType": "ALL" }
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### Item Structure
| Attribute | Type | Description |
|-----------|------|-------------|
| user_id | String (PK) | User who made request |
| verification_id | String (SK) | Unique: `ver_{ulid}` |
| document_id | String | Source document verified against |
| ai_response | String | Original AI output (truncated 1000 chars) |
| overall_score | Number | Aggregate confidence (0.0-1.0) |
| verdict | String | VERIFIED, PARTIALLY_VERIFIED, UNSUPPORTED |
| claims | List<Map> | Individual claim results |
| processing_time_ms | Number | Total processing time |
| created_at | String | ISO 8601 timestamp |
| ttl | Number | 90-day expiration |

### Claims Sub-structure
```json
{
  "claim_id": "clm_001",
  "text": "Revenue was $4.2 billion",
  "confidence": 0.94,
  "verdict": "VERIFIED",
  "matched_chunk_id": "chk_0042",
  "matched_text": "reported revenue of $4.2 billion"
}
```

### Sample Item
```json
{
  "user_id": "usr_456def",
  "verification_id": "ver_01HQ4MXYZ789ABC",
  "document_id": "doc_01HQ3KXYZ123ABC",
  "ai_response": "The company reported $4.2 billion in revenue with 23% margins.",
  "overall_score": 0.87,
  "verdict": "VERIFIED",
  "claims": [
    {
      "claim_id": "clm_001",
      "text": "The company reported $4.2 billion in revenue",
      "confidence": 0.94,
      "verdict": "VERIFIED",
      "matched_chunk_id": "chk_0042",
      "matched_text": "reported revenue of $4.2 billion"
    },
    {
      "claim_id": "clm_002",
      "text": "23% margins",
      "confidence": 0.78,
      "verdict": "VERIFIED",
      "matched_chunk_id": "chk_0042",
      "matched_text": "Operating margins improved to 23.4%"
    }
  ],
  "processing_time_ms": 67,
  "created_at": "2024-01-15T14:30:00Z",
  "ttl": 1744023600
}
```

---

## 5. Table: ApiKeys

Stores API key metadata for authentication.

### Schema
```json
{
  "TableName": "TruthLayer_ApiKeys",
  "KeySchema": [
    { "AttributeName": "key_hash", "KeyType": "HASH" }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "key_hash", "AttributeType": "S" },
    { "AttributeName": "user_id", "AttributeType": "S" }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "UserKeysIndex",
      "KeySchema": [
        { "AttributeName": "user_id", "KeyType": "HASH" }
      ],
      "Projection": { "ProjectionType": "ALL" }
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### Item Structure
| Attribute | Type | Description |
|-----------|------|-------------|
| key_hash | String (PK) | SHA-256 hash of API key |
| key_prefix | String | First 8 chars for display: `tlk_live_a1b2...` |
| user_id | String | Owner user ID |
| name | String | User-defined key name |
| tier | String | FREE, DEVELOPER, ENTERPRISE |
| rate_limit_burst | Number | Requests per second (burst) |
| rate_limit_sustained | Number | Requests per second (sustained) |
| monthly_limit | Number | Monthly request cap |
| monthly_usage | Number | Current month usage |
| is_active | Boolean | Key enabled/disabled |
| created_at | String | ISO 8601 timestamp |
| last_used_at | String | Last successful request |
| expires_at | String | Optional expiration |

---

## 6. Table: Analytics

Stores time-series metrics for dashboard.

### Schema
```json
{
  "TableName": "TruthLayer_Analytics",
  "KeySchema": [
    { "AttributeName": "metric_type", "KeyType": "HASH" },
    { "AttributeName": "timestamp", "KeyType": "RANGE" }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "metric_type", "AttributeType": "S" },
    { "AttributeName": "timestamp", "AttributeType": "S" }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### Metric Types
| metric_type | Description |
|-------------|-------------|
| `daily_verifications` | Daily verification counts |
| `daily_verdicts` | Daily verdict breakdown |
| `daily_latency` | Daily latency percentiles |
| `hourly_requests` | Hourly API request counts |

---

## 7. Access Patterns

### Primary Access Patterns
| Pattern | Table | Access Method |
|---------|-------|---------------|
| Get document by ID | Documents | GetItem(document_id) |
| List user's documents | Documents | Query(UserDocumentsIndex, user_id) |
| Get all chunks for document | Embeddings | Query(document_id) |
| Get single chunk | Embeddings | GetItem(document_id, chunk_id) |
| Get verification by ID | Verifications | GetItem(user_id, verification_id) |
| List verifications for document | Verifications | Query(DocumentVerificationsIndex) |
| Validate API key | ApiKeys | GetItem(key_hash) |

### Query Examples

**List user's documents (newest first):**
```python
response = table.query(
    IndexName='UserDocumentsIndex',
    KeyConditionExpression='user_id = :uid',
    ExpressionAttributeValues={':uid': 'usr_456def'},
    ScanIndexForward=False,  # Descending
    Limit=20
)
```

**Get all embeddings for a document:**
```python
response = table.query(
    KeyConditionExpression='document_id = :doc_id',
    ExpressionAttributeValues={':doc_id': 'doc_01HQ3KXYZ123ABC'}
)
embeddings = response['Items']
```

**Get recent verifications for a document:**
```python
response = table.query(
    IndexName='DocumentVerificationsIndex',
    KeyConditionExpression='document_id = :doc_id AND created_at > :since',
    ExpressionAttributeValues={
        ':doc_id': 'doc_01HQ3KXYZ123ABC',
        ':since': '2024-01-01T00:00:00Z'
    },
    ScanIndexForward=False,
    Limit=50
)
```
