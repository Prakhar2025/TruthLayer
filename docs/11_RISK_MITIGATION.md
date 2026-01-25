# Risk Mitigation Plan

## 1. Technical Risks and Solutions

### 1.1 Risk Matrix

| Risk | Probability | Impact | Priority | Mitigation |
|------|-------------|--------|----------|------------|
| Bedrock API latency spikes | Medium | High | P1 | Caching, fallback, timeouts |
| Lambda cold starts | Medium | Medium | P2 | Provisioned concurrency |
| DynamoDB throttling | Low | High | P2 | On-demand scaling, retries |
| Embedding quality issues | Medium | High | P1 | Threshold tuning, validation |
| Document parsing failures | Medium | Medium | P3 | Multi-parser fallback |
| API Gateway throttling | Low | Medium | P3 | Rate limit monitoring |
| Cost overrun | Low | Medium | P3 | Usage alerts, circuit breakers |

### 1.2 Bedrock API Latency

**Risk:** Bedrock embedding API may experience latency spikes (>100ms) or temporary unavailability.

**Mitigation Strategies:**

```python
# Strategy 1: Request timeout with fallback
async def get_embedding_with_timeout(text: str) -> List[float]:
    try:
        async with asyncio.timeout(3.0):  # 3 second hard timeout
            return await generate_embedding(text)
    except asyncio.TimeoutError:
        logger.warning("Bedrock timeout, using cached/fallback")
        return get_fallback_embedding(text)

# Strategy 2: Embedding cache
EMBEDDING_CACHE_TTL = 86400 * 7  # 7 days

def get_cached_embedding(text: str) -> Optional[List[float]]:
    cache_key = hashlib.md5(text.lower().encode()).hexdigest()
    cached = dynamodb_cache.get(cache_key)
    if cached and cached['ttl'] > time.time():
        return cached['embedding']
    return None

def cache_embedding(text: str, embedding: List[float]):
    cache_key = hashlib.md5(text.lower().encode()).hexdigest()
    dynamodb_cache.put({
        'cache_key': cache_key,
        'embedding': embedding,
        'ttl': int(time.time()) + EMBEDDING_CACHE_TTL
    })

# Strategy 3: Circuit breaker
class BedrockCircuitBreaker:
    def __init__(self):
        self.failures = 0
        self.last_failure = 0
        self.threshold = 5
        self.reset_timeout = 60
    
    def is_open(self) -> bool:
        if self.failures >= self.threshold:
            if time.time() - self.last_failure > self.reset_timeout:
                self.failures = 0
                return False
            return True
        return False
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
    
    def record_success(self):
        self.failures = 0
```

### 1.3 Lambda Cold Starts

**Risk:** Cold starts can add 500-1200ms latency for initial requests.

**Mitigation Strategies:**

```yaml
# Strategy 1: Provisioned Concurrency (Production)
Resources:
  VerificationFunctionProvisionedConcurrency:
    Type: AWS::Lambda::Alias
    Properties:
      FunctionName: !Ref VerificationFunction
      FunctionVersion: !GetAtt VerificationFunctionVersion.Version
      Name: live
      ProvisionedConcurrencyConfig:
        ProvisionedConcurrentExecutions: 5

# Strategy 2: Keep-warm CloudWatch Event (Dev/Free Tier)
  WarmupSchedule:
    Type: AWS::Events::Rule
    Properties:
      ScheduleExpression: rate(5 minutes)
      Targets:
        - Id: WarmupTarget
          Arn: !GetAtt VerificationFunction.Arn
          Input: '{"warmup": true}'
```

```python
# Lambda handler warmup check
def lambda_handler(event, context):
    # Check for warmup request
    if event.get('warmup'):
        return {'statusCode': 200, 'body': 'warm'}
    
    # Normal processing
    return process_verification(event)
```

### 1.4 DynamoDB Throttling

**Risk:** Burst traffic may exceed on-demand capacity, causing throttling.

**Mitigation Strategies:**

