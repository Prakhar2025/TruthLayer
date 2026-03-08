"""AWS Lambda handler for API key management endpoints."""

import sys
sys.path.insert(0, '/opt/python/python')
sys.path.insert(0, '/opt/python')

import hashlib
import json
import logging
import os
import secrets
import time
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy-init DynamoDB resource
_keys_table = None


def get_table():
    """Get DynamoDB ApiKeys table (lazy init for cold start optimization)."""
    global _keys_table
    if _keys_table is None:
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("APIKEYS_TABLE", "TruthLayerApiKeys")
        _keys_table = dynamodb.Table(table_name)
        logger.info(f"Connected to DynamoDB table: {table_name}")
    return _keys_table


def build_response(status_code, body):
    """Build API Gateway response with CORS headers."""
    return {
        "statusCode": status_code,
        "body": json.dumps(body, default=str),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        }
    }


def handler(event, context):
    """
    Lambda handler for /keys endpoint.

    POST /keys — Generate a new API key
        Body: { "owner": "string", "email": "string", "use_case": "string" }
        Returns: { "api_key": "tl_xxx", "message": "..." }
        The raw key is returned ONCE — only the hash is stored.
    """
    http_method = event.get("httpMethod", "GET")
    logger.info(f"Keys handler: {http_method}")

    # Handle CORS preflight
    if http_method == "OPTIONS":
        return build_response(200, {"message": "OK"})

    if http_method != "POST":
        return build_response(405, {
            "error": "METHOD_NOT_ALLOWED",
            "message": "Only POST is supported",
        })

    # Parse and validate request body
    try:
        body = json.loads(event.get("body", "{}") or "{}")
    except json.JSONDecodeError:
        return build_response(400, {
            "error": "INVALID_JSON",
            "message": "Request body must be valid JSON",
        })

    owner = body.get("owner", "").strip()
    email = body.get("email", "").strip()
    use_case = body.get("use_case", "").strip()

    # Validate required fields
    if not owner:
        return build_response(400, {
            "error": "MISSING_FIELD",
            "message": "Field 'owner' is required",
        })

    if not email:
        return build_response(400, {
            "error": "MISSING_FIELD",
            "message": "Field 'email' is required",
        })

    # Basic email format validation (not overly strict — just sanity check)
    if "@" not in email or "." not in email.split("@")[-1]:
        return build_response(400, {
            "error": "INVALID_EMAIL",
            "message": "Field 'email' must be a valid email address",
        })

    # Rate limit: max 5 keys per email (prevent abuse)
    try:
        table = get_table()

        # Scan for existing keys by this email (not ideal at scale, fine for competition)
        scan_response = table.scan(
            FilterExpression="email = :email AND is_active = :active",
            ExpressionAttributeValues={
                ":email": email,
                ":active": True,
            },
            Select="COUNT",
        )
        existing_count = scan_response.get("Count", 0)

        if existing_count >= 5:
            return build_response(429, {
                "error": "KEY_LIMIT_REACHED",
                "message": f"Maximum 5 active API keys per email. You have {existing_count}.",
            })

    except Exception as e:
        logger.error(f"Error checking existing keys: {traceback.format_exc()}")
        return build_response(500, {
            "error": "SERVICE_UNAVAILABLE",
            "message": "Unable to validate key limit. Try again.",
        })

    # Generate the API key
    try:
        raw_key = "tl_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Store in DynamoDB — only the hash, NEVER the raw key
        item = {
            "api_key_hash": key_hash,
            "owner": owner,
            "email": email,
            "use_case": use_case or "unspecified",
            "created_at": int(time.time()),
            "is_active": True,
            "permissions": ["verify", "documents", "analytics"],
            "rate_limit": 1000,
            "usage_count": 0,
        }

        table.put_item(Item=item)

        logger.info(f"API key created for owner={owner} email={email}")

        return build_response(201, {
            "api_key": raw_key,
            "owner": owner,
            "permissions": item["permissions"],
            "rate_limit": item["rate_limit"],
            "message": "API key created. Save it now — it cannot be retrieved again.",
        })

    except Exception as e:
        logger.error(f"Error creating API key: {traceback.format_exc()}")
        return build_response(500, {
            "error": "KEY_GENERATION_FAILED",
            "message": "Failed to generate API key. Try again.",
        })
