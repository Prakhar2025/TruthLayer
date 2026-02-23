"""AWS Lambda handler for analytics endpoints."""

import json
import time
import logging
import traceback
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_verifications_table = None


def get_table():
    """Get DynamoDB Verifications table (lazy init)."""
    global _verifications_table
    if _verifications_table is None:
        import os
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table_name = os.environ.get("VERIFICATIONS_TABLE", "TruthLayerVerifications")
        _verifications_table = dynamodb.Table(table_name)
        logger.info(f"Connected to DynamoDB table: {table_name}")
    return _verifications_table


def build_response(status_code, body):
    """Build API Gateway response with CORS."""
    return {
        "statusCode": status_code,
        "body": json.dumps(body, default=str),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        }
    }


def handler(event, context):
    """
    Lambda handler for GET /analytics

    Returns aggregated verification statistics.
    """
    if event.get("httpMethod") == "OPTIONS":
        return build_response(200, {"message": "OK"})

    try:
        query_params = event.get("queryStringParameters") or {}
        action = query_params.get("action", "summary")

        if action == "summary":
            return _get_summary()
        elif action == "recent":
            return _get_recent(query_params)
        elif action == "trends":
            return _get_trends(query_params)
        else:
            return build_response(400, {
                "error": "INVALID_ACTION",
                "message": f"Unknown action: {action}. Use: summary, recent, trends"
            })

    except Exception as e:
        logger.error(f"Analytics error: {traceback.format_exc()}")
        return build_response(500, {
            "error": "INTERNAL_ERROR",
            "message": "An internal error occurred"
        })


def _get_summary():
    """Get overall verification statistics."""
    table = get_table()

    # Scan all verifications (fine for free tier volume)
    response = table.scan()
    items = response.get("Items", [])

    total = len(items)
    if total == 0:
        return build_response(200, {
            "total_verifications": 0,
            "total_claims": 0,
            "avg_latency_ms": 0,
            "accuracy_breakdown": {
                "verified": 0,
                "uncertain": 0,
                "unsupported": 0
            },
            "verification_rate": 0
        })

    total_claims = 0
    total_verified = 0
    total_uncertain = 0
    total_unsupported = 0
    total_latency = 0

    for item in items:
        summary = item.get("summary", {})
        v = int(summary.get("verified", 0))
        u = int(summary.get("uncertain", 0))
        us = int(summary.get("unsupported", 0))

        total_verified += v
        total_uncertain += u
        total_unsupported += us
        total_claims += v + u + us

        latency = float(item.get("latency_ms", 0))
        total_latency += latency

    avg_latency = round(total_latency / total, 2) if total > 0 else 0
    verification_rate = round(
        (total_verified / total_claims * 100) if total_claims > 0 else 0, 2
    )

    return build_response(200, {
        "total_verifications": total,
        "total_claims": total_claims,
        "avg_latency_ms": avg_latency,
        "accuracy_breakdown": {
            "verified": total_verified,
            "uncertain": total_uncertain,
            "unsupported": total_unsupported
        },
        "verification_rate": verification_rate
    })


def _get_recent(query_params):
    """Get recent verifications."""
    limit = min(int(query_params.get("limit", "20")), 50)

    table = get_table()
    response = table.scan(Limit=limit)
    items = response.get("Items", [])

    # Sort by timestamp descending
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)

    verifications = []
    for item in items[:limit]:
        verifications.append({
            "verification_id": item.get("verification_id"),
            "summary": item.get("summary", {}),
            "latency_ms": float(item.get("latency_ms", 0)),
            "created_at": item.get("created_at", 0),
            "total_claims": int(item.get("total_claims", 0)),
        })

    return build_response(200, {
        "verifications": verifications,
        "count": len(verifications)
    })


def _get_trends(query_params):
    """Get verification trends over time."""
    days = min(int(query_params.get("days", "7")), 30)

    table = get_table()
    response = table.scan()
    items = response.get("Items", [])

    cutoff = int(time.time()) - (days * 86400)

    # Group by day
    daily_stats = {}
    for item in items:
        created_at = int(item.get("created_at", 0))
        if created_at < cutoff:
            continue

        # Group by date string
        day_key = time.strftime("%Y-%m-%d", time.gmtime(created_at))

        if day_key not in daily_stats:
            daily_stats[day_key] = {
                "date": day_key,
                "verifications": 0,
                "verified": 0,
                "uncertain": 0,
                "unsupported": 0,
                "total_latency": 0
            }

        daily_stats[day_key]["verifications"] += 1
        summary = item.get("summary", {})
        daily_stats[day_key]["verified"] += int(summary.get("verified", 0))
        daily_stats[day_key]["uncertain"] += int(summary.get("uncertain", 0))
        daily_stats[day_key]["unsupported"] += int(summary.get("unsupported", 0))
        daily_stats[day_key]["total_latency"] += float(item.get("latency_ms", 0))

    # Calculate averages and sort
    trends = []
    for stats in sorted(daily_stats.values(), key=lambda x: x["date"]):
        if stats["verifications"] > 0:
            stats["avg_latency_ms"] = round(
                stats["total_latency"] / stats["verifications"], 2
            )
        else:
            stats["avg_latency_ms"] = 0
        del stats["total_latency"]
        trends.append(stats)

    return build_response(200, {
        "trends": trends,
        "days": days
    })
