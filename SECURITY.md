# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability in TruthLayer, please report it responsibly.

### Contact

**Email:** [prakhar230125@gmail.com](mailto:prakhar230125@gmail.com)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment

### Response Timeline

- **Acknowledgment:** Within 48 hours
- **Assessment:** Within 1 week
- **Fix:** As soon as possible, depending on severity

## Security Practices

### API Key Security
- API keys are **never stored in plaintext** — only SHA-256 hashes are stored in DynamoDB
- Keys use the format `tl_{token_urlsafe(32)}` (46 characters)
- Rate limiting enforced per API key (atomic DynamoDB counter)

### Infrastructure
- All Lambda functions run with **least-privilege IAM policies**
- API Gateway enforces CORS and request validation
- DynamoDB tables use **on-demand billing** (no over-provisioning)
- No secrets in source code — all sensitive values via environment variables

### Data Handling
- Source documents are processed in-memory and stored only if explicitly uploaded via `/documents`
- Verification results are logged for analytics but contain no source content
- Embedding cache uses SHA-256 content hashes — original text is not recoverable from cache keys

## Dependency Security

TruthLayer backend has **zero third-party dependencies** — it uses only:
- Python standard library
- AWS SDK (boto3, provided by Lambda runtime)

The Python SDK (`truthlayer-sdk`) uses only the standard library (`urllib`, `json`).
