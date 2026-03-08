# Contributing to TruthLayer

Thank you for your interest in contributing to TruthLayer! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.9+
- AWS CLI configured (for integration tests)
- Node.js 18+ (for dashboard)
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (for deployment)

### Local Setup
```bash
# Clone the repository
git clone https://github.com/Prakhar2025/TruthLayer.git
cd TruthLayer

# Install Python dependencies
pip install -r requirements.txt

# Run tests (no AWS credentials needed)
pytest tests/ -v

# Run locally with mock embeddings
python main.py --mock
```

## Code Standards

### Python
- Follow PEP 8 conventions
- All Lambda handlers must include `sys.path.insert` for Layer compatibility
- Use `Decimal` for DynamoDB float values
- Alias DynamoDB reserved words with `ExpressionAttributeNames`

### TypeScript (Dashboard)
- API calls go through `dashboard/src/lib/api.ts`
- Environment variables via `process.env.NEXT_PUBLIC_*`

## Testing

All changes must pass the existing test suite:

```bash
pytest tests/ -v  # 87 tests must pass
```

- Use `MockEmbeddingProvider` for unit tests — no AWS credentials required
- Add tests for new functionality in the `tests/` directory

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Write tests for new functionality
4. Ensure all 87 tests pass
5. Submit a pull request with a clear description

## Architecture Guidelines

- Core verification logic lives in `src/`
- Lambda handlers in `lambda/` import from `src/` via the Lambda Layer
- Always copy `src/` to `layer/python/src/` before building
- Never commit real API keys or `dashboard/.env.local`

## Contact

Questions? Reach out to [prakhar230125@gmail.com](mailto:prakhar230125@gmail.com).