```python
# Strategy 1: Exponential backoff with jitter
def dynamodb_get_with_retry(table, key, max_retries=3):
    for attempt in range(max_retries):
        try:
            return table.get_item(Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue
            raise
    raise Exception("DynamoDB max retries exceeded")

# Strategy 2: Batch operations to reduce calls
def batch_get_embeddings(document_id: str, chunk_ids: List[str]):
    # Use BatchGetItem instead of multiple GetItem calls
    response = dynamodb.batch_get_item(
        RequestItems={
            'TruthLayer-Embeddings': {
                'Keys': [
                    {'document_id': document_id, 'chunk_id': cid}
                    for cid in chunk_ids
                ]
            }
        }
    )
    return response['Responses']['TruthLayer-Embeddings']
```

### 1.5 Embedding Quality Issues

**Risk:** Some claims may not match well due to embedding semantic gaps.

**Mitigation Strategies:**

```python
# Strategy 1: Multi-signal verification
def enhanced_confidence_scoring(claim: str, best_match: Match) -> float:
    # Base semantic similarity
    semantic_score = best_match.similarity
    
    # Keyword overlap validation
    keyword_score = calculate_keyword_overlap(claim, best_match.text)
    
    # Named entity matching
    entity_score = match_named_entities(claim, best_match.text)
    
    # Numeric precision check
    numeric_score = validate_numeric_claims(claim, best_match.text)
    
    # Weighted combination
    confidence = (
        0.50 * semantic_score +
        0.20 * keyword_score +
        0.15 * entity_score +
        0.15 * numeric_score
    )
    
    return min(1.0, max(0.0, confidence))

# Strategy 2: Threshold validation with human review flag
def flag_for_review(result: VerificationResult) -> bool:
    # Flag if confidence is in uncertain range
    if 0.55 <= result.overall_score <= 0.70:
        return True
    
    # Flag if there's high variance between claims
    scores = [c.confidence for c in result.claims]
    if max(scores) - min(scores) > 0.4:
        return True
    
    return False
```

---

## 2. AWS Free Tier Limit Monitoring

### 2.1 Usage Tracking

```python
# Track usage against Free Tier limits
FREE_TIER_LIMITS = {
    'lambda_invocations': 1_000_000,
    'lambda_gb_seconds': 400_000,
    'api_gateway_requests': 1_000_000,
    'dynamodb_storage_gb': 25,
    's3_storage_gb': 5,
    's3_get_requests': 20_000,
    's3_put_requests': 2_000
}

def check_usage_percentage(current_usage: dict) -> dict:
    alerts = {}
    for resource, limit in FREE_TIER_LIMITS.items():
        used = current_usage.get(resource, 0)
        percentage = (used / limit) * 100
        
        if percentage >= 80:
            alerts[resource] = {
                'status': 'CRITICAL',
                'percentage': percentage,
                'message': f'{resource} at {percentage:.1f}% of Free Tier'
            }
        elif percentage >= 60:
            alerts[resource] = {
                'status': 'WARNING',
                'percentage': percentage
            }
    
    return alerts
```

### 2.2 CloudWatch Billing Alarms

```yaml
Resources:
  BillingAlarm10USD:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: TruthLayer-Billing-10USD
      AlarmDescription: Alert when charges exceed $10
      MetricName: EstimatedCharges
      Namespace: AWS/Billing
      Statistic: Maximum
      Period: 21600  # 6 hours
      EvaluationPeriods: 1
      Threshold: 10
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: Currency
          Value: USD
      AlarmActions:
        - !Ref BillingAlertTopic

  BillingAlarm5USD:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: TruthLayer-Billing-5USD
      AlarmDescription: Early warning at $5
      MetricName: EstimatedCharges
      Namespace: AWS/Billing
      Statistic: Maximum
      Period: 21600
      EvaluationPeriods: 1
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: Currency
          Value: USD
      AlarmActions:
        - !Ref BillingAlertTopic

  BillingAlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: TruthLayer-Billing-Alerts
      Subscription:
        - Endpoint: admin@truthlayer.io
          Protocol: email
```

### 2.3 Usage Dashboard Widget

```python
# Lambda to generate usage report
def generate_usage_report():
    cloudwatch = boto3.client('cloudwatch')
    
    # Lambda invocations (last 30 days)
    lambda_response = cloudwatch.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName='Invocations',
        Dimensions=[{'Name': 'FunctionName', 'Value': 'TruthLayer-*'}],
        StartTime=datetime.now() - timedelta(days=30),
        EndTime=datetime.now(),
        Period=2592000,  # 30 days
        Statistics=['Sum']
    )
    
    return {
        'lambda_invocations': lambda_response['Datapoints'][0]['Sum'],
        'free_tier_remaining': FREE_TIER_LIMITS['lambda_invocations'] - lambda_response['Datapoints'][0]['Sum'],
        'percentage_used': (lambda_response['Datapoints'][0]['Sum'] / FREE_TIER_LIMITS['lambda_invocations']) * 100
    }
```

