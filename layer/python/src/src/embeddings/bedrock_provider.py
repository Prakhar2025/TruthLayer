"""AWS Bedrock Titan Embeddings provider for production-grade semantic embeddings."""

import json
import time
import logging
from typing import List, Optional

import numpy as np

try:
    import boto3
    from botocore.exceptions import ClientError, EndpointConnectionError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from src.embeddings.base import EmbeddingProvider
from src.config import BEDROCK_MODEL_ID, BEDROCK_REGION, BEDROCK_EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class BedrockEmbeddingProvider(EmbeddingProvider):
    """
    Production embedding provider using Amazon Bedrock Titan Embeddings V2.
    
    Features:
        - Real semantic embeddings (1024 dimensions)
        - Automatic batching (groups of 25 to respect API limits)
        - Exponential backoff retry logic
        - Graceful error handling with fallback support
        - Normalized output vectors
    """

    # Titan Embeddings V2 limits
    MAX_INPUT_TOKENS = 8192
    MAX_BATCH_SIZE = 25
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5  # seconds

    def __init__(
        self,
        model_id: str = None,
        region: str = None,
        embedding_dimension: int = None,
        boto3_client=None
    ):
        """
        Initialize the Bedrock embedding provider.

        Args:
            model_id: Bedrock model ID (default: amazon.titan-embed-text-v2:0)
            region: AWS region (default: us-east-1)
            embedding_dimension: Target embedding dimension (default: 1024)
            boto3_client: Optional pre-configured boto3 client (for testing)
        """
        if not HAS_BOTO3 and boto3_client is None:
            raise ImportError(
                "boto3 is required for BedrockEmbeddingProvider. "
                "Install it with: pip install boto3"
            )

        self.model_id = model_id or BEDROCK_MODEL_ID
        self.region = region or BEDROCK_REGION
        self._dimension = embedding_dimension or BEDROCK_EMBEDDING_DIMENSION

        if boto3_client:
            self._client = boto3_client
        else:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region
            )

        logger.info(
            f"BedrockEmbeddingProvider initialized: model={self.model_id}, "
            f"region={self.region}, dimension={self._dimension}"
        )

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text using Bedrock Titan.

        Args:
            text: Text string to embed

        Returns:
            numpy array of shape (dimension,)
        """
        if not text or not text.strip():
            return np.zeros(self._dimension)

        # Truncate if too long (rough estimate: ~4 chars per token)
        max_chars = self.MAX_INPUT_TOKENS * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} chars for embedding")

        embedding = self._invoke_bedrock(text)
        return np.array(embedding, dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Handles batching internally — splits into groups of MAX_BATCH_SIZE
        to respect Bedrock API limits.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of shape (len(texts), dimension)
        """
        if not texts:
            return np.array([])

        all_embeddings = []

        # Process in batches
        for batch_start in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[batch_start:batch_start + self.MAX_BATCH_SIZE]
            batch_embeddings = []

            for text in batch:
                embedding = self.embed(text)
                batch_embeddings.append(embedding)

            all_embeddings.extend(batch_embeddings)

        result = np.array(all_embeddings, dtype=np.float32)

        # Normalize vectors
        norms = np.linalg.norm(result, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        result = result / norms

        return result

    def _invoke_bedrock(self, text: str) -> List[float]:
        """
        Call Bedrock Titan Embeddings API with retry logic.

        Args:
            text: Text to generate embedding for

        Returns:
            List of float values (the embedding vector)
        """
        request_body = json.dumps({
            "inputText": text.strip(),
            "dimensions": self._dimension,
            "normalize": True
        })

        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=request_body
                )

                response_body = json.loads(response["body"].read())
                embedding = response_body.get("embedding", [])

                if not embedding:
                    logger.error("Empty embedding returned from Bedrock")
                    return [0.0] * self._dimension

                # Pad or truncate to target dimension if needed
                if len(embedding) < self._dimension:
                    embedding.extend([0.0] * (self._dimension - len(embedding)))
                elif len(embedding) > self._dimension:
                    embedding = embedding[:self._dimension]

                return embedding

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                last_error = e

                if error_code == "ThrottlingException":
                    # Exponential backoff for throttling
                    delay = self.BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Bedrock throttled (attempt {attempt + 1}/{self.MAX_RETRIES}), "
                        f"retrying in {delay}s..."
                    )
                    time.sleep(delay)
                elif error_code == "ValidationException":
                    logger.error(f"Bedrock validation error: {e}")
                    return [0.0] * self._dimension
                elif error_code == "AccessDeniedException":
                    logger.error(
                        "Bedrock access denied. Ensure:\n"
                        "1. Titan Embeddings V2 is enabled in Bedrock console\n"
                        "2. IAM role has bedrock:InvokeModel permission\n"
                        f"3. Region is correct: {self.region}"
                    )
                    raise
                else:
                    logger.error(f"Bedrock client error: {error_code} - {e}")
                    raise

            except EndpointConnectionError as e:
                logger.error(
                    f"Cannot connect to Bedrock endpoint in {self.region}. "
                    "Check your AWS region and network connection."
                )
                raise

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error calling Bedrock: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.BASE_RETRY_DELAY * (2 ** attempt))
                else:
                    raise

        logger.error(f"All {self.MAX_RETRIES} Bedrock retries failed")
        raise last_error


def is_bedrock_available() -> bool:
    """
    Check if AWS Bedrock is available and accessible.
    
    Returns:
        True if Bedrock can be used, False otherwise
    """
    if not HAS_BOTO3:
        return False

    try:
        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        # Try a minimal invoke to test access
        client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": "test", "dimensions": 256, "normalize": True})
        )
        return True
    except Exception:
        return False
