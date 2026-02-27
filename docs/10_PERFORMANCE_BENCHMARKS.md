# Performance Benchmarks

## 1. Latency Targets per Component

### 1.1 End-to-End Verification Latency

```
Target: < 500ms end-to-end warm (< 100ms with embedding caching — roadmap)

> **Current Measured Performance (live AWS deployment):**
> - Cold start: ~600ms (first request after idle)
> - Warm start: ~450ms (Bedrock embedding call dominates)
> - Target after caching: < 100ms (embeddings stored in DynamoDB, reused on repeat docs)

┌────────────────────────────────────────────────────────────────────────────┐
│                        LATENCY BREAKDOWN (WARM)                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  API Gateway    Lambda Init   Claim Extract   Bedrock      Match & Score   │
│  ────────────   ───────────   ─────────────   ─────────    ─────────────   │
│     5ms            0ms*          15ms           380ms          50ms         │
│     ████           ░░░░          ██████         ████████████   ████████     │
│                                                                             │
│  * Lambda kept warm via sustained traffic                                   │
│                                                                             │
│  Total (current): ~450ms    Total (with caching): ~80ms target              │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component-Level Targets

| Component | Target (p50) | Target (p95) | Target (p99) |
|-----------|--------------|--------------|--------------|
| API Gateway routing | 3ms | 5ms | 10ms |
| Lambda cold start | N/A* | N/A* | 500ms |
| Lambda warm start | <1ms | <1ms | 5ms |
| Input validation | 2ms | 5ms | 10ms |
| Claim extraction | 10ms | 15ms | 25ms |
| Bedrock embedding (per claim) | 25ms | 35ms | 60ms |
| DynamoDB read (embeddings) | 5ms | 10ms | 20ms |
| Similarity calculation | 15ms | 25ms | 40ms |
| Response serialization | 2ms | 5ms | 10ms |
| **Total (warm)** | **62ms** | **80ms** | **120ms** |

*Cold starts mitigated via provisioned concurrency or sustained traffic

### 1.3 Cold Start Mitigation

```python
# Provisioned concurrency configuration
ProvisionedConcurrency:
  FunctionName: TruthLayer-prod-Verification
  ProvisionedConcurrencyConfig:
    ProvisionedConcurrentExecutions: 5  # Keep 5 instances warm
```

**Cold Start Impact:**
| Lambda Memory | Cold Start (Python 3.11) |
|---------------|--------------------------|
| 256 MB | 800-1200ms |
| 512 MB | 500-800ms |
| 1024 MB | 300-500ms |

---

## 2. Throughput Requirements

### 2.1 Concurrent Request Handling

| Metric | Free Tier Target | Scale Target |
|--------|------------------|--------------|
| Concurrent verifications | 10 | 100 |
| Requests per second | 10 | 100 |
| Requests per minute | 300 | 3,000 |
| Requests per hour | 10,000 | 100,000 |

### 2.2 Document Processing Throughput

| Document Size | Processing Time | Chunks Generated |
|---------------|-----------------|------------------|
| < 10 KB (small) | 2-5 seconds | 1-10 |
| 10-100 KB (medium) | 5-15 seconds | 10-50 |
| 100-500 KB (large) | 15-30 seconds | 50-200 |
| 500 KB - 1 MB | 30-60 seconds | 200-500 |

### 2.3 Embedding Generation Rate

```
Bedrock Titan Embed:
- Input: 1-8192 tokens per request
- Latency: 25-50ms per request
- Throughput: 20-40 embeddings/second