---

## 3. Fallback Strategies

### 3.1 Service Degradation Levels

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SERVICE DEGRADATION LEVELS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LEVEL 0: NORMAL                                                         │
│  ─────────────────                                                       │
│  All systems operational. Full verification with Bedrock embeddings.    │
│                                                                          │
│  LEVEL 1: DEGRADED                                                       │
│  ─────────────────                                                       │
│  Bedrock latency elevated (>100ms). Enable aggressive caching.          │
│  Reduce max claims from 10 to 5.                                         │
│                                                                          │
│  LEVEL 2: PARTIAL                                                        │
│  ─────────────────                                                       │
│  Bedrock unavailable. Use fallback keyword matching.                    │
│  Return results with "reduced_confidence" flag.                          │
│                                                                          │
│  LEVEL 3: MAINTENANCE                                                    │
│  ─────────────────                                                       │
│  Critical issue. Return 503 with ETA.                                   │
│  Queue requests for later processing.                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Fallback Implementation

```python
class FallbackVerifier:
    """Keyword-based fallback when Bedrock is unavailable."""
    
    def __init__(self):
        self.stopwords = {'the', 'a', 'an', 'is', 'was', 'are', 'were', 
                          'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    
    def extract_keywords(self, text: str) -> set:
        words = text.lower().split()
        return {w for w in words if w not in self.stopwords and len(w) > 2}
    
    def calculate_similarity(self, claim: str, chunk: str) -> float:
        claim_keywords = self.extract_keywords(claim)
        chunk_keywords = self.extract_keywords(chunk)
        
        if not claim_keywords:
            return 0.0
        
        intersection = claim_keywords.intersection(chunk_keywords)
        return len(intersection) / len(claim_keywords)
    
    def verify(self, claim: str, chunks: List[str]) -> dict:
        best_score = 0.0
        best_chunk = None
        
        for chunk in chunks:
            score = self.calculate_similarity(claim, chunk)
            if score > best_score:
                best_score = score
                best_chunk = chunk
        
        return {
            'confidence': best_score * 0.7,  # Reduce confidence for fallback
            'matched_chunk': best_chunk,
            'fallback_mode': True
        }
```

### 3.3 Graceful Error Responses

```python
def create_error_response(error_type: str, message: str) -> dict:
    responses = {
        'SERVICE_DEGRADED': {
            'statusCode': 200,
            'body': {
                'status': 'degraded',
                'message': 'Verification completed with reduced accuracy',
                'recommendations': ['Retry in 5 minutes for full accuracy']
            }
        },
        'SERVICE_UNAVAILABLE': {
            'statusCode': 503,
            'body': {
                'error': 'SERVICE_UNAVAILABLE',
                'message': 'Verification service temporarily unavailable',
                'retry_after': 60,
                'queue_id': generate_queue_id()  # Queue for later
            }
        },
        'RATE_LIMITED': {
            'statusCode': 429,
            'body': {
                'error': 'RATE_LIMITED',
                'message': 'Request rate exceeded. Please slow down.',
                'retry_after': 30
            }
        }
    }
    return responses.get(error_type, {
        'statusCode': 500,
        'body': {'error': 'INTERNAL_ERROR', 'message': message}
    })
```

---

## 4. Data Security Measures

### 4.1 Data Classification

| Data Type | Classification | Encryption | Retention |
|-----------|----------------|------------|-----------|
| API Keys | Secret | AES-256 (hashed) | Until revoked |
| Source Documents | Confidential | S3 SSE-S3 | User-defined |
| Document Embeddings | Internal | DynamoDB encryption | 30 days TTL |
| Verification Results | Internal | DynamoDB encryption | 90 days TTL |
| Analytics Data | Internal | DynamoDB encryption | 365 days |

### 4.2 Encryption Configuration

