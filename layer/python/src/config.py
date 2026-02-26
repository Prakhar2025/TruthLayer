"""Configuration settings for TruthLayer verification system."""

import os

# ---------- Similarity Thresholds ----------
VERIFIED_THRESHOLD = float(os.environ.get("VERIFIED_THRESHOLD", "0.80"))
UNCERTAIN_THRESHOLD = float(os.environ.get("UNCERTAIN_THRESHOLD", "0.55"))

# ---------- AWS Bedrock Settings ----------
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "amazon.titan-embed-text-v2:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_EMBEDDING_DIMENSION = int(
    os.environ.get("BEDROCK_EMBEDDING_DIMENSION", "1024")
)

# ---------- Mock Embedding Settings ----------
MOCK_EMBEDDING_DIMENSION = 384

# ---------- Text Splitting ----------
MAX_CHUNK_SIZE = int(os.environ.get("MAX_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "50"))

# ---------- Convenience alias ----------
EMBEDDING_DIMENSION = BEDROCK_EMBEDDING_DIMENSION