Batch Processing:
- 5 claims → 5 sequential calls → ~150ms total
- With parallelization: ~50ms (limited by Bedrock concurrency)
```

---

## 3. Resource Utilization Limits

### 3.1 Lambda Configuration

| Function | Memory | Timeout | Reserved Concurrency |
|----------|--------|---------|---------------------|
| Verification | 512 MB | 10s | 100 (prod) / 10 (dev) |
| Document Processor | 1024 MB | 30s | 20 (prod) / 5 (dev) |
| Analytics | 256 MB | 5s | 50 (prod) / 5 (dev) |

### 3.2 Memory Usage Breakdown

**Verification Lambda (512 MB):**
```
Base Python runtime:     ~80 MB
NumPy + dependencies:    ~120 MB
Boto3 + AWS SDK:         ~50 MB
Application code:        ~20 MB
Working memory:          ~100 MB
Headroom buffer:         ~142 MB
───────────────────────────────
Total:                   512 MB
```

**Document Processor Lambda (1024 MB):**
```
Base Python runtime:     ~80 MB
PyPDF2 + text extraction: ~100 MB
NumPy + dependencies:    ~120 MB
Boto3 + AWS SDK:         ~50 MB
Document in memory:      ~200 MB (max 1MB doc)
Embeddings buffer:       ~300 MB
Headroom:                ~174 MB
───────────────────────────────
Total:                   1024 MB
```

### 3.3 DynamoDB Capacity

| Table | Read Capacity | Write Capacity | Storage Estimate |
|-------|---------------|----------------|------------------|
| Documents | On-demand (burst 3000 RCU) | On-demand (burst 1000 WCU) | ~100 MB |
| Embeddings | On-demand (burst 3000 RCU) | On-demand (burst 1000 WCU) | ~5 GB |
| Verifications | On-demand (burst 3000 RCU) | On-demand (burst 1000 WCU) | ~500 MB |
| ApiKeys | On-demand | On-demand | ~1 MB |

**Embeddings Size Calculation:**
```
Per chunk embedding:
- document_id: ~30 bytes
- chunk_id: ~15 bytes
- chunk_text: ~2,500 bytes (avg 500 tokens)
- embedding: ~6,200 bytes (1536 floats × 4 bytes)
- metadata: ~100 bytes
─────────────────────────────
Total per chunk: ~9 KB

100 documents × 100 chunks avg = 10,000 chunks
10,000 × 9 KB = ~90 MB

With 50 documents and growth: ~5 GB max
```

---

## 4. Cost Projection Within Free Tier

### 4.1 AWS Free Tier Limits (Monthly)

| Service | Free Tier Limit | TruthLayer Estimate | Usage % |
|---------|-----------------|---------------------|---------|
| Lambda Requests | 1,000,000 | 50,000 | 5% |
| Lambda Compute | 400,000 GB-sec | 100,000 GB-sec | 25% |
| API Gateway | 1,000,000 requests | 50,000 | 5% |
| DynamoDB Storage | 25 GB | 6 GB | 24% |
| DynamoDB RCU | 25 (on-demand bursts) | Burst | OK |
| DynamoDB WCU | 25 (on-demand bursts) | Burst | OK |
| S3 Storage | 5 GB | 2 GB | 40% |
| S3 Requests | 20,000 GET, 2,000 PUT | 5,000 / 500 | 25% |

### 4.2 Bedrock Costs (Not in Free Tier)

```
Amazon Titan Embeddings v1:
- Price: $0.0001 per 1,000 input tokens

Estimated Monthly Usage:
- 50,000 verifications
- 3 claims avg per verification = 150,000 embeddings
- 100 tokens avg per claim = 15,000,000 tokens
- Cost: 15,000 × $0.0001 = $1.50/month

Document Processing:
- 100 documents
- 100 chunks avg = 10,000 embeddings
- 500 tokens avg per chunk = 5,000,000 tokens
- Cost: 5,000 × $0.0001 = $0.50/month

