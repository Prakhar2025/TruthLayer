"""API key validation for TruthLayer Lambda handlers."""

import hashlib
import os
import logging

logger = logging.getLogger(__name__)

_api_keys_table = None


def _get_api_keys_table():
    """Lazy-init DynamoDB ApiKeys table (reused across warm invocations)."""
    global _api_keys_table
    if _api_keys_table is None:
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("APIKEYS_TABLE", "TruthLayerApiKeys")
        _api_keys_table = dynamodb.Table(table_name)
    return _api_keys_table


def validate_api_key(event):
    """
    Validate the x-api-key header against DynamoDB.

    Returns:
        (True, None) if valid
        (False, error_response_dict) if invalid
    """
    # Extract key from headers (API Gateway lowercases header names)
    headers = event.get("headers") or {}
    api_key = (
        headers.get("x-api-key")
        or headers.get("X-Api-Key")
        or headers.get("X-API-Key")
        or ""
    ).strip()

    if not api_key:
        logger.warning("Request missing x-api-key header")
        return False, {
            "statusCode": 401,
            "body": '{"error": "UNAUTHORIZED", "message": "API key required. Include x-api-key header."}',
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            }
        }

    # Hash and look up in DynamoDB
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    try:
        table = _get_api_keys_table()
        response = table.get_item(Key={"api_key_hash": key_hash})
        item = response.get("Item")

        if not item:
            logger.warning(f"API key not found: hash={key_hash[:16]}...")
            return False, {
                "statusCode": 401,
                "body": '{"error": "UNAUTHORIZED", "message": "Invalid API key."}',
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                }
            }

        if not item.get("is_active", False):
            logger.warning(f"Inactive API key used: hash={key_hash[:16]}...")
            return False, {
                "statusCode": 403,
                "body": '{"error": "FORBIDDEN", "message": "API key is inactive."}',
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                }
            }

        # Check rate limit
        usage_count = int(item.get("usage_count", 0))
        rate_limit = int(item.get("rate_limit", 1000))
        if usage_count >= rate_limit:
            logger.warning(
                f"Rate limit exceeded for owner={item.get('owner', 'unknown')}: "
                f"{usage_count}/{rate_limit}"
            )
            return False, {
                "statusCode": 429,
                "body": '{"error": "RATE_LIMITED", "message": "API key rate limit exceeded. Try again tomorrow."}',
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Retry-After": "3600",
                }
            }

        # Increment usage count atomically
        try:
            table.update_item(
                Key={"api_key_hash": key_hash},
                UpdateExpression="SET usage_count = if_not_exists(usage_count, :zero) + :one",
                ExpressionAttributeValues={":zero": 0, ":one": 1},
            )
        except Exception as ue:
            # Non-fatal — don't block request if counter update fails
            logger.warning(f"Failed to increment usage_count: {ue}")

        logger.info(f"Valid API key for owner: {item.get('owner', 'unknown')} (usage: {usage_count + 1}/{rate_limit})")
        return True, None

    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        # Fail closed — if DynamoDB is down, deny access
        return False, {
            "statusCode": 503,
            "body": '{"error": "SERVICE_UNAVAILABLE", "message": "Authentication service unavailable."}',
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            }
        }