```yaml
# S3 Bucket Encryption
Resources:
  DocumentsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub truthlayer-documents-${Environment}
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      VersioningConfiguration:
        Status: Enabled

# DynamoDB Encryption (enabled by default)
  DocumentsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      SSESpecification:
        SSEEnabled: true
        SSEType: KMS
        KMSMasterKeyId: alias/aws/dynamodb
```

### 4.3 API Key Security

```python
import hashlib
import secrets

def generate_api_key() -> tuple:
    """Generate API key and its hash for storage."""
    # Generate 32 random bytes
    raw_key = secrets.token_hex(32)
    
    # Create display format
    environment = "live"  # or "test"
    api_key = f"tlk_{environment}_{raw_key}"
    
    # Hash for storage
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Prefix for display (show first 8 chars after prefix)
    key_prefix = f"tlk_{environment}_{raw_key[:8]}..."
    
    return api_key, key_hash, key_prefix

def validate_api_key(provided_key: str) -> bool:
    """Validate API key against stored hash."""
    key_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    
    # Lookup in DynamoDB
    response = api_keys_table.get_item(Key={'key_hash': key_hash})
    
    if 'Item' not in response:
        return False
    
    item = response['Item']
    
    # Check if key is active
    if not item.get('is_active', False):
        return False
    
    # Check expiration
    if item.get('expires_at'):
        if datetime.fromisoformat(item['expires_at']) < datetime.now():
            return False
    
    return True
```

### 4.4 Input Sanitization

```python
import re
from html import escape

def sanitize_input(ai_response: str) -> str:
    """Sanitize AI response input to prevent injection."""
    # Remove any HTML/script tags
    sanitized = re.sub(r'<[^>]+>', '', ai_response)
    
    # Escape special characters
    sanitized = escape(sanitized)
    
    # Remove control characters
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length
    sanitized = sanitized[:10000]
    
    return sanitized

def validate_document_id(document_id: str) -> bool:
    """Validate document ID format to prevent injection."""
    pattern = r'^doc_[a-zA-Z0-9]{16,32}$'
    return bool(re.match(pattern, document_id))
```

### 4.5 Audit Logging

```python
def log_audit_event(event_type: str, user_id: str, details: dict):
    """Log security-relevant events for audit trail."""
    audit_entry = {
        'event_id': str(uuid.uuid4()),
        'event_type': event_type,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        'details': details,
        'source_ip': get_client_ip(),
        'user_agent': get_user_agent()
    }
    
    # Log to CloudWatch Logs
    logger.info(json.dumps(audit_entry))
    
    # Store in audit table for compliance
    audit_table.put_item(Item=audit_entry)

# Example usage
log_audit_event(
    event_type='API_KEY_CREATED',
    user_id='usr_123',
    details={'key_prefix': 'tlk_live_abc12345...'}
)

log_audit_event(
    event_type='DOCUMENT_DELETED',
    user_id='usr_123',
    details={'document_id': 'doc_xyz789'}
)
```

---

## 5. Incident Response Plan

### 5.1 Severity Levels

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| SEV-1 | Complete service outage | 15 minutes | Immediate |
| SEV-2 | Degraded performance (>200ms p95) | 1 hour | Team lead |
| SEV-3 | Minor issues, workaround available | 4 hours | On-call |
| SEV-4 | Low impact, scheduled fix | 24 hours | Backlog |

### 5.2 Response Runbooks

```markdown
## Runbook: Bedrock Latency Spike

### Detection
- CloudWatch alarm: BedrockLatency p95 > 100ms for 5 minutes

### Immediate Actions
1. Check AWS Health Dashboard for Bedrock status
2. Enable Level 1 degradation (aggressive caching)
3. If sustained >15 min, enable Level 2 (fallback mode)

### Investigation
1. Check Bedrock service quotas
2. Review request patterns for anomalies
3. Check for regional issues

### Resolution
1. Once Bedrock latency normalizes, disable degradation mode
2. Clear caches if stale data suspected
3. Document incident

## Runbook: DynamoDB Throttling

### Detection
- CloudWatch alarm: WriteThrottleEvents > 0

### Immediate Actions
1. Reduce concurrent Lambda executions
2. Enable more aggressive batching
3. Add jitter to retry logic

### Investigation
1. Check DynamoDB metrics for burst patterns
2. Review recent code changes
3. Analyze traffic patterns

### Resolution
1. Throttling should auto-resolve with on-demand
2. Consider splitting hot partitions if recurring
```
