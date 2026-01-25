# System Architecture Document

## 1. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT LAYER                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                  │
│  │   Web Dashboard │    │   REST Client   │    │   SDK (Py/JS)   │                  │
│  │   (React SPA)   │    │   (curl/REST)   │    │                 │                  │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘                  │
└───────────┼──────────────────────┼──────────────────────┼───────────────────────────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY LAYER                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Amazon API Gateway (REST API)                            │    │
│  │  • Rate Limiting: 100 req/sec burst, 50 req/sec sustained                   │    │
│  │  • CORS enabled for dashboard origin                                         │    │
│  │  • API Key authentication                                                    │    │
│  │  • Request validation                                                        │    │
│  └─────────────────────────────────────────────────┬───────────────────────────┘    │
└────────────────────────────────────────────────────┼────────────────────────────────┘
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                             COMPUTE LAYER (Lambda)                                   │
│                                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ Verification     │  │ Document         │  │ Analytics        │                   │
│  │ Lambda           │  │ Processor        │  │ Lambda           │                   │
│  │ • 512MB RAM      │  │ Lambda           │  │ • 256MB RAM      │                   │
│  │ • 10s timeout    │  │ • 1024MB RAM     │  │ • 5s timeout     │                   │
│  │ • Python 3.11    │  │ • 30s timeout    │  │ • Python 3.11    │                   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘                   │
│           │                     │                     │                              │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AI/ML LAYER                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                     Amazon Bedrock                                           │    │
│  │  • Model: amazon.titan-embed-text-v1 (embedding generation)                 │    │
│  │  • Dimension: 1536-dimensional vectors                                       │    │
│  │  • Max tokens: 8,192 per request                                            │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                              │
│                                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ DynamoDB         │  │ DynamoDB         │  │ Amazon S3        │                   │
│  │ (Verifications)  │  │ (Documents)      │  │ (Source Files)   │                   │
│  │ • On-demand      │  │ • On-demand      │  │ • Standard tier  │                   │
│  │ • GSI for queries│  │ • GSI for lookup │  │ • 5GB Free Tier  │                   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘                   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                    DynamoDB (Embeddings Cache)                               │    │
│  │  • Stores pre-computed document chunk embeddings                            │    │
│  │  • Key: document_id + chunk_id                                              │    │
│  │  • TTL: 30 days                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 API Gateway
| Responsibility | Details |
|----------------|---------|
| Request Routing | Routes `/verify`, `/documents`, `/analytics` endpoints |
| Authentication | API Key validation via x-api-key header |
| Rate Limiting | 100 requests/second burst, 50 sustained |
| Request Validation | JSON schema validation before Lambda invocation |
| CORS | Allows dashboard domain, preflight caching 300s |

### 2.2 Verification Lambda
| Responsibility | Details |
|----------------|---------|
| Claim Extraction | Parses AI response into atomic claims |
| Embedding Generation | Calls Bedrock for claim embeddings |
| Similarity Matching | Cosine similarity against document embeddings |
| Confidence Scoring | Calculates verification confidence (0-100) |
| Response Assembly | Returns structured verification result |

### 2.3 Document Processor Lambda
| Responsibility | Details |
|----------------|---------|
| File Parsing | Extracts text from PDF, DOCX, TXT, MD |
| Chunking | Splits documents into 512-token overlapping chunks |
| Embedding Generation | Batch embedding via Bedrock |
| Storage | Saves embeddings to DynamoDB, files to S3 |

### 2.4 Analytics Lambda
| Responsibility | Details |
|----------------|---------|
| Metrics Aggregation | Computes verification stats per time window |
| Dashboard Data | Returns formatted data for visualization |
| Usage Tracking | Monitors API usage against Free Tier limits |

---

## 3. Data Flow Diagrams

### 3.1 Verification Request Flow

```
┌──────────┐    ┌─────────────┐    ┌────────────────┐    ┌──────────┐    ┌──────────────┐
│  Client  │───▶│ API Gateway │───▶│ Verification   │───▶│ Bedrock  │───▶│ Return       │
│          │    │             │    │ Lambda         │    │ Embeddings│    │ Embeddings   │
└──────────┘    └─────────────┘    └────────────────┘    └──────────┘    └──────────────┘
                                           │                                     │
                                           ▼                                     │
                                   ┌───────────────┐                             │
                                   │ DynamoDB      │◀────────────────────────────┘
                                   │ (Embeddings)  │
                                   └───────────────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Cosine        │
                                   │ Similarity    │
                                   │ Calculation   │
                                   └───────────────┘
                                           │
                                           ▼
                                   ┌───────────────┐    ┌──────────────┐
                                   │ Confidence    │───▶│ Return JSON  │
                                   │ Scoring       │    │ Response     │
                                   └───────────────┘    └──────────────┘
```

