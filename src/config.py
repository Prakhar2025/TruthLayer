"""Configuration settings for TruthLayer verification system."""

import os

# Calibrated for Amazon Bedrock Titan Embed Text v2 (1024-dim)
# COMBINED with entity_checker.py which applies multiplicative penalties
# for numerical/negation contradictions.
#
# Two-signal verification:
#   Signal 1 (embeddings): captures topical/semantic relevance
#   Signal 2 (entity checker): catches literal contradictions
#
# Empirical ranges (Titan cosine similarity):
#   - Exact / near-exact match:      0.55 – 0.85
#   - Paraphrased but correct:       0.35 – 0.55
#   - Subtly hallucinated (wrong #): 0.25 – 0.45 (before penalty)
#   - After entity penalty (×0.5):   0.12 – 0.22 (→ UNSUPPORTED)
#   - Completely fabricated:          0.05 – 0.25
#
# These thresholds can be overridden via environment variables.
VERIFIED_THRESHOLD = float(os.environ.get("VERIFIED_THRESHOLD", "0.65"))
UNCERTAIN_THRESHOLD = float(os.environ.get("UNCERTAIN_THRESHOLD", "0.30"))

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
