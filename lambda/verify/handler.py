"""AWS Lambda handler for the /verify endpoint."""

import sys
import os

# Add Lambda Layer path so 'from src.xxx' imports work
# Layer structure: python/python/src/ -> runtime: /opt/python/python/src/
sys.path.insert(0, '/opt/python/python')
sys.path.insert(0, '/opt/python')

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
_documents_table = None


def get_verifier():
    """Lazy-initialize the verifier (reused across invocations)."""
    global _verifier
    if _verifier is None:
        from src.verifier.verifier import TruthLayerVerifier
        from src.embeddings.bedrock_provider import BedrockEmbeddingProvider
        from src.embeddings.cached_provider import CachedEmbeddingProvider
        inner = BedrockEmbeddingProvider()
        provider = CachedEmbeddingProvider(inner_provider=inner)
        _verifier = TruthLayerVerifier(embedding_provider=provider)
        logger.info("TruthLayerVerifier initialized with cached Bedrock provider")
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


def get_documents_table():
    """Lazy-initialize DynamoDB documents table."""
    global _documents_table
    if _documents_table is None:
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("DOCUMENTS_TABLE", "TruthLayerDocuments")
        _documents_table = dynamodb.Table(table_name)
    return _documents_table


def resolve_document_ids(document_ids):
    """
    Fetch document content from DynamoDB by IDs.

    Args:
        document_ids: List of document_id strings

    Returns:
        Tuple of (resolved_texts: list[str], errors: list[str])
    """
    resolved = []
    errors = []
    table = get_documents_table()

    for doc_id in document_ids:
        try:
            # 'content' is a DynamoDB reserved word — must use alias
            response = table.get_item(
                Key={"document_id": doc_id},
                ProjectionExpression="#c, title",
                ExpressionAttributeNames={"#c": "content"},
            )
            item = response.get("Item")
            if item and item.get("content"):
                resolved.append(item["content"])
            else:
                errors.append(f"Document '{doc_id}' not found or has no content")
        except Exception as e:
            logger.error(f"Failed to fetch document {doc_id}: {e}")
            errors.append(f"Failed to fetch document '{doc_id}'")

    if errors:
        logger.warning(f"Document resolution issues: {errors}")

    return resolved, errors


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
        "source_documents": ["Source 1", "Source 2"],  // optional if document_ids provided
        "document_ids": ["doc-uuid-1", "doc-uuid-2"],  // optional if source_documents provided
        "options": {  // optional
            "verified_threshold": 0.80,
            "uncertain_threshold": 0.55
        }
    }

    At least one of source_documents or document_ids must be provided.
    Both can be provided — their contents are merged.

    Returns verification result with claims, summary, and metadata.
    """
    # Handle CORS preflight — no auth needed
    if event.get("httpMethod") == "OPTIONS":
        return build_response(200, {"message": "OK"})

    # Validate API key
    from src.utils.auth import validate_api_key
    is_valid, error_response = validate_api_key(event)
    if not is_valid:
        return error_response

    start_time = time.time()

    try:
        # Parse request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        ai_response = body.get("ai_response", "")
        source_documents = body.get("source_documents", [])
        document_ids = body.get("document_ids", [])
        options = body.get("options", {})

        # Validate input
        if not ai_response or not ai_response.strip():
            return build_response(400, {
                "error": "INVALID_INPUT",
                "message": "ai_response is required and cannot be empty"
            })

        # Resolve document IDs to content
        if document_ids:
            if not isinstance(document_ids, list):
                return build_response(400, {
                    "error": "INVALID_INPUT",
                    "message": "document_ids must be a list of document ID strings"
                })
            if len(document_ids) > 20:
                return build_response(400, {
                    "error": "INPUT_TOO_LARGE",
                    "message": "Maximum 20 document_ids allowed"
                })
            resolved_docs, resolve_errors = resolve_document_ids(document_ids)
            if resolve_errors and not resolved_docs and not source_documents:
                return build_response(404, {
                    "error": "DOCUMENTS_NOT_FOUND",
                    "message": "None of the provided document_ids could be resolved",
                    "details": resolve_errors
                })
            source_documents = source_documents + resolved_docs

        # Must have at least one source
        if not source_documents or not isinstance(source_documents, list):
            return build_response(400, {
                "error": "INVALID_INPUT",
                "message": "At least one of source_documents or document_ids is required"
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