**Step-by-step flow:**
1. **Client** sends POST to `/verify` with `{ document_id, ai_response }`
2. **API Gateway** validates API key, enforces rate limit, validates JSON schema
3. **Verification Lambda** receives event, extracts claims from `ai_response`
4. **Bedrock** generates 1536-dim embeddings for each claim (batched)
5. **DynamoDB** returns pre-computed document chunk embeddings
6. **Lambda** computes cosine similarity for each claim vs all chunks
7. **Confidence scoring** assigns GREEN (≥0.85), YELLOW (0.60-0.84), RED (<0.60)
8. **Response** returns to client with per-claim scores and overall verdict

### 3.2 Document Upload Flow

```
┌──────────┐    ┌─────────────┐    ┌────────────────┐    ┌──────────┐
│  Client  │───▶│ API Gateway │───▶│ Document       │───▶│ S3       │
│  (File)  │    │             │    │ Processor      │    │ (Store)  │
└──────────┘    └─────────────┘    └────────────────┘    └──────────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Text          │
                                   │ Extraction    │
                                   └───────────────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Chunking      │
                                   │ (512 tokens)  │
                                   └───────────────┘
                                           │
                                           ▼
                                   ┌───────────────┐    ┌──────────────┐
                                   │ Bedrock       │───▶│ DynamoDB     │
                                   │ Embeddings    │    │ (Store)      │
                                   └───────────────┘    └──────────────┘
```

---

## 4. Technology Stack Justification

| Layer | Technology | Justification |
|-------|------------|---------------|
| **API** | API Gateway REST | Native AWS integration, built-in throttling, Free Tier: 1M requests/month |
| **Compute** | Lambda (Python 3.11) | Zero cold-start optimization, Free Tier: 1M requests + 400,000 GB-seconds |
| **Embeddings** | Amazon Bedrock Titan | Low latency (<50ms), 1536 dimensions, no infrastructure management |
| **Database** | DynamoDB On-Demand | Single-digit ms latency, Free Tier: 25GB storage, 25 RCU/WCU |
| **Storage** | S3 Standard | Free Tier: 5GB, lifecycle rules for cost optimization |
| **Frontend** | React 18 + Vite | Fast builds, small bundle, WebSocket support |

---

## 5. AWS Service Selection Rationale

### Why Bedrock over SageMaker?
- **Latency**: Bedrock Titan averages 30-50ms per embedding request
- **Cost**: Pay-per-token vs provisioned endpoints
- **Simplicity**: No model deployment, scaling, or infrastructure management
- **Free Tier Impact**: No persistent compute costs

### Why DynamoDB over Aurora Serverless?
- **Latency**: Single-digit ms vs 25-50ms for Aurora
- **Free Tier**: 25GB storage included vs separate RDS charges
- **Scaling**: Instant on-demand scaling without connection pooling
- **Use Case Fit**: Key-value access pattern for embeddings

### Why Lambda over Fargate?
- **Cold Start**: Python 3.11 with provisioned concurrency: <100ms
- **Cost**: Free Tier includes 1M invocations/month
- **Scaling**: 0 to 1000 concurrent without configuration
- **Simplicity**: No container management

---

## 6. Scalability Within Free Tier

### Free Tier Limits Reference

| Service | Free Tier Limit | TruthLayer Usage Estimate |
|---------|-----------------|---------------------------|
| Lambda Invocations | 1,000,000/month | ~50,000 (demo phase) |
| Lambda Compute | 400,000 GB-sec/month | ~100,000 GB-sec |
| API Gateway | 1,000,000 requests/month | ~50,000 requests |
| DynamoDB Storage | 25 GB | ~5 GB (embeddings) |
| DynamoDB RCU/WCU | 25 each (on-demand) | Burst capable |
| S3 Storage | 5 GB | ~2 GB (documents) |
| S3 Requests | 20,000 GET, 2,000 PUT | ~5,000 combined |

### Scaling Strategies

1. **Embedding Caching**: Cache Bedrock responses in DynamoDB (TTL: 30 days)
2. **Batch Processing**: Batch up to 5 claims per Bedrock call
3. **Connection Reuse**: Lambda connection pooling for DynamoDB
4. **Lazy Loading**: Load document embeddings on-demand, not preloaded
5. **Pagination**: Limit dashboard queries to 100 items per page