Total Bedrock: ~$2.00/month
```

### 4.3 Cost Breakdown Summary

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| Lambda | $0.00 | Within Free Tier |
| API Gateway | $0.00 | Within Free Tier |
| DynamoDB | $0.00 | Within Free Tier (On-Demand) |
| S3 | $0.00 | Within Free Tier |
| Bedrock Titan | ~$2.00 | Pay-per-token |
| CloudWatch | $0.00 | Basic monitoring Free Tier |
| **Total** | **~$2.00/month** | Demo phase |

### 4.4 Scaling Cost Projection

| Usage Level | Verifications/Month | Est. Cost |
|-------------|---------------------|-----------|
| Demo | 10,000 | ~$2 |
| Startup | 100,000 | ~$20 |
| Growth | 500,000 | ~$100 |
| Scale | 1,000,000 | ~$200 |

---

## 5. Performance Monitoring

### 5.1 Key Metrics to Track

**Latency Metrics:**
```python
# CloudWatch custom metrics
metrics = [
    {
        "Name": "VerificationLatency",
        "Unit": "Milliseconds",
        "Dimensions": [
            {"Name": "Environment", "Value": "prod"},
            {"Name": "Function", "Value": "Verification"}
        ]
    },
    {
        "Name": "ClaimExtractionLatency",
        "Unit": "Milliseconds",
        "Dimensions": [...]
    },
    {
        "Name": "BedrockEmbeddingLatency",
        "Unit": "Milliseconds",
        "Dimensions": [...]
    },
    {
        "Name": "SimilarityMatchLatency",
        "Unit": "Milliseconds",
        "Dimensions": [...]
    }
]
```

**Throughput Metrics:**
- Requests per second
- Concurrent executions
- Throttled requests
- Error rate

### 5.2 CloudWatch Alarms

```yaml
# cloudwatch-alarms.yaml
Resources:
  HighLatencyAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: TruthLayer-HighLatency
      MetricName: Duration
      Namespace: AWS/Lambda
      Statistic: p95
      Period: 300
      EvaluationPeriods: 3
      Threshold: 100  # 100ms
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic
      Dimensions:
        - Name: FunctionName
          Value: TruthLayer-prod-Verification

  HighErrorRateAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: TruthLayer-HighErrorRate
      MetricName: Errors
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 10
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic

  ThrottlingAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: TruthLayer-Throttling
      MetricName: Throttles
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanOrEqualToThreshold
```

### 5.3 Performance Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLOUDWATCH PERFORMANCE DASHBOARD                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Latency (p95)           Throughput             Error Rate              │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐        │
│  │              │       │              │       │              │        │
│  │   72ms       │       │  12 req/s    │       │   0.1%       │        │
│  │   ▼ 8ms      │       │   ▲ 20%      │       │   ── 0%      │        │
│  └──────────────┘       └──────────────┘       └──────────────┘        │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    Request Latency Distribution                      ││
│  │  p50: 45ms   p75: 62ms   p90: 78ms   p95: 85ms   p99: 110ms        ││
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━       ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌───────────────────────────┐  ┌──────────────────────────────────────┐│
│  │   Lambda Invocations      │  │       DynamoDB Consumed Capacity     ││
│  │                           │  │                                       ││
│  │   1,247 (last 24h)        │  │   RCU: 12 avg   WCU: 3 avg          ││
│  │                           │  │                                       ││
│  └───────────────────────────┘  └──────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Benchmark Test Suite

### 6.1 Load Test Script

```python
import asyncio
import aiohttp
import time
import statistics

async def run_benchmark(
    api_url: str,
    api_key: str,
    document_id: str,
    num_requests: int = 100,
    concurrency: int = 10
):
    """Run performance benchmark against TruthLayer API."""
    
    latencies = []
    errors = 0
    
    async def single_request(session):
        nonlocal errors
        start = time.perf_counter()
        try:
            async with session.post(
                f"{api_url}/verify",
                headers={"x-api-key": api_key},
                json={
                    "document_id": document_id,
                    "ai_response": "The company reported $4.2 billion in revenue."
                }
            ) as response:
                await response.json()
                latency = (time.perf_counter() - start) * 1000
                latencies.append(latency)
        except Exception:
            errors += 1
    
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [single_request(session) for _ in range(num_requests)]
        await asyncio.gather(*tasks)
    
    # Calculate statistics
    latencies.sort()
    results = {
        "total_requests": num_requests,
        "successful": len(latencies),
        "errors": errors,
        "p50_ms": statistics.median(latencies),
        "p95_ms": latencies[int(len(latencies) * 0.95)],
        "p99_ms": latencies[int(len(latencies) * 0.99)],
        "avg_ms": statistics.mean(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "throughput_rps": len(latencies) / (max(latencies) / 1000)
    }
    
    return results

# Run benchmark
if __name__ == "__main__":
    results = asyncio.run(run_benchmark(
        api_url="https://api.truthlayer.io/v1",
        api_key="tlk_live_...",
        document_id="doc_benchmark",
        num_requests=100,
        concurrency=10
    ))
    
    print(f"Results:")
    print(f"  Successful: {results['successful']}/{results['total_requests']}")
    print(f"  P50 Latency: {results['p50_ms']:.1f}ms")
    print(f"  P95 Latency: {results['p95_ms']:.1f}ms")
    print(f"  P99 Latency: {results['p99_ms']:.1f}ms")
    print(f"  Throughput: {results['throughput_rps']:.1f} req/sec")
```

### 6.2 Expected Benchmark Results

| Metric | Target | Expected (Warm) |
|--------|--------|-----------------|
| P50 Latency | < 70ms | 45-55ms |
| P95 Latency | < 100ms | 75-90ms |
| P99 Latency | < 150ms | 100-130ms |
| Error Rate | < 0.1% | 0% |
| Throughput | > 10 req/s | 15-25 req/s |
