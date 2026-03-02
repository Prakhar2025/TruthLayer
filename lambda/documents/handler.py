"""AWS Lambda handler for document management endpoints."""

import sys
sys.path.insert(0, '/opt/python/python')
sys.path.insert(0, '/opt/python')

import json
import uuid
import time
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy-init DynamoDB resource
_documents_table = None


def get_table():
    """Get DynamoDB Documents table (lazy init)."""
    global _documents_table
    if _documents_table is None:
        import os
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("DOCUMENTS_TABLE", "TruthLayerDocuments")
        _documents_table = dynamodb.Table(table_name)
        logger.info(f"Connected to DynamoDB table: {table_name}")
    return _documents_table


def build_response(status_code, body):
    """Build API Gateway response with CORS."""
    return {
        "statusCode": status_code,
        "body": json.dumps(body, default=str),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        }
    }


def handler(event, context):
    """
    Lambda handler for /documents endpoints.

    POST /documents — Upload a new document
    GET /documents — List all documents
    GET /documents/{id} — Get a specific document
    DELETE /documents/{id} — Delete a document
    """
    if event.get("httpMethod") == "OPTIONS":
        return build_response(200, {"message": "OK"})

    # Validate API key
    from src.utils.auth import validate_api_key
    is_valid, error_response = validate_api_key(event)
    if not is_valid:
        return error_response

    method = event.get("httpMethod", "GET")
    path_params = event.get("pathParameters") or {}
    doc_id = path_params.get("id")

    try:
        if method == "POST":
            return _create_document(event)
        elif method == "GET" and doc_id:
            return _get_document(doc_id)
        elif method == "GET":
            return _list_documents(event)
        elif method == "DELETE" and doc_id:
            return _delete_document(doc_id)
        else:
            return build_response(405, {
                "error": "METHOD_NOT_ALLOWED",
                "message": f"Method {method} not supported"
            })

    except Exception as e:
        logger.error(f"Document handler error: {traceback.format_exc()}")
        return build_response(500, {
            "error": "INTERNAL_ERROR",
            "message": "An internal error occurred"
        })


def _create_document(event):
    """Create a new document."""
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    title = body.get("title", "")
    content = body.get("content", "")
    metadata = body.get("metadata", {})

    if not content or not content.strip():
        return build_response(400, {
            "error": "INVALID_INPUT",
            "message": "content is required"
        })

    if len(content) > 100000:
        return build_response(400, {
            "error": "INPUT_TOO_LARGE",
            "message": "Document content must be under 100,000 characters"
        })

    doc_id = str(uuid.uuid4())
    timestamp = int(time.time())

    item = {
        "document_id": doc_id,
        "title": title or f"Document {doc_id[:8]}",
        "content": content,
        "metadata": metadata,
        "created_at": timestamp,
        "updated_at": timestamp,
        "content_length": len(content),
        "chunk_count": 0,  # Updated when embeddings are generated
    }

    table = get_table()
    table.put_item(Item=item)

    logger.info(f"Created document {doc_id}: {item['title']}")

    return build_response(201, {
        "document_id": doc_id,
        "title": item["title"],
        "content_length": len(content),
        "created_at": timestamp,
        "message": "Document created successfully"
    })


def _get_document(doc_id):
    """Get a document by ID."""
    table = get_table()
    response = table.get_item(Key={"document_id": doc_id})

    item = response.get("Item")
    if not item:
        return build_response(404, {
            "error": "NOT_FOUND",
            "message": f"Document {doc_id} not found"
        })

    return build_response(200, {
        "document_id": item["document_id"],
        "title": item.get("title", ""),
        "content": item.get("content", ""),
        "metadata": item.get("metadata", {}),
        "content_length": item.get("content_length", 0),
        "created_at": item.get("created_at", 0),
    })


def _list_documents(event):
    """List all documents (with pagination)."""
    query_params = event.get("queryStringParameters") or {}
    limit = min(int(query_params.get("limit", "50")), 100)

    table = get_table()

    scan_kwargs = {"Limit": limit}

    # Support pagination via last_key
    last_key = query_params.get("last_key")
    if last_key:
        scan_kwargs["ExclusiveStartKey"] = {"document_id": last_key}

    response = table.scan(**scan_kwargs)

    documents = []
    for item in response.get("Items", []):
        documents.append({
            "document_id": item["document_id"],
            "title": item.get("title", ""),
            "content_length": item.get("content_length", 0),
            "created_at": item.get("created_at", 0),
        })

    # Sort by created_at descending
    documents.sort(key=lambda x: x.get("created_at", 0), reverse=True)

    result = {
        "documents": documents,
        "count": len(documents),
    }

    if "LastEvaluatedKey" in response:
        result["last_key"] = response["LastEvaluatedKey"]["document_id"]

    return build_response(200, result)


def _delete_document(doc_id):
    """Delete a document by ID."""
    table = get_table()

    # Check if it exists first
    response = table.get_item(Key={"document_id": doc_id})
    if not response.get("Item"):
        return build_response(404, {
            "error": "NOT_FOUND",
            "message": f"Document {doc_id} not found"
        })

    table.delete_item(Key={"document_id": doc_id})
    logger.info(f"Deleted document {doc_id}")

    return build_response(200, {
        "message": f"Document {doc_id} deleted successfully"
    })
