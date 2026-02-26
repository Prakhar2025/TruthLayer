"""AWS Lambda handler for the /verify endpoint."""

import sys
import os

# Add Lambda Layer path so 'from src.xxx' imports work
# Layer structure: python/python/src/ -> runtime: /opt/python/python/src/
sys.path.insert(0, '/opt/python/python')

import json
import time
import uuid
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize outside handler for connection reuse (cold start optimization)
_verifier = None
_verifications_table = None


def get_verifier():
    """Lazy-initialize the verifier (reused across invocations)."""
    global _verifier
    if _verifier is None:
        from src.verifier.verifier import TruthLayerVerifier
        from src.embeddings.bedrock_provider import BedrockEmbeddingProvider
        provider = BedrockEmbeddingProvider()
        _verifier = TruthLayerVerifier(embedding_provider=provider)
        logger.info("TruthLayerVerifier initialized with Bedrock provider")
    return _verifier


def get_verifications_table():
    """Lazy-initialize DynamoDB verifications table."""
    global _verifications_table
    if _verifications_table is None:
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("VERIFICATIONS_TABLE", "TruthLayerVerifications")
        _verifications_table = dynamodb.Table(table_name)
    return _verifications_table


def save_verification(result):
    """Save verification result to DynamoDB for analytics."""
    try:
        from decimal import Decimal
        table = get_verifications_table()
        
        # Convert floats to Decimal for DynamoDB
        item = {
            "verification_id": str(uuid.uuid4()),
            "summary": result.get("summary", {}),
            "total_claims": len(result.get("claims", [])),
            "latency_ms": Decimal(str(result.get("metadata", {}).get("latency_ms", 0))),
            "provider": result.get("metadata", {}).get("provider", "unknown"),
            "created_at": int(time.time()),
        }
        table.put_item(Item=item)
        logger.info(f"Saved verification {item['verification_id']}")
    except Exception as e:
        logger.warning(f"Failed to save verification to DynamoDB: {e}")
        # Don't fail the request if analytics save fails


def build_response(status_code, body, cors=True):
    """Build an API Gateway-compatible response."""
    response = {
        "statusCode": status_code,
        "body": json.dumps(body, default=str),
        "headers": {
            "Content-Type": "application/json",
        }
    }
    if cors:
        response["headers"].update({
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        })
    return response


def handler(event, context):
    """
    Lambda handler for POST /verify

    Expects JSON body:
    {
        "ai_response": "Text to verify...",
        "source_documents": ["Source 1", "Source 2"],
        "options": {  // optional
            "verified_threshold": 0.80,
            "uncertain_threshold": 0.55
        }
    }

    Returns verification result with claims, summary, and metadata.
    """
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return build_response(200, {"message": "OK"})

    start_time = time.time()

    try:
        # Parse request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        ai_response = body.get("ai_response", "")
        source_documents = body.get("source_documents", [])
        options = body.get("options", {})

        # Validate input
        if not ai_response or not ai_response.strip():
            return build_response(400, {
                "error": "INVALID_INPUT",
                "message": "ai_response is required and cannot be empty"
            })

        if not source_documents or not isinstance(source_documents, list):
            return build_response(400, {
                "error": "INVALID_INPUT",
                "message": "source_documents is required and must be a non-empty list"
            })

        # Validate text lengths
        if len(ai_response) > 50000:
            return build_response(400, {
                "error": "INPUT_TOO_LARGE",
                "message": "ai_response must be under 50,000 characters"
            })

        for i, doc in enumerate(source_documents):
            if not isinstance(doc, str) or not doc.strip():
                return build_response(400, {
                    "error": "INVALID_INPUT",
                    "message": f"source_documents[{i}] must be a non-empty string"
                })

        if len(source_documents) > 20:
            return build_response(400, {
                "error": "INPUT_TOO_LARGE",
                "message": "Maximum 20 source documents allowed"
            })

        # Run verification
        verifier = get_verifier()
        result = verifier.verify(ai_response, source_documents)

        # Add request metadata
        result["metadata"]["request_id"] = (
            context.aws_request_id if context else "local"
        )
        result["metadata"]["total_latency_ms"] = round(
            (time.time() - start_time) * 1000, 2
        )

        logger.info(
            f"Verification complete: {result['summary']} "
            f"in {result['metadata']['total_latency_ms']}ms"
        )

        # Save to DynamoDB for analytics
        save_verification(result)

        return build_response(200, result)

    except json.JSONDecodeError:
        return build_response(400, {
            "error": "INVALID_JSON",
            "message": "Request body must be valid JSON"
        })

    except Exception as e:
        logger.error(f"Verification error: {traceback.format_exc()}")
        return build_response(500, {
            "error": "INTERNAL_ERROR",
            "message": "An internal error occurred during verification"
        })
